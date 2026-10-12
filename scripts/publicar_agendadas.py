#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publicar_agendadas.py — Portal Júnior Arrais

Robô da GAVETA: coloca no ar, no horário marcado, as matérias que ficaram prontas
com antecedência (a grade montada no domingo).

Como funciona
  - agendadas/agenda.json lista as matérias, cada uma com `publicar_em` (UTC) e
    `status` ("pendente" -> "publicado");
  - a página pronta fica compactada em agendadas/<slug>.html.gz até a hora, para não
    ser lida nem indexada antes (o robots.txt também bloqueia /agendadas/);
  - na hora, o robô: grava noticias/<slug>.html, põe o card no topo do noticias.html,
    a URL no sitemap, gira a home (a nova vira o 1º destaque; o 2º destaque desce para
    a lateral; a última da lateral vira o 1º card de "Últimas"; o último card sai),
    roda gerar_relacionadas.py e aplicar_links_contextuais.py e valida a home.

Quem chama: scripts/processar_fila_instagram.py, no começo de cada execução do
workflow "Publicar no Instagram" (a cada ~10 min, com reforço externo). Chamado
assim, com push=True, este script faz o próprio commit e push (com nova tentativa).
Até 12/10/2026 ele era chamado pelo workflow dos Shorts, mas aquele cron atrasava
até 3 horas: a matéria das 8h não tinha saído às 9h.

Segurança
  - nunca derruba quem chamou: qualquer erro é impresso e o script segue;
  - se a home não passar no validar_home.py, a home volta ao estado anterior e só a
    página, o arquivo e o sitemap são publicados;
  - publica no máximo MAX_POR_RODADA matérias por execução (se o robô ficou parado,
    não despeja a semana inteira de uma vez).

Uso manual:
    python3 scripts/publicar_agendadas.py            # publica o que venceu
    python3 scripts/publicar_agendadas.py --listar   # mostra a agenda
