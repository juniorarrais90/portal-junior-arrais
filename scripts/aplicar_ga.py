#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Garante que a tag do Google Analytics esteja em todas as paginas .html do portal.

A tag entra com o "modo consentimento" do Google: por padrao NADA e medido.
A medicao so comeca depois que a pessoa clica em Aceitar no aviso de cookies
(quem libera o consentimento e o site.js).

Roda junto com a rotina automatica, entao qualquer materia nova publicada sem a
tag e corrigida sozinha. Rodar a mao:  python3 scripts/aplicar_ga.py
"""
import os, re, sys

ID = "G-LHNP03K7G6"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INICIO = "<!-- Google Analytics (Portal Junior Arrais) -->"
FIM = "<!-- fim do Google Analytics -->"

BLOCO = """  %s
  <script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('consent', 'default', {
      'ad_storage': 'denied',
      'ad_user_data': 'denied',
      'ad_personalization': 'denied',
      'analytics_storage': 'denied'
    });
    try {
      if (localStorage.getItem('pja-cookies') === 'ok') {
        gtag('consent', 'update', {
          'ad_storage': 'granted',
          'ad_user_data': 'granted',
          'ad_personalization': 'granted',
          'analytics_storage': 'granted'
        });
      }
    } catch (e) {}
    gtag('js', new Date());
    gtag('config', '%s');
  </script>
  %s
""" % (INICIO, ID, ID, FIM)


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
        original = h
        if INICIO in h and FIM in h:
            antes, resto = h.split(INICIO, 1)
            _, depois = resto.split(FIM, 1)
            h = antes + BLOCO.strip() + depois
        elif INICIO in h:
            # versao antiga da tag, sem marcador de fim: remove e reinsere
            h = re.sub(re.escape(INICIO) + r".*?</script>\s*</head>", "</head>", h, flags=re.S)
            h = h.replace("</head>", BLOCO + "</head>", 1)
        elif "</head>" in h:
            h = h.replace("</head>", BLOCO + "</head>", 1)
        else:
            print("sem </head>, pulando: " + os.path.relpath(caminho, RAIZ))
            continue
        if h != original:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(h)
            mexidos.append(os.path.relpath(caminho, RAIZ))
    print("Tag atualizada em %d pagina(s)." % len(mexidos))
    for m in mexidos:
        print("  - " + m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
