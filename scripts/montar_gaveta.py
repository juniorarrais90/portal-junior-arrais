#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
montar_gaveta.py — Portal Júnior Arrais

Monta a GRADE SEMANAL de matérias de gaveta (feita no domingo) a partir de:
  - um JSON por matéria (--materias), com os campos:
      num, slug, titulo, descricao, categoria, titulo_capa, titulo_feed, chapeu,
      linhas_story ("a | b | c | d"), alt, corpo (HTML), legenda (Instagram),
      banco (nome do arquivo para img/banco, sem extensão),
      topo (fração 0-1 da altura onde começa a faixa da capa; padrão 0.05)
  - a foto 3:4 de cada matéria (--masters/NN.png, NN = num com 2 dígitos)

e gera, dentro do repositório:
  - agendadas/<slug>.html.gz          página pronta, guardada até a hora (robô: publicar_agendadas.py)
  - agendadas/agenda.json             acrescenta os itens (não apaga os que já estão lá)
  - img/<slug>.png, img/stories/, img/feed/, img/feed45/   as quatro artes
  - img/youtube/<slug>.jpg            arte quadrada dos posts da aba Postagens do YouTube
  - img/banco/<banco>.png + linha no img/banco/CREDITOS.md
  - instagram/legendas, facebook/legendas e os itens nas duas filas
  - <trabalho>/youtube.json           texto, data e hora de cada post do YouTube

Grade: 3 matérias por dia a partir de --inicio (segunda). Site às 8h/14h/20h,
Instagram às 9h30/15h30/21h30, Facebook 15 min depois do Instagram, YouTube às
9h/15h/21h (horário de Brasília). num 1-3 = 1º dia, 4-6 = 2º dia etc.

Uso:
  python3 scripts/montar_gaveta.py --materias ~/w/materias --masters ~/w/master \
      --inicio 2026-10-19 --trabalho ~/w

