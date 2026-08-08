#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aplicar_links_contextuais.py — Portal Júnior Arrais

Transforma termos do CORPO da matéria em links para outra matéria do portal,
segundo o mapa em data/links-internos.json.

Complementa o bloco "Leia também" (scripts/gerar_relacionadas.py). A diferença:
link no meio do texto vale mais para o Google e para o leitor, porque a âncora
é a própria palavra-chave e o clique acontece no momento da dúvida.

SALVAGUARDAS — o texto editorial é intocável, o script só embrulha a palavra:

  1. mexe apenas dentro de <div class="artigo-conteudo">;
  2. só dentro de <p>; nunca em <h1>, <h2>, <ul>, <li>, <em>, <strong> isolado;
  3. NUNCA no primeiro parágrafo (o lead responde o essencial sem distração);
  4. nunca dentro de um <a> que já existe;
  5. não linka o parágrafo do disclaimer final;
  6. no máximo MAX_POR_MATERIA links por matéria (padrão 3);
  7. um link por destino, e só na PRIMEIRA ocorrência do termo;
  8. no máximo um link por parágrafo;
  9. não linka a própria matéria, nem destino bloqueado no campo "nao_em" do mapa
     (para termo que tem outro sentido naquela matéria);
 10. PREFERE destino que ainda não está no bloco "Leia também" (evita redundância);
 11. âncora mais específica ganha da mais genérica ("consignado do INSS" antes
     de "consignado");
 12. preserva exatamente o texto original — inclusive maiúsculas e acentos;
 13. teto de MAX_INLINKS links de entrada por destino, para não concentrar todos
     os links nas mesmas duas ou três matérias.

Idempotente: remove os links que ele mesmo criou (class="link-interno") antes
de reaplicar. Nunca toca em link escrito à mão.

Uso:
    python scripts/aplicar_links_contextuais.py --dry-run --verbose
    python scripts/aplicar_links_contextuais.py
    python scripts/aplicar_links_contextuais.py --max 2
    python scripts/aplicar_links_contextuais.py --limpar    # desfaz tudo
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_NOTICIAS = os.path.join(RAIZ, "noticias")
MAPA = os.path.join(RAIZ, "data", "links-internos.json")

MAX_POR_MATERIA = 3
MAX_INLINKS = 8
CLASSE = "link-interno"

RE_CORPO = re.compile(r'(<div class="artigo-conteudo">)(.*?)(\n      </div>)', re.S)
RE_PARAGRAFO = re.compile(r"<p>(.*?)</p>", re.S)
RE_LINK_NOSSO = re.compile(
    r'<a class="' + CLASSE + r'"[^>]*>(.*?)</a>', re.S)

# Trechos de parágrafo que nunca recebem link.
RE_DISCLAIMER = re.compile(r"Conteúdo informativo|não substitui orientação", re.I)


def carregar_mapa():
    with open(MAPA, encoding="utf-8") as f:
        dados = json.load(f)
    itens = []
    for d in dados["destinos"]:
        bloqueio = set(d.get("nao_em", []))
        for a in d["ancoras"]:
            itens.append((a, d["slug"], bloqueio))
    # Âncora mais longa primeiro: garante que a específica ganhe da genérica.
    itens.sort(key=lambda x: -len(x[0]))
    return itens


def limpar(html):
    """Desfaz os links criados por este script, devolvendo o texto puro."""
    return RE_LINK_NOSSO.sub(lambda m: m.group(1), html)


def destinos_do_leia_tambem(html):
    bloco = re.search(r"LEIA TAMBEM \(gerado.*?fim LEIA TAMBEM", html, re.S)
    if not bloco:
        return set()
    return {h[:-5] for h in re.findall(r'class="lt-link" href="([^"]+)"', bloco.group(0))}


def fatias_livres(texto):
    """Devolve os intervalos do parágrafo que estão fora de qualquer tag <a>."""
    ocupados = [(m.start(), m.end()) for m in re.finditer(r"<a\b.*?</a>", texto, re.S)]
    livres = []
    pos = 0
    for ini, fim in ocupados:
        if ini > pos:
            livres.append((pos, ini))
        pos = fim
    if pos < len(texto):
        livres.append((pos, len(texto)))
    return livres


def achar_ancora(paragrafo, ancora):
    """
    Posição da primeira ocorrência da âncora fora de tags e fora de links.
    Devolve (inicio, fim) ou None. Casa sem diferenciar maiúsculas, mas o
    trecho devolvido é o texto original.
    """
    padrao = re.compile(r"(?<![\wÀ-ÿ-])" + re.escape(ancora) + r"(?![\wÀ-ÿ])",
                        re.IGNORECASE)
    for ini, fim in fatias_livres(paragrafo):
        trecho = paragrafo[ini:fim]
        # Não casar dentro de tag HTML aberta (ex.: atributo).
        for m in padrao.finditer(trecho):
            abs_ini = ini + m.start()
            antes = paragrafo[:abs_ini]
            if antes.count("<") > antes.count(">"):
                continue
            return abs_ini, ini + m.end()
    return None


