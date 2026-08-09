#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera a arte de FEED do Portal Júnior Arrais (1080x1440, Instagram/Facebook).

Terceiro formato do portal, ao lado da capa 16:9 (gerar_capa.py) e do story 9:16
(gerar_story.py). Sai em 3:4 porque desde 2025 a grade do perfil do Instagram é
3:4 — post quadrado perde as laterais na grade. Replica o modelo do Canva "MODELO Portal Junior Arrais":
foto real em cima, faixa azul com chapéu + manchete embaixo, recorte do Júnior à
esquerda, rodapé com o endereço do portal e o selo "LINK NOS STORIES" no topo.

Uso típico:
  python gerar_post_feed.py --saida img/feed/<slug>.png \
      --chapeu "BOLSA FAMÍLIA" \
      --titulo "BOLSA FAMÍLIA DE AGOSTO COMEÇA A SER PAGO DIA 18" \
      --foto-fundo img/banco/bolsa-familia.jpg \
      --foto img/recorte-junior.png \
      --credito "Foto: Marcelo Camargo/Agência Brasil"

Argumentos:
  --saida       caminho do PNG de saída (usar o slug da notícia). Sai 1080x1440.
  --titulo      manchete em uma string; o script quebra em linhas e ajusta o corpo
                sozinho (2 a 3 linhas). Sai sempre em CAIXA ALTA.
  --chapeu      texto da tarja vermelha acima da manchete (tema: BOLSA FAMÍLIA,
                BPC/LOAS, INSS...). Até ~18 caracteres; acima disso o corpo diminui.
  --foto-fundo  foto real que ocupa a área de cima (jpg/png). Sem ela, entra um
                gradiente azul da marca.
  --foto        PNG já recortado do Júnior, entra à esquerda (ver recortar_fundo.py)
  --credito     crédito da foto, impresso pequeno no canto da imagem
  --sem-selo    remove o selo "LINK NOS STORIES" (por padrão ele SAI na arte)
  --texto-selo  troca o texto do selo (padrão: "LINK NOS STORIES")
  --logo        selo circular do portal (PNG). Se o repositório tiver o logo real,
                passar aqui; sem ele o script desenha um selo equivalente.

Diferença importante para o modelo do Canva: aqui a manchete tem AUTOAJUSTE. O
corpo cai de 64 até 44 px conforme o tamanho do título, então manchete longa não
estoura a faixa nem é cortada — o problema que existia na arte original.

