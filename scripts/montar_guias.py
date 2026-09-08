"""Monta noticias/<slug>.html para cada guia em guias-fonte/g*.html (corpo + bloco <!--META ... META-->) usando a matéria
MOLDE como base. Para REVISAR um guia: editar o arquivo em guias-fonte/, ajustar a data de revisão no fecho, rodar este
script, depois scripts/gerar_relacionadas.py e scripts/aplicar_links_contextuais.py. Ajustar MOLDE e DATA_* abaixo."""
import re, glob, os, json, html as H, urllib.parse as U
REPO=os.path.expanduser('~/repo'); os.chdir(REPO)
MOLDE='noticias/tempo-de-contribuicao-por-que-conferir-o-historico-do-inss.html'
molde=open(MOLDE,encoding='utf-8').read()
DATA_ISO='2026-09-08'; DATA_EXT='8 de set. de 2026'
BANNERS={'Bolsa Família':'Precisando de um dinheiro extra?','BPC/LOAS':'O orçamento da família apertou?','Benefícios':'Precisando de um dinheiro extra?','Pé-de-Meia':'As contas da casa apertaram?','Gás do Povo':'O orçamento do mês não fechou?','INSS':'Aposentado e precisando de crédito?','Minha Casa Minha Vida':'Precisando de crédito para a casa?','Direitos':'Precisando de crédito com segurança?'}
def esc(s): return H.escape(s, quote=False)
def parse(path):
    s=open(path,encoding='utf-8').read()
    m=re.search(r'<!--META(.*?)META-->',s,re.S); meta={}
    for ln in m.group(1).strip().splitlines():
        k,v=ln.split(':',1); meta[k.strip()]=v.strip()
    corpo=s[m.end():].strip()
    return meta,corpo
guias=[]
for f in sorted(glob.glob(os.path.expanduser('guias-fonte/g*.html'))):
    meta,corpo=parse(f); slug=meta['slug']; tit=meta['titulo']; desc=meta['descricao']; cat=meta['categoria']
    url=f'https://portaljuniorarrais.com.br/noticias/{slug}.html'
    s=molde
    # head
    s=re.sub(r'<title>.*?</title>', f'<title>{esc(tit)}</title>', s, count=1, flags=re.S)
    s=re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{esc(desc)}">', s, count=1)
    s=re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">', s, count=1)
    s=re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{esc(tit)}">', s, count=1)
    s=re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{esc(desc)}">', s, count=1)
    s=re.sub(r'<meta property="og:image" content="[^"]*">', f'<meta property="og:image" content="https://portaljuniorarrais.com.br/img/{slug}.png">', s, count=1)
    s=re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">', s, count=1)
    # json-ld
    def ld(m):
        d=json.loads(m.group(1))
        d['@type']='Article'; d['headline']=tit; d['description']=desc
        d['image']=[f'https://portaljuniorarrais.com.br/img/{slug}.png']
        d['datePublished']=DATA_ISO; d['dateModified']=DATA_ISO; d['mainEntityOfPage']=url
        d['articleSection']=cat
        return '<script type="application/ld+json">\n'+json.dumps(d,ensure_ascii=False,indent=2)+'\n  </script>'
    s=re.sub(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', ld, s, count=1, flags=re.S)
    # chip, h1, meta, capa
    s=re.sub(r'<span class="chip">[^<]*</span>', f'<span class="chip">Guia · {esc(cat)}</span>', s, count=1)
    s=re.sub(r'<h1>.*?</h1>', f'<h1>{esc(tit)}</h1>', s, count=1, flags=re.S)
    s=re.sub(r'(class="autor-link">J&uacute;nior Arrais</a> &middot; )[^<]*(</div>)', lambda m: m.group(1)+esc(DATA_EXT)+m.group(2), s, count=1)
    s=re.sub(r'<div class="artigo-capa"><img src="[^"]*" alt="[^"]*"></div>', f'<div class="artigo-capa"><img src="../img/{slug}.png" alt="{esc(tit)}"></div>', s, count=1)
    # conteúdo
    s=re.sub(r'(<div class="artigo-conteudo">).*?(\n\s*</div>\s*\n\s*<!-- AUTOR)', lambda m: m.group(1)+'\n'+corpo+'\n'+m.group(2), s, count=1, flags=re.S)
    # autor: assunto do e-mail
    s=re.sub(r'subject=Correcao: [a-z0-9-]+', f'subject=Correcao: {slug}', s)
    # relacionadas: remover bloco (gerar_relacionadas recria)
    s=re.sub(r'\s*<!-- LEIA TAMBEM \(gerado por scripts/gerar_relacionadas\.py\) -->.*?<!-- fim LEIA TAMBEM -->', '\n', s, count=1, flags=re.S)
    assert 'leia-tambem' not in s, 'bloco leia-tambem sobrou'
    # share
    qt=U.quote(tit); qu=U.quote(url)
    s=re.sub(r'href="https://api\.whatsapp\.com/send\?text=[^"]*"', f'href="https://api.whatsapp.com/send?text={qt}%0A%0A{qu}"', s, count=1)
    s=re.sub(r'href="https://t\.me/share/url\?url=[^"]*"', f'href="https://t.me/share/url?url={qu}&amp;text={qt}"', s, count=1)
    s=re.sub(r'(<span class="share-titulo">)[^<]*(</span>)', r'\1Este guia pode ajudar alguém? Compartilhe:\2', s, count=1)
    # vídeo: remover bloco se houver
    s=re.sub(r'\s*<div class="video-relacionado">.*?</div>\s*</div>', '\n', s, count=1, flags=re.S)
    # banner
    s=re.sub(r'(<div class="banner-emprestimo">\s*<div>\s*<span class="chip-verde">Serviço</span>\s*<h2>)[^<]*(</h2>)', lambda m: m.group(1)+esc(BANNERS[cat])+m.group(2), s, count=1)
    # sanity: nada do molde
    for resto in ['As falhas mais comuns','hist&oacute;rico de contribui&ccedil;&otilde;es antes','Por que isso pesa tanto']:
        assert resto not in s, f'resto do molde: {resto}'
    open(f'noticias/{slug}.html','w',encoding='utf-8').write(s)
    guias.append(dict(meta, data=DATA_ISO))
    print('ok', slug, len(re.sub(r'<[^>]+>',' ',corpo).split()), 'palavras')
json.dump(guias, open('guias-fonte/guias.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
