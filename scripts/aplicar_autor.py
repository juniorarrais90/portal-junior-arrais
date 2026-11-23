"""Aplica em todas as páginas: caixa de autor (matérias), JSON-LD com url do autor e logo do publisher,
link no 'Por Júnior Arrais', rodapé com Termos de Uso, item 'Guias' no menu, remoção do rótulo PUBLICIDADE vazio.
Idempotente: pode rodar quantas vezes quiser."""
import re, glob, json, sys, os

INI = '      <!-- AUTOR (Portal Junior Arrais) -->'

# Autor como advogado, com todas as inscrições (Júnior, 21/11/2026, GEO: as IAs e o Google dão mais peso a
# autor com credencial em direito e dinheiro). Mudou uma OAB? Troque aqui e rode o script (o robô diário
# da página do Bolsa Família também roda).
OABS = [("MG", "193.054"), ("SP", "535.563"), ("RJ", "268.781"), ("PE", "71.237"), ("AL", "24.340-A"), ("PA", "41.782-A"), ("PR", "138.540")]  # PR: suplementar desde 23/11/2026
OABS_TEXTO = ", ".join(f"OAB/{uf} {n}" for uf, n in OABS[:-1]) + f" e OAB/{OABS[-1][0]} {OABS[-1][1]}"
SAME_AS = ["https://www.youtube.com/@juniorarrais.advogado", "https://www.instagram.com/juniorarraisadvogado/",
           "https://www.tiktok.com/@juniorarrais.advogado", "https://www.kwai.com/@juniorarraisadvogado",
           "https://www.facebook.com/advogadojuniorarrais/", "https://www.threads.com/@juniorarraisadvogado"]
AUTOR_LD = {"@type": "Person", "@id": "https://portaljuniorarrais.com.br/sobre.html#autor",
            "name": "Júnior Arrais", "url": "https://portaljuniorarrais.com.br/sobre.html",
            "jobTitle": "Advogado e editor responsável",
            "description": f"Advogado ({OABS_TEXTO}), atuante em direito previdenciário e trabalhista, e editor do Portal Júnior Arrais.",
            "knowsAbout": ["Direito previdenciário", "INSS", "Benefícios sociais", "Bolsa Família", "BPC/LOAS", "Direito do trabalho"],
            "hasCredential": [{"@type": "EducationalOccupationalCredential", "credentialCategory": "Inscrição na Ordem dos Advogados do Brasil",
                               "name": f"OAB/{uf} {n}",
                               "recognizedBy": {"@type": "Organization", "name": f"Ordem dos Advogados do Brasil, Seccional {uf}"}} for uf, n in OABS],
            "sameAs": SAME_AS}
FIM = '      <!-- FIM AUTOR -->'

def caixa_autor(slug):
    assunto = f'Correcao: {slug}'
    return f'''{INI}
      <div class="autor-box" id="autor">
        <img class="autor-box-foto" src="../img/junior-avatar.png" alt="Júnior Arrais" width="72" height="72" loading="lazy">
        <div class="autor-box-texto">
          <p class="autor-box-nome"><a href="../sobre.html#autor">Júnior Arrais</a> <span class="autor-box-cargo">· Advogado e editor do Portal Júnior Arrais</span></p>
          <p class="autor-box-bio">Advogado ({OABS_TEXTO}), atuante em direito previdenciário e trabalhista, e comunicador de Ubá (MG). Escreve todos os dias sobre benefícios sociais, INSS, trabalho e economia do dia a dia, a partir do Diário Oficial, de portarias e de fontes oficiais, em linguagem simples. Conheça a <a href="../sobre.html#linha-editorial">linha editorial</a> e a <a href="../sobre.html#correcoes">política de correções</a> do portal.</p>
          <p class="autor-box-links"><a href="mailto:contato@portaljuniorarrais.com.br?subject={assunto}">Encontrou um erro? Avise a redação</a></p>
        </div>
      </div>
{FIM}'''

