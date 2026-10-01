#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publicar_facebook.py — Portal Júnior Arrais

Publica um post de foto na Página do Facebook do portal usando a Graph API
(POST /{page-id}/photos). Irmão do publicar_instagram.py: mesma arquitetura,
mesmas defesas, adaptado à API de Páginas.

Como no Instagram, a Meta NÃO recebe o arquivo: ela busca a arte numa URL
pública do GitHub Pages. A arte padrão é a 4:5 (1080x1350) do Instagram,
img/feed45/<slug>.png. O processador da fila passa --arte img/feedfb/<slug>.png
quando existe a versão do Facebook, com o selo "LINK NA LEGENDA" no lugar de
"LINK NOS STORIES" (ver gerar_arte_facebook.py). Se essa versão não entrar no ar
a tempo, o script publica com a arte do Instagram em vez de falhar.

CREDENCIAIS — nunca em arquivo, sempre em variável de ambiente:
    export FB_PAGE_ID="..."      # ID da Página do portal
    export FB_PAGE_TOKEN="..."   # token da PÁGINA (não o token de usuário)

    O IG_TOKEN do robô do Instagram NÃO serve aqui: a API do Instagram e a
    API de Páginas do Facebook são produtos diferentes da Meta.

Uso:
    python scripts/publicar_facebook.py --slug <slug> --legenda facebook/legendas/<slug>.txt
    python scripts/publicar_facebook.py --slug <slug> --legenda ... --arte img/feedfb/<slug>.png
    python scripts/publicar_facebook.py --slug <slug> --legenda ... --dry-run
    python scripts/publicar_facebook.py --checar-pagina     # diagnóstico, não publica

O --dry-run valida a arte e a legenda, mas NÃO publica. Não exige credenciais.

Códigos de saída (o processador da fila usa):
    0  publicado (ou dry-run/diagnóstico ok)
    1  erro comum — o item continua pendente e conta como falha
    3  a Meta bloqueou a página por spam (código 368) — a fila deve ser PAUSADA
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://graph.facebook.com/v23.0"
SITE = "https://portaljuniorarrais.com.br"
BASE_MATERIA = "https://portaljuniorarrais.com.br/noticias"
LIMITE_LEGENDA = 63206                 # limite de caracteres de um post no Facebook
MAX_BYTES = 8 * 1024 * 1024
TAMANHO_ARTE = (1080, 1350)

# Termos que não podem sair na legenda (comparação sem diferenciar maiúsculas).
# Promessa de gratuidade/garantia e chamada para WhatsApp/direct derrubam o
# alcance e chamam golpista para os comentários.
TERMOS_PROIBIDOS = ("grátis", "de graça", "gratuit", "garantid", "whatsapp", "direct")

# Falha de download da arte pela Meta: códigos que merecem nova tentativa.
CODIGOS_DOWNLOAD = {324, 9004}
PAUSAS_DOWNLOAD = (30, 60, 120, 180)   # segundos entre as tentativas (~6,5 min)
ESPERA_ARTE_MAX = 600                  # até 10 min esperando a arte entrar no ar

PERMISSOES = ("pages_manage_posts", "pages_read_engagement", "pages_show_list")

SAIDA_PAUSAR_FILA = 3


def mascarar(texto):
    """Troca o token por *** em qualquer texto que vá para a tela ou para o log."""
    texto = str(texto)
    tok = os.environ.get("FB_PAGE_TOKEN", "")
    if tok:
        texto = texto.replace(tok, "***")
    return texto


def sair(msg, codigo=1):
    print(mascarar(msg), file=sys.stderr)
    sys.exit(codigo)


class ErroAPI(Exception):
    """Erro devolvido pela Graph API, com o JSON da Meta já decodificado."""

    def __init__(self, codigo_http, metodo, caminho, detalhe):
        self.codigo_http = codigo_http
        self.detalhe = mascarar(detalhe)
        try:
            self.erro = json.loads(detalhe).get("error", {})
        except Exception:
            self.erro = {}
        super().__init__(mascarar(
            f"Erro da API ({codigo_http}) em {metodo} {caminho}:\n{self.detalhe}"))

    @property
    def codigo(self):
        return self.erro.get("code")

    def falha_de_download(self):
        msg = str(self.erro.get("message", "")).lower()
        return (self.codigo in CODIGOS_DOWNLOAD
                or "download" in msg or "fetch" in msg)

    def explicacao(self):
        """Explica em português o que fazer nos erros conhecidos."""
        c = self.codigo
        if c == 190:
            return ("Token inválido ou vencido (código 190). Gere um token novo da "
                    "PÁGINA (GET /me/accounts com um token de usuário de longa "
                    "duração) e atualize o secret FB_PAGE_TOKEN.")
        if c in (200, 10):
            return (f"Permissão faltando no app (código {c}). O token precisa de "
                    "pages_manage_posts (e de pages_read_engagement e "
                    "pages_show_list). Peça as permissões no app da Meta e gere "
                    "o token da página de novo.")
        if c == 368:
            return ("A Meta bloqueou a página temporariamente por ação considerada "
                    "spam (código 368). A fila deve ficar PAUSADA: espere o "
                    "bloqueio passar, confira os avisos na página e só então "
                    "retome.")
        if c in (4, 17, 32):
            return (f"Limite de chamadas da API atingido (código {c}). Nada a "
                    "corrigir: o robô tenta de novo nas próximas execuções.")
        return ""


