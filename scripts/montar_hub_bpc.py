#!/usr/bin/env python3
"""Monta a página central do BPC/LOAS (bpc-loas.html).

O BPC é pago no calendário do INSS, na faixa de quem ganha até um salário mínimo,
então as datas vêm de data/inss.json (mesma fonte de inss.html). As últimas
notícias saem das matérias com o chip "BPC/LOAS" e sem noindex.
Reaproveita o visual da página do Bolsa Família. Criado em 14/11/2026.

Uso:  python scripts/montar_hub_bpc.py [--hoje AAAA-MM-DD]
"""
import datetime as dt
import glob
import html
import json
import os
import re
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from montar_hub_bolsa_familia import (CSS, DIAS, FINAIS, MESES, MOLDE, RAIZ, d,  # noqa: E402
                                      data_curta, data_extenso_curto, data_longa,
                                      hoje_brasilia)
from montar_hub_inss import carregar as carregar_inss, comp_atual, nome_comp, tabela_ano  # noqa: E402

SAIDA = os.path.join(RAIZ, "bpc-loas.html")
URL = "https://portaljuniorarrais.com.br/bpc-loas.html"
ATUALIZADO = "2026-11-14"
PUBLICADO = "2026-11-14"
e = html.escape


def noticias_bpc(limite=8):
    itens = []
    for arq in glob.glob(os.path.join(RAIZ, "noticias", "*.html")):
        slug = os.path.basename(arq)[:-5]
        if slug.startswith("guia-"):
            continue
        t = open(arq, encoding="utf-8").read()
        if 'name="robots" content="noindex' in t:
            continue
        chip = re.search(r'<span class="chip">([^<]*)</span>', t)
        if not chip or html.unescape(chip.group(1)).strip() != "BPC/LOAS":
            continue
        h1 = re.search(r"<h1>(.*?)</h1>", t, re.S)
        pub = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})', t)
        if not h1 or not pub:
            continue
        titulo = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
        itens.append((pub.group(1), slug, titulo))
    itens.sort(reverse=True)
    return itens[:limite]


def tabela_comp(datas, hoje, destacar=True):
    linhas = []
    for i, x in enumerate(datas):
        cls = ' class="bf-hoje"' if destacar and x == hoje else (' class="bf-pago"' if destacar and x < hoje else "")
        linhas.append(f'<tr{cls}><td>Final {FINAIS[i]}</td><td>{data_curta(x)}</td><td>{DIAS[x.weekday()]}</td></tr>')
    return ('<div class="bf-tabela-wrap"><table class="bf-tabela"><thead><tr><th>Final do benefício</th>'
            '<th>Data</th><th>Dia</th></tr></thead><tbody>' + "".join(linhas) + '</tbody></table></div>')


def bloco_comp(k, datas, hoje, atual):
    mes = MESES[int(k[5:]) - 1]
    return (f'<h2 id="calendario-{k}">Calendário do BPC: pagamento de {nome_comp(k)}</h2>\n'
            f'<p>O BPC de {mes} é pago entre <strong>{data_longa(min(datas))}</strong> e '
            f'<strong>{data_longa(max(datas))}</strong>, um final do cartão por dia útil, junto com quem recebe '
            f'aposentadoria ou pensão de um salário mínimo.</p>\n' + tabela_comp(datas, hoje, atual))


