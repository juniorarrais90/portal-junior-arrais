#!/usr/bin/env python3
"""Monta a página central do INSS (inss.html).

Fonte dos dados: data/inss.json (calendário oficial de pagamentos por mês do
benefício, salário mínimo, teto e reajuste). As últimas notícias saem das
matérias de noticias/ com o chip "INSS" ou "BPC/LOAS" e sem noindex.

Reaproveita o visual e as funções da página do Bolsa Família
(scripts/montar_hub_bolsa_familia.py). Criado em 14/11/2026.

Rodar sempre que mudar o JSON. O robô .github/workflows/hub-bolsa-familia.yml
também roda este script todo dia.

Uso:  python scripts/montar_hub_inss.py [--hoje AAAA-MM-DD]
Imprime MUDOU quando o arquivo foi regravado.
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

DADOS = os.path.join(RAIZ, "data", "inss.json")
SAIDA = os.path.join(RAIZ, "inss.html")
URL = "https://portaljuniorarrais.com.br/inss.html"
PARES = {1: 6, 2: 7, 3: 8, 4: 9, 5: 0, 6: 6, 7: 7, 8: 8, 9: 9, 0: 0}  # acima do mínimo: final -> final cuja data vale
e = html.escape


def carregar():
    with open(DADOS, encoding="utf-8") as f:
        dados = json.load(f)
    comps = {}
    for k, datas in sorted(dados["competencias"].items()):
        assert len(datas) == 10, k
        comps[k] = [d(x) for x in datas]
    return dados, comps


def data_acima(datas, final):
    return datas[FINAIS.index(PARES[final])]


def todas_datas(datas):
    return set(datas)


def comp_atual(comps, hoje):
    """Primeiro mês de benefício que ainda tem pagamento de hoje em diante."""
    for k, ds in comps.items():
        if max(ds) >= hoje:
            return k
    return None


def nome_comp(k):
    return f"{MESES[int(k[5:]) - 1]} de {k[:4]}"


def noticias_inss(limite=8):
    itens = []
    for arq in glob.glob(os.path.join(RAIZ, "noticias", "*.html")):
        slug = os.path.basename(arq)[:-5]
        if slug.startswith("guia-"):
            continue
        t = open(arq, encoding="utf-8").read()
        if 'name="robots" content="noindex' in t:
            continue
        chip = re.search(r'<span class="chip">([^<]*)</span>', t)
        if not chip or html.unescape(chip.group(1)).strip() not in ("INSS", "BPC/LOAS"):
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
        f = FINAIS[i]
        y = data_acima(datas, f)
        cls = ""
        if destacar and hoje in (x, y):
            cls = ' class="bf-hoje"'
        elif destacar and max(x, y) < hoje:
            cls = ' class="bf-pago"'
        linhas.append(
            f'<tr{cls}><td>Final {f}</td><td>{data_curta(x)} <small>{DIAS[x.weekday()][:3]}</small></td>'
            f'<td>{data_curta(y)} <small>{DIAS[y.weekday()][:3]}</small></td></tr>')
    return ('<div class="bf-tabela-wrap"><table class="bf-tabela in-comp">'
            '<thead><tr><th>Final do benefício</th><th>Até 1 salário mínimo</th>'
            '<th>Acima de 1 salário mínimo</th></tr></thead>'
            '<tbody>' + "".join(linhas) + '</tbody></table></div>')


def bloco_comp(k, datas, hoje, atual):
    mes = MESES[int(k[5:]) - 1]
    ini, fim = min(datas), max(datas)
    acima_ini = min(datas[5:])
    return (
        f'<h2 id="calendario-{k}">Calendário do INSS: benefícios de {nome_comp(k)}</h2>\n'
        f'<p>O benefício de {mes} é pago entre <strong>{data_longa(ini)}</strong> e '
        f'<strong>{data_longa(fim)}</strong>. Quem ganha <strong>até um salário mínimo</strong> recebe '
        f'primeiro, um final por dia útil, a partir de {data_longa(ini)}. Quem ganha '
        f'<strong>acima do mínimo</strong> começa a receber em {data_longa(acima_ini)}, com os finais '
        f'agrupados de dois em dois.</p>\n'
        + tabela_comp(datas, hoje, destacar=atual))


def tabela_ano(ano, comps):
    cab = "".join(f"<th>{f}</th>" for f in FINAIS)
    linhas = []
    for k, ds in comps.items():
        if int(k[:4]) != ano:
            continue
        cels = "".join(f"<td>{data_curta(x)}</td>" for x in ds)
        linhas.append(f'<tr><th scope="row">{MESES[int(k[5:]) - 1].capitalize()}</th>{cels}</tr>')
    return (f'<div class="bf-tabela-wrap"><table class="bf-tabela bf-ano in-ano"><thead><tr><th>Benefício de</th>{cab}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def dados_js(comps):
    return json.dumps({"comps": {k: [x.isoformat() for x in v] for k, v in comps.items()}},
                      ensure_ascii=False, separators=(",", ":"))


CSS_INSS = """
  <style>
  .in-faixa { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
  .in-faixa button { min-height: 48px; border: 0; border-radius: 12px; background: rgba(255, 255, 255, .18); color: #fff; font: inherit; font-size: .98rem; font-weight: 700; line-height: 1.2; cursor: pointer; padding: 8px 10px; }
  .in-faixa button:hover { background: rgba(255, 255, 255, .3); }
  .in-faixa button[aria-pressed="true"] { background: #fff; color: #1e5fb0; }
  .in-faixa button:focus-visible { outline: 3px solid #fff; outline-offset: 2px; }
  .in-comp td small { color: #6b7a8c; font-size: .8rem; margin-left: 4px; }
  .in-comp th:nth-child(2), .in-comp th:nth-child(3) { white-space: normal; }
  .in-ano td, .in-ano th { font-size: .85rem; }
  @media (max-width: 520px) { .in-comp td small { display: none; } .in-comp th, .in-comp td { padding: 9px 8px; white-space: normal; } }
  </style>
"""

JS = r"""
<script>
(function () {
  var IN = __DADOS__;
  var MESES = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
  var DIAS = ["domingo","segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado"];
  var FINAIS = [1,2,3,4,5,6,7,8,9,0];
  var PARES = {1:6,2:7,3:8,4:9,5:0,6:6,7:7,8:8,9:9,0:0};
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
  function naData(s, h) {
    var q = quando(s, h);
    if (q === "hoje" || q === "amanhã") return q;
    return (dt(s).getDay() === 0 || dt(s).getDay() === 6 ? "no " : "na ") + q;
  }
  function nomeComp(k) { return MESES[+k.slice(5, 7) - 1]; }
  function dataDe(k, f, acima) { return IN.comps[k][FINAIS.indexOf(acima ? PARES[f] : +f)]; }
  var h = hoje();
  var chaves = Object.keys(IN.comps).sort();
  // próximo pagamento (qualquer faixa)
  var prox = null, quemAte = [], quemAcima = [], compProx = null;
  chaves.forEach(function (k) {
    IN.comps[k].forEach(function (x) { if (x >= h && (!prox || x < prox)) { prox = x; compProx = k; } });
  });
  var elData = document.getElementById("bf-proximo-data");
  var elQuem = document.getElementById("bf-proximo-quem");
  if (!prox) {
    elData.textContent = "Calendário do próximo ano ainda não saiu";
    elQuem.textContent = "Assim que o INSS divulgar, o portal atualiza esta página.";
  } else {
    FINAIS.forEach(function (f, i) {
      if (IN.comps[compProx][i] === prox) quemAte.push(f);
      if (i >= 5 && IN.comps[compProx][i] === prox) quemAcima.push((f === 0 ? 5 : f - 5) + " e " + f);
    });
    var q = quando(prox, h);
    elData.textContent = q.charAt(0).toUpperCase() + q.slice(1) + (q === "hoje" || q === "amanhã" ? " (" + longa(prox) + ")" : "");
    var t = "Recebe: final " + quemAte.join(", ") + " (até 1 salário mínimo)";
    if (quemAcima.length) t += " e finais " + quemAcima.join(", ") + " (acima do mínimo)";
    elQuem.textContent = t + ", benefício de " + nomeComp(compProx) + ".";
  }
  var resp = document.getElementById("bf-resposta");
  var botoes = document.querySelectorAll(".bf-botoes button");
  var faixas = document.querySelectorAll(".in-faixa button");
  var faixa = null, fin = null;
  function responder() {
    if (faixa === null || fin === null) {
      resp.textContent = faixa === null && fin !== null ? "Agora escolha quanto você recebe." : "";
      return;
    }
    var acima = faixa === "acima";
    var achou = null;
    for (var i = 0; i < chaves.length; i++) {
      var x = dataDe(chaves[i], fin, acima);
      if (x >= h) { achou = {k: chaves[i], x: x, ant: i > 0 ? dataDe(chaves[i - 1], fin, acima) : null}; break; }
    }
    if (!achou) { resp.textContent = "As datas do próximo ano ainda não foram divulgadas."; return; }
    var txt = "Final " + fin + (acima ? " (acima do mínimo)" : " (até 1 salário mínimo)") + ": o benefício de " +
      nomeComp(achou.k) + " cai <strong>" + naData(achou.x, h) + "</strong>.";
    resp.innerHTML = txt;
    try { localStorage.setItem("pja-inss", faixa + "|" + fin); } catch (e) {}
  }
  faixas.forEach(function (b) {
    b.addEventListener("click", function () {
      faixa = b.getAttribute("data-faixa");
      faixas.forEach(function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); });
      responder();
    });
  });
  botoes.forEach(function (b) {
    b.addEventListener("click", function () {
      fin = b.getAttribute("data-final");
      botoes.forEach(function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); });
      responder();
    });
  });
  try {
    var s = (localStorage.getItem("pja-inss") || "").split("|");
    if (s.length === 2) {
      faixa = s[0]; fin = s[1];
      faixas.forEach(function (o) { o.setAttribute("aria-pressed", o.getAttribute("data-faixa") === faixa ? "true" : "false"); });
      botoes.forEach(function (o) { o.setAttribute("aria-pressed", o.getAttribute("data-final") === fin ? "true" : "false"); });
      responder();
    }
  } catch (e) {}
})();
</script>
"""


def montar(hoje):
    dados, comps = carregar()
    v = dados["valores"]
    k = comp_atual(comps, hoje)
    molde = open(MOLDE, encoding="utf-8").read()
    m_head = re.search(r"(  <!-- ADSENSE -->.*?)</head>", molde, re.S)
    m_topo = re.search(r"<body>(.*?)<main>", molde, re.S)
    m_rodape = re.search(r"</main>(.*?)<script src=\"site\.js[^\"]*\"></script>", molde, re.S)
    assert m_head and m_topo and m_rodape, "molde guias.html mudou: revisar regex"
    site_js = re.search(r'<script src="site\.js[^"]*"></script>', molde).group(0)
    css_v = re.search(r'styles\.css\?v=\d+', molde).group(0)

    if k:
        ds = comps[k]
        mes = MESES[int(k[5:]) - 1]
        ini, fim = min(ds), max(ds)
        titulo = f"Calendário do INSS 2026: pagamento de {mes}, valores e últimas notícias"
        descricao = (f"Calendário do INSS do benefício de {mes} ({data_curta(ini)} a {data_curta(fim)}) "
                     f"por final do benefício, para quem ganha até e acima do salário mínimo, valores de "
                     f"2026, 13º e as notícias mais recentes de aposentados e pensionistas.")
        futuras = sorted(x for kk in comps for x in comps[kk] if x >= hoje)
        p = futuras[0]
        q = "hoje" if p == hoje else ("amanhã" if p == hoje + dt.timedelta(days=1) else f"{DIAS[p.weekday()]}, {data_longa(p)}")
        fallback_data = (q[0].upper() + q[1:]) + (f" ({data_longa(p)})" if q in ("hoje", "amanhã") else "")
        fallback_quem = "Escolha abaixo quanto você recebe e o final do benefício."
        lead = (f'<p>Os aposentados, pensionistas e demais beneficiários do INSS recebem o benefício de '
                f'<strong>{mes}</strong> entre <strong>{data_longa(ini)}</strong> e '
                f'<strong>{data_longa(fim)}</strong>. A data depende de duas coisas: o <strong>valor</strong> do '
                f'benefício (até ou acima de um salário mínimo) e o <strong>último número do cartão do '
                f'benefício</strong>, sem contar o dígito que vem depois do traço. Aqui você encontra a data de '
                f'cada final, o calendário do ano inteiro, os valores de {v["ano"]} e as notícias mais '
                f'recentes, atualizadas todos os dias.</p>')
    else:
        titulo = "Calendário do INSS: pagamento, valores e últimas notícias"
        descricao = "Calendário de pagamento do INSS por final do benefício, valores e as notícias mais recentes."
        fallback_data = "Calendário do próximo ano ainda não saiu"
        fallback_quem = "Assim que o INSS divulgar, o portal atualiza esta página."
        lead = '<p>O calendário do INSS do próximo ano ainda não foi divulgado. Assim que sair, esta página traz a data de cada final.</p>'

    blocos = []
    if k:
        chaves = list(comps)
        i = chaves.index(k)
        blocos.append(bloco_comp(k, comps[k], hoje, True))
        if i + 1 < len(chaves):
            blocos.append(bloco_comp(chaves[i + 1], comps[chaves[i + 1]], hoje, False))

    ano = v["ano"]
    noticias = noticias_inss()
    lis = "".join(
        f'<li><a href="noticias/{s}.html"><img src="img/{s}.png" alt="" loading="lazy" width="112" height="63">'
        f'<span>{e(t)}<small>{data_extenso_curto(d(pub))}</small></span></a></li>'
        for pub, s, t in noticias)
    atualizado = data_extenso_curto(d(dados["atualizado_em"]))
    titulo_share = quote(titulo)
    nov = comps.get(f"{ano}-11")

    faq = [
        ("Qual número do cartão define a data?",
         "É o último algarismo do número do benefício, sem contar o dígito verificador, aquele que vem "
         "depois do traço. Se o número termina em 123.456.789-0, o final que vale é o 9."),
        ("Por que quem ganha mais recebe depois?",
         "O INSS paga primeiro quem recebe até um salário mínimo, nos últimos dias úteis do mês. Quem ganha "
         "acima do mínimo recebe nos primeiros dias úteis do mês seguinte, com os finais agrupados de dois em "
         "dois: 1 e 6, 2 e 7, 3 e 8, 4 e 9, 5 e 0."),
        (f"Quanto é o salário mínimo e o teto do INSS em {ano}?",
         f"O salário mínimo é de R$ {v['salario_minimo']}, que é também o menor valor pago a aposentados, "
         f"pensionistas e a quem recebe o BPC. O teto, o maior valor que o INSS paga, é de R$ {v['teto']}. "
         f"Os benefícios acima do mínimo tiveram reajuste de {v['reajuste_acima']} em janeiro."),
        (f"Quando sai o 13º do INSS em {ano}?",
         f"Neste ano o 13º foi antecipado e pago em abril e maio para quem já recebia benefício. Quem começou "
         f"a receber a partir de maio recebe o 13º junto com o benefício de novembro"
         + (f", entre {data_longa(min(nov))} e {data_longa(max(nov))}" if nov else "")
         + ". O BPC/LOAS não tem 13º, porque é benefício assistencial."),
        ("O dinheiro não caiu na data. E agora?",
         "Confira primeiro se a data é mesmo a do seu final e da sua faixa de valor. Se a data passou e nada "
         "apareceu, o benefício pode estar suspenso, por exemplo por falta de prova de vida ou por revisão. "
         "Não pague ninguém para liberar: procure um profissional de sua confiança para olhar o caso."),
    ]
    faq_html = "".join(f"<h3>{e(pq)}</h3>\n<p>{e(rp)}</p>\n" for pq, rp in faq)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": pq,
                              "acceptedAnswer": {"@type": "Answer", "text": rp}} for pq, rp in faq]}
    page_ld = {
        "@context": "https://schema.org", "@type": "WebPage", "name": titulo, "description": descricao,
        "url": URL, "inLanguage": "pt-BR", "datePublished": dados["publicado_em"],
        "dateModified": dados["atualizado_em"],
        "isPartOf": {"@type": "WebSite", "name": "Portal Júnior Arrais", "url": "https://portaljuniorarrais.com.br/"},
        "about": {"@type": "GovernmentOrganization", "name": "Instituto Nacional do Seguro Social (INSS)"},
        "author": {"@type": "Person", "@id": "https://portaljuniorarrais.com.br/sobre.html#autor",
                   "name": "Júnior Arrais", "url": "https://portaljuniorarrais.com.br/sobre.html#autor",
                   "jobTitle": "Editor responsável"},
        "publisher": {"@type": "NewsMediaOrganization", "@id": "https://portaljuniorarrais.com.br/sobre.html#organizacao",
                      "name": "Portal Júnior Arrais",
                      "logo": {"@type": "ImageObject", "url": "https://portaljuniorarrais.com.br/img/logo-portal.png"}},
        "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Início", "item": "https://portaljuniorarrais.com.br/"},
            {"@type": "ListItem", "position": 2, "name": "INSS", "item": URL}]},
    }
    cal = dados["calendario"][str(ano)]
    fontes = [
        (cal["fonte"], f"INSS: tabela oficial de pagamento de benefícios de {ano}"),
        (cal["noticia"], f"INSS: calendário de pagamentos de {ano} está disponível"),
        (v["norma_url"], v["norma"] + " (reajuste, teto e salário mínimo)"),
        ("https://www.gov.br/previdencia/pt-br/noticias/2026/janeiro/beneficios-com-valor-acima-do-salario-minimo-sao-reajustados-em-3-9",
         "Ministério da Previdência: benefícios acima do mínimo reajustados em 3,9%"),
        ("https://www.planalto.gov.br/ccivil_03/leis/l8213cons.htm", "Lei nº 8.213/1991 (benefícios da Previdência Social)"),
    ]
    fontes_html = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a></li>' for u, t in fontes)

    corpo = f"""
    <article class="artigo">
      <p class="bf-trilha"><a href="/">Início</a> › INSS</p>
      <div><span class="chip">INSS</span></div>
      <h1>{e(titulo)}</h1>
      <div class="meta"><img src="img/junior-avatar.png" alt="Júnior Arrais" class="autor-foto"> Por <a href="sobre.html#autor" class="autor-link">Júnior Arrais</a> &middot; Atualizado em {atualizado}</div>

      <section class="bf-proximo" aria-live="polite">
        <span class="bf-proximo-rotulo">Próximo pagamento do INSS</span>
        <span class="bf-proximo-data" id="bf-proximo-data">{e(fallback_data)}</span>
        <span class="bf-proximo-quem" id="bf-proximo-quem">{e(fallback_quem)}</span>
        <div class="bf-seletor">
          <span class="bf-seletor-rotulo">1. Quanto você recebe?</span>
          <div class="in-faixa" role="group" aria-label="Valor do benefício">
            <button type="button" data-faixa="ate" aria-pressed="false">Até 1 salário mínimo</button>
            <button type="button" data-faixa="acima" aria-pressed="false">Acima de 1 salário mínimo</button>
          </div>
          <span class="bf-seletor-rotulo">2. Toque no último número do cartão (sem o dígito depois do traço):</span>
          <div class="bf-botoes" role="group" aria-label="Final do benefício">
            {"".join(f'<button type="button" data-final="{f}" aria-pressed="false">{f}</button>' for f in FINAIS)}
          </div>
          <p class="bf-resposta" id="bf-resposta"></p>
        </div>
      </section>

      <div class="artigo-conteudo">
{lead}
{blocos[0] if blocos else ""}
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
{"".join(blocos[1:])}
<h2 id="valores">Valores do INSS em {ano}</h2>
<p>Os números abaixo valem desde 1º de janeiro e estão na {e(v['norma'])}:</p>
<ul class="bf-valores">
<li><strong>R$ {v['salario_minimo']}</strong>salário mínimo, o menor valor pago pelo INSS</li>
<li><strong>R$ {v['teto']}</strong>teto, o maior valor de aposentadoria ou pensão</li>
<li><strong>{v['reajuste_acima']}</strong>reajuste de quem ganha acima do mínimo</li>
<li><strong>R$ {v['salario_minimo']}</strong>valor do BPC/LOAS para idoso ou pessoa com deficiência</li>
</ul>
<p>Quem ganha exatamente um salário mínimo teve o aumento do próprio mínimo. Quem ganha mais recebeu o reajuste pela inflação medida pelo INPC. As regras de cada aposentadoria estão no <a href="noticias/guia-aposentadoria-inss-2026-idade-pontos-rural-e-especial.html">guia da aposentadoria</a>, e as do auxílio-doença no <a href="noticias/guia-auxilio-doenca-e-aposentadoria-por-incapacidade-inss.html">guia dos benefícios por incapacidade</a>.</p>
<h2 id="13">13º do INSS em {ano}</h2>
<p>O 13º, que o INSS chama de abono anual, foi <strong>antecipado</strong> neste ano e pago em duas parcelas, em abril e maio, para quem já recebia benefício. Quem começou a receber a partir de maio entra no calendário normal e recebe o 13º junto com o benefício de novembro{f", entre {data_longa(min(nov))} e {data_longa(max(nov))}" if nov else ""}. Quem recebe o BPC/LOAS não tem 13º, porque o BPC é assistencial e não vem de contribuição. Os detalhes estão na matéria <a href="noticias/13-do-inss-quem-entrou-depois-de-maio-recebe-em-novembro.html">13º do INSS: quem começou a receber depois de maio só recebe em novembro</a>.</p>
<h2 id="calendario-{ano}">Calendário completo do INSS de {ano}</h2>
<p>Cada linha é o mês do benefício e cada coluna, um final do cartão. A tabela mostra as datas de quem ganha <strong>até um salário mínimo</strong>. Quem ganha acima do mínimo recebe na data da coluna do final 6 a 0: finais 1 e 6 juntos na coluna 6, 2 e 7 na coluna 7, 3 e 8 na 8, 4 e 9 na 9, e 5 e 0 na coluna 0.</p>
{tabela_ano(ano, comps)}
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
<h2 id="noticias">Últimas notícias do INSS</h2>
<ul class="bf-noticias">{lis}</ul>
<p><a href="noticias.html?cat=INSS">Ver todas as notícias do INSS</a></p>
<h2 id="outros">Outros benefícios</h2>
<div class="bf-outros">
<a href="bolsa-familia.html">Bolsa Família<small>calendário pelo final do NIS</small></a>
<a href="noticias/guia-bpc-loas-quem-tem-direito-renda-e-avaliacao.html">BPC/LOAS<small>renda, avaliação e o que faz parar</small></a>
<a href="noticias/guia-aposentadoria-inss-2026-idade-pontos-rural-e-especial.html">Aposentadoria<small>idade, pontos, rural e especial</small></a>
<a href="noticias/guia-golpes-contra-quem-recebe-beneficio-como-reconhecer.html">Golpes<small>como reconhecer antes de cair</small></a>
</div>
<h2 id="perguntas">Perguntas frequentes</h2>
{faq_html}<h2>Cuidado com golpe</h2>
<p>Aposentado e pensionista são o alvo preferido dos golpistas. As mensagens mais comuns falam em "revisão liberada", "dinheiro esquecido do INSS", "desconto indevido para devolver" ou "prova de vida pelo link", e terminam sempre pedindo senha, foto do documento, código que chegou por SMS ou um Pix de taxa. Ligação de falso funcionário oferecendo empréstimo consignado também é frequente.</p>
<p>Nenhum órgão do governo cobra taxa nem pede Pix, senha ou foto do cartão para pagar ou liberar benefício. Se o valor vier menor, aparecer um desconto que você não reconhece ou o pagamento parar, não entregue dinheiro a quem promete resolver rápido: procure um profissional de sua confiança para analisar o seu caso.</p>
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
          <p class="autor-box-links"><a href="mailto:contato@portaljuniorarrais.com.br?subject=Correcao: inss">Encontrou um erro? Avise a redação</a></p>
        </div>
      </div>
      <!-- FIM AUTOR -->

      <div class="share-bar">
        <span class="share-titulo">Compartilhe o calendário com quem é aposentado:</span>
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
  <meta property="og:image" content="https://portaljuniorarrais.com.br/img/guia-aposentadoria-inss-2026-idade-pontos-rural-e-especial.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="favicon.png">
  <link rel="stylesheet" href="{css_v}">
  <script type="application/ld+json">{json.dumps(page_ld, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>
{m_head.group(1).rstrip()}
{CSS}{CSS_INSS}</head>
<body>"""

    return (head + m_topo.group(1) + "<main>\n" + corpo + "  </main>" + m_rodape.group(1)
            + site_js + "\n" + JS.replace("__DADOS__", dados_js(comps)) + "</body>\n</html>\n")


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