def processar(caminho, mapa, maximo, verbose, inlinks, teto):
    with open(caminho, encoding="utf-8") as f:
        original = f.read()

    slug = os.path.basename(caminho)[:-5]
    html = limpar(original)

    m = RE_CORPO.search(html)
    if not m:
        return original, [], "sem-corpo"

    abre, corpo, fecha = m.group(1), m.group(2), m.group(3)
    ja_no_leia_tambem = destinos_do_leia_tambem(html)

    paragrafos = list(RE_PARAGRAFO.finditer(corpo))
    aplicados = []
    usados = set()
    novo_corpo = corpo
    deslocamento = 0

    for indice, p in enumerate(paragrafos):
        if len(aplicados) >= maximo:
            break
        if indice == 0:            # salvaguarda 3: nunca no lead
            continue
        texto = p.group(1)
        if RE_DISCLAIMER.search(texto):
            continue

        # Passe 1: destino que ainda NÃO está no bloco "Leia também" — espalha mais.
        # Passe 2: se nada casou, aceita repetir um destino do "Leia também";
        #          redundância é melhor que parágrafo sem link.
        achado = None
        for passe in (1, 2):
            for ancora, destino, bloqueio in mapa:
                if destino == slug or destino in usados:
                    continue
                if slug in bloqueio:      # o termo tem outro sentido nesta matéria
                    continue
                if passe == 1 and destino in ja_no_leia_tambem:
                    continue
                if inlinks[destino] >= teto:   # salvaguarda 13
                    continue
                if not os.path.exists(os.path.join(DIR_NOTICIAS, destino + ".html")):
                    continue
                pos = achar_ancora(texto, ancora)
                if pos:
                    achado = (pos, destino)
                    break
            if achado:
                break

        if not achado:
            continue

        (ini, fim), destino = achado
        literal = texto[ini:fim]
        novo_texto = (texto[:ini]
                      + f'<a class="{CLASSE}" href="{destino}.html">{literal}</a>'
                      + texto[fim:])

        ini_abs = p.start(1) + deslocamento
        fim_abs = p.end(1) + deslocamento
        novo_corpo = novo_corpo[:ini_abs] + novo_texto + novo_corpo[fim_abs:]
        deslocamento += len(novo_texto) - len(texto)

        usados.add(destino)
        inlinks[destino] += 1
        aplicados.append((literal, destino, indice + 1))

    resultado = html[:m.start()] + abre + novo_corpo + fecha + html[m.end():]

    if verbose and aplicados:
        print(f"\n{slug}")
        for literal, destino, par in aplicados:
            print(f'    §{par}  "{literal}" -> {destino}')

    situacao = "igual" if resultado == original else ("aplicado" if aplicados else "limpo")
    return resultado, aplicados, situacao


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=MAX_POR_MATERIA)
    ap.add_argument("--teto", type=int, default=MAX_INLINKS,
                    help="máximo de links de entrada por matéria de destino")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--limpar", action="store_true", help="remove todos os links do script")
    args = ap.parse_args()

    arquivos = sorted(glob.glob(os.path.join(DIR_NOTICIAS, "*.html")))
    if not arquivos:
        print("Nenhuma matéria em noticias/", file=sys.stderr)
        return 1

    if args.limpar:
        n = 0
        for c in arquivos:
            o = open(c, encoding="utf-8").read()
            l = limpar(o)
            if l != o:
                n += 1
                if not args.dry_run:
                    open(c, "w", encoding="utf-8").write(l)
        print(f"links contextuais removidos de {n} matérias")
        return 0

    mapa = carregar_mapa()
    print(f"mapa: {len(mapa)} âncoras para "
          f"{len({d for _, d, _ in mapa})} matérias de destino")
    print(f"teto de {args.teto} links de entrada por destino, "
          f"máximo de {args.max} por matéria\n")

    # Da mais nova para a mais antiga: a matéria nova é a que circula, então ela
    # escolhe primeiro os destinos ainda abaixo do teto.
    def data_de(c):
        m = re.search(r'"datePublished"\s*:\s*"([0-9-]{10})"',
                      open(c, encoding="utf-8").read())
        return m.group(1) if m else "0000-00-00"

    ordem = sorted(arquivos, key=data_de, reverse=True)

    situacoes = Counter()
    inlinks = Counter()
    total = 0
    sem_nenhum = []

    for c in ordem:
        novo, aplicados, situacao = processar(c, mapa, args.max, args.verbose,
                                              inlinks, args.teto)
        situacoes[situacao] += 1
        total += len(aplicados)
        if not aplicados:
            sem_nenhum.append(os.path.basename(c)[:-5])
        if novo != open(c, encoding="utf-8").read() and not args.dry_run:
            open(c, "w", encoding="utf-8").write(novo)

    print("\n=== RESUMO ===")
    print(f"links contextuais criados: {total}")
    print(f"matérias com pelo menos 1 link: {len(arquivos) - len(sem_nenhum)} de {len(arquivos)}")
    print(f"média por matéria: {total/len(arquivos):.1f}")
    for k, v in situacoes.items():
        print(f"  {k}: {v}")

    if sem_nenhum:
        print(f"\nsem nenhum link contextual ({len(sem_nenhum)}):")
        for s in sem_nenhum:
            print("   ", s)

    print("\nmatérias mais apontadas:")
    for slug, n in inlinks.most_common(10):
        print(f"  {n:3d}  {slug}")

    if args.dry_run:
        print("\n(dry-run: nada foi gravado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