class ArteIndisponivel(Exception):
    """A arte não ficou acessível publicamente dentro do tempo de espera."""


def env(nome):
    v = os.environ.get(nome)
    if not v:
        sair(f"Falta a variável de ambiente {nome}. "
             f"Defina com: export {nome}=\"...\" (nunca grave o token em arquivo).")
    return v


def chamar(caminho, dados=None, metodo="GET"):
    """Chamada à API. Devolve o JSON decodificado ou levanta ErroAPI."""
    url = f"{API}/{caminho}"
    corpo = None
    if metodo == "POST":
        corpo = urllib.parse.urlencode(dados or {}).encode()
    elif dados:
        url += "?" + urllib.parse.urlencode(dados)
    req = urllib.request.Request(url, data=corpo, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode(errors="replace")
        raise ErroAPI(e.code, metodo, caminho, detalhe)


def baixar_arte(url):
    """Baixa a arte, esperando o GitHub Pages terminar o build se ainda não estiver no ar.

    Cada checagem leva ?v=<timestamp> para furar cache velho de CDN.
    """
    inicio = time.time()
    tentativa = 0
    while True:
        tentativa += 1
        url_teste = f"{url}?v={int(time.time())}"
        try:
            req = urllib.request.Request(url_teste, method="GET",
                                         headers={"Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=30) as r:
                status = r.status
                tipo = r.headers.get("Content-Type", "")
                dados = r.read()
            if status != 200:
                raise ValueError(f"HTTP {status}")
            if not tipo.startswith("image/"):
                raise ValueError(f"resposta não é imagem (Content-Type: {tipo})")
            if tentativa > 1:
                print(f"  arte no ar após {int(time.time() - inicio)} s de espera")
            return dados, tipo
        except Exception as e:
            if time.time() - inicio >= ESPERA_ARTE_MAX:
                raise ArteIndisponivel(f"A arte não está acessível publicamente: {url}\n{e}")
            print(f"  arte ainda não acessível ({e}); nova checagem em 30 s...")
            time.sleep(30)


def conferir_imagem(url):
    """Confere que a arte está pública, é imagem, cabe em 8 MB e mede 1080x1350."""
    dados, tipo = baixar_arte(url)

    if len(dados) > MAX_BYTES:
        sair(f"Arte com {len(dados)/1e6:.1f} MB — o limite da Meta é 8 MB.")

    try:
        from PIL import Image
        import io
        w, h = Image.open(io.BytesIO(dados)).size
        if (w, h) != TAMANHO_ARTE:
            sair(f"Arte com {w}x{h}; o esperado é {TAMANHO_ARTE[0]}x{TAMANHO_ARTE[1]} "
                 f"(4:5). Gere a arte com gerar_post_feed.py --formato 4x5.")
        print(f"  imagem: {w}x{h}, {len(dados)/1024:.0f} KB, {tipo}")
    except ImportError:
        print(f"  imagem: {len(dados)/1024:.0f} KB, {tipo} "
              f"(Pillow ausente, medidas não conferidas)")


def conferir_legenda(slug, legenda):
    """Valida a legenda. Encerra com erro claro, sem publicar, se algo estiver fora."""
    if not legenda:
        sair("Legenda vazia.")
    if len(legenda) > LIMITE_LEGENDA:
        sair(f"Legenda com {len(legenda)} caracteres — o limite do Facebook é "
             f"{LIMITE_LEGENDA}.")
    link = f"{BASE_MATERIA}/{slug}.html"
    if link not in legenda:
        sair(f"A legenda não traz o link da matéria: {link}")
    baixa = legenda.lower()
    achados = [t for t in TERMOS_PROIBIDOS if t in baixa]
    if achados:
        sair(f"A legenda contém termo proibido: {', '.join(achados)}. "
             f"Corrija o arquivo de legenda; nada foi publicado.")
    print(f"Legenda.: {len(legenda)} caracteres, {legenda.count('#')} hashtags, "
          f"link da matéria presente")


def checar_pagina():
    """Diagnóstico: confirma página, token e permissões antes de tentar publicar."""
    token, pid = env("FB_PAGE_TOKEN"), env("FB_PAGE_ID")
    r = chamar(pid, {"fields": "id,name,link", "access_token": token})
    print("Página conectada:")
    print(f"  id.....: {r.get('id')}")
    print(f"  nome...: {r.get('name')}")
    print(f"  link...: {r.get('link')}")

    concedidas = None
    try:
        d = chamar("debug_token", {"input_token": token, "access_token": token})
        info = d.get("data", {})
        concedidas = set(info.get("scopes", []))
        print(f"  tipo do token: {info.get('type')}"
              + ("" if info.get("type") == "PAGE"
                 else "  <- ATENÇÃO: precisa ser token de PÁGINA"))
        print(f"  token válido.: {info.get('is_valid')}")
        exp = info.get("expires_at")
        print(f"  vence em.....: {'nunca' if not exp else time.strftime('%d/%m/%Y %H:%M UTC', time.gmtime(exp))}")
    except ErroAPI as e:
        print(f"  debug_token indisponível ({e.erro.get('message')}); tentando /me/permissions")
        try:
            d = chamar("me/permissions", {"access_token": token})
            concedidas = {p["permission"] for p in d.get("data", [])
                          if p.get("status") == "granted"}
        except ErroAPI as e2:
            print(f"  /me/permissions indisponível ({e2.erro.get('message')})")

    if concedidas is None:
        print("  Não consegui ler as permissões do token.")
        return 1
    faltando = False
    print("Permissões:")
    for p in PERMISSOES:
        ok = p in concedidas
        faltando |= not ok
        print(f"  {'OK   ' if ok else 'FALTA'} {p}")
    return 1 if faltando else 0


def escolher_arte(slug, arte):
    """Confere a arte pedida; se ela não entrar no ar, cai para a do Instagram."""
    padrao = f"img/feed45/{slug}.png"
    arte = (arte or padrao).lstrip("/")
    url = f"{SITE}/{arte}"
    print(f"Arte....: {url}")
    try:
        conferir_imagem(url)
        return url
    except ArteIndisponivel as e:
        if arte == padrao:
            sair(str(e))
        print(f"  {e}\n  usando a arte do Instagram no lugar")
    url = f"{SITE}/{padrao}"
    print(f"Arte....: {url}")
    try:
        conferir_imagem(url)
    except ArteIndisponivel as e:
        sair(str(e))
    return url


def publicar(slug, legenda, arte=None, dry_run=False):
    url = escolher_arte(slug, arte)
    print(f"  arte usada: {url}")

    legenda = legenda.strip()
    conferir_legenda(slug, legenda)

    if dry_run:
        print("\n--- DRY-RUN: nada foi publicado ---")
        print(legenda)
        return 0

    token, pid = env("FB_PAGE_TOKEN"), env("FB_PAGE_ID")
    print("\npublicando na página...")
    r = enviar_foto(pid, token, url, legenda)
    print(f"  foto: {r.get('id')}")
    post_id = r.get("post_id") or r.get("id")
    print(f"  post: {post_id}")
    print(f"  link: https://www.facebook.com/{post_id}")
    return 0


def enviar_foto(pid, token, url, legenda):
    """Publica a foto. Se a Meta não conseguir baixar a arte, tenta de novo."""
    tentativas = len(PAUSAS_DOWNLOAD) + 1
    for n in range(1, tentativas + 1):
        # a partir da 2ª tentativa, ?v= muda a URL e fura cache velho de CDN
        url_envio = url if n == 1 else f"{url}?v={int(time.time())}"
        dados = {"url": url_envio, "message": legenda, "published": "true",
                 "access_token": token}
        try:
            return chamar(f"{pid}/photos", dados, "POST")
        except ErroAPI as e:
            if not e.falha_de_download() or n == tentativas:
                raise
            pausa = PAUSAS_DOWNLOAD[n - 1]
            print(f"  a Meta não conseguiu baixar a arte (tentativa {n}/{tentativas}, "
                  f"código {e.codigo}). Nova tentativa em {pausa} s...")
            time.sleep(pausa)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="slug da matéria (nome do arquivo em img/feed45/)")
    ap.add_argument("--legenda", help="arquivo .txt com a legenda")
    ap.add_argument("--arte", default=None,
                    help="caminho da arte no site (padrão: img/feed45/<slug>.png)")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="valida arte e legenda, mas não publica")
    ap.add_argument("--checar-pagina", dest="checar", action="store_true",
                    help="só diagnostica a página, o token e as permissões")
    a = ap.parse_args()

    try:
        if a.checar:
            return checar_pagina()
        if not a.slug or not a.legenda:
            ap.error("--slug e --legenda são obrigatórios (ou use --checar-pagina)")
        if not os.path.exists(a.legenda):
            sair(f"Arquivo de legenda não encontrado: {a.legenda}")
        legenda = open(a.legenda, encoding="utf-8").read()
        return publicar(a.slug, legenda, a.arte, a.dry_run)
    except ErroAPI as e:
        print(str(e), file=sys.stderr)
        dica = e.explicacao()
        if dica:
            print(f"O que fazer: {dica}", file=sys.stderr)
        return SAIDA_PAUSAR_FILA if e.codigo == 368 else 1


if __name__ == "__main__":
    sys.exit(main())