JS = r"""
<script>
(function () {
  var B = __DADOS__;
  var MESES = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
  var DIAS = ["domingo","segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado"];
  var FINAIS = [1,2,3,4,5,6,7,8,9,0];
  function hoje() {
    try {
      return new Intl.DateTimeFormat("en-CA", {timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit"}).format(new Date());
    } catch (e) { var d = new Date(); d.setHours(d.getHours() - 3); return d.toISOString().slice(0, 10); }
  }
  function dt(s) { var p = s.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function longa(s) { var x = dt(s); return x.getDate() + " de " + MESES[x.getMonth()]; }
  function quando(s, h) {
    if (s === h) return "hoje";
    if (Math.round((dt(s) - dt(h)) / 86400000) === 1) return "amanhã";
    return DIAS[dt(s).getDay()] + ", " + longa(s);
  }
  function naData(s, h) { var q = quando(s, h); if (q === "hoje" || q === "amanhã") return q; return (dt(s).getDay() % 6 === 0 ? "no " : "na ") + q; }
  var h = hoje(), chaves = Object.keys(B.comps).sort();
  var prox = null, compProx = null;
  chaves.forEach(function (k) { B.comps[k].forEach(function (x) { if (x >= h && (!prox || x < prox)) { prox = x; compProx = k; } }); });
  var elD = document.getElementById("bf-proximo-data"), elQ = document.getElementById("bf-proximo-quem");
  if (!prox) { elD.textContent = "Calendário do próximo ano ainda não saiu"; elQ.textContent = "Assim que o INSS divulgar, o portal atualiza esta página."; }
  else {
    var quem = []; B.comps[compProx].forEach(function (x, i) { if (x === prox) quem.push(FINAIS[i]); });
    var q = quando(prox, h);
    elD.textContent = q.charAt(0).toUpperCase() + q.slice(1) + (q === "hoje" || q === "amanhã" ? " (" + longa(prox) + ")" : "");
    elQ.textContent = "Recebe: final " + quem.join(", ") + ", BPC de " + MESES[+compProx.slice(5, 7) - 1] + ".";
  }
  var resp = document.getElementById("bf-resposta"), bs = document.querySelectorAll(".bf-botoes button");
  function escolher(f) {
    bs.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-final") === String(f) ? "true" : "false"); });
    var idx = FINAIS.indexOf(+f), achou = null;
    for (var i = 0; i < chaves.length; i++) { var x = B.comps[chaves[i]][idx]; if (x >= h) { achou = {k: chaves[i], x: x}; break; } }
    if (!achou) { resp.textContent = "As datas do próximo ano ainda não foram divulgadas."; return; }
    resp.innerHTML = "Final " + f + ": o BPC de " + MESES[+achou.k.slice(5, 7) - 1] + " cai <strong>" + naData(achou.x, h) + "</strong>.";
    try { localStorage.setItem("pja-bpc", String(f)); } catch (e) {}
  }
  bs.forEach(function (b) { b.addEventListener("click", function () { escolher(b.getAttribute("data-final")); }); });
  try { var s = localStorage.getItem("pja-bpc"); if (s !== null && s !== "") escolher(s); } catch (e) {}
})();
</script>
"""

CSS_BPC = """
  <style>
  .bp-proximo { background: linear-gradient(135deg, #9a3412, #ea580c 60%, #f97316); box-shadow: 0 8px 26px rgba(234, 88, 12, .25); }
  .bp-proximo .bf-botoes button[aria-pressed="true"] { color: #9a3412; }
  </style>
"""


