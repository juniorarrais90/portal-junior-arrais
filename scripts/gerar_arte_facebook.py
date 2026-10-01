#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_arte_facebook.py — Portal Júnior Arrais

Gera a arte do Facebook a partir da arte 4:5 do Instagram, trocando o selo
"LINK NOS STORIES" por "LINK NA LEGENDA" (com a seta apontando para baixo, para
a legenda). No Facebook o link da matéria vai clicável na própria legenda, então
o selo de stories confunde quem lê.

Não refaz a arte: carimba um selo novo, do mesmo tamanho e na mesma posição
(400x84 em 48,48 — ver desenhar_selo_stories em gerar_post_feed.py), por cima do
antigo. Assim não depende da foto, do chapéu nem do título originais.

    entrada: img/feed45/<slug>.png   (1080x1350, a do Instagram)
    saída:   img/feedfb/<slug>.png   (1080x1350, a do Facebook)

Uso:
    python scripts/gerar_arte_facebook.py --slug <slug>
    python scripts/gerar_arte_facebook.py --fila      # todos os pendentes da fila sem arte
    python scripts/gerar_arte_facebook.py --slug <slug> --entrada x.png --saida y.png

O robô (workflow Publicar no Facebook) roda o --fila a cada execução e publica
as artes novas antes de processar a fila. O processar_fila_facebook.py usa a
arte de img/feedfb/ quando ela existe e, se não existir, a do Instagram.
"""

import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILA = os.path.join(RAIZ, "facebook", "fila.json")
DIR_ORIGEM = os.path.join(RAIZ, "img", "feed45")
DIR_DESTINO = os.path.join(RAIZ, "img", "feedfb")
FONTE = os.path.join(RAIZ, "fontes", "Outfit-Bold.ttf")   # mesma fonte das artes

TEXTO_SELO = "LINK NA LEGENDA"
AZUL_SELO = (39, 86, 158)      # #27569e, igual ao gerar_post_feed.py
BRANCO = (255, 255, 255)
POS_SELO = (48, 48)
PW, PH = 400, 84               # tamanho do selo original
SS = 4                         # supersampling para as curvas
TAMANHO = (1080, 1350)


def fonte_bold(tam):
    if os.path.exists(FONTE):
        return ImageFont.truetype(FONTE, tam)
    sys.path.insert(0, os.path.join(RAIZ, "scripts"))
    from gerar_post_feed import achar_fonte
    print("  aviso: fontes/Outfit-Bold.ttf não encontrada; usando a fonte reserva")
    return ImageFont.truetype(achar_fonte("Bold"), tam)


def desenhar_selo(texto=TEXTO_SELO):
    """Pill azul com seta curva apontando para BAIXO (para a legenda)."""
    im = Image.new("RGBA", (PW * SS, PH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, PW * SS, PH * SS], radius=(PH // 2) * SS, fill=AZUL_SELO)

    # mesma seta do selo de stories, desenhada e depois espelhada na vertical:
    # o pill é simétrico, então só a seta muda de sentido
    cx, cy, r, esp = 48 * SS, 48 * SS, 14 * SS, 5 * SS
    d.arc([cx - r, cy - r, cx + r, cy + r], start=0, end=180, fill=BRANCO, width=esp)
    d.line([(cx - r, cy), (cx - r, cy - 14 * SS)], fill=BRANCO, width=esp)
    lado = 10 * SS
    d.polygon([(cx - r, cy - 30 * SS), (cx - r + lado, cy - 13 * SS),
               (cx - r - lado, cy - 13 * SS)], fill=BRANCO)
    im = im.transpose(Image.FLIP_TOP_BOTTOM)

    d = ImageDraw.Draw(im)
    f = fonte_bold(27 * SS)
    tw = d.textlength(texto, font=f)
    d.text(((78 * SS + PW * SS - tw) / 2, 26 * SS), texto, font=f, fill=BRANCO)
    return im.resize((PW, PH), Image.LANCZOS)


def gerar(entrada, saida):
    base = Image.open(entrada).convert("RGBA")
    if base.size != TAMANHO:
        raise ValueError(f"{entrada} mede {base.size[0]}x{base.size[1]}; "
                         f"o esperado é {TAMANHO[0]}x{TAMANHO[1]} (4:5)")
    base.alpha_composite(desenhar_selo(), POS_SELO)
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    base.convert("RGB").save(saida, "PNG", optimize=True)
    print(f"Arte do Facebook salva: {os.path.relpath(saida, RAIZ)}")


def caminhos(slug):
    return (os.path.join(DIR_ORIGEM, f"{slug}.png"),
            os.path.join(DIR_DESTINO, f"{slug}.png"))


def gerar_da_fila(forcar=False):
    """Gera a arte de todo item pendente que ainda não tem a versão do Facebook."""
    if not os.path.exists(FILA):
        print("Sem fila. Nada a gerar.")
        return 0
    fila = json.load(open(FILA, encoding="utf-8")).get("fila", [])
    novas = 0
    for item in fila:
        if item.get("status") != "pendente":
            continue
        entrada, saida = caminhos(item["slug"])
        if os.path.exists(saida) and not forcar:
            continue
        if not os.path.exists(entrada):
            print(f"  sem arte do Instagram ainda: {item['slug']} (fica para a próxima)")
            continue
        try:
            gerar(entrada, saida)
            novas += 1
        except Exception as e:
            # uma arte com problema não pode travar as outras nem a publicação:
            # sem a versão do Facebook, o robô usa a do Instagram
            print(f"  não consegui gerar {item['slug']}: {e}")
    print(f"{novas} arte(s) nova(s) do Facebook.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="slug da matéria")
    ap.add_argument("--fila", action="store_true",
                    help="gera para todos os pendentes de facebook/fila.json")
    ap.add_argument("--forcar", action="store_true", help="refaz mesmo se já existir")
    ap.add_argument("--entrada", help="PNG de entrada (padrão: img/feed45/<slug>.png)")
    ap.add_argument("--saida", help="PNG de saída (padrão: img/feedfb/<slug>.png)")
    a = ap.parse_args()

    if a.fila:
        return gerar_da_fila(a.forcar)
    if not a.slug and not (a.entrada and a.saida):
        ap.error("use --slug <slug>, --fila ou --entrada/--saida")
    entrada, saida = caminhos(a.slug) if a.slug else (None, None)
    gerar(a.entrada or entrada, a.saida or saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
