#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Garante que a tag do Google Analytics esteja em todas as paginas .html do portal.
Roda junto com a rotina automatica, entao qualquer materia nova publicada sem a
tag e corrigida sozinha. Rodar a mao:  python3 scripts/aplicar_ga.py
"""
import os, sys

ID = "G-LHNP03K7G6"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG = """  <!-- Google Analytics (Portal Junior Arrais) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', '%s');
  </script>
""" % (ID, ID)


def paginas():
    for pasta, _, arquivos in os.walk(RAIZ):
        if os.sep + "." in pasta:
            continue
        for a in arquivos:
            if a.endswith(".html"):
                yield os.path.join(pasta, a)


def main():
    mexidos = []
    for caminho in paginas():
        with open(caminho, encoding="utf-8") as f:
            h = f.read()
        if ID in h:
            continue
        if "</head>" not in h:
            print("sem </head>, pulando: " + os.path.relpath(caminho, RAIZ))
            continue
        h = h.replace("</head>", TAG + "</head>", 1)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(h)
        mexidos.append(os.path.relpath(caminho, RAIZ))
    print("Tag aplicada em %d pagina(s)." % len(mexidos))
    for m in mexidos:
        print("  - " + m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