def aplicar_materia(path):
    s = open(path, encoding='utf-8').read(); o = s
    slug = os.path.basename(path)[:-5]
    bloco = caixa_autor(slug)
    if INI in s and FIM in s:
        s = re.sub(r'\n?[ \t]*' + re.escape(INI) + r'.*?' + re.escape(FIM) + r'\n*', '\n', s, flags=re.S)
    if True:
        # depois do fechamento do artigo-conteudo: ANTES do marcador do gerar_relacionadas (senão ele apaga a caixa)
        for alvo in ['<!-- LEIA TAMBEM (gerado por scripts/gerar_relacionadas.py) -->', '      <aside class="leia-tambem"', '<div class="share-bar">']:
            i = s.find(alvo)
            if i != -1:
                recuo = s[:i].rsplit('\n', 1)[-1]
                s = s[:i - len(recuo)] + bloco + '\n\n' + recuo + s[i:]
                break
        else:
            print('SEM PONTO DE INSERÇÃO', path); return False
    # JSON-LD
    def fix_ld(m):
        try:
            d = json.loads(m.group(1))
        except Exception:
            return m.group(0)
        if d.get('@type') not in ('NewsArticle', 'Article'):
            return m.group(0)
        d['author'] = AUTOR_LD
        d['publisher'] = {"@type": "NewsMediaOrganization", "@id": "https://portaljuniorarrais.com.br/#organizacao",
                          "name": "Portal Júnior Arrais", "url": "https://portaljuniorarrais.com.br/",
                          "logo": {"@type": "ImageObject", "url": "https://portaljuniorarrais.com.br/img/logo-header.png"}}
        d.setdefault('inLanguage', 'pt-BR')
        d.setdefault('isAccessibleForFree', True)
        return '<script type="application/ld+json">\n' + json.dumps(d, ensure_ascii=False, indent=2) + '\n  </script>'
    s = re.sub(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', fix_ld, s, count=1, flags=re.S)
    # link no byline
    s = s.replace('class="autor-foto"> Por J&uacute;nior Arrais &middot;', 'class="autor-foto"> Por <a href="../sobre.html#autor" class="autor-link">J&uacute;nior Arrais</a> &middot;')
    s = s.replace('class="autor-foto"> Por Júnior Arrais &middot;', 'class="autor-foto"> Por <a href="../sobre.html#autor" class="autor-link">Júnior Arrais</a> &middot;')
    s = geral(s, '../')
    if s != o:
        open(path, 'w', encoding='utf-8', newline='').write(s)
    return s != o

def geral(s, pre):
    # rodapé: Termos de Uso
    s = s.replace(f'<a href="{pre}politica-de-privacidade.html">Política de Privacidade</a></p>',
                  f'<a href="{pre}politica-de-privacidade.html">Política de Privacidade</a> &middot; <a href="{pre}termos-de-uso.html">Termos de Uso</a></p>')
    # menu: Guias depois de Notícias
    if 'guias.html' not in s:
        s = s.replace(f'<a href="{pre}noticias.html">Not&iacute;cias</a>', f'<a href="{pre}noticias.html">Not&iacute;cias</a>\n        <a href="{pre}guias.html">Guias</a>', 1)
        s = s.replace(f'<a href="{pre}noticias.html">Notícias</a>', f'<a href="{pre}noticias.html">Notícias</a>\n        <a href="{pre}guias.html">Guias</a>', 1)
    # rótulo PUBLICIDADE sobre slot vazio
    s = s.replace('<span class="ad-label">PUBLICIDADE</span>', '')
    return s

if __name__ == '__main__':
    n = 0
    for f in sorted(glob.glob('noticias/*.html')):
        n += aplicar_materia(f)
    print('matérias alteradas:', n)
    for f in sorted(glob.glob('*.html')):
        s = open(f, encoding='utf-8').read(); t = geral(s, '')
        if t != s:
            open(f, 'w', encoding='utf-8', newline='').write(t); print('página fixa alterada:', f)
