#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Capa 16:9 do Portal Júnior Arrais no layout de FAIXA (1200x675).

Substitui o layout antigo, em que a manchete era escrita POR CIMA da foto com um
degradê escuro. Ali, qualquer imagem que já tivesse texto (logo, banner, arte de
canal) resultava em texto sobre texto e a manchete ficava ilegível.

Aqui a estrutura é a mesma da arte de feed 3:4 (gerar_post_feed.py): foto em cima,
faixa azul com chapéu + manchete embaixo, rodapé com o endereço do portal. A foto
e o texto nunca se sobrepõem, então arte com texto pode ser usada sem problema.

Uso:
  python gerar_capa_faixa.py --saida img/<slug>.png \
      --categoria "INSS" \
      --titulo "Consignado do INSS mudou: veja os novos limites" \
      --foto-fundo img/banco/foto.jpg \
      --credito "Foto: José Cruz/Agência Brasil"

Argumentos:
  --saida       caminho do PNG de saída (usar o slug da notícia). Sai 1200x675.
  --titulo      manchete em uma string; o script quebra e ajusta o corpo sozinho.
  --categoria   texto da tarja vermelha (chip do tema). Com --urgente vira ÚLTIMA HORA.
  --foto-fundo  foto da área de cima. Sem ela, entra o gradiente azul da marca.
  --credito     crédito da foto, impresso pequeno no canto da imagem.
  --urgente     tarja em vermelho mais vivo e texto "ÚLTIMA HORA".

