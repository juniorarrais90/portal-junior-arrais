#!/usr/bin/env python3
"""Monta a página central do Gás do Povo (gas-do-povo.html).

Fonte dos dados: data/gas-do-povo.json (regras oficiais, lotes do dia 10).
As últimas notícias saem das matérias com o chip "Gás do Povo" e sem noindex.
Reaproveita o visual e as funções da página do Bolsa Família. Criado em 14/11/2026.

Uso:  python scripts/montar_hub_gas.py [--hoje AAAA-MM-DD]
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
from montar_hub_bolsa_familia import (CSS, DIAS, MESES, MOLDE, RAIZ, d,  # noqa: E402
                                      data_extenso_curto, data_longa, hoje_brasilia)

DADOS = os.path.join(RAIZ, "data", "gas-do-povo.json")
SAIDA = os.path.join(RAIZ, "gas-do-povo.html")
URL = "https://portaljuniorarrais.com.br/gas-do-povo.html"
e = html.escape


def soma_meses(ano, mes, n):
    t = ano * 12 + (mes - 1) + n
    return t // 12, t % 12 + 1


def proximo_lote(hoje, dia):
    x = dt.date(hoje.year, hoje.month, dia)
    if x < hoje:
        a, m = soma_meses(hoje.year, hoje.month, 1)
        x = dt.date(a, m, dia)
    return x


def noticias_gas(limite=8):
    itens = []
    for arq in glob.glob(os.path.join(RAIZ, "noticias", "*.html")):
        slug = os.path.basename(arq)[:-5]
        if slug.startswith("guia-"):
            continue
        t = open(arq, encoding="utf-8").read()
        if 'name="robots" content="noindex' in t:
            continue
        chip = re.search(r'<span class="chip">([^<]*)</span>', t)
        if not chip or html.unescape(chip.group(1)).strip() != "Gás do Povo":
            continue
        h1 = re.search(r"<h1>(.*?)</h1>", t, re.S)
        pub = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})', t)
        if not h1 or not pub:
            continue
        titulo = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
        itens.append((pub.group(1), slug, titulo))
    itens.sort(reverse=True)
    return itens[:limite]


CSS_GAS = """
  <style>
  .gp-proximo { background: linear-gradient(135deg, #0f7a3d, #16a34a 60%, #22c55e); box-shadow: 0 8px 26px rgba(22, 163, 74, .25); }
  .gp-proximo .bf-botoes button[aria-pressed="true"], .gp-proximo .in-faixa button[aria-pressed="true"] { color: #0f7a3d; }
  .in-faixa { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
  .in-faixa button { min-height: 48px; border: 0; border-radius: 12px; background: rgba(255, 255, 255, .18); color: #fff; font: inherit; font-size: .98rem; font-weight: 700; line-height: 1.2; cursor: pointer; padding: 8px 10px; }
  .in-faixa button:hover { background: rgba(255, 255, 255, .3); }
  .in-faixa button[aria-pressed="true"] { background: #fff; }
  .in-faixa button:focus-visible, .gp-meses button:focus-visible { outline: 3px solid #fff; outline-offset: 2px; }
  .gp-meses { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .gp-meses button { min-height: 44px; border: 0; border-radius: 12px; background: rgba(255, 255, 255, .18); color: #fff; font: inherit; font-size: .95rem; font-weight: 700; cursor: pointer; text-transform: capitalize; }
  .gp-meses button:hover { background: rgba(255, 255, 255, .3); }
  .gp-meses button[aria-pressed="true"] { background: #fff; color: #0f7a3d; }
  </style>
"""

JS = r"""
<script>
(function () {
  var GP = __DADOS__;
  var MESES = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
  var DIAS = ["domingo","segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado"];
  function hoje() {
    try {
      return new Intl.DateTimeFormat("en-CA", {timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit"}).format(new Date());
    } catch (e) { var d = new Date(); d.setHours(d.getHours() - 3); return d.toISOString().slice(0, 10); }
  }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function iso(a, m, d) { return a + "-" + pad(m) + "-" + pad(d); }
  function soma(a, m, n) { var t = a * 12 + (m - 1) + n; return [Math.floor(t / 12), t % 12 + 1]; }
  function dt(s) { var p = s.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function longa(s) { var x = dt(s); return x.getDate() + " de " + MESES[x.getMonth()]; }
  function quando(s, h) {
    if (s === h) return "hoje";
    if (Math.round((dt(s) - dt(h)) / 86400000) === 1) return "amanhã";
    return DIAS[dt(s).getDay()] + ", " + longa(s);
  }
  var h = hoje(), A = +h.slice(0, 4), M = +h.slice(5, 7), D = +h.slice(8, 10);
  var prox = D <= GP.dia ? iso(A, M, GP.dia) : (function () { var s = soma(A, M, 1); return iso(s[0], s[1], GP.dia); })();
  var q = quando(prox, h);
  document.getElementById("bf-proximo-data").textContent = q.charAt(0).toUpperCase() + q.slice(1) + (q === "hoje" || q === "amanhã" ? " (" + longa(prox) + ")" : "");
  var dias = Math.round((dt(prox) - dt(h)) / 86400000);
  document.getElementById("bf-proximo-quem").textContent = dias === 0 ? "O lote de vales do mês sai hoje." : "Faltam " + dias + (dias === 1 ? " dia" : " dias") + " para o próximo lote de vales.";
  // botões dos últimos 6 meses (o mês do lote atual primeiro)
  var caixa = document.getElementById("gp-meses");
  var base = D >= GP.dia ? [A, M] : soma(A, M, -1);
  for (var i = 0; i < 6; i++) {
    var s = soma(base[0], base[1], -i);
    var b = document.createElement("button");
    b.type = "button"; b.setAttribute("aria-pressed", "false");
    b.setAttribute("data-mes", s[0] + "-" + pad(s[1]));
    b.textContent = MESES[s[1] - 1].slice(0, 3) + (s[0] !== A ? "/" + String(s[0]).slice(2) : "");
    b.setAttribute("aria-label", MESES[s[1] - 1] + " de " + s[0]);
    caixa.appendChild(b);
  }
  var resp = document.getElementById("bf-resposta");
  var tam = null, mes = null;
  function responder() {
    if (tam === null || mes === null) { resp.textContent = tam === null && mes !== null ? "Agora escolha o tamanho da família." : ""; return; }
    var ciclo = tam === "grande" ? GP.ciclo_grande : GP.ciclo_pequena;
    var a = +mes.slice(0, 4), m = +mes.slice(5, 7);
    var s = soma(a, m, ciclo), nx = iso(s[0], s[1], GP.dia);
    var t;
    if (nx >= h) {
      t = "Com vale de " + MESES[m - 1] + ", o próximo deve sair <strong>" + (quando(nx, h) === "hoje" || quando(nx, h) === "amanhã" ? quando(nx, h) : "em " + longa(nx) + " de " + s[0]) + "</strong>, se a família continuar dentro das regras. O vale atual pode ser usado até a chegada do próximo.";
    } else {
      t = "Pelo ciclo de " + ciclo + " meses, o vale seguinte ao de " + MESES[m - 1] + " já deveria ter saído em " + longa(nx) + ". Se ele não apareceu, o cadastro pode ter alguma pendência.";
    }
    resp.innerHTML = t;
    try { localStorage.setItem("pja-gas", tam + "|" + mes); } catch (e) {}
  }
  var bt = document.querySelectorAll(".in-faixa button"), bm = caixa.querySelectorAll("button");
  bt.forEach(function (b) { b.addEventListener("click", function () { tam = b.getAttribute("data-tam"); bt.forEach(function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); }); responder(); }); });
  bm.forEach(function (b) { b.addEventListener("click", function () { mes = b.getAttribute("data-mes"); bm.forEach(function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); }); responder(); }); });
  try {
    var sv = (localStorage.getItem("pja-gas") || "").split("|");
    if (sv.length === 2) {
      tam = sv[0];
      bt.forEach(function (o) { o.setAttribute("aria-pressed", o.getAttribute("data-tam") === tam ? "true" : "false"); });
      bm.forEach(function (o) { if (o.getAttribute("data-mes") === sv[1]) { mes = sv[1]; o.setAttribute("aria-pressed", "true"); } });
      responder();
    }
  } catch (e) {}
})();
</script>
"""


def tabela_lotes(hoje, dados, n=6):
    r = dados["regras"]
    x = proximo_lote(hoje, r["dia_do_lote"])
    a, m = x.year, x.month
    linhas = []
    for i in range(-1, n - 1):
        aa, mm = soma_meses(a, m, i)
        dia = dt.date(aa, mm, r["dia_do_lote"])
        k = f"{aa}-{mm:02d}"
        lote = dados["lotes"].get(k)
        qtd = f'{e(lote["vales"])} de vales' if lote else ("a divulgar" if dia >= hoje else "—")
        cls = ' class="bf-pago"' if dia < hoje else (' class="bf-hoje"' if dia == hoje else "")
        linhas.append(f'<tr{cls}><td>{MESES[mm - 1].capitalize()} de {aa}</td><td>{dia.day:02d}/{mm:02d}</td>'
                      f'<td>{DIAS[dia.weekday()]}</td><td>{qtd}</td></tr>')
    return ('<div class="bf-tabela-wrap"><table class="bf-tabela"><thead><tr><th>Lote</th><th>Data</th>'
            '<th>Dia</th><th>Vales</th></tr></thead><tbody>' + "".join(linhas) + '</tbody></table></div>')


def montar(hoje):
    with open(DADOS, encoding="utf-8") as f:
        dados = json.load(f)
    r = dados["regras"]
    molde = open(MOLDE, encoding="utf-8").read()
    m_head = re.search(r"(  <!-- ADSENSE -->.*?)</head>", molde, re.S)
    m_topo = re.search(r"<body>(.*?)<main>", molde, re.S)
    m_rodape = re.search(r"</main>(.*?)<script src=\"site\.js[^\"]*\"></script>", molde, re.S)
    assert m_head and m_topo and m_rodape, "molde guias.html mudou: revisar regex"
    site_js = re.search(r'<script src="site\.js[^"]*"></script>', molde).group(0)
    css_v = re.search(r'styles\.css\?v=\d+', molde).group(0)

    px = proximo_lote(hoje, r["dia_do_lote"])
    mes_px = MESES[px.month - 1]
    titulo = f"Gás do Povo: próximo vale em {px.day} de {mes_px}, quem recebe e regras"
    descricao = (f"O próximo lote do Gás do Povo sai em {data_longa(px)} ({DIAS[px.weekday()]}). Veja de quanto "
                 f"em quanto tempo a família recebe, quanto dura o vale, quem tem direito, o que a revenda "
                 f"pode cobrar e as últimas notícias do programa.")
    q = "hoje" if px == hoje else ("amanhã" if px == hoje + dt.timedelta(days=1) else f"{DIAS[px.weekday()]}, {data_longa(px)}")
    fallback_data = (q[0].upper() + q[1:]) + (f" ({data_longa(px)})" if q in ("hoje", "amanhã") else "")
    dias = (px - hoje).days
    fallback_quem = "O lote de vales do mês sai hoje." if dias == 0 else f"Faltam {dias} dias para o próximo lote de vales."

    ultimo_k = max(dados["lotes"])
    ul = dados["lotes"][ultimo_k]
    ul_mes = MESES[int(ultimo_k[5:]) - 1]

    noticias = noticias_gas()
    lis = "".join(
        f'<li><a href="noticias/{s}.html"><img src="img/{s}.png" alt="" loading="lazy" width="112" height="63">'
        f'<span>{e(t)}<small>{data_extenso_curto(d(pub))}</small></span></a></li>'
        for pub, s, t in noticias)
    atualizado = data_extenso_curto(d(dados["atualizado_em"]))
    titulo_share = quote(titulo)
    vig = d(r["vigencia_ate"])

    faq = [
        ("Todo mundo recebe o vale todo mês?",
         f"Não. Cada família tem o próprio ciclo. Família de 2 ou 3 pessoas recebe um vale a cada "
         f"{r['ciclo_pequena']} meses; família de 4 pessoas ou mais, a cada {r['ciclo_grande']} meses. Por isso "
         f"a vizinha pode receber num mês em que você não recebe, sem erro nenhum."),
        ("Até quando posso usar o vale?",
         f"Segundo o Ministério do Desenvolvimento e Assistência Social, o vale tem validade de "
         f"{r['ciclo_pequena']} meses para família de 2 ou 3 pessoas e de {r['ciclo_grande']} meses para família "
         f"de 4 pessoas ou mais, ou seja, até perto da chegada do vale seguinte. Vale que vence sem uso não "
         f"se acumula."),
        ("Quem tem direito ao Gás do Povo?",
         f"Família inscrita no CadÚnico, com renda de até {r['renda']} (R$ {r['renda_valor']} em 2026), cadastro "
         f"atualizado nos últimos {r['cadastro_meses']} meses, sem pendência como averiguação cadastral e com o "
         f"CPF do responsável regular. A entrada é automática e, neste momento, a prioridade é para famílias do "
         f"Bolsa Família com duas pessoas ou mais."),
        ("A revenda pode cobrar alguma coisa?",
         "O vale cobre só a recarga do botijão de 13 kg. A revenda pode cobrar à parte a entrega em casa, o "
         "vasilhame, quando a família não tem botijão vazio para trocar, e a instalação. Taxa para liberar o vale "
         "não existe."),
        ("O programa vai acabar?",
         f"Não há previsão de fim. Em novembro de 2026 o governo prorrogou a vigência do Gás do Povo até "
         f"{vig.day} de {MESES[vig.month - 1]} de {vig.year}."),
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
        "about": {"@type": "GovernmentService", "name": "Programa Gás do Povo",
                  "provider": {"@type": "GovernmentOrganization",
                               "name": "Ministério do Desenvolvimento e Assistência Social, Família e Combate à Fome"}},
        "author": {"@type": "Person", "@id": "https://portaljuniorarrais.com.br/sobre.html#autor",
                   "name": "Júnior Arrais", "url": "https://portaljuniorarrais.com.br/sobre.html#autor",
                   "jobTitle": "Editor responsável"},
        "publisher": {"@type": "NewsMediaOrganization", "@id": "https://portaljuniorarrais.com.br/sobre.html#organizacao",
                      "name": "Portal Júnior Arrais",
                      "logo": {"@type": "ImageObject", "url": "https://portaljuniorarrais.com.br/img/logo-portal.png"}},
        "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Início", "item": "https://portaljuniorarrais.com.br/"},
            {"@type": "ListItem", "position": 2, "name": "Gás do Povo", "item": URL}]},
    }
    fontes_html = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a></li>' for u, t in dados["fontes"])
    js_dados = json.dumps({"dia": r["dia_do_lote"], "ciclo_pequena": r["ciclo_pequena"], "ciclo_grande": r["ciclo_grande"]})

    corpo = f"""
    <article class="artigo">
      <p class="bf-trilha"><a href="/">Início</a> › Gás do Povo</p>
      <div><span class="chip">Gás do Povo</span></div>
      <h1>{e(titulo)}</h1>
      <div class="meta"><img src="img/junior-avatar.png" alt="Júnior Arrais" class="autor-foto"> Por <a href="sobre.html#autor" class="autor-link">Júnior Arrais</a> &middot; Atualizado em {atualizado}</div>

      <section class="bf-proximo gp-proximo" aria-live="polite">
        <span class="bf-proximo-rotulo">Próximo lote de vales</span>
        <span class="bf-proximo-data" id="bf-proximo-data">{e(fallback_data)}</span>
        <span class="bf-proximo-quem" id="bf-proximo-quem">{e(fallback_quem)}</span>
        <div class="bf-seletor">
          <span class="bf-seletor-rotulo" style="font-size:1.1rem">Quando sai o seu próximo vale?</span>
          <span class="bf-seletor-rotulo">1. Quantas pessoas tem a família?</span>
          <div class="in-faixa" role="group" aria-label="Tamanho da família">
            <button type="button" data-tam="pequena" aria-pressed="false">2 ou 3 pessoas</button>
            <button type="button" data-tam="grande" aria-pressed="false">4 pessoas ou mais</button>
          </div>
          <span class="bf-seletor-rotulo">2. Em que mês saiu o seu último vale?</span>
          <div class="gp-meses" id="gp-meses" role="group" aria-label="Mês do último vale"></div>
          <p class="bf-resposta" id="bf-resposta"></p>
        </div>
      </section>

      <div class="artigo-conteudo">
<p>O Gás do Povo troca o antigo Auxílio Gás em dinheiro por um <strong>vale-recarga</strong>: a família leva o vale a uma revenda credenciada e sai com o botijão de 13 kg cheio, sem pagar pela recarga. Os vales novos saem sempre no <strong>dia {r['dia_do_lote']} de cada mês</strong>, e o próximo lote é em <strong>{data_longa(px)}</strong>. Aqui você descobre quando sai o seu próximo vale, quanto tempo ele dura, quem tem direito e as notícias mais recentes, atualizadas todos os dias.</p>
<h2 id="lotes">Calendário de lotes do Gás do Povo</h2>
<p>O lote sai no dia {r['dia_do_lote']} mesmo quando cai em fim de semana ou feriado. Em {ul_mes}, foram liberados <strong>{e(ul['vales'])} de vales</strong>: {e(ul['novas'])} para famílias que entraram no programa e {e(ul['antigas'])} para famílias que já participavam. Desde o começo do programa, {e(r['vales_usados'])} de vales já foram usados.</p>
{tabela_lotes(hoje, dados)}
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
<h2 id="frequencia">De quanto em quanto tempo a família recebe</h2>
<p>Nem toda família recebe vale em todo lote. O intervalo depende do número de pessoas registrado no CadÚnico:</p>
<ul class="bf-valores">
<li><strong>A cada {r['ciclo_pequena']} meses</strong>família de 2 ou 3 pessoas, com vale válido por {r['ciclo_pequena']} meses</li>
<li><strong>A cada {r['ciclo_grande']} meses</strong>família de 4 pessoas ou mais, com vale válido por {r['ciclo_grande']} meses</li>
</ul>
<p>O ciclo conta a partir do mês em que a família recebeu o último vale. Em {ul_mes}, por exemplo, ganharam vale novo as famílias de 2 ou 3 pessoas que tinham recebido {r['ciclo_pequena']} meses antes e as de 4 ou mais que tinham recebido {r['ciclo_grande']} meses antes. Para que o vale seguinte venha, a família precisa continuar dentro das regras, com o cadastro em dia.</p>
<h2 id="direito">Quem tem direito</h2>
<ul>
<li>família inscrita no <strong>CadÚnico</strong>, com os dados atualizados nos últimos {r['cadastro_meses']} meses;</li>
<li>renda de até <strong>{r['renda']}</strong>, o que dá R$ {r['renda_valor']} em 2026;</li>
<li>cadastro sem pendência, como averiguação cadastral ou indício de óbito do responsável familiar;</li>
<li>CPF do responsável familiar regular na Receita Federal.</li>
</ul>
<p>Não existe inscrição própria: a seleção é automática e leva em conta a menor renda, o tamanho da família e o risco de insegurança alimentar. Neste momento, o governo dá prioridade às famílias do Bolsa Família com duas pessoas ou mais. Em novembro de 2026, o programa foi prorrogado até {vig.day} de {MESES[vig.month - 1]} de {vig.year}. As regras completas estão no <a href="noticias/guia-gas-do-povo-como-funciona-quem-recebe-e-prazos.html">guia do Gás do Povo</a>.</p>
<h2 id="cobranca">O que a revenda pode cobrar</h2>
<p>O vale paga só a recarga do botijão de 13 kg; a Caixa ressarce a revenda por um preço de referência da região. Pode haver cobrança à parte, e ela é legítima, pela <strong>entrega em casa</strong>, pelo <strong>vasilhame</strong>, quando a família não tem o botijão vazio para trocar, e pela <strong>instalação</strong>. Pergunte o valor antes de fechar. Já "taxa do programa", "taxa de liberação" ou "diferença do governo" não existem.</p>
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
<h2 id="noticias">Últimas notícias do Gás do Povo</h2>
<ul class="bf-noticias">{lis}</ul>
<p><a href="noticias.html?cat=G%C3%A1s%20do%20Povo">Ver todas as notícias do Gás do Povo</a></p>
<h2 id="outros">Outros benefícios</h2>
<div class="bf-outros">
<a href="bolsa-familia.html">Bolsa Família<small>calendário pelo final do NIS</small></a>
<a href="inss.html">INSS<small>calendário de aposentados e pensionistas</small></a>
<a href="noticias/guia-cadunico-o-que-e-quem-pode-e-quando-atualizar.html">CadÚnico<small>quem pode entrar e quando atualizar</small></a>
<a href="noticias/guia-conta-de-luz-tarifa-social-luz-do-povo-e-desconto-social.html">Conta de luz<small>tarifa social e descontos</small></a>
</div>
<h2 id="perguntas">Perguntas frequentes</h2>
{faq_html}<h2>Cuidado com golpe</h2>
<p>Como o Gás do Povo não deposita dinheiro, qualquer mensagem que fale em "sacar o valor do gás", "resgatar o benefício pelo link" ou "pagar taxa para não perder o vale do mês" é golpe. Também circula a promessa de "vale em dobro" ou de "cadastro rápido" no programa, sempre pedindo os dados do cartão ou um Pix.</p>
<p>Nenhum órgão do governo cobra taxa nem pede Pix, senha ou dados do cartão para liberar recarga. Se a família está dentro das regras e o vale não vem, se a revenda recusou a troca ou se o benefício foi cortado sem explicação, não pague ninguém para destravar: procure um profissional de sua confiança para olhar a situação do cadastro.</p>
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
          <p class="autor-box-links"><a href="mailto:contato@portaljuniorarrais.com.br?subject=Correcao: gas-do-povo">Encontrou um erro? Avise a redação</a></p>
        </div>
      </div>
      <!-- FIM AUTOR -->

      <div class="share-bar">
        <span class="share-titulo">Compartilhe com quem recebe o Gás do Povo:</span>
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
  <meta property="og:image" content="https://portaljuniorarrais.com.br/img/guia-gas-do-povo-como-funciona-quem-recebe-e-prazos.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="favicon.png">
  <link rel="stylesheet" href="{css_v}">
  <script type="application/ld+json">{json.dumps(page_ld, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>
{m_head.group(1).rstrip()}
{CSS}{CSS_GAS}</head>
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
