#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aplicar_noindex_agendado.py — Portal Júnior Arrais

Lê data/noindex-agendado.json e, para cada matéria cuja data "a_partir_de" já
chegou (horário de Brasília), insere <meta name="robots" content="noindex, follow">
no <head> e tira a URL do sitemap.xml. Marca o item com "aplicado_em".

Contexto: revisão do AdSense (12/10/2026). Matéria de prazo vencido é conteúdo
de baixo valor para o Google; com noindex ela continua no ar para quem tem o
link, mas deixa de contar na avaliação do site. Depois de rodar, gerar
o "Leia também" de novo (scripts/gerar_relacionadas.py pula páginas com noindex).

Uso:
    python scripts/aplicar_noindex_agendado.py            # aplica o que venceu
    python scripts/aplicar_noindex_agendado.py --dry-run  # só mostra
Sai com código 0 sempre; imprime "MUDOU" quando alterou algum arquivo.
"""
import argparse
import datetime as dt
import json
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENDA = os.path.join(RAIZ, "data", "noindex-agendado.json")
SITEMAP = os.path.join(RAIZ, "sitemap.xml")
META = '  <meta name="robots" content="noindex, follow">\n'


def hoje_brasilia():
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).date().isoformat()


def ler(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return f.read()


def gravar(caminho, texto):
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.write(texto)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    agenda = json.loads(ler(AGENDA))
    hoje = hoje_brasilia()
    sitemap = ler(SITEMAP)
    mudou = False

    for item in agenda["itens"]:
        if item.get("aplicado_em") or item["a_partir_de"] > hoje:
            continue
        slug = item["slug"]
        pagina = os.path.join(RAIZ, "noticias", slug + ".html")
        if not os.path.exists(pagina):
            print(f"AVISO: {slug}.html não existe; item ignorado.")
            continue
        html = ler(pagina)
        if 'name="robots"' not in html:
            novo = re.sub(r'(<meta name="viewport"[^>]*>\n)', lambda m: m.group(1) + META, html, count=1)
            if novo == html:
                print(f"AVISO: {slug} sem a meta viewport; noindex não inserido.")
                continue
            if not args.dry_run:
                gravar(pagina, novo)
        sitemap = re.sub(r'[ \t]*<url><loc>https://portaljuniorarrais\.com\.br/noticias/'
                         + re.escape(slug) + r'\.html</loc>.*?</url>\r?\n', '', sitemap)
        item["aplicado_em"] = hoje
        mudou = True
        print(f"noindex: {slug} (a partir de {item['a_partir_de']})")

    if mudou and not args.dry_run:
        gravar(SITEMAP, sitemap)
        gravar(AGENDA, json.dumps(agenda, ensure_ascii=False, indent=2) + "\n")
        print("MUDOU")
    elif not mudou:
        print(f"Nada a aplicar em {hoje}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
