#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valida a estrutura do HTML do Portal Júnior Arrais antes de publicar.

Motivo de existir: em 15/08/2026 a home foi ao ar sem os </div> de fechamento
de .col-esq e .col-dir. O navegador aninhou o vídeo e a coluna lateral dentro
da primeira coluna e a home inteira ficou espremida em uma faixa estreita.
Os scripts de publicação recortam esses blocos com regex — este validador é a
rede de segurança que impede que um recorte errado chegue ao ar.

Uso:
    python3 scripts/validar_home.py            # valida index.html + todas as páginas
    python3 scripts/validar_home.py index.html # valida só os arquivos indicados

Sai com código 0 quando está tudo certo e 1 quando encontra problema.
Rodar SEMPRE antes do `git commit` da publicação.
"""

import sys
import glob
import os
import re
from html.parser import HTMLParser

VAZIAS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
# dentro de <svg> a marcação é XML (self-closing solto); não conferimos aninhamento lá
IGNORAR_DENTRO = {"svg"}


class Balanco(HTMLParser):
    """Confere se cada tag aberta tem o fechamento correspondente."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pilha = []
        self.erros = []
        self.profundidade_svg = 0

    def handle_starttag(self, tag, attrs):
        if self.profundidade_svg:
            if tag in IGNORAR_DENTRO:
                self.profundidade_svg += 1
            return
        if tag in IGNORAR_DENTRO:
            self.profundidade_svg = 1
            return
        if tag in VAZIAS:
            return
        self.pilha.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if self.profundidade_svg:
            if tag in IGNORAR_DENTRO:
                self.profundidade_svg -= 1
            return
        if tag in VAZIAS:
            return
        if self.pilha and self.pilha[-1][0] == tag:
            self.pilha.pop()
            return
        # fechamento fora de ordem: procura o par mais próximo na pilha
        for i in range(len(self.pilha) - 1, -1, -1):
            if self.pilha[i][0] == tag:
                abertas = self.pilha[i + 1:]
                nomes = ", ".join(f"<{t}> da linha {l}" for t, l in abertas)
                self.erros.append(
                    f"linha {self.getpos()[0]}: </{tag}> fechou antes de {nomes} "
                    f"— provavelmente falta um fechamento"
                )
                self.pilha = self.pilha[:i]
                return
        self.erros.append(
            f"linha {self.getpos()[0]}: </{tag}> sem abertura correspondente"
        )


def validar_balanceamento(caminho):
    html = open(caminho, encoding="utf-8").read()
    b = Balanco()
    b.feed(html)
    b.close()
    erros = list(b.erros)
    for tag, linha in b.pilha:
        erros.append(f"linha {linha}: <{tag}> aberta e nunca fechada")
    return erros


def validar_home(caminho="index.html"):
    """Confere as invariantes da seção de destaque da home."""
    html = open(caminho, encoding="utf-8").read()
    erros = []

    inicio = html.find('class="container destaque-3col"')
    if inicio == -1:
        return ["não encontrei a seção <section class=\"container destaque-3col\">"]
    fim = html.find("</section>", inicio)
    bloco = html[inicio:fim]

    abre = len(re.findall(r"<div\b", bloco))
    fecha = len(re.findall(r"</div>", bloco))
    if abre != fecha:
        erros.append(
            f"destaque-3col: {abre} <div> abertas e {fecha} </div> fechadas "
            f"— o grid de 3 colunas vai colapsar na coluna da esquerda"
        )

    for classe in ("col-esq", "col-video", "col-dir"):
        n = len(re.findall(r'<div class="%s"' % classe, bloco))
        if n != 1:
            erros.append(f"destaque-3col: esperava 1 div .{classe}, encontrei {n}")

    destaques = len(re.findall(r'class="mini-card grande"', bloco))
    if destaques != 2:
        erros.append(f"col-esq: esperava 2 destaques (mini-card grande), encontrei {destaques}")

    laterais = len(re.findall(r'class="lateral-item"', bloco))
    if laterais != 6:
        erros.append(f"col-dir: esperava 6 chamadas (lateral-item), encontrei {laterais}")

    # ordem das colunas dentro da section
    ordem = re.findall(r'<div class="(col-esq|col-video|col-dir)"', bloco)
    if ordem != ["col-esq", "col-video", "col-dir"]:
        erros.append(f"destaque-3col: ordem das colunas fora do padrão: {ordem}")

    # cards de #ultimas
    m = re.search(r'<section class="section" id="ultimas">(.*?)</section>', html, re.S)
    if m:
        cards = len(re.findall(r'<a class="card"', m.group(1)))
        if not 1 <= cards <= 6:
            erros.append(f"#ultimas: esperava de 1 a 6 cards, encontrei {cards}")
    else:
        erros.append("não encontrei a seção #ultimas")

    return erros


def main():
    alvos = sys.argv[1:]
    if not alvos:
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(raiz)
        alvos = sorted(glob.glob("*.html")) + sorted(glob.glob("noticias/*.html"))

    problemas = 0
    for caminho in alvos:
        erros = validar_balanceamento(caminho)
        if os.path.basename(caminho) == "index.html":
            erros += validar_home(caminho)
        if erros:
            problemas += 1
            print(f"\n[ERRO] {caminho}")
            for e in erros:
                print(f"   - {e}")

    total = len(alvos)
    if problemas:
        print(f"\n{problemas} de {total} arquivo(s) com problema. NÃO publicar assim.")
        return 1
    print(f"OK — {total} arquivo(s) validado(s), estrutura íntegra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
