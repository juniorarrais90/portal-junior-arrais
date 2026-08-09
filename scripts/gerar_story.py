#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera a arte 9:16 (1080x1920) da notícia para Stories, no estilo da capa do portal.
Uso:
  python3 scripts/gerar_story.py --saida img/stories/<slug>.png --categoria "FGTS" \
      --linhas "LINHA 1|LINHA 2|LINHA 3" --foto-fundo img/banco/foto.jpg \
      [--credito "Foto: Fulano/Agência Brasil"]
"""
import argparse, glob
from PIL import Image, ImageDraw, ImageFilter

CIANO=(43,218,253); VERMELHO=(226,59,59); W,H=1080,1920

def fonte(peso, tam):
    from PIL import ImageFont
    pads=[f"/sessions/*/mnt/.claude/skills/canvas-design/canvas-fonts/Outfit-{peso}.ttf"]
    for p in pads:
        h=glob.glob(p)
        if h: return ImageFont.truetype(h[0], tam)
    base="/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if peso=="Bold" else "")
    from PIL import ImageFont as F
    return F.truetype(base, tam)

def cover(im,w,h):
    r=max(w/im.width,h/im.height)
    im=im.resize((int(im.width*r)+1,int(im.height*r)+1))
    x=(im.width-w)//2; y=(im.height-h)//2
    return im.crop((x,y,x+w,y+h))

ap=argparse.ArgumentParser()
ap.add_argument("--saida",required=True); ap.add_argument("--categoria",required=True)
ap.add_argument("--linhas",required=True); ap.add_argument("--foto-fundo",dest="foto",required=True)
ap.add_argument("--credito",default="")
ap.add_argument("--encaixe",default="cobrir",choices=["cobrir","conter"])
a=ap.parse_args()

base=Image.open(a.foto).convert("RGB")
if a.encaixe=="conter":
    # ARTE COM TEXTO: nada de recorte nem de manchete por cima. A arte entra
    # inteira, encostada na largura, e o texto do story fica embaixo, no fundo
    # chapado da marca. Em 9:16 o recorte "cobrir" comeria as laterais da arte.
    TOPO,BASE=(13,30,50),(24,48,74)
    col=Image.new("RGB",(1,H))
    for y in range(H):
        k=y/H
        col.putpixel((0,y),tuple(int(TOPO[i]+(BASE[i]-TOPO[i])*k) for i in range(3)))
    im=col.resize((W,H))
    k=min(W/base.width,(H*0.52)/base.height)
    art=base.resize((int(base.width*k),int(base.height*k)),Image.LANCZOS)
    x0,y0=(W-art.width)//2,int(H*0.30)-art.height//2
    im.paste(Image.new("RGB",(art.width+24,art.height+24),(6,16,28)),(x0-12,y0-12))
    im.paste(art,(x0,y0))
else:
    im=cover(base,W,H)
    # degradê escuro embaixo e leve no topo
    ov=Image.new("L",(W,H),0); d=ImageDraw.Draw(ov)
    for y in range(H):
        v=0
        if y>H*0.45: v=int(230*((y-H*0.45)/(H*0.55))**1.3)
        if y<H*0.14: v=max(v,int(120*(1-y/(H*0.14))))
        d.line([(0,y),(W,y)],fill=v)
    im=Image.composite(Image.new("RGB",(W,H),(10,18,28)),im,ov)
dr=ImageDraw.Draw(im)

# chip vermelho
f_chip=fonte("Bold",44)
tx=a.categoria.upper(); tw=dr.textlength(tx,font=f_chip)
dr.rounded_rectangle([60,90,60+tw+56,90+86],radius=43,fill=VERMELHO)
dr.text((60+28,90+20),tx,font=f_chip,fill=(255,255,255))

# manchete (fonte diminui até caber na largura)
linhas=a.linhas.split("|"); tam=84
while tam>40:
    f_t=fonte("Bold",tam)
    if max(dr.textlength(l,font=f_t) for l in linhas) <= W-180: break
    tam-=4
lh=int(tam*1.2); y0=H-330-lh*len(linhas)

# faixa do endereço, acima da manchete: bloco azul com globo + tarja amarela.
# Serve para quem vê o story sem tocar em nada — o endereço fica visível sempre,
# independente da figurinha de link (que a API não publica).
AMARELO=(255,200,0); AZUL_FAIXA=(11,58,138)
f_site=fonte("Bold",40)
site="PORTALJUNIORARRAIS.COM.BR"
sw=dr.textlength(site,font=f_site)
fx0,fy0=100,y0-108
alt_f=68
dr.rectangle([fx0,fy0,fx0+alt_f,fy0+alt_f],fill=AZUL_FAIXA)
# globo simplificado
cx,cy,r=fx0+alt_f/2,fy0+alt_f/2,alt_f*0.30
dr.ellipse([cx-r,cy-r,cx+r,cy+r],outline=AMARELO,width=4)
dr.line([(cx-r,cy),(cx+r,cy)],fill=AMARELO,width=4)
dr.ellipse([cx-r*0.5,cy-r,cx+r*0.5,cy+r],outline=AMARELO,width=4)
dr.rectangle([fx0+alt_f,fy0,fx0+alt_f+sw+48,fy0+alt_f],fill=AMARELO)
dr.text((fx0+alt_f+24,fy0+13),site,font=f_site,fill=AZUL_FAIXA)

dr.rectangle([60,y0+8,74,y0+lh*len(linhas)-6],fill=CIANO)
for i,l in enumerate(linhas):
    dr.text((100,y0+i*lh),l,font=f_t,fill=(255,255,255),stroke_width=2,stroke_fill=(0,0,0))

# assinatura e crédito
dr.text((100,H-200),"PORTAL JÚNIOR ARRAIS",font=fonte("Bold",40),fill=CIANO)
dr.text((100,H-140),"portaljuniorarrais.com.br",font=fonte("Regular",34),fill=(220,230,240))
if a.credito:
    f_c=fonte("Regular",28); cw=dr.textlength(a.credito,font=f_c)
    dr.text((W-60-cw,H-110),a.credito,font=f_c,fill=(200,210,220))
im.save(a.saida,"PNG")
print("Story salvo:",a.saida)
