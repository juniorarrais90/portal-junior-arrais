#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_relacionadas.py — Portal Júnior Arrais

Insere (ou atualiza) o bloco "Leia também" no fim de cada matéria de noticias/.

Objetivo de SEO: criar malha de links internos entre as matérias. Sem isso,
toda notícia é uma folha ligada apenas ao menu e ao noticias.html, e o Google
rastreia as do topo da lista e abandona o resto ("Detectada, mas não indexada").

Regras de escolha das relacionadas:
  1. tema em comum (Bolsa Família, BPC, INSS, FGTS...) vale mais que tudo;
  2. mesma categoria (chip) reforça;
  3. palavras raras em comum no título reforçam;
  4. matéria recente leva leve vantagem;
  5. PENALIDADE por links de entrada já recebidos — é o que faz as matérias
     esquecidas receberem link em vez de todo mundo apontar para as mesmas.

O bloco é delimitado por marcadores HTML, então rodar de novo apenas
reescreve o bloco. É idempotente e seguro rodar a cada publicação.

Uso:
    python scripts/gerar_relacionadas.py              # aplica
    python scripts/gerar_relacionadas.py --dry-run    # só mostra o que faria
    python scripts/gerar_relacionadas.py --n 4        # quantidade por matéria
"""

import argparse
import glob
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_NOTICIAS = os.path.join(RAIZ, "noticias")
DIR_IMG = os.path.join(RAIZ, "img")

INICIO = "<!-- LEIA TAMBEM (gerado por scripts/gerar_relacionadas.py) -->"
FIM = "<!-- fim LEIA TAMBEM -->"

# Temas do portal. A chave é o nome do tema; os valores são os radicais que,
# se aparecerem no slug ou no título, marcam a matéria com aquele tema.
TEMAS = {
    "bolsa-familia": ["bolsa-familia", "bolsa familia", "bolsa família", "auxilio brasil"],
    "cadunico": ["cadunico", "cadúnico", "cadastro unico", "cadastro único", "cras"],
    "bpc": ["bpc", "loas", "beneficio assistencial", "benefício assistencial", "auxilio-inclusao", "auxílio-inclusão"],
    "inss": ["inss", "aposentadoria", "aposentar", "pericia", "perícia", "auxilio-doenca",
             "auxílio-doença", "atestmed", "salario-maternidade", "salário-maternidade",
             "auxilio-reclusao", "auxílio-reclusão", "pensao", "pensão", "salario-familia",
             "salário-família", "consignado-inss", "revisao da vida toda", "revisão da vida toda"],
    "fgts": ["fgts", "saque-aniversario", "saque-aniversário", "abono-salarial", "abono salarial", "pis"],
    "gas-do-povo": ["gas-do-povo", "gás do povo", "vale-gas", "vale-gás", "botijao", "botijão"],
    "pe-de-meia": ["pe-de-meia", "pé-de-meia", "prouni", "encceja", "estudante", "escola"],
    "moradia": ["minha-casa-minha-vida", "minha casa minha vida", "moradia", "fghab", "habitacao", "habitação"],
    "energia": ["tarifa-social", "tarifa social", "conta-de-luz", "conta de luz", "bandeira", "luz do povo"],
    "trabalho": ["seguro-desemprego", "trabalhador", "clt", "carteira", "demissao", "demissão",
                 "assedio", "assédio", "frete", "emprego"],
    "credito": ["consignado", "emprestimo", "empréstimo", "desenrola", "divida", "dívida",
                "endividamento", "credito", "crédito", "poupanca", "poupança", "bets", "aposta"],
    "impostos": ["imposto-de-renda", "imposto de renda", "ir-2026", "restituicao", "restituição",
                 "isencao", "isenção", "receita"],
    "saude": ["farmacia-popular", "farmácia popular", "sus", "absorvente", "menstrual", "saude", "saúde"],
    "eleicoes": ["eleicoes", "eleições", "eleitoral", "biometria", "urna", "candidat"],
    "golpe": ["golpe", "falso", "fraude", "desconto-indevido", "descontos indevidos", "site falso"],
    "salario-minimo": ["salario-minimo", "salário mínimo", "salario minimo"],
    "idoso": ["idoso", "pessoa idosa", "id-jovem", "passagem"],
}

STOPWORDS = set("""
a as o os um uma uns umas de do da dos das em no na nos nas por para com sem sob sobre
e ou mas que se ao aos à às pelo pela pelos pelas ate até entre apos após como quando
onde qual quais quem cujo cuja mais menos muito muita ja já nao não sim tem ter tem-se
ser sera será sao são foi foram vai vao vão pode podem deve devem quanto quantos
novo nova novos novas todo toda todos todas outro outra este esta esse essa aquele aquela
seu sua seus suas meu minha isso isto aquilo agora hoje ontem amanha amanhã ano anos mes
meses dia dias de-verdade real mesmo mesma so só apenas ainda entao então porque pois
r$ reais mil milhoes milhões bilhoes bilhões por-cento
janeiro fevereiro marco março abril maio junho julho agosto setembro outubro novembro dezembro
2024 2025 2026 2027
""".split())


def sem_acento(txt):
    return "".join(c for c in unicodedata.normalize("NFD", txt)
                   if unicodedata.category(c) != "Mn")


def tokens(txt):
    base = sem_acento(txt.lower())
    base = re.sub(r"[^a-z0-9\s-]", " ", base)
    base = base.replace("-", " ")
    return {t for t in base.split() if len(t) > 3 and t not in STOPWORDS}


def desescapa(txt):
    """Converte as entidades HTML que o portal usa nos títulos."""
    ent = {
        "&aacute;": "á", "&eacute;": "é", "&iacute;": "í", "&oacute;": "ó", "&uacute;": "ú",
        "&acirc;": "â", "&ecirc;": "ê", "&ocirc;": "ô", "&atilde;": "ã", "&otilde;": "õ",
        "&ccedil;": "ç", "&Aacute;": "Á", "&Eacute;": "É", "&Iacute;": "Í", "&Oacute;": "Ó",
        "&Uacute;": "Ú", "&Acirc;": "Â", "&Ecirc;": "Ê", "&Ocirc;": "Ô", "&Atilde;": "Ã",
        "&Otilde;": "Õ", "&Ccedil;": "Ç", "&agrave;": "à", "&Agrave;": "À",
        "&middot;": "·", "&nbsp;": " ", "&amp;": "&", "&quot;": '"', "&#39;": "'",
    }
    for k, v in ent.items():
        txt = txt.replace(k, v)
    return txt


def escapa(txt):
    """Escapa o mínimo necessário para o texto entrar no HTML com segurança."""
    return (txt.replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;")
               .replace('"', "&quot;"))


def ler_materia(caminho):
    with open(caminho, encoding="utf-8") as f:
        html = f.read()

    slug = os.path.basename(caminho)[:-5]

    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    titulo = desescapa(re.sub(r"<[^>]+>", "", m.group(1)).strip()) if m else slug

    m = re.search(r'class="chip"[^>]*>(.*?)</span>', html, re.S)
    categoria = desescapa(re.sub(r"<[^>]+>", "", m.group(1)).strip()) if m else ""

    data = ""
    m = re.search(r'"datePublished"\s*:\s*"([0-9-]{10})"', html)
    if m:
        data = m.group(1)

    data_extenso = ""
    m = re.search(r'class="meta"[^>]*>(.*?)</div>', html, re.S)
    if m:
        texto_meta = desescapa(re.sub(r"<[^>]+>", " ", m.group(1)))
        m2 = re.search(r"(\d{1,2} de \w+\.? de \d{4})", texto_meta)
        if m2:
            data_extenso = m2.group(1)

    base = sem_acento((slug + " " + titulo).lower())
    temas = {nome for nome, chaves in TEMAS.items()
             if any(sem_acento(c.lower()) in base for c in chaves)}

    return {
        "slug": slug,
        "arquivo": caminho,
        "html": html,
        "titulo": titulo,
        "categoria": categoria,
        "data": data,
        "data_extenso": data_extenso,
        "temas": temas,
        "tokens": tokens(slug + " " + titulo),
        "capa": f"../img/{slug}.png" if os.path.exists(os.path.join(DIR_IMG, slug + ".png")) else None,
    }


def pontua(origem, alvo, inlinks):
    """Quanto 'alvo' combina com 'origem'. Maior é melhor."""
    if origem["slug"] == alvo["slug"]:
        return -999

    temas_comuns = origem["temas"] & alvo["temas"]
    score = 5.0 * len(temas_comuns)

    if origem["categoria"] and origem["categoria"] == alvo["categoria"]:
        score += 2.5

    score += 1.2 * len(origem["tokens"] & alvo["tokens"])

    # Recência: matéria mais nova é mais útil ao leitor e ao Google.
    if alvo["data"]:
        try:
            ordem = sorted(d for d in [alvo["data"]] if d)
            score += 0.4 if alvo["data"] >= "2026-08-01" else 0.0
        except Exception:
            pass

    # Equalização: quem já recebeu muito link perde prioridade.
    score -= 1.6 * inlinks.get(alvo["slug"], 0)

    return score


def escolher(materias, n):
    """Devolve {slug: [slugs relacionados]} distribuindo os links de entrada."""
    inlinks = defaultdict(int)
    resultado = {}

    # Da mais nova para a mais antiga: as novas puxam as antigas para cima.
    ordem = sorted(materias, key=lambda m: (m["data"], m["slug"]), reverse=True)

    for origem in ordem:
        candidatos = sorted(
            materias,
            key=lambda alvo: (-pontua(origem, alvo, inlinks), alvo["data"]),
        )
        escolhidos = []
        for alvo in candidatos:
            if alvo["slug"] == origem["slug"]:
                continue
            escolhidos.append(alvo["slug"])
            inlinks[alvo["slug"]] += 1
            if len(escolhidos) == n:
                break
        resultado[origem["slug"]] = escolhidos

    return resultado, inlinks


def montar_bloco(relacionadas):
    linhas = [INICIO,
              '      <aside class="leia-tambem" aria-label="Outras notícias do portal">',
              "        <h2>Leia também</h2>",
              '        <ul class="lt-lista">']
    for m in relacionadas:
        titulo = escapa(m["titulo"])
        href = f'{m["slug"]}.html'
        linhas.append('          <li class="lt-item">')
        linhas.append(f'            <a class="lt-link" href="{href}">')
        if m["capa"]:
            linhas.append(
                f'              <img class="lt-thumb" src="{m["capa"]}" alt="" loading="lazy" width="120" height="68">')
        linhas.append('              <span class="lt-texto">')
        if m["categoria"]:
            linhas.append(f'                <span class="lt-chip">{escapa(m["categoria"])}</span>')
        linhas.append(f"                <span class=\"lt-titulo\">{titulo}</span>")
        if m["data_extenso"]:
            linhas.append(f'                <span class="lt-data">{escapa(m["data_extenso"])}</span>')
        linhas.append("              </span>")
        linhas.append("            </a>")
        linhas.append("          </li>")
    linhas += ["        </ul>",
               '        <p class="lt-mais"><a href="../noticias.html">Ver todas as notícias do portal</a></p>',
               "      </aside>",
               FIM]
    return "\n".join(linhas)


def aplicar(html, bloco):
    """Insere ou substitui o bloco. Devolve (html_novo, situacao)."""
    if INICIO in html and FIM in html:
        novo = re.sub(re.escape(INICIO) + r".*?" + re.escape(FIM), lambda _: bloco, html, flags=re.S)
        return novo, ("igual" if novo == html else "atualizado")

    # Ponto de inserção preferido: antes da barra de compartilhamento.
    alvos = ['      <!-- COMPARTILHAR (Portal Junior Arrais) -->',
             '<!-- COMPARTILHAR (Portal Junior Arrais) -->',
             '<div class="share-bar">',
             '<!-- ADSENSE: espaço de anúncio dentro da matéria -->',
             '<div class="ad-slot">']
    for alvo in alvos:
        i = html.find(alvo)
        if i != -1:
            recuo = html[:i].rsplit("\n", 1)[-1]
            return html[:i - len(recuo)] + bloco + "\n\n" + recuo + html[i:], "inserido"

    # Último recurso: antes do fim do <article>.
    i = html.find("</article>")
    if i != -1:
        return html[:i] + bloco + "\n    " + html[i:], "inserido"

    return html, "sem-ponto-de-insercao"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4, help="relacionadas por matéria (padrão 4)")
    ap.add_argument("--dry-run", action="store_true", help="não grava, só relata")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    arquivos = sorted(glob.glob(os.path.join(DIR_NOTICIAS, "*.html")))
    if not arquivos:
        print("Nenhuma matéria encontrada em noticias/", file=sys.stderr)
        return 1

    materias = [ler_materia(c) for c in arquivos]
    por_slug = {m["slug"]: m for m in materias}

    escolhas, inlinks = escolher(materias, args.n)

    contagem = defaultdict(int)
    for m in materias:
        rel = [por_slug[s] for s in escolhas[m["slug"]]]
        bloco = montar_bloco(rel)
        novo, situacao = aplicar(m["html"], bloco)
        contagem[situacao] += 1

        if args.verbose:
            print(f"{m['slug']} [{situacao}]")
            for r in rel:
                print(f"    -> {r['slug']}")

        if situacao in ("inserido", "atualizado") and not args.dry_run:
            with open(m["arquivo"], "w", encoding="utf-8") as f:
                f.write(novo)

    print("\n=== RESUMO ===")
    for k in ("inserido", "atualizado", "igual", "sem-ponto-de-insercao"):
        if contagem[k]:
            print(f"{k}: {contagem[k]}")

    sem_link = [m["slug"] for m in materias if inlinks.get(m["slug"], 0) == 0]
    print(f"matérias sem nenhum link de entrada: {len(sem_link)}")
    for s in sem_link:
        print("   ", s)

    valores = sorted(inlinks.get(m["slug"], 0) for m in materias)
    if valores:
        print(f"links de entrada por matéria — mín {valores[0]}, "
              f"máx {valores[-1]}, média {sum(valores)/len(valores):.1f}")

    if args.dry_run:
        print("\n(dry-run: nada foi gravado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
