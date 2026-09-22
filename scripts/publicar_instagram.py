#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publicar_instagram.py — Portal Júnior Arrais

Publica um post de feed no @portaljuniorarrais usando a API oficial da Meta
(Instagram Platform — Content Publishing).

Por que funciona sem upload de arquivo: a Meta NÃO recebe o arquivo. Ela busca
a imagem numa URL pública. As artes do portal já estão públicas no GitHub Pages
(https://portaljuniorarrais.com.br/img/feed45/<slug>.png), então basta apontar.

FORMATO — o detalhe que quebra tudo se for ignorado:
    A documentação da Meta aceita proporção de 4:5 a 1.91:1 para publicação.
    A arte padrão do portal é 3:4 (1080x1440), que fica FORA dessa faixa e sai
    recortada. Por isso publicamos a variante 4:5 (1080x1350), gerada com
    `gerar_post_feed.py --formato 4x5`, que preserva manchete, selo e CTA.

CREDENCIAIS — nunca em arquivo, sempre em variável de ambiente:
    export IG_TOKEN="..."      # token de acesso de longa duração
    export IG_USER_ID="..."    # ID da conta profissional do Instagram

Uso:
    python scripts/publicar_instagram.py --slug <slug> --legenda legenda.txt
    python scripts/publicar_instagram.py --slug <slug> --legenda legenda.txt --dry-run
    python scripts/publicar_instagram.py --checar-conta     # diagnóstico, não publica

O --dry-run monta tudo, valida a imagem e a legenda, mas NÃO publica. É o modo
recomendado para o primeiro teste.

FALHA DE DOWNLOAD DA ARTE — incidente de 22/09/2026 (run #5558):
    A Meta respondeu 400, código 9004 / subcódigo 2207052 ("Media download has
    failed. The media URI doesn't meet our requirements"), embora a arte
    estivesse no ar. O servidor da Meta não conseguiu baixar a imagem
    naquele instante — build do GitHub Pages ainda propagando ou CDN servindo
    cópia velha. O item só saiu 16 minutos depois, e o Júnior recebeu
    e-mail de falha e aviso no Telegram por um erro passageiro.
    Defesas:
      1. espera a arte ficar acessível (até ESPERA_ARTE_MAX s) em vez de
         desistir no primeiro 404;
      2. nessa falha de download, tenta criar o contêiner de novo, com
         pausa crescente e parâmetro ?v= na URL para furar cache de CDN;
      3. em vez de pausa fixa, espera o contêiner ficar FINISHED antes de
         publicar.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

API = "https://graph.instagram.com/v23.0"
BASE_IMG = "https://portaljuniorarrais.com.br/img/feed45"
LIMITE_LEGENDA = 2200
MAX_BYTES = 8 * 1024 * 1024

# Falha de download da arte pela Meta: códigos que merecem nova tentativa.
SUBCODIGOS_DOWNLOAD = {2207052, 2207003, 2207020, 2207026}
PAUSAS_DOWNLOAD = (30, 60, 120, 180)   # segundos entre as tentativas (~6,5 min)
ESPERA_ARTE_MAX = 600                  # até 10 min esperando a arte entrar no ar
ESPERA_CONTEINER_MAX = 60              # até 1 min esperando o contêiner ficar pronto


class ErroAPI(Exception):
    """Erro devolvido pela Graph API, com o JSON da Meta já decodificado."""

    def __init__(self, codigo_http, metodo, caminho, detalhe):
        self.codigo_http = codigo_http
        self.detalhe = detalhe
        try:
            self.erro = json.loads(detalhe).get("error", {})
        except Exception:
            self.erro = {}
        super().__init__(f"Erro da API ({codigo_http}) em {metodo} {caminho}:\n{detalhe}")

    def falha_de_download(self):
        e = self.erro
        return (e.get("error_subcode") in SUBCODIGOS_DOWNLOAD
                or (e.get("code") == 9004 and "download" in str(e).lower()))


def env(nome):
    v = os.environ.get(nome)
    if not v:
        sys.exit(f"Falta a variável de ambiente {nome}. "
                 f"Defina com: export {nome}=\"...\" (nunca grave o token em arquivo).")
    return v


def chamar(caminho, dados=None, metodo="GET"):
    """Chamada à API. Devolve o JSON decodificado ou encerra com a mensagem da Meta."""
    url = f"{API}/{caminho}"
    corpo = None
    if metodo == "POST":
        corpo = urllib.parse.urlencode(dados or {}).encode()
    else:
        if dados:
            url += "?" + urllib.parse.urlencode(dados)
    req = urllib.request.Request(url, data=corpo, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode(errors="replace")
        raise ErroAPI(e.code, metodo, caminho, detalhe)


def baixar_arte(url):
    """Baixa a arte, esperando o GitHub Pages terminar o build se ainda não estiver no ar."""
    inicio = time.time()
    tentativa = 0
    while True:
        tentativa += 1
        try:
            req = urllib.request.Request(url, method="GET",
                                         headers={"Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=30) as r:
                tipo = r.headers.get("Content-Type", "")
                dados = r.read()
            if not tipo.startswith("image/"):
                raise ValueError(f"resposta não é imagem (Content-Type: {tipo})")
            if tentativa > 1:
                print(f"  arte no ar após {int(time.time() - inicio)} s de espera")
            return dados, tipo
        except Exception as e:
            decorrido = time.time() - inicio
            if decorrido >= ESPERA_ARTE_MAX:
                sys.exit(f"A arte não está acessível publicamente: {url}\n{e}")
            print(f"  arte ainda não acessível ({e}); nova checagem em 30 s...")
            time.sleep(30)


def conferir_imagem(url):
    """Confere que a arte está pública, é JPEG/PNG, cabe no limite e tem proporção válida."""
    dados, tipo = baixar_arte(url)

    if len(dados) > MAX_BYTES:
        sys.exit(f"Arte com {len(dados)/1e6:.1f} MB — o limite da Meta é 8 MB.")

    try:
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(dados))
        w, h = im.size
        prop = w / h
        if not (0.8 <= prop <= 1.91):
            sys.exit(f"Proporção {w}x{h} ({prop:.2f}) fora da faixa aceita pela API "
                     f"(0.8 a 1.91). Gere a arte com --formato 4x5.")
        print(f"  imagem: {w}x{h} ({prop:.2f}), {len(dados)/1024:.0f} KB, {tipo}")
    except ImportError:
        print(f"  imagem: {len(dados)/1024:.0f} KB, {tipo} (PIL ausente, proporção não conferida)")
    return True


def checar_conta():
    """Diagnóstico: confirma token, conta e permissão antes de tentar publicar."""
    token, uid = env("IG_TOKEN"), env("IG_USER_ID")
    r = chamar(uid, {"fields": "id,username,account_type", "access_token": token})
    print("Conta conectada:")
    print(f"  id............: {r.get('id')}")
    print(f"  username......: @{r.get('username')}")
    print(f"  tipo de conta.: {r.get('account_type')}")
    if r.get("account_type") not in ("BUSINESS", "MEDIA_CREATOR", "CREATOR"):
        print("  ATENÇÃO: a publicação por API exige conta profissional "
              "(Empresa ou Criador).")
    lim = chamar(f"{uid}/content_publishing_limit",
                 {"fields": "quota_usage,config", "access_token": token})
    print(f"  cota 24h......: {json.dumps(lim.get('data', []), ensure_ascii=False)}")


def publicar(slug, legenda, alt_text=None, dry_run=False):
    token, uid = env("IG_TOKEN"), env("IG_USER_ID")
    url = f"{BASE_IMG}/{slug}.png"

    print(f"Arte....: {url}")
    conferir_imagem(url)

    legenda = legenda.strip()
    print(f"Legenda.: {len(legenda)} caracteres, "
          f"{legenda.count('#')} hashtags")
    if len(legenda) > LIMITE_LEGENDA:
        sys.exit(f"Legenda com {len(legenda)} caracteres — o limite do Instagram é {LIMITE_LEGENDA}.")
    if legenda.count("#") > 5:
        sys.exit("Mais de 5 hashtags — regra do portal.")

    if dry_run:
        print("\n--- DRY-RUN: nada foi publicado ---")
        print(legenda)
        return

    print("\n1/2 criando o contêiner...")
    cid = criar_conteiner(uid, token, url, legenda, alt_text)
    print(f"  contêiner: {cid}")
    esperar_conteiner(cid, token)

    print("2/2 publicando...")
    pub = chamar(f"{uid}/media_publish",
                 {"creation_id": cid, "access_token": token}, "POST")
    mid = pub["id"]
    print(f"  publicado: media id {mid}")

    perm = chamar(mid, {"fields": "permalink", "access_token": token})
    print(f"  link: {perm.get('permalink')}")


def criar_conteiner(uid, token, url, legenda, alt_text):
    """Cria o contêiner. Se a Meta não conseguir baixar a arte, tenta de novo."""
    tentativas = len(PAUSAS_DOWNLOAD) + 1
    for n in range(1, tentativas + 1):
        # a partir da 2ª tentativa, ?v= muda a URL e fura cache velho de CDN
        url_envio = url if n == 1 else f"{url}?v={int(time.time())}"
        dados = {"image_url": url_envio, "caption": legenda, "access_token": token}
        if alt_text:
            dados["alt_text"] = alt_text
        try:
            return chamar(f"{uid}/media", dados, "POST")["id"]
        except ErroAPI as e:
            if not e.falha_de_download() or n == tentativas:
                raise
            pausa = PAUSAS_DOWNLOAD[n - 1]
            print(f"  a Meta não conseguiu baixar a arte (tentativa {n}/{tentativas}, "
                  f"subcódigo {e.erro.get('error_subcode')}). Nova tentativa em {pausa} s...")
            time.sleep(pausa)


def esperar_conteiner(cid, token):
    """Espera o contêiner ficar FINISHED. Se a consulta falhar, segue como antes."""
    inicio = time.time()
    while True:
        time.sleep(5)
        try:
            st = chamar(cid, {"fields": "status_code", "access_token": token})
        except ErroAPI as e:
            print(f"  não consegui consultar o contêiner, seguindo: {e.erro.get('message')}")
            return
        codigo = st.get("status_code")
        if codigo in (None, "FINISHED", "PUBLISHED"):
            return
        if codigo in ("ERROR", "EXPIRED"):
            sys.exit(f"Contêiner {cid} com status {codigo}: {json.dumps(st, ensure_ascii=False)}")
        if time.time() - inicio >= ESPERA_CONTEINER_MAX:
            print(f"  contêiner ainda {codigo} após {ESPERA_CONTEINER_MAX} s; tentando publicar")
            return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="slug da matéria (nome do arquivo em img/feed45/)")
    ap.add_argument("--legenda", help="arquivo .txt com a legenda")
    ap.add_argument("--alt-text", dest="alt_text", default=None,
                    help="texto alternativo da imagem (acessibilidade)")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="monta e valida, mas não publica")
    ap.add_argument("--checar-conta", dest="checar", action="store_true",
                    help="só diagnostica a conta e a cota")
    a = ap.parse_args()

    try:
        if a.checar:
            return checar_conta()
        if not a.slug or not a.legenda:
            ap.error("--slug e --legenda são obrigatórios (ou use --checar-conta)")

        legenda = open(a.legenda, encoding="utf-8").read()
        publicar(a.slug, legenda, a.alt_text, a.dry_run)
    except ErroAPI as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
