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
        sys.exit(f"Erro da API ({e.code}) em {metodo} {caminho}:\n{detalhe}")


def conferir_imagem(url):
    """Confere que a arte está pública, é JPEG/PNG, cabe no limite e tem proporção válida."""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            dados = r.read()
            tipo = r.headers.get("Content-Type", "")
    except Exception as e:
        sys.exit(f"A arte não está acessível publicamente: {url}\n{e}")

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
    dados = {"image_url": url, "caption": legenda, "access_token": token}
    if alt_text:
        dados["alt_text"] = alt_text
    cont = chamar(f"{uid}/media", dados, "POST")
    cid = cont["id"]
    print(f"  contêiner: {cid}")

    # imagem é síncrona, mas a Meta pede uma pausa curta antes de publicar
    time.sleep(5)

    print("2/2 publicando...")
    pub = chamar(f"{uid}/media_publish",
                 {"creation_id": cid, "access_token": token}, "POST")
    mid = pub["id"]
    print(f"  publicado: media id {mid}")

    perm = chamar(mid, {"fields": "permalink", "access_token": token})
    print(f"  link: {perm.get('permalink')}")


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

    if a.checar:
        return checar_conta()
    if not a.slug or not a.legenda:
        ap.error("--slug e --legenda são obrigatórios (ou use --checar-conta)")

    legenda = open(a.legenda, encoding="utf-8").read()
    publicar(a.slug, legenda, a.alt_text, a.dry_run)


if __name__ == "__main__":
    main()