def montar(hoje):
    dados, comps = carregar_inss()
    v = dados["valores"]
    sm = v["salario_minimo"]
    ano = v["ano"]
    k = comp_atual(comps, hoje)
    molde = open(MOLDE, encoding="utf-8").read()
    m_head = re.search(r"(  <!-- ADSENSE -->.*?)</head>", molde, re.S)
    m_topo = re.search(r"<body>(.*?)<main>", molde, re.S)
    m_rodape = re.search(r"</main>(.*?)<script src=\"site\.js[^\"]*\"></script>", molde, re.S)
    assert m_head and m_topo and m_rodape, "molde guias.html mudou: revisar regex"
    site_js = re.search(r'<script src="site\.js[^"]*"></script>', molde).group(0)
    css_v = re.search(r'styles\.css\?v=\d+', molde).group(0)

    # comps só com as datas de até 1 SM (o BPC é sempre de 1 salário mínimo)
    if k:
        ds = comps[k]
        mes = MESES[int(k[5:]) - 1]
        titulo = f"BPC/LOAS 2026: pagamento de {mes}, valor, regras e últimas notícias"
        descricao = (f"Calendário do BPC/LOAS de {mes} ({data_curta(min(ds))} a {data_curta(max(ds))}) por final do "
                     f"benefício, valor de R$ {sm}, limite de renda, revisão do cadastro e as notícias mais recentes "
                     f"para idosos e pessoas com deficiência.")
        futuras = sorted(x for kk in comps for x in comps[kk] if x >= hoje)
        p = futuras[0]
        kp = next(kk for kk in comps if p in comps[kk])
        quem = [FINAIS[i] for i, x in enumerate(comps[kp]) if x == p]
        q = "hoje" if p == hoje else ("amanhã" if p == hoje + dt.timedelta(days=1) else f"{DIAS[p.weekday()]}, {data_longa(p)}")
        fb_data = (q[0].upper() + q[1:]) + (f" ({data_longa(p)})" if q in ("hoje", "amanhã") else "")
        fb_quem = f"Recebe: final {', '.join(map(str, quem))}, BPC de {MESES[int(kp[5:]) - 1]}."
    else:
        titulo = "BPC/LOAS: calendário de pagamento, valor, regras e últimas notícias"
        descricao = "Calendário do BPC/LOAS por final do benefício, valor, regras e notícias."
        fb_data, fb_quem = "Calendário do próximo ano ainda não saiu", "Assim que o INSS divulgar, o portal atualiza esta página."

    blocos = []
    if k:
        ch = list(comps)
        i = ch.index(k)
        blocos.append(bloco_comp(k, comps[k], hoje, True))
        if i + 1 < len(ch):
            blocos.append(bloco_comp(ch[i + 1], comps[ch[i + 1]], hoje, False))

    noticias = noticias_bpc()
    lis = "".join(
        f'<li><a href="noticias/{s}.html"><img src="img/{s}.png" alt="" loading="lazy" width="112" height="63">'
        f'<span>{e(t)}<small>{data_extenso_curto(d(pub))}</small></span></a></li>'
        for pub, s, t in noticias)
    atualizado = data_extenso_curto(d(ATUALIZADO))
    titulo_share = quote(titulo)

    faq = [
        ("Qual é o valor do BPC em 2026?",
         f"Um salário mínimo, R$ {sm} por mês. O BPC não tem 13º e não gera pensão por morte para a família, "
         f"porque é um benefício assistencial e não depende de contribuição."),
        ("Qual é o limite de renda para ter o BPC?",
         "A renda da família, dividida pelas pessoas que moram juntas, tem de ficar em até um quarto do salário "
         "mínimo por pessoa, R$ 405,25 em 2026. Pelas regras atuais, o benefício é mantido se a renda do último "
         "mês ou a média dos últimos 12 meses ficar dentro desse limite. Gastos contínuos e comprovados com saúde "
         "que o SUS não oferece podem ser descontados da conta."),
        ("Quando o BPC cai?",
         "No calendário do INSS, junto com aposentadorias e pensões de um salário mínimo: nos últimos dias úteis "
         "do mês e nos primeiros do mês seguinte, conforme o último número do cartão, sem o dígito depois do traço."),
        ("Quem recebe Bolsa Família pode pedir o BPC?",
         "Pode. O valor do Bolsa Família conta como renda no cálculo do BPC, e por isso existe o desligamento "
         "voluntário, que pode ser pedido no próprio requerimento. Segundo o Ministério do Desenvolvimento e "
         "Assistência Social, o Bolsa Família não é interrompido de imediato enquanto o BPC é analisado."),
        ("Meu BPC foi bloqueado. O que significa?",
         "Na revisão do cadastro, o benefício passa por etapas: primeiro o bloqueio, quando o dinheiro entra mas o "
         "saque fica travado; depois a suspensão, quando os depósitos param; e por fim a cessação, quando o "
         "benefício é encerrado. Quanto antes a pendência for resolvida, menor o prejuízo. Não pague ninguém para "
         "desbloquear: procure um profissional de sua confiança para olhar o caso."),
    ]
    faq_html = "".join(f"<h3>{e(pq)}</h3>\n<p>{e(rp)}</p>\n" for pq, rp in faq)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": pq,
                              "acceptedAnswer": {"@type": "Answer", "text": rp}} for pq, rp in faq]}
    page_ld = {
        "@context": "https://schema.org", "@type": "WebPage", "name": titulo, "description": descricao,
        "url": URL, "inLanguage": "pt-BR", "datePublished": PUBLICADO, "dateModified": ATUALIZADO,
        "isPartOf": {"@type": "WebSite", "name": "Portal Júnior Arrais", "url": "https://portaljuniorarrais.com.br/"},
        "about": {"@type": "GovernmentService", "name": "Benefício de Prestação Continuada (BPC/LOAS)",
                  "provider": {"@type": "GovernmentOrganization", "name": "Instituto Nacional do Seguro Social (INSS)"}},
        "author": {"@type": "Person", "@id": "https://portaljuniorarrais.com.br/sobre.html#autor",
                   "name": "Júnior Arrais", "url": "https://portaljuniorarrais.com.br/sobre.html#autor",
                   "jobTitle": "Editor responsável"},
        "publisher": {"@type": "NewsMediaOrganization", "@id": "https://portaljuniorarrais.com.br/sobre.html#organizacao",
                      "name": "Portal Júnior Arrais",
                      "logo": {"@type": "ImageObject", "url": "https://portaljuniorarrais.com.br/img/logo-portal.png"}},
        "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Início", "item": "https://portaljuniorarrais.com.br/"},
            {"@type": "ListItem", "position": 2, "name": "BPC/LOAS", "item": URL}]},
    }
    cal = dados["calendario"][str(ano)]
    fontes = [
        (cal["fonte"], f"INSS: tabela oficial de pagamento de benefícios de {ano}"),
        ("https://www.planalto.gov.br/ccivil_03/leis/l8742.htm", "Lei nº 8.742/1993 (Lei Orgânica da Assistência Social)"),
        ("https://www.gov.br/mds/pt-br/noticias-e-conteudos/desenvolvimento-social/noticias-desenvolvimento-social/portaria-atualiza-regras-do-bpc-que-pode-ser-mantido-mesmo-em-caso-de-variacao-da-renda-familiar-per-capita/",
         "MDS: portaria atualiza regras do BPC (renda do último mês ou média de 12 meses)"),
        ("https://www.gov.br/mds/pt-br/noticias-e-conteudos/Noticias/2026/desligamento-voluntario-do-bolsa-familia-entenda-como-funciona-a-protecao-de-renda-para-quem-solicita-o-bpc", "MDS: desligamento voluntário do Bolsa Família para quem pede o BPC (13/11/2026)"),
        (v["norma_url"], v["norma"] + " (salário mínimo de 2026)"),
    ]
    fontes_html = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a></li>' for u, t in fontes)
    js_dados = json.dumps({"comps": {kk: [x.isoformat() for x in vv] for kk, vv in comps.items()}}, separators=(",", ":"))

    corpo = f"""
    <article class="artigo">
      <p class="bf-trilha"><a href="/">Início</a> › BPC/LOAS</p>
      <div><span class="chip">BPC/LOAS</span></div>
      <h1>{e(titulo)}</h1>
      <div class="meta"><img src="img/junior-avatar.png" alt="Júnior Arrais" class="autor-foto"> Por <a href="sobre.html#autor" class="autor-link">Júnior Arrais</a> &middot; Atualizado em {atualizado}</div>

      <section class="bf-proximo bp-proximo" aria-live="polite">
        <span class="bf-proximo-rotulo">Próximo pagamento do BPC</span>
        <span class="bf-proximo-data" id="bf-proximo-data">{e(fb_data)}</span>
        <span class="bf-proximo-quem" id="bf-proximo-quem">{e(fb_quem)}</span>
        <div class="bf-seletor">
          <span class="bf-seletor-rotulo">Toque no último número do cartão (sem o dígito depois do traço):</span>
          <div class="bf-botoes" role="group" aria-label="Final do benefício">
            {"".join(f'<button type="button" data-final="{f}" aria-pressed="false">{f}</button>' for f in FINAIS)}
          </div>
          <p class="bf-resposta" id="bf-resposta"></p>
        </div>
      </section>

      <div class="artigo-conteudo">
<p>O <strong>Benefício de Prestação Continuada (BPC)</strong>, que muita gente chama de LOAS, paga <strong>um salário mínimo por mês, R$ {sm}</strong> em {ano}, ao idoso com 65 anos ou mais e à pessoa com deficiência de família de baixa renda. Não é aposentadoria e não exige contribuição ao INSS. O pagamento segue o calendário do INSS pelo último número do cartão. Aqui você encontra a data de cada final, o calendário do ano, as regras de renda, o que acontece na revisão do cadastro e as notícias mais recentes, atualizadas todos os dias.</p>
{blocos[0] if blocos else ""}
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
{"".join(blocos[1:])}
<h2 id="valores">Valor e limite de renda em {ano}</h2>
<ul class="bf-valores">
<li><strong>R$ {sm}</strong>valor mensal do BPC, um salário mínimo</li>
<li><strong>R$ 405,25</strong>limite de renda por pessoa da família, um quarto do mínimo</li>
<li><strong>R$ 810,50</strong>auxílio-inclusão para quem recebe BPC e passa a trabalhar</li>
<li><strong>65 anos</strong>idade mínima no BPC do idoso; na deficiência, qualquer idade</li>
</ul>
<p>Pelas regras atualizadas pelo MDS e pelo INSS, o benefício continua mesmo que a renda varie, desde que a renda do último mês ou a média dos últimos 12 meses fique em até um quarto do salário mínimo por pessoa. Entram na conta o requerente, o cônjuge ou companheiro, os pais, os irmãos e os filhos solteiros que moram na mesma casa. Ficam de fora, entre outros, o BPC de outro idoso ou pessoa com deficiência da família e a aposentadoria de até um salário mínimo de um idoso ou pessoa com deficiência. Gastos contínuos com saúde, como remédios, fraldas e alimentação especial que o SUS não oferece, podem ser descontados, com comprovação.</p>
<h2 id="quem">Quem tem direito</h2>
<ul>
<li><strong>pessoa idosa</strong> com 65 anos ou mais;</li>
<li><strong>pessoa com deficiência</strong> de qualquer idade, com impedimento de longo prazo, de pelo menos dois anos, que dificulte a participação na sociedade;</li>
<li>família com renda dentro do limite e inscrita no <strong>CadÚnico</strong>, com os dados em dia.</li>
</ul>
<p>No BPC da pessoa com deficiência, o INSS faz duas avaliações, a perícia médica e a avaliação social, e as duas contam juntas. O que decide não é o nome da doença, e sim as limitações que ela causa no dia a dia. As regras completas estão no <a href="noticias/guia-bpc-loas-quem-tem-direito-renda-e-avaliacao.html">guia do BPC/LOAS</a>.</p>
<h2 id="revisao">Revisão do cadastro: bloqueio, suspensão e corte</h2>
<p>O INSS cruza os dados do CadÚnico com outras bases do governo e convoca quem está sem cadastro ou com o cadastro desatualizado há muito tempo. Quem não responde passa por três etapas:</p>
<ul>
<li><strong>bloqueio</strong>: o dinheiro entra na conta, mas o saque fica travado;</li>
<li><strong>suspensão</strong>: os depósitos param até a pendência ser resolvida, num prazo de 45 ou 90 dias conforme o tamanho da cidade;</li>
<li><strong>cessação</strong>: o benefício é encerrado, e a volta passa a depender de recurso ou de um novo pedido.</li>
</ul>
<p>Quem resolve a pendência dentro do prazo da suspensão tem direito a receber os valores que ficaram retidos. Além disso, a lei manda reavaliar o benefício a cada dois anos, e quem tem impedimento permanente reconhecido fica dispensado de nova perícia. Veja <a href="noticias/reavaliacao-do-bpc-quem-esta-dispensado.html">quem está dispensado da reavaliação</a>.</p>
<h2 id="nao">O que o BPC não dá</h2>
<p>O BPC <strong>não paga 13º</strong>, não deixa pensão por morte para a família e não pode ser somado a aposentadoria, pensão ou seguro-desemprego. Quem tem deficiência e já contribuiu ao INSS pode ter direito à aposentadoria da pessoa com deficiência, que paga 13º e pensão e não olha a renda da família. Para quem recebe BPC e consegue emprego com salário de até dois mínimos, o benefício vira <a href="noticias/auxilio-inclusao-bpc-trabalho.html">auxílio-inclusão</a> automaticamente, sem novo pedido.</p>
<h2 id="calendario-{ano}">Calendário completo do BPC de {ano}</h2>
<p>Cada linha é o mês do benefício e cada coluna, um final do cartão. O BPC segue as datas de quem ganha até um salário mínimo no INSS.</p>
{tabela_ano(ano, comps)}
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
<h2 id="noticias">Últimas notícias do BPC/LOAS</h2>
<ul class="bf-noticias">{lis}</ul>
<p><a href="noticias.html?cat=BPC%2FLOAS">Ver todas as notícias do BPC/LOAS</a></p>
<h2 id="outros">Outros benefícios</h2>
<div class="bf-outros">
<a href="inss.html">INSS<small>calendário de aposentados e pensionistas</small></a>
<a href="bolsa-familia.html">Bolsa Família<small>calendário pelo final do NIS</small></a>
<a href="gas-do-povo.html">Gás do Povo<small>quando sai o próximo vale</small></a>
<a href="noticias/guia-cadunico-o-que-e-quem-pode-e-quando-atualizar.html">CadÚnico<small>quem pode entrar e quando atualizar</small></a>
</div>
<h2 id="perguntas">Perguntas frequentes</h2>
{faq_html}<h2>Cuidado com golpe</h2>
<p>O BPC é um dos temas preferidos de quem promete o que não pode cumprir: "consigo o BPC para qualquer pessoa", "acelero o seu pedido", "pague uma taxa e sai em uma semana". A revisão do cadastro também virou isca, com mensagens dizendo que o benefício "será cortado em 48 horas" e um link para "regularizar", ou pedindo senha para "confirmar a perícia".</p>
<p>Nenhum órgão do governo cobra taxa nem pede Pix, senha ou foto de documento para conceder, manter ou desbloquear benefício. A conta da renda, quem entra no grupo familiar e a documentação da deficiência pedem análise cuidadosa: procure um profissional de sua confiança para olhar o seu caso.</p>
<h2>Fontes oficiais</h2>
<ul class="fontes-oficiais">{fontes_html}</ul>
<p><em>Página atualizada em {atualizado}. Conteúdo informativo — não substitui orientação individualizada sobre o seu caso.</em></p>
      </div>
      <!-- AUTOR (Portal Junior Arrais) -->
      <div class="autor-box" id="autor">
        <img class="autor-box-foto" src="img/junior-avatar.png" alt="Júnior Arrais" width="72" height="72" loading="lazy">
        <div class="autor-box-texto">
          <p class="autor-box-nome"><a href="sobre.html#autor">Júnior Arrais</a> <span class="autor-box-cargo">· Editor do Portal Júnior Arrais</span></p>
          <p class="autor-box-bio">Comunicador de Ubá (MG). Escreve todos os dias sobre benefícios sociais, INSS, trabalho e economia do dia a dia, a partir do Diário Oficial, de portarias e de fontes oficiais, em linguagem simples. Conheça a <a href="sobre.html#linha-editorial">linha editorial</a> e a <a href="sobre.html#correcoes">política de correções</a> do portal.</p>
          <p class="autor-box-links"><a href="mailto:contato@portaljuniorarrais.com.br?subject=Correcao: bpc-loas">Encontrou um erro? Avise a redação</a></p>
        </div>
      </div>
      <!-- FIM AUTOR -->

      <div class="share-bar">
        <span class="share-titulo">Compartilhe com quem recebe o BPC:</span>
        <div class="share-botoes">
          <a class="share-btn share-wa" target="_blank" rel="noopener" href="https://api.whatsapp.com/send?text={titulo_share}%0A%0A{URL}">WhatsApp</a>
          <button class="share-btn share-fb" type="button" onclick="pjaFacebook(this)">Facebook</button>
          <a class="share-btn share-tg" target="_blank" rel="noopener" href="https://t.me/share/url?url={URL}&amp;text={titulo_share}">Telegram</a>
          <button class="share-btn share-copiar" type="button" onclick="pjaCopiarLink(this)">Copiar link</button>
        </div>
      </div>
      <!-- fim COMPARTILHAR -->
    </article>
"""

    head = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(titulo)} · Portal Júnior Arrais</title>
  <meta name="description" content="{e(descricao)}">
  <link rel="canonical" href="{URL}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Portal Júnior Arrais">
  <meta property="og:title" content="{e(titulo)}">
  <meta property="og:description" content="{e(descricao)}">
  <meta property="og:url" content="{URL}">
  <meta property="og:image" content="https://portaljuniorarrais.com.br/img/guia-bpc-loas-quem-tem-direito-renda-e-avaliacao.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="favicon.png">
  <link rel="stylesheet" href="{css_v}">
  <script type="application/ld+json">{json.dumps(page_ld, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>
{m_head.group(1).rstrip()}
{CSS}{CSS_BPC}</head>
<body>"""

    return (head + m_topo.group(1) + "<main>\n" + corpo + "  </main>" + m_rodape.group(1)
            + site_js + "\n" + JS.replace("__DADOS__", js_dados) + "</body>\n</html>\n")


def main():
    pagina = montar(hoje_brasilia())
    antigo = open(SAIDA, encoding="utf-8").read() if os.path.exists(SAIDA) else ""
    if pagina != antigo:
        with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
            f.write(pagina)
        print("MUDOU")
    else:
        print("igual")


if __name__ == "__main__":
    main()
