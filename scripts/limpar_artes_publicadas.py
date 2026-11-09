"""Tira do site as artes de redes sociais de posts que já foram publicados.

Por quê: o GitHub Pages aceita site de até 1 GB. Em 09/11/2026 o portal tinha
2,5 GB, quase tudo em artes de Instagram/Facebook, e o deploy do site começou
a falhar por tempo esgotado ("artifact exceeds 1 GB").

Essas artes só precisam estar no ar NA HORA da publicação: o Instagram, o
Facebook e o Telegram buscam a imagem pelo endereço do site e guardam a cópia
deles. Depois disso ninguém mais usa:
    img/stories/<slug>.png   story (vai ao Telegram; botão "baixar arte" cai
                             na capa quando não existe)
    img/feed/<slug>.png      feed 3:4 (nenhuma página usa)
    img/feed45/<slug>.png    feed 4:5 (a que vai ao Instagram)
    img/feedfb/<slug>.png    feed do Facebook

NUNCA mexe em:
    img/<slug>.png           capa da matéria (página e prévia do WhatsApp)
    img/banco/               fotos de origem para gerar artes novas
    img/youtube/, img/calculadora/, img/parceiros/ etc.

Regras (um slug só perde as artes quando TODAS as condições valem):
  - está em instagram/fila.json ou facebook/fila.json;
  - em todas as filas onde aparece, o status é "publicado" ou "expirado";
  - não está pendente em agendadas/agenda.json;
  - a publicação mais recente foi há mais de DIAS dias (folga para repostar).
Slug que não está em fila nenhuma fica, a não ser com --fora-da-fila (usado
uma única vez, na limpeza de 09/11/2026, para as artes antigas de antes da fila).

Os originais ficam no histórico do git (e a limpeza de 09/11 tem cópia em
D:\\Junior\\Desktop\\Backup artes do portal 2026-11-09).

Uso:
    python scripts/limpar_artes_publicadas.py            # mostra o que sairia
    python scripts/limpar_artes_publicadas.py --apagar   # apaga de fato
"""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTAS = ["stories", "feed", "feed45", "feedfb"]
FINAIS = {"publicado", "expirado"}
DIAS = 2


def ler(caminho, chave):
    p = os.path.join(RAIZ, caminho)
    if not os.path.exists(p):
        return []
    return json.load(open(p, encoding="utf-8")).get(chave, [])


def data(txt):
    try:
        return datetime.fromisoformat(str(txt).replace("Z", "+00:00"))
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apagar", action="store_true", help="apaga de verdade")
    ap.add_argument("--dias", type=int, default=DIAS)
    ap.add_argument("--fora-da-fila", action="store_true",
                    help="também apaga artes de slugs que não estão em fila nenhuma")
    a = ap.parse_args()

    agora = datetime.now(timezone.utc)
    limite = agora - timedelta(days=a.dias)

    status = {}   # slug -> lista de status
    ultima = {}   # slug -> publicação mais recente
    for fila in ("instagram/fila.json", "facebook/fila.json"):
        for it in ler(fila, "fila"):
            s = it.get("slug")
            if not s:
                continue
            status.setdefault(s, []).append(it.get("status"))
            d = data(it.get("publicado_em") or it.get("expirado_em") or it.get("publicar_em"))
            if d and (s not in ultima or d > ultima[s]):
                ultima[s] = d

    agendados = {it.get("slug") for it in ler("agendadas/agenda.json", "agenda")
                 if it.get("status") != "publicado"}

    def pode_sair(slug):
        if slug in agendados:
            return False
        if slug not in status:
            return a.fora_da_fila
        if not all(x in FINAIS for x in status[slug]):
            return False
        d = ultima.get(slug)
        return d is not None and d < limite

    total = 0
    qtd = 0
    for pasta in PASTAS:
        base = os.path.join(RAIZ, "img", pasta)
        if not os.path.isdir(base):
            continue
        for nome in sorted(os.listdir(base)):
            p = os.path.join(base, nome)
            if not os.path.isfile(p) or not nome.lower().endswith(".png"):
                continue
            if pode_sair(os.path.splitext(nome)[0]):
                total += os.path.getsize(p)
                qtd += 1
                if a.apagar:
                    os.remove(p)

    acao = "Apagadas" if a.apagar else "Sairiam"
    print(f"{acao}: {qtd} artes ({total / 2**20:.0f} MB).")


if __name__ == "__main__":
    main()