Fontes: tenta Outfit (canvas-design do Cowork) e cai para DejaVu se não achar.
"""
import argparse, os, glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter

AZUL_FAIXA   = (154, 183, 212)   # #9ab7d4  faixa da manchete (mesma do feed)
AZUL_FAIXA_E = (120, 152, 186)   # tom fechado à esquerda, para dar profundidade
VERMELHO     = (226, 59, 59)     # #e23b3b  chapéu e faixa do rodapé
VERMELHO_VIVO= (240, 80, 74)
ESCURO       = (11, 26, 44)      # #0b1a2c  rodapé
AZUL_MARCA   = (44, 137, 231)    # #2c89e7  fallback sem foto
CIANO        = (43, 218, 253)    # #2bdafd  filete da assinatura
BRANCO       = (255, 255, 255)

W, H     = 1200, 675
FOTO_H   = 455                   # foto de 0 a 455
FAIXA_B  = 630                   # faixa azul de 455 a 630 (175px)
MARGEM_X = 48
COL_W    = W - MARGEM_X * 2 - 30
CHAPEU_H = 46
SS       = 4


def achar_fonte(peso):
    padroes = [
        f"/sessions/*/mnt/.claude/skills/canvas-design/canvas-fonts/Outfit-{peso}.ttf",
        f"/mnt/skills/**/canvas-fonts/Outfit-{peso}.ttf",
    ]
    for p in padroes:
        hits = glob.glob(p, recursive=True)
        if hits:
            return hits[0]
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if peso == "Bold" \
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def quebrar(d, texto, fonte, largura):
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if d.textlength(teste, font=fonte) <= largura or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def ajustar_manchete(d, texto, caminho_fonte, largura, altura_max,
                     tam_max=54, tam_min=34, entrelinha=1.08, max_linhas=3):
    """Maior corpo em que a manchete cabe na coluna E na faixa. Evita corte."""
    tam = tam_max
    while tam >= tam_min:
        f = ImageFont.truetype(caminho_fonte, tam)
        linhas = quebrar(d, texto, f, largura)
        alt = len(linhas) * int(tam * entrelinha)
        if len(linhas) <= max_linhas and alt <= altura_max:
            return f, linhas, alt
        tam -= 2
    f = ImageFont.truetype(caminho_fonte, tam_min)
    linhas = quebrar(d, texto, f, largura)[:max_linhas]
    return f, linhas, len(linhas) * int(tam_min * entrelinha)


def faixa_azul():
    alt = FAIXA_B - FOTO_H
    g = Image.new("RGB", (W, 1))
    for x in range(W):
        k = min(1.0, x / (W * 0.75))
        g.putpixel((x, 0), tuple(
            int(AZUL_FAIXA_E[i] + (AZUL_FAIXA[i] - AZUL_FAIXA_E[i]) * k) for i in range(3)))
    return g.resize((W, alt))


def fundo_marca():
    g = Image.new("RGB", (1, FOTO_H))
    for y in range(FOTO_H):
        k = y / FOTO_H
        g.putpixel((0, y), tuple(
            int(ESCURO[i] + (AZUL_MARCA[i] - ESCURO[i]) * k) for i in range(3)))
    return g.resize((W, FOTO_H))


def cortar_foto(caminho, encaixe="auto"):
    """Prepara a imagem para a área de 1200 x FOTO_H.

    encaixe="cobrir"  → preenche a área toda cortando as sobras (foto comum).
    encaixe="conter"  → mostra a imagem inteira, sem cortar nada, sobre um fundo
                        borrado dela mesma. É o modo para ARTE COM TEXTO: a faixa
                        da capa é bem mais larga que alta, então cortar uma arte
                        quadrada decepa justamente o texto dela.
    encaixe="auto"    → usa "conter" quando o corte comeria mais de 35% da altura.
    """
    base = Image.open(caminho).convert("RGB")
    alvo = W / FOTO_H
    bw, bh = base.size

    if encaixe == "auto":
        perda = 1 - (bw / alvo) / bh if bw / bh < alvo else 0
        encaixe = "conter" if perda > 0.35 else "cobrir"

    if encaixe == "conter":
        # A arte inteira aparece, centralizada, sobre um fundo CHAPADO da marca.
        #
        # Já tentei esticar a coluna da borda e borrar a própria imagem: nos dois
        # casos a lateral vira rastro quando a borda tem detalhe (uma nota, um
        # recorte de foto). Fundo chapado não tenta disfarçar nada — lê como
        # moldura proposital, no mesmo azul do rodapé. Em arte que já é azul-escura
        # a emenda praticamente some; nas claras, a arte ganha destaque de card.
        k = min(W / bw, FOTO_H / bh)
        frente = base.resize((max(1, int(bw * k)), max(1, int(bh * k))), Image.LANCZOS)
        fw, fh = frente.size
        x0, y0 = (W - fw) // 2, (FOTO_H - fh) // 2

        TOPO_FUNDO, BASE_FUNDO = (13, 30, 50), (24, 48, 74)
        col = Image.new("RGB", (1, FOTO_H))
        for y in range(FOTO_H):
            k2 = y / FOTO_H
            col.putpixel((0, y), tuple(
                int(TOPO_FUNDO[i] + (BASE_FUNDO[i] - TOPO_FUNDO[i]) * k2) for i in range(3)))
        tela = col.resize((W, FOTO_H))
        tela.paste(Image.new("RGB", (fw + 20, fh + 20), (6, 16, 28)), (x0 - 10, y0 - 10))
        tela.paste(frente, (x0, y0))
        return tela

    if bw / bh > alvo:
        nw = int(bh * alvo)
        base = base.crop(((bw - nw) // 2, 0, (bw - nw) // 2 + nw, bh))
    else:
        nh = int(bw / alvo)
        y0 = max(0, (bh - nh) // 3)
        base = base.crop((0, y0, bw, y0 + nh))
    return base.resize((W, FOTO_H), Image.LANCZOS)


def listras_rodape():
    alt = H - FAIXA_B
    im = Image.new("RGBA", (W * 2, alt * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for bloco_x in (0, (W - 130) * 2):
        for i in range(5):
            x = bloco_x + i * 26
            d.polygon([(x, alt * 2), (x + 14, alt * 2), (x + 14 + 22, 0), (x + 22, 0)],
                      fill=VERMELHO + (255,))
    return im.resize((W, alt), Image.LANCZOS)


def gerar(saida, titulo, categoria, foto_fundo=None, credito=None, urgente=False, encaixe="auto"):
    im = Image.new("RGB", (W, H), ESCURO)
    im.paste(cortar_foto(foto_fundo, encaixe) if foto_fundo and os.path.exists(foto_fundo)
             else fundo_marca(), (0, 0))
    im.paste(faixa_azul(), (0, FOTO_H))
    ImageDraw.Draw(im).rectangle([0, FAIXA_B, W, H], fill=ESCURO)

    im = im.convert("RGBA")
    im.alpha_composite(listras_rodape(), (0, FAIXA_B))
    im = im.convert("RGB")

    d = ImageDraw.Draw(im)
    bold, reg = achar_fonte("Bold"), achar_fonte("Regular")

    # filete ciano à esquerda da manchete, como no feed
    d.rectangle([MARGEM_X - 18, FOTO_H + 16, MARGEM_X - 12, FAIXA_B - 14], fill=CIANO)

    # chapéu: tarja encostada no topo da faixa azul, sobre a foto
    texto_ch = "ÚLTIMA HORA" if urgente else (categoria or "").upper()
    if texto_ch:
        cor_ch = VERMELHO_VIVO if urgente else VERMELHO
        tam_ch = 26
        while tam_ch > 16 and d.textlength(texto_ch, font=ImageFont.truetype(bold, tam_ch)) > 300 - 32:
            tam_ch -= 1
        f_ch = ImageFont.truetype(bold, tam_ch)
        larg_ch = int(d.textlength(texto_ch, font=f_ch)) + 44
        topo_ch = FOTO_H - CHAPEU_H
        d.rectangle([MARGEM_X - 18, topo_ch, MARGEM_X - 18 + larg_ch, topo_ch + CHAPEU_H], fill=cor_ch)
        d.text((MARGEM_X - 18 + 22, topo_ch + (CHAPEU_H - tam_ch * 1.3) / 2),
               texto_ch, font=f_ch, fill=BRANCO)

    # manchete com autoajuste, centralizada na faixa
    f_tit, linhas, alt_bloco = ajustar_manchete(
        d, titulo.upper(), bold, COL_W, altura_max=FAIXA_B - FOTO_H - 26)
    y = FOTO_H + (FAIXA_B - FOTO_H - alt_bloco) // 2
    passo = int(f_tit.size * 1.08)
    for l in linhas:
        d.text((MARGEM_X, y), l, font=f_tit, fill=BRANCO)
        y += passo

    # rodapé: assinatura do portal
    f_rod = ImageFont.truetype(bold, 22)
    d.text((MARGEM_X, FAIXA_B + (H - FAIXA_B - 26) / 2), "PORTAL JÚNIOR ARRAIS",
           font=f_rod, fill=CIANO)
    f_cta = ImageFont.truetype(reg, 20)
    cta = "portaljuniorarrais.com.br"
    tw = d.textlength(cta, font=f_cta)
    d.text((W - tw - MARGEM_X, FAIXA_B + (H - FAIXA_B - 24) / 2), cta,
           font=f_cta, fill=(206, 218, 232))

    # crédito da foto, dentro da área da imagem
    if credito:
        f_cr = ImageFont.truetype(reg, 16)
        cw = d.textlength(credito, font=f_cr)
        d.rectangle([W - cw - 26, FOTO_H - 26, W, FOTO_H], fill=(0, 0, 0))
        d.text((W - cw - 14, FOTO_H - 22), credito, font=f_cr, fill=(226, 232, 240))

    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    im.save(saida, "PNG")
    print(f"Capa salva: {saida}  ({len(linhas)} linha(s), corpo {f_tit.size}px)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", required=True)
    ap.add_argument("--titulo", required=True)
    ap.add_argument("--categoria", default=None)
    ap.add_argument("--foto-fundo", dest="foto_fundo", default=None)
    ap.add_argument("--credito", default=None)
    ap.add_argument("--urgente", action="store_true")
    ap.add_argument("--encaixe", default="auto", choices=["auto", "cobrir", "conter"])
    a = ap.parse_args()
    gerar(a.saida, a.titulo, a.categoria, a.foto_fundo, a.credito, a.urgente, a.encaixe)