Fontes: tenta Outfit (canvas-design do Cowork) e cai para DejaVu se não achar.
"""
import argparse, os, glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Paleta do modelo (lida direto do design do Canva)
AZUL_FAIXA   = (154, 183, 212)   # #9ab7d4  faixa da manchete
AZUL_FAIXA_E = (120, 152, 186)   # tom mais fechado à esquerda, para dar profundidade
AZUL_SELO    = (39, 86, 158)     # #27569e  pill do "link nos stories"
VERMELHO     = (226, 59, 59)     # #e23b3b  chapéu e faixa do rodapé
ESCURO       = (11, 26, 44)      # #0b1a2c  rodapé
AZUL_MARCA   = (44, 137, 231)    # #2c89e7  fallback sem foto
BRANCO       = (255, 255, 255)

W, H     = 1080, 1440   # 3:4 — proporção da grade do perfil do Instagram desde 2025.
                        # Em 1:1 o Instagram corta as laterais na grade, comendo o
                        # recorte do Júnior e o selo de stories. Em 3:4 não corta nada.
FOTO_H   = 1120         # a foto ocupa de 0 a 1120 (todo o ganho de altura foi para ela)
FAIXA_B  = 1356         # faixa azul de 1120 a 1356 (236px, igual à do formato antigo)
MARGEM_X = 380          # coluna onde começam chapéu e manchete
COL_W    = 656          # largura útil da coluna de texto
CHAPEU_H = 56           # altura da tarja de tema
SS       = 4            # supersampling para as formas curvas


def achar_fonte(peso):
    """peso: 'Bold' ou 'Regular'. Procura Outfit nos caminhos conhecidos do Cowork."""
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
    """Quebra o texto em linhas que caibam na largura dada."""
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
                     tam_max=64, tam_min=44, entrelinha=1.09, max_linhas=3):
    """Acha o maior corpo em que a manchete cabe na coluna e na faixa.

    É isto que impede o título de vazar: testa de 64 px para baixo até o bloco
    inteiro caber tanto na largura da coluna quanto na altura da faixa azul.
    """
    tam = tam_max
    while tam >= tam_min:
        f = ImageFont.truetype(caminho_fonte, tam)
        linhas = quebrar(d, texto, f, largura)
        alt = len(linhas) * int(tam * entrelinha)
        if len(linhas) <= max_linhas and alt <= altura_max:
            return f, linhas, alt
        tam -= 2
    # piso: aceita o menor corpo e corta em max_linhas
    f = ImageFont.truetype(caminho_fonte, tam_min)
    linhas = quebrar(d, texto, f, largura)[:max_linhas]
    return f, linhas, len(linhas) * int(tam_min * entrelinha)


def faixa_azul():
    """Faixa da manchete: gradiente horizontal sutil, mais fechado à esquerda."""
    alt = FAIXA_B - FOTO_H
    g = Image.new("RGB", (W, 1))
    for x in range(W):
        k = min(1.0, x / (W * 0.75))
        g.putpixel((x, 0), tuple(
            int(AZUL_FAIXA_E[i] + (AZUL_FAIXA[i] - AZUL_FAIXA_E[i]) * k) for i in range(3)))
    return g.resize((W, alt))


def fundo_marca():
    """Gradiente azul da marca, usado quando não há foto do assunto."""
    g = Image.new("RGB", (1, FOTO_H))
    for y in range(FOTO_H):
        k = y / FOTO_H
        g.putpixel((0, y), tuple(
            int(ESCURO[i] + (AZUL_MARCA[i] - ESCURO[i]) * k) for i in range(3)))
    return g.resize((W, FOTO_H))


def cortar_foto(caminho):
    """Corte centralizado da foto para a área da imagem (1080 x FOTO_H)."""
    base = Image.open(caminho).convert("RGB")
    alvo = W / FOTO_H
    bw, bh = base.size
    if bw / bh > alvo:
        nw = int(bh * alvo)
        base = base.crop(((bw - nw) // 2, 0, (bw - nw) // 2 + nw, bh))
    else:
        nh = int(bw / alvo)
        y0 = max(0, (bh - nh) // 3)          # corte alto: preserva rostos
        base = base.crop((0, y0, bw, y0 + nh))
    return base.resize((W, FOTO_H))


def desenhar_selo_stories(texto="LINK NOS STORIES"):
    """Pill azul com seta curva apontando para cima. Devolve RGBA já reduzido."""
    pw, ph = 400, 84                          # tamanho final do pill
    im = Image.new("RGBA", (pw * SS, ph * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, pw * SS, ph * SS], radius=(ph // 2) * SS, fill=AZUL_SELO)

    # seta: base em U + haste subindo pela esquerda + ponta para cima
    cx, cy, r, esp = 48 * SS, 48 * SS, 14 * SS, 5 * SS
    d.arc([cx - r, cy - r, cx + r, cy + r], start=0, end=180, fill=BRANCO, width=esp)
    d.line([(cx - r, cy), (cx - r, cy - 14 * SS)], fill=BRANCO, width=esp)
    lado = 10 * SS
    d.polygon([(cx - r, cy - 30 * SS), (cx - r + lado, cy - 13 * SS),
               (cx - r - lado, cy - 13 * SS)], fill=BRANCO)

    f = ImageFont.truetype(achar_fonte("Bold"), 27 * SS)
    tw = d.textlength(texto, font=f)
    d.text(((78 * SS + pw * SS - tw) / 2, 26 * SS), texto, font=f, fill=BRANCO)
    return im.resize((pw, ph), Image.LANCZOS)


def desenhar_selo_portal(logo=None):
    """Selo circular do portal. Usa o logo real se informado; senão desenha o fallback."""
    lado = 118
    if logo and os.path.exists(logo):
        return Image.open(logo).convert("RGBA").resize((lado, lado), Image.LANCZOS)

    im = Image.new("RGBA", (lado * SS, lado * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, lado * SS, lado * SS], fill=BRANCO)
    c, r = lado * SS / 2, lado * SS * 0.25
    cy = c - lado * SS * 0.07                      # play um pouco acima do centro
    d.ellipse([c - r, cy - r, c + r, cy + r], fill=AZUL_SELO)
    t = r * 0.44
    d.polygon([(c - t * 0.65, cy - t), (c - t * 0.65, cy + t), (c + t, cy)], fill=BRANCO)

    # texto: reduz até caber na corda do círculo naquela altura
    cabe = lado * SS * 0.62
    tam = int(11 * SS)
    while tam > 4 and max(d.textlength(s, font=ImageFont.truetype(achar_fonte("Bold"), tam))
                          for s in ("PORTAL", "JÚNIOR ARRAIS")) > cabe:
        tam -= 2
    f = ImageFont.truetype(achar_fonte("Bold"), tam)
    y = cy + r + lado * SS * 0.06
    for linha in ("PORTAL", "JÚNIOR ARRAIS"):
        tw = d.textlength(linha, font=f)
        d.text((c - tw / 2, y), linha, font=f, fill=AZUL_SELO)
        y += tam * 1.1
    return im.resize((lado, lado), Image.LANCZOS)


def listras_rodape():
    """Listras vermelhas diagonais decorativas nas pontas do rodapé."""
    alt = H - FAIXA_B
    im = Image.new("RGBA", (W * 2, alt * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for bloco_x in (0, (W - 150) * 2):
        for i in range(5):
            x = bloco_x + i * 30
            d.polygon([(x, alt * 2), (x + 16, alt * 2), (x + 16 + 26, 0), (x + 26, 0)],
                      fill=VERMELHO + (255,))
    return im.resize((W, alt), Image.LANCZOS)


def gerar(saida, titulo, chapeu, foto_fundo=None, foto=None, credito=None,
          selo=True, texto_selo="LINK NOS STORIES", logo=None):
    im = Image.new("RGB", (W, H), ESCURO)

    # 1. imagem de cima
    im.paste(cortar_foto(foto_fundo) if foto_fundo and os.path.exists(foto_fundo)
             else fundo_marca(), (0, 0))

    # 2. faixa azul da manchete e rodapé escuro
    im.paste(faixa_azul(), (0, FOTO_H))
    ImageDraw.Draw(im).rectangle([0, FAIXA_B, W, H], fill=ESCURO)

    im = im.convert("RGBA")
    im.alpha_composite(listras_rodape(), (0, FAIXA_B))

    # 3. recorte do Júnior à esquerda, sangrando no rodapé
    if foto and os.path.exists(foto):
        ft = Image.open(foto).convert("RGBA")
        alt = 900
        ft = ft.resize((int(ft.width * alt / ft.height), alt), Image.LANCZOS)
        im.alpha_composite(ft, (-108, FAIXA_B - alt))

    im.alpha_composite(desenhar_selo_portal(logo), (214, FOTO_H + 60))
    if selo:
        im.alpha_composite(desenhar_selo_stories(texto_selo), (48, 48))

    im = im.convert("RGB")
    d = ImageDraw.Draw(im)
    bold, reg = achar_fonte("Bold"), achar_fonte("Regular")

    # 4. linha vertical branca separando o recorte da coluna de texto
    d.rectangle([352, FOTO_H + 18, 357, FAIXA_B - 14], fill=BRANCO)

    # 5. chapéu: tarja vermelha encostada no topo da faixa azul
    if chapeu:
        tam_ch = 31
        while tam_ch > 20:
            f_ch = ImageFont.truetype(bold, tam_ch)
            if d.textlength(chapeu.upper(), font=f_ch) <= 340 - 32:
                break
            tam_ch -= 1
        f_ch = ImageFont.truetype(bold, tam_ch)
        topo_ch = FOTO_H - CHAPEU_H          # tarja encostada no topo da faixa azul
        d.rectangle([MARGEM_X, topo_ch, MARGEM_X + 340, topo_ch + CHAPEU_H], fill=VERMELHO)
        tw = d.textlength(chapeu.upper(), font=f_ch)
        d.text((MARGEM_X + (340 - tw) / 2, topo_ch + (CHAPEU_H - tam_ch * 1.25) / 2),
               chapeu.upper(), font=f_ch, fill=BRANCO)

    # 6. manchete com autoajuste, centralizada na faixa
    f_tit, linhas, alt_bloco = ajustar_manchete(
        d, titulo.upper(), bold, COL_W, altura_max=FAIXA_B - FOTO_H - 28)
    y = FOTO_H + (FAIXA_B - FOTO_H - alt_bloco) // 2
    passo = int(f_tit.size * 1.09)
    for l in linhas:
        d.text((MARGEM_X, y), l, font=f_tit, fill=BRANCO)
        y += passo

    # 7. rodapé: endereço do portal
    f_cta = ImageFont.truetype(bold, 30)
    cta = "Acesse: portaljuniorarrais.com.br"
    tw = d.textlength(cta, font=f_cta)
    d.rectangle([MARGEM_X, FAIXA_B + 16, MARGEM_X + tw + 60, FAIXA_B + 62], fill=VERMELHO)
    d.text((MARGEM_X + 30, FAIXA_B + 24), cta, font=f_cta, fill=BRANCO)

    # 8. crédito da foto
    if credito:
        f_cr = ImageFont.truetype(reg, 19)
        cw = d.textlength(credito, font=f_cr)
        d.text((W - cw - 20, FOTO_H - 30), credito, font=f_cr, fill=(228, 234, 240))

    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    im.save(saida, "PNG")
    print(f"Arte de feed salva: {saida}  ({len(linhas)} linha(s), corpo {f_tit.size}px)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", required=True)
    ap.add_argument("--titulo", required=True)
    ap.add_argument("--chapeu", default=None)
    ap.add_argument("--foto-fundo", dest="foto_fundo", default=None)
    ap.add_argument("--foto", default=None)
    ap.add_argument("--credito", default=None)
    ap.add_argument("--sem-selo", dest="sem_selo", action="store_true")
    ap.add_argument("--texto-selo", dest="texto_selo", default="LINK NOS STORIES")
    ap.add_argument("--logo", default=None, help="logo circular do portal (PNG); sem ele, desenha o fallback")
    ap.add_argument("--formato", default="3x4", choices=["3x4", "4x5"],
                    help="3x4 (1080x1440, padrao do perfil) ou 4x5 (1080x1350, exigido pela API do Instagram)")
    a = ap.parse_args()

    # Formato 4:5 (1080x1350) para publicacao via API do Instagram. A doc da Meta
    # aceita de 4:5 a 1.91:1; o 3:4 fica FORA da faixa e a imagem sai recortada.
    # Encurtamos so a area da FOTO: faixa azul (236px) e rodape (84px) ficam
    # intactos, entao chapeu, manchete, selo e CTA nao perdem nada.
    if a.formato == "4x5":
        globals()["H"] = 1350
        globals()["FAIXA_B"] = 1350 - 84          # 1266
        globals()["FOTO_H"] = 1350 - 84 - 236     # 1030

    gerar(a.saida, a.titulo, a.chapeu, a.foto_fundo, a.foto, a.credito,
          selo=not a.sem_selo, texto_selo=a.texto_selo, logo=a.logo)
