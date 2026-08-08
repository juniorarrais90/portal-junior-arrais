#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalizar_links.py — Portal Júnior Arrais

Elimina os links internos que apontam para `index.html`.

Por que: o GitHub Pages serve a home em duas URLs — `/` e `/index.html`. O
canonical já aponta para `/`, então não há duplicação de conteúdo, mas cada link
para `/index.html` convida o Googlebot a rastrear a URL secundária. Em site com
orçamento de rastreamento apertado, isso é desperdício. Em agosto de 2026 havia
319 links assim, e o Search Console registrava a home em "Página alternativa com
tag canônica adequada".

O que faz:
    noticias/*.html   href="../index.html"        -> href="../"
                      href="../index.html#videos" -> href="../#videos"
    raiz *.html       href="index.html"           -> href="/"
                      href="index.html#videos"    -> href="/#videos"

Só mexe em `href`. Não toca em canonical, Open Graph, JSON-LD nem sitemap, que
já usam a URL canônica com barra.

Idempotente: rodar de novo não muda nada.

Uso:
    python scripts/normalizar_links.py --dry-run
    python scripts/normalizar_links.py
"""

import argparse
import glob
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (regex, substituição) para as matérias em noticias/
REGRAS_NOTICIAS = [
    (re.compile(r'href="\.\./index\.html#'), 'href="../#'),
    (re.compile(r'href="\.\./index\.html"'), 'href="../"'),
]

# (regex, substituição) para as páginas da raiz
REGRAS_RAIZ = [
    (re.compile(r'href="index\.html#'), 'href="/#'),
    (re.compile(r'href="index\.html"'), 'href="/"'),
]


def aplicar(caminho, regras):
    with open(caminho, encoding="utf-8") as f:
        original = f.read()
    novo = original
    trocas = 0
    for padrao, destino in regras:
        novo, n = padrao.subn(destino, novo)
        trocas += n
    return original, novo, trocas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    alvos = []
    for c in sorted(glob.glob(os.path.join(RAIZ, "noticias", "*.html"))):
        alvos.append((c, REGRAS_NOTICIAS))
    for c in sorted(glob.glob(os.path.join(RAIZ, "*.html"))):
        alvos.append((c, REGRAS_RAIZ))

    total = 0
    arquivos = 0
    for caminho, regras in alvos:
        original, novo, trocas = aplicar(caminho, regras)
        if trocas:
            total += trocas
            arquivos += 1
            print(f"{os.path.relpath(caminho, RAIZ)}: {trocas} troca(s)")
            if not args.dry_run:
                with open(caminho, "w", encoding="utf-8") as f:
                    f.write(novo)

    print("\n=== RESUMO ===")
    print(f"links corrigidos: {total} em {arquivos} arquivo(s)")

    # Conferência final: não deve sobrar nenhum href para index.html.
    sobrando = []
    for caminho, _ in alvos:
        conteudo = open(caminho, encoding="utf-8").read()
        if re.search(r'href="[^"]*index\.html', conteudo):
            sobrando.append(os.path.relpath(caminho, RAIZ))
    if sobrando:
        print(f"\nATENÇÃO — ainda há href para index.html em {len(sobrando)} arquivo(s):")
        for s in sobrando:
            print("   ", s)
    else:
        print("nenhum href para index.html restante")

    if args.dry_run:
        print("\n(dry-run: nada foi gravado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