É idempotente por slug: rodar de novo não duplica agenda, filas nem créditos.
"""
import argparse, glob, gzip, html, json, os, re, subprocess, sys, urllib.parse
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://portaljuniorarrais.com.br'
MESES = ['jan.', 'fev.', 'mar.', 'abr.', 'mai.', 'jun.', 'jul.', 'ago.', 'set.', 'out.', 'nov.', 'dez.']
SLOT_SITE = [(8, 0), (14, 0), (20, 0)]
SLOT_IG = [(9, 30), (15, 30), (21, 30)]
SLOT_YT = ['9:00 AM', '3:00 PM', '9:00 PM']
FONTE = os.path.join(RAIZ, 'fontes', 'Outfit-Bold.ttf')


def esc(s): return html.escape(s, quote=True)
def data_ext(d): return f'{d.day} de {MESES[d.month-1]} de {d.year}'
def utc(d, hm): return d.replace(hour=hm[0], minute=hm[1]) + timedelta(hours=3)
def iso(d): return d.strftime('%Y-%m-%dT%H:%M:%SZ')


def py(*a):
    subprocess.run([sys.executable, *a], cwd=RAIZ, check=True, stdout=subprocess.DEVNULL)


def master_capa(src, topo, dst):
    """A área de foto da capa é 1200x455 (2,637:1): recorta já nessa proporção a partir de `topo`."""
    im = Image.open(src).convert('RGB'); W, H = im.size
    h = int(W / (1200 / 455.0)); y = max(0, min(int(topo * H), H - h))
    im.crop((0, y, W, y + h)).save(dst, quality=95)


def master_feed(src, ratio, dst):
    """Topo da foto na proporção da área do feed, com 10% de folga para o selo LINK NOS STORIES."""
    im = Image.open(src).convert('RGB'); W, H = im.size
    alvo = int(W / ratio); d = int(alvo * 0.10)
    novo = Image.new('RGB', (W, alvo))
    novo.paste(im.crop((0, 0, W, 4)).resize((W, d), Image.BILINEAR), (0, 0))
    novo.paste(im.crop((0, 0, W, alvo - d)), (0, d)); novo.save(dst, quality=95)


def master_story(src, dst):
    """8% de folga no alto para o chip da categoria não tapar placa/letreiro."""
    im = Image.open(src).convert('RGB'); W, H = im.size; d = int(H * 0.08)
    novo = Image.new('RGB', (W, H + d))
    novo.paste(im.crop((0, 0, W, 4)).resize((W, d), Image.BILINEAR), (0, 0)); novo.paste(im, (0, d))
    novo.save(dst, quality=95)


def arte_youtube(slug, dst):
    S = Image.new('RGB', (1080, 1080), (30, 42, 56))
    S.paste(Image.open(os.path.join(RAIZ, 'img', slug + '.png')).convert('RGB').resize((1080, 608), Image.LANCZOS), (0, 236))
    d = ImageDraw.Draw(S)
    d.rectangle((0, 0, 1080, 10), fill=(44, 137, 231))
    lg = Image.open(os.path.join(RAIZ, 'img', 'logo-portal.png')).convert('RGBA')
    lg = lg.resize((int(lg.width * 140 / lg.height), 140)); S.paste(lg, (60, 48), lg)
    d.text((160, 78), 'PORTAL JÚNIOR ARRAIS', font=ImageFont.truetype(FONTE, 46), fill='white')
    d.text((160, 134), 'Seu lugar de informação', font=ImageFont.truetype(FONTE, 32), fill=(43, 218, 253))
    f2 = ImageFont.truetype(FONTE, 44); t = 'LEIA A MATÉRIA: LINK NO POST'; w = d.textlength(t, font=f2)
    d.rounded_rectangle(((1080 - w) / 2 - 40, 900, (1080 + w) / 2 + 40, 1000), radius=50, fill=(226, 59, 59))
    d.text(((1080 - w) / 2, 922), t, font=f2, fill='white')
    S.save(dst, quality=90)


def molde_atual():
    """Matéria mais recente que não é guia, pela ordem do noticias.html."""
    arq = open(os.path.join(RAIZ, 'noticias.html'), encoding='utf-8').read()
    for s in re.findall(r'href="noticias/([^"]+)\.html"', arq):
        if not s.startswith('guia-') and os.path.exists(os.path.join(RAIZ, 'noticias', s + '.html')):
            return s
    raise SystemExit('Nenhuma matéria para servir de molde.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--materias', required=True); ap.add_argument('--masters', required=True)
    ap.add_argument('--inicio', required=True, help='data do 1º dia da grade, AAAA-MM-DD')
    ap.add_argument('--trabalho', required=True, help='pasta de trabalho fora do repositório')
    a = ap.parse_args()
    dia0 = datetime.strptime(a.inicio, '%Y-%m-%d')
    mst = os.path.join(a.trabalho, 'mst'); os.makedirs(mst, exist_ok=True)

    MOLDE = molde_atual()
    molde = open(os.path.join(RAIZ, 'noticias', MOLDE + '.html'), encoding='utf-8').read()
    titulo_molde = re.search(r'<h1>(.*?)</h1>', molde, re.S).group(1)
    cab = molde[:molde.find('<main>') + len('<main>')]
    cauda = molde[molde.find('<!-- fim COMPARTILHAR -->'):]
    autor = molde[molde.find('<!-- AUTOR (Portal Junior Arrais) -->'):molde.find('<!-- FIM AUTOR -->') + len('<!-- FIM AUTOR -->')]
    assert cab and cauda and autor, 'molde sem os marcadores esperados'

    for p in ('agendadas', 'img/stories', 'img/feed', 'img/feed45', 'img/youtube', 'img/banco',
              'instagram/legendas', 'facebook/legendas'):
        os.makedirs(os.path.join(RAIZ, p), exist_ok=True)
    ag_p = os.path.join(RAIZ, 'agendadas', 'agenda.json')
    ag = json.load(open(ag_p, encoding='utf-8')) if os.path.exists(ag_p) else {
        '_leia_me': 'Matérias que o robô (scripts/publicar_agendadas.py) põe no ar no horário de publicar_em (UTC). '
                    'As páginas ficam compactadas em agendadas/<slug>.html.gz até a hora.', 'agenda': []}
    filas = {r: json.load(open(os.path.join(RAIZ, r, 'fila.json'), encoding='utf-8')) for r in ('instagram', 'facebook')}
    cred_p = os.path.join(RAIZ, 'img', 'banco', 'CREDITOS.md')
    cred = open(cred_p, encoding='utf-8').read() if os.path.exists(cred_p) else ''
    youtube = []

    for f in sorted(glob.glob(os.path.join(a.materias, '*.json'))):
        m = json.load(open(f, encoding='utf-8')); n = m['num']; slug = m['slug']
        dia = dia0 + timedelta(days=(n - 1) // 3); k = (n - 1) % 3
        dext = data_ext(dia); url = f'{SITE}/noticias/{slug}.html'; img = f'{SITE}/img/{slug}.png'
        t, d, cat = m['titulo'], m['descricao'], m['categoria']

        # página
        c = re.sub(r'<title>.*?</title>', f'<title>{esc(t)}</title>', cab, flags=re.S)
        for prop, val in (('name="description"', d), ('property="og:title"', t), ('property="og:description"', d),
                          ('property="og:image"', img), ('property="og:url"', url)):
            c = re.sub(r'(<meta ' + prop + r' content=")[^"]*', lambda x, v=val: x.group(1) + esc(v), c)
        c = re.sub(r'(<link rel="canonical" href=")[^"]*', lambda x: x.group(1) + url, c)
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', c, re.S).group(1))
        ld.update({'headline': t, 'description': d, 'image': [img], 'datePublished': dia.strftime('%Y-%m-%d'),
                   'dateModified': dia.strftime('%Y-%m-%d'), 'mainEntityOfPage': url, 'articleSection': cat})
        c = re.sub(r'(<script type="application/ld\+json">).*?(</script>)',
                   lambda x: x.group(1) + '\n' + json.dumps(ld, ensure_ascii=False, indent=2) + '\n  ' + x.group(2), c, flags=re.S)
        tq = urllib.parse.quote(t, safe='')
        share = f'''      <div class="share-bar">
        <span class="share-titulo">Gostou? Compartilhe esta not&iacute;cia:</span>
        <div class="share-botoes">
          <a class="share-btn share-wa" target="_blank" rel="noopener" href="https://api.whatsapp.com/send?text={tq}%0A%0A{url}">WhatsApp</a>
          <button class="share-btn share-fb" type="button" onclick="pjaFacebook(this)">Facebook</button>
          <a class="share-btn share-tg" target="_blank" rel="noopener" href="https://t.me/share/url?url={url}&amp;text={tq}">Telegram</a>
          <button class="share-btn share-ig share-arte" type="button" onclick="pjaBaixarArte(this)">Baixar arte 9:16</button>
          <button class="share-btn share-copiar" type="button" onclick="pjaCopiarLink(this)">Copiar link</button>
        </div>
      </div>
'''
        corpo = '\n'.join(l.strip() for l in m['corpo'].split('\n') if l.strip())
        art = f'''
    <article class="artigo">
      <a class="voltar" href="../">&larr; Voltar para o in&iacute;cio</a>
      <div><span class="chip">{esc(cat)}</span></div>
      <h1>{esc(t)}</h1>
      <div class="meta"><img src="../img/junior-avatar.png" alt="J&uacute;nior Arrais" class="autor-foto"> Por <a href="../sobre.html#autor" class="autor-link">J&uacute;nior Arrais</a> &middot; {dext}</div>
      <div class="artigo-capa"><img src="../img/{slug}.png" alt="{esc(m['alt'])}"></div>
      <div class="artigo-conteudo">
{corpo}
      </div>
      {autor.replace(MOLDE, slug)}

'''
        pagina = c + '\n' + art + share + '      ' + cauda
        assert MOLDE not in pagina and titulo_molde not in pagina, f'resto do molde em {slug}'
        with gzip.open(os.path.join(RAIZ, 'agendadas', slug + '.html.gz'), 'wt', encoding='utf-8') as g:
            g.write(pagina)

        # artes
        src = os.path.join(a.masters, f'{n:02d}.png')
        banco = m.get('banco') or slug
        Image.open(src).save(os.path.join(RAIZ, 'img', 'banco', banco + '.png'), optimize=True)
        mc, ms, m34, m45 = (os.path.join(mst, f'{n:02d}_{x}.jpg') for x in ('capa', 'st', 'f34', 'f45'))
        master_capa(src, float(m.get('topo', 0.05)), mc); master_story(src, ms)
        master_feed(src, 1080 / 1120, m34); master_feed(src, 1080 / 1030, m45)
        py('scripts/gerar_capa_faixa.py', '--saida', f'img/{slug}.png', '--titulo', m['titulo_capa'],
           '--categoria', cat, '--foto-fundo', mc, '--encaixe', 'cobrir')
        py('scripts/gerar_story.py', '--saida', f'img/stories/{slug}.png', '--categoria', cat,
           '--linhas', '|'.join(x.strip() for x in m['linhas_story'].split('|')), '--foto-fundo', ms, '--encaixe', 'cobrir')
        for fmt, pasta, mf in (('3x4', 'feed', m34), ('4x5', 'feed45', m45)):
            py('scripts/gerar_post_feed.py', '--formato', fmt, '--saida', f'img/{pasta}/{slug}.png',
               '--chapeu', m['chapeu'], '--titulo', m['titulo_feed'], '--foto-fundo', mf,
               '--foto', 'img/recorte-junior.png', '--logo', 'img/logo-portal.png')
        arte_youtube(slug, os.path.join(RAIZ, 'img', 'youtube', slug + '.jpg'))

        # legendas
        leg = m['legenda'].strip()
        open(os.path.join(RAIZ, 'instagram', 'legendas', slug + '.txt'), 'w', encoding='utf-8').write(leg + '\n')
        tags = re.findall(r'#\S+', leg)
        fb = re.sub(r'\n*(#\S+\s*)+$', '', leg).replace('📲 A matéria completa está no link dos stories.',
                                                        f'📲 Leia a matéria completa: {url}')
        if url not in fb:
            fb += f'\n\n📲 Leia a matéria completa: {url}'
        open(os.path.join(RAIZ, 'facebook', 'legendas', slug + '.txt'), 'w', encoding='utf-8').write(fb + '\n\n' + ' '.join(tags[:3]) + '\n')

        # agenda e filas (sem duplicar)
        h_site = dia.replace(hour=SLOT_SITE[k][0], minute=SLOT_SITE[k][1])
        h_ig = dia.replace(hour=SLOT_IG[k][0], minute=SLOT_IG[k][1]); h_fb = h_ig + timedelta(minutes=15)
        if slug not in {i['slug'] for i in ag['agenda']}:
            ag['agenda'].append({'slug': slug, 'titulo': t, 'categoria': cat, 'data_exibicao': dext, 'alt': m['alt'],
                                 'publicar_em': iso(h_site + timedelta(hours=3)),
                                 'horario_brasilia': h_site.strftime('%d/%m %H:%M'), 'status': 'pendente'})
        if slug not in {i['slug'] for i in filas['instagram']['fila']}:
            filas['instagram']['fila'].append({'slug': slug, 'titulo': t, 'publicar_em': iso(h_ig + timedelta(hours=3)),
                                               'horario_brasilia': h_ig.strftime('%d/%m %H:%M'), 'alt_text': t, 'status': 'pendente'})
        if slug not in {i['slug'] for i in filas['facebook']['fila']}:
            filas['facebook']['fila'].append({'slug': slug, 'titulo': t, 'link': url, 'arte': f'img/feed45/{slug}.png',
                                              'publicar_em': iso(h_fb + timedelta(hours=3)),
                                              'horario_brasilia': h_fb.strftime('%d/%m %H:%M'), 'status': 'pendente'})
        if f'| {slug} |' not in cred:
            cred += f'| `{banco}.png` ({Image.open(src).width}x{Image.open(src).height}) | {m["alt"]} | IA — acervo próprio | {m.get("tipo_cena", "")} | {slug} |\n'
        youtube.append({'num': n, 'slug': slug, 'data': dia.strftime('%b %d').replace(' 0', ' '), 'dia': dia.day,
                        'hora': SLOT_YT[k], 'imagem': f'{SITE}/img/youtube/{slug}.jpg',
                        'texto': leg.split('\n')[0] + '\n\nEntenda a regra completa no Portal Júnior Arrais:\n' + url + ' '})
        print('ok', n, slug)

    json.dump(ag, open(ag_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    for r, d in filas.items():
        with open(os.path.join(RAIZ, r, 'fila.json'), 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False, indent=2); fh.write('\n')
    open(cred_p, 'w', encoding='utf-8').write(cred)
    json.dump(youtube, open(os.path.join(a.trabalho, 'youtube.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('Molde usado:', MOLDE)


if __name__ == '__main__':
    main()
