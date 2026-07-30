#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Garante a barra de compartilhamento (WhatsApp, Facebook, Telegram, Stories, copiar
link) em todas as matérias de noticias/. Também garante o site.js na página.
Roda junto com a rotina de publicação: python3 scripts/aplicar_compartilhar.py
"""
import os, re, urllib.parse

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INICIO = "<!-- COMPARTILHAR (Portal Junior Arrais) -->"
FIM = "<!-- fim COMPARTILHAR -->"

MODELO = """      %s
      <div class="share-bar">
        <span class="share-titulo">Gostou? Compartilhe esta not&iacute;cia:</span>
        <div class="share-botoes">
          <a class="share-btn share-wa" target="_blank" rel="noopener" href="https://api.whatsapp.com/send?text={WA}">WhatsApp</a>
          <a class="share-btn share-fb" target="_blank" rel="noopener" href="https://www.facebook.com/sharer/sharer.php?u={URL}">Facebook</a>
          <a class="share-btn share-tg" target="_blank" rel="noopener" href="https://t.me/share/url?url={URL}&text={TIT}">Telegram</a>
          <button class="share-btn share-ig" type="button" onclick="pjaStories(this)">Instagram / Stories</button>
          <button class="share-btn share-copiar" type="button" onclick="pjaCopiarLink(this)">Copiar link</button>
        </div>
      </div>
      %s
""" % (INICIO, FIM)

def processa(caminho):
    h = open(caminho, encoding='utf-8').read()
    tit = re.search(r'<meta property="og:title" content="([^"]*)"', h)
    url = re.search(r'<link rel="canonical" href="([^"]*)"', h)
    if not (tit and url): return False
    t = urllib.parse.quote(tit.group(1)); u = urllib.parse.quote(url.group(1))
    bloco = MODELO.replace('{URL}', u).replace('{TIT}', t).replace('{WA}', t + '%0A%0A' + u)
    # remove versão antiga, se houver
    h = re.sub(re.escape(INICIO) + r'.*?' + re.escape(FIM) + r'\n?', '', h, flags=re.S)
    alvo = '      <!-- ADSENSE: espaço de anúncio dentro da matéria -->'
    if alvo not in h: return False
    h = h.replace(alvo, bloco + alvo, 1)
    if 'site.js' not in h:
        h = h.replace('</body>', '  <script src="../site.js"></script>\n</body>', 1)
    open(caminho, 'w', encoding='utf-8').write(h)
    return True

if __name__ == '__main__':
    ok = 0
    for f in sorted(os.listdir(os.path.join(RAIZ, 'noticias'))):
        if f.endswith('.html'):
            if processa(os.path.join(RAIZ, 'noticias', f)): ok += 1
            else: print('  AVISO: nao processada:', f)
    print('Barra de compartilhamento aplicada em %d materias.' % ok)
