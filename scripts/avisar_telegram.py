#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
avisar_telegram.py — Portal Júnior Arrais

Manda para o Telegram do Júnior um aviso com a ARTE DE STORY anexada, logo depois
de um post sair no feed. Serve de lembrete para ele publicar o story à mão com a
figurinha de link — que a API do Instagram não publica.

Uso como módulo:
    from avisar_telegram import avisar
    avisar(slug, titulo, link_post)

Uso direto (teste):
    python scripts/avisar_telegram.py --slug <slug> --titulo "..." --link "..."

Variáveis de ambiente: TG_TOKEN e TG_CHAT_ID.
Se faltarem, a função apenas avisa e segue — nunca derruba a publicação, porque
o aviso é acessório e o post no feed é o que importa.

Nota técnica: o multipart é montado à mão de propósito. Enviar legenda com
acentos e quebras de linha via curl -F embaralha o texto.
"""

import argparse
import json
import os
import sys
import urllib.request
import uuid

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_MATERIA = "https://portaljuniorarrais.com.br/noticias"


def _escapar(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def avisar(slug, titulo, link_post=None, arte=None):
    token = os.environ.get("TG_TOKEN")
    chat = os.environ.get("TG_CHAT_ID")
    if not token or not chat:
        print("Telegram não configurado (TG_TOKEN/TG_CHAT_ID). Aviso não enviado.")
        return False

    arte = arte or os.path.join(RAIZ, "img", "stories", f"{slug}.png")
    if not os.path.exists(arte):
        print(f"Arte de story não encontrada: {arte}. Aviso não enviado.")
        return False

    partes = [
        "<b>Post publicado no feed</b>",
        "",
        _escapar(titulo),
        "",
        "Story pronto — salve a imagem acima, poste e adicione a figurinha de link para:",
        f"{BASE_MATERIA}/{slug}.html",
    ]
    if link_post:
        partes += ["", f"Post no feed: {link_post}"]
    legenda = "\n".join(partes)

    b = uuid.uuid4().hex
    corpo = []
    for k, v in (("chat_id", chat), ("parse_mode", "HTML"), ("caption", legenda)):
        corpo.append(
            f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    corpo.append(
        f'--{b}\r\nContent-Disposition: form-data; name="photo"; '
        f'filename="{slug}.png"\r\nContent-Type: image/png\r\n\r\n'.encode())
    corpo.append(open(arte, "rb").read())
    corpo.append(f"\r\n--{b}--\r\n".encode())

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data=b"".join(corpo),
        headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=90))
    except Exception as e:
        print(f"Falha ao avisar no Telegram: {e}")
        return False

    if d.get("ok"):
        print("Aviso enviado no Telegram com a arte de story.")
        return True
    print(f"Telegram recusou: {d}")
    return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--titulo", required=True)
    ap.add_argument("--link", default=None)
    a = ap.parse_args()
    sys.exit(0 if avisar(a.slug, a.titulo, a.link) else 1)
