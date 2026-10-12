#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atualiza a secao "YouTube Shorts" do index.html com os shorts mais recentes
do canal. Roda sozinho pelo GitHub Actions (.github/workflows/atualizar-shorts.yml)
e tambem pode ser rodado a mao:  python3 scripts/atualizar_shorts.py

Como funciona:
1. le o feed RSS do canal (os 15 uploads mais recentes), com ate 3 tentativas;
2. identifica quais entradas sao Shorts pelo proprio link do feed
   (<link rel="alternate" href=".../shorts/<id>">); so cai para o teste por
   requisicao HTTP se o feed nao trouxer a informacao;
3. pega os N primeiros shorts, limpa o titulo (tira emoji, arruma o CAIXA ALTA)
   e reescreve o bloco entre os marcadores no index.html.

Se nada mudar, o arquivo nao e tocado.

IMPORTANTE: se o YouTube nao responder (bloqueio esporadico aos servidores do
GitHub, que devolve 404/429), o script AVISA e encerra com sucesso (codigo 0).
Ele nao derruba o workflow, porque nao ha nada de errado com o site - e apenas
uma indisponibilidade temporaria da fonte.
"""
import os, re, sys, html, time, urllib.request, urllib.error

CANAL_ID = "UCWWGynJoaGOzT-n5xueEqOQ"
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=" + CANAL_ID
QUANTOS = 5
TENTATIVAS = 3
ESPERA = 8  # segundos entre as tentativas (dobra a cada vez)
INDEX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html")
INICIO = "<!-- INICIO DOS SHORTS (atualizado automaticamente pelo scripts/atualizar_shorts.py) -->"
FIM = "<!-- FIM DOS SHORTS -->"

# User-Agent de navegador real: o YouTube recusa agentes que se identificam como robo
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# termos que mantem a grafia propria quando o titulo vem em CAIXA ALTA
GLOSSARIO = ["Bolsa Familia", "Bolsa Família", "BPC/LOAS", "BPC", "LOAS", "INSS", "CRAS", "CadUnico",
             "CadÚnico", "FGTS", "Pe-de-Meia", "Pé-de-Meia", "Gas do Povo", "Gás do Povo",
             "Minha Casa Minha Vida", "Caixa Tem", "SUS", "IRPF", "PIS", "Pasep",
             "Luz do Povo", "Tarifa Social", "DPVAT", "CLT", "CTPS", "Novo Horizonte", "Brasil"]
# atencao: nada de termo curto e ambiguo aqui (ex.: "Caixa" quebraria "caixa d'agua"
# e "MEI" quebraria "Pe-de-Meia"). A substituicao usa limite de palavra.


class FonteIndisponivel(Exception):
    """O YouTube nao respondeu. Nao e erro do site: so tentar de novo depois."""


def baixar(url, tentativas=TENTATIVAS):
    """Baixa a URL com repeticao. Levanta FonteIndisponivel se nao conseguir."""
    espera = ESPERA
    ultimo = ""
    for n in range(1, tentativas + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            ultimo = "HTTP %s" % e.code
        except Exception as e:
            ultimo = type(e).__name__
        if n < tentativas:
            print("Tentativa %d de %d falhou (%s). Esperando %ds..." % (n, tentativas, ultimo, espera))
            time.sleep(espera)
            espera *= 2
    raise FonteIndisponivel(ultimo)


def sem_emoji(txt):
    return re.sub(r"[\U00002190-\U0001FAFF☀-➿️‍]", "", txt)


def arrumar_titulo(t):
    t = sem_emoji(html.unescape(t)).strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"#\w+", "", t).strip()          # tira hashtags
    letras = [c for c in t if c.isalpha()]
    if letras and sum(1 for c in letras if c.isupper()) / len(letras) > 0.7:
        t = t.capitalize()                       # estava em CAIXA ALTA
        for termo in GLOSSARIO:                  # devolve a grafia certa
            t = re.sub(r"\b" + re.escape(termo) + r"\b", termo, t, flags=re.I)
        # maiuscula depois de ponto, exclamacao ou interrogacao
        t = re.sub(r"([.!?]\s+)([a-zà-ú])", lambda m: m.group(1) + m.group(2).upper(), t)
    t = t.strip(" -–—|")
    t = re.sub(r"!+$", "", t).strip()             # tira o ponto de exclamacao do fim
    return t[:1].upper() + t[1:] if t else t


def eh_short_por_requisicao(vid):
    """Reserva: Short abre em /shorts/<id>; video comum redireciona para /watch."""
    req = urllib.request.Request("https://www.youtube.com/shorts/" + vid, headers=UA, method="HEAD")
    classe = type("NoRedirect", (urllib.request.HTTPRedirectHandler,),
                  {"redirect_request": lambda *a, **k: None})
    op = urllib.request.build_opener(classe)
    try:
        with op.open(req, timeout=20) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        return e.code == 200
    except Exception:
        return False


def buscar_shorts():
    xml = baixar(FEED)
    entradas = re.findall(r"<entry>(.*?)</entry>", xml, re.S)
    achados = []
    incertos = []
    for e in entradas:
        vid = re.search(r"<yt:videoId>(.*?)</yt:videoId>", e)
        tit = re.search(r"<title>(.*?)</title>", e, re.S)
        if not vid or not tit:
            continue
        vid, tit = vid.group(1), arrumar_titulo(tit.group(1))
        link = re.search(r'<link[^>]+rel="alternate"[^>]+href="([^"]+)"', e)
        alvo = link.group(1) if link else ""
        if "/shorts/" in alvo:
            achados.append((vid, tit))         # o proprio feed ja disse que e Short
            if len(achados) == QUANTOS:
                return achados
        elif "/watch" not in alvo:
            incertos.append((vid, tit))        # feed nao disse: confere depois

    # so consulta o YouTube de novo se o feed nao tiver resolvido tudo
    for vid, tit in incertos:
        if len(achados) == QUANTOS:
            break
        if eh_short_por_requisicao(vid):
            achados.append((vid, tit))
    return achados


def montar_html(shorts):
    play = ('<span class="short-play"><svg viewBox="0 0 24 24" width="26" height="26" fill="#fff">'
            '<path d="M8 5.5v13l11-6.5z"/></svg></span>')
    linhas = []
    for vid, tit in shorts:
        t = html.escape(tit, quote=True)
        linhas.append(
            '          <a class="short-card" href="https://www.youtube.com/shorts/%s" target="_blank" rel="noopener">\n'
            '            <img src="https://i.ytimg.com/vi/%s/oardefault.jpg" onerror="this.src=\'https://i.ytimg.com/vi/%s/hqdefault.jpg\'" alt="%s" loading="lazy">\n'
            '            %s\n'
            '            <span class="short-titulo">%s</span>\n'
            '          </a>' % (vid, vid, vid, t, play, t))
    return "\n".join(linhas)


def main():
    try:
        shorts = buscar_shorts()
    except FonteIndisponivel as e:
        # Nao e erro do portal: o YouTube bloqueou/nao respondeu agora.
        # Encerra com sucesso para nao disparar e-mail de falha do GitHub Actions.
        print("AVISO: o YouTube nao respondeu ao feed (%s). Mantendo os Shorts atuais "
              "no index.html. A proxima execucao tenta de novo." % e)
        return 0
    if len(shorts) < QUANTOS:
        print("Encontrei so %d shorts; nao vou mexer no index para nao quebrar a secao." % len(shorts))
        return 0
    with open(INDEX, encoding="utf-8") as f:
        idx = f.read()
    if INICIO not in idx or FIM not in idx:
        print("ERRO: marcadores dos shorts nao encontrados no index.html")
        return 1
    antes, resto = idx.split(INICIO, 1)
    _, depois = resto.split(FIM, 1)
    novo = antes + INICIO + "\n" + montar_html(shorts) + "\n          " + FIM + depois
    if novo == idx:
        print("Shorts ja estao atualizados.")
        return 0
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(novo)
    print("Atualizado com: " + " | ".join(t for _, t in shorts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