"""

import gzip
import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(RAIZ, "agendadas")
AGENDA = os.path.join(DIR, "agenda.json")
INDEX = os.path.join(RAIZ, "index.html")
ARQUIVO = os.path.join(RAIZ, "noticias.html")
SITEMAP = os.path.join(RAIZ, "sitemap.xml")
SITE = "https://portaljuniorarrais.com.br"
MAX_POR_RODADA = 3
MARCA_ARQ = "<!-- INÍCIO DO ARQUIVO DE NOTÍCIAS (mais novas primeiro) -->"
MARCA_ULT = "<!-- INÍCIO DOS CARDS DE NOTÍCIA (os mais novos ficam primeiro) -->"


def ler(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def gravar(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def e(s):
    return html.escape(s, quote=True)


def card(slug, cat, titulo, data, alt):
    return f'''          <a class="card" href="noticias/{slug}.html">
            <div class="card-thumb"><img src="img/{slug}.png" alt="{e(alt)}"></div>
            <div class="card-corpo">
              <span class="chip">{e(cat)}</span>
              <h3>{e(titulo)}</h3>
              <span class="meta">{e(data)}</span>
            </div>
          </a>
'''


def dados_da_materia(slug):
    """Chip, título, data e alt da capa, lidos da própria página da matéria."""
    h = ler(os.path.join(RAIZ, "noticias", slug + ".html"))
    def g(rx):
        m = re.search(rx, h, re.S)
        return html.unescape(re.sub(r"<.*?>", "", m.group(1))).strip() if m else ""
    data = g(r'<div class="meta">.*?&middot;\s*([^<]+)</div>')
    return (g(r'<span class="chip">(.*?)</span>'), g(r"<h1>(.*?)</h1>"), data,
            g(r'<div class="artigo-capa"><img [^>]*alt="([^"]*)"'))


def girar_home(item):
    h = ler(INDEX)
    m = re.search(r'(<div class="col-esq">)(.*?)(\s*</div>\s*<div class="col-video">)', h, re.S)
    dest = re.findall(r'<a class="mini-card grande".*?</a>', m.group(2), re.S)
    md = re.search(r'(<div class="col-dir">)(.*?)(\s*</div>\s*</section>)', h, re.S)
    lat = re.findall(r'<a class="lateral-item".*?</a>', md.group(2), re.S)
    mu = re.search(re.escape(MARCA_ULT) + r'(.*?)(\s*</div>\s*</div>\s*</section>)', h, re.S)
    ult = re.findall(r'<a class="card".*?</a>', mu.group(1), re.S)
    assert len(dest) == 2 and len(lat) == 6 and len(ult) >= 1, (len(dest), len(lat), len(ult))

    slug, titulo = item["slug"], item["titulo"]
    novo_dest = f'''<a class="mini-card grande" href="noticias/{slug}.html">
          <div class="mini-thumb"><img src="img/{slug}.png" alt="{e(titulo)}"></div>
          <h3>{e(titulo)}</h3>
          <span class="meta">{e(item["data_exibicao"])}</span>
        </a>'''
    sai_dest = dest[1]
    s2 = re.search(r'href="noticias/([^"]+)\.html"', sai_dest).group(1)
    t2 = html.unescape(re.search(r"<h3>(.*?)</h3>", sai_dest, re.S).group(1))
    novo_lat = f'''<a class="lateral-item" href="noticias/{s2}.html">
          <img src="img/{s2}.png" alt="" loading="lazy">
          <span>{e(t2)}</span>
        </a>'''
    sai_lat = lat[-1]
    s3 = re.search(r'href="noticias/([^"]+)\.html"', sai_lat).group(1)
    cat3, tit3, data3, alt3 = dados_da_materia(s3)
    novo_card = card(s3, cat3, tit3, data3, alt3).strip()

    dest = [novo_dest, dest[0]]
    lat = [novo_lat] + lat[:-1]
    ult = [novo_card] + ult[:-1]
    h = h[:m.start(2)] + "\n        " + "\n        ".join(dest) + h[m.end(2):]
    md = re.search(r'(<div class="col-dir">)(.*?)(\s*</div>\s*</section>)', h, re.S)
    h = h[:md.start(2)] + "\n        " + "\n        ".join(lat) + h[md.end(2):]
    mu = re.search(re.escape(MARCA_ULT) + r'(.*?)(\s*</div>\s*</div>\s*</section>)', h, re.S)
    h = h[:mu.start(1)] + "\n          " + "\n          ".join(ult) + h[mu.end(1):]
    gravar(INDEX, h)


def publicar(item):
    slug = item["slug"]
    gz = os.path.join(DIR, slug + ".html.gz")
    with gzip.open(gz, "rt", encoding="utf-8") as f:
        pagina = f.read()
    gravar(os.path.join(RAIZ, "noticias", slug + ".html"), pagina)

    arq = ler(ARQUIVO)
    if f'href="noticias/{slug}.html"' not in arq:
        arq = arq.replace(MARCA_ARQ, MARCA_ARQ + "\n" + card(slug, item["categoria"], item["titulo"],
                                                             item["data_exibicao"], item["alt"]).rstrip("\n"), 1)
        gravar(ARQUIVO, arq)

    sm = ler(SITEMAP)
    loc = f"{SITE}/noticias/{slug}.html"
    if loc not in sm:
        dia = item["publicar_em"][:10]
        linha = f"  <url><loc>{loc}</loc><lastmod>{dia}</lastmod></url>\n"
        i = sm.find(f"  <url><loc>{SITE}/noticias/")
        sm = sm[:i] + linha + sm[i:] if i >= 0 else sm.replace("</urlset>", linha + "</urlset>")
        gravar(SITEMAP, sm)

    home_antes = ler(INDEX)
    try:
        if f'href="noticias/{slug}.html"' not in home_antes:
            girar_home(item)
            r = subprocess.run([sys.executable, os.path.join(RAIZ, "scripts", "validar_home.py"), "index.html"],
                               cwd=RAIZ, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError("validar_home reprovou: " + (r.stdout + r.stderr)[-400:])
    except Exception as ex:
        gravar(INDEX, home_antes)
        print(f"AVISO: home não foi girada para {slug} ({ex}). Página, arquivo e sitemap publicados.")

    os.remove(gz)
    item["status"] = "publicado"
    item["publicado_em"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("Publicada:", slug)


def git(*a, timeout=120):
    return subprocess.run(["git", *a], cwd=RAIZ, capture_output=True, text=True, timeout=timeout)


def gravar_no_git(slugs):
    """Commit + push só dos caminhos que a publicação mexe, com até 5 tentativas."""
    caminhos = ["noticias", "noticias.html", "index.html", "sitemap.xml", "agendadas"]
    for tentativa in range(1, 6):
        git("add", "-A", *caminhos)
        if git("diff", "--cached", "--quiet").returncode != 0:
            git("-c", "user.name=Portal Júnior Arrais", "-c", "user.email=juniorarrais90@gmail.com",
                "commit", "-q", "-m", "Gaveta: publica " + ", ".join(slugs))
        r = git("push", "origin", "HEAD:main")
        if r.returncode == 0:
            print(f"Gaveta gravada no GitHub (tentativa {tentativa}).")
            return True
        print(f"Push recusado (tentativa {tentativa}); sincronizando...")
        p = git("-c", "user.name=Portal Júnior Arrais", "-c", "user.email=juniorarrais90@gmail.com",
                "pull", "--rebase", "origin", "main")
        if p.returncode != 0:
            git("rebase", "--abort")
            print("Rebase falhou:", (p.stdout + p.stderr)[-300:])
            return False
    return False


def main(push=False):
    if not os.path.exists(AGENDA):
        return 0
    ag = json.load(open(AGENDA, encoding="utf-8"))
    if "--listar" in sys.argv:
        for i in ag["agenda"]:
            print(i["horario_brasilia"], i["status"], i["slug"])
        return 0
    if ag.get("pausado"):
        print("Agenda pausada:", ag.get("pausa_motivo", ""))
        return 0
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    vencidos = sorted((i for i in ag["agenda"] if i.get("status") == "pendente" and i["publicar_em"] <= agora),
                      key=lambda i: i["publicar_em"])[:MAX_POR_RODADA]
    if not vencidos:
        print("Agenda: nada vencido.")
        return 0
    feitos = 0
    for item in vencidos:
        try:
            publicar(item)
            feitos += 1
        except Exception as ex:
            item["falhas"] = item.get("falhas", 0) + 1
            item["ultima_falha"] = str(ex)[:300]
            print("ERRO ao publicar", item["slug"], ex)
    json.dump(ag, open(AGENDA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if feitos:
        for sc in ("gerar_relacionadas.py", "aplicar_links_contextuais.py"):
            r = subprocess.run([sys.executable, os.path.join(RAIZ, "scripts", sc)], cwd=RAIZ,
                               capture_output=True, text=True)
            print(sc, "ok" if r.returncode == 0 else "FALHOU: " + r.stderr[-300:])
        if push:
            gravar_no_git([i["slug"] for i in vencidos if i.get("status") == "publicado"])
    return 0


if __name__ == "__main__":
    sys.exit(main(push="--push" in sys.argv))
