#!/usr/bin/env python3
"""Monta a página central do Pé-de-Meia (pe-de-meia.html).

Fonte dos dados: data/pe-de-meia.json (janelas oficiais do MEC, valores).
As últimas notícias saem das matérias com o chip "Pé-de-Meia" e sem noindex.
Reaproveita o visual e as funções da página do Bolsa Família. Criado em 14/11/2026.

O dia exato por mês de nascimento só é mostrado como "confirmado" quando a
parcela tem 'por_nascimento' no JSON (tabela da Caixa). Sem isso, e se a janela
tiver exatamente 6 dias úteis, a página mostra a previsão pela ordem de sempre
(jan-fev no 1º dia útil ... nov-dez no 6º), marcada como previsão.

Uso:  python scripts/montar_hub_pe_de_meia.py [--hoje AAAA-MM-DD]
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
                                      data_curta, data_extenso_curto, data_longa,
                                      hoje_brasilia)

DADOS = os.path.join(RAIZ, "data", "pe-de-meia.json")
SAIDA = os.path.join(RAIZ, "pe-de-meia.html")
URL = "https://portaljuniorarrais.com.br/pe-de-meia.html"
FERIADOS = {"2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03", "2026-04-21", "2026-05-01",
            "2026-06-04", "2026-09-07", "2026-10-12", "2026-11-02", "2026-11-15", "2026-11-20",
            "2026-12-25", "2027-01-01", "2027-02-08", "2027-02-09"}
PARES = ["janeiro ou fevereiro", "março ou abril", "maio ou junho", "julho ou agosto",
         "setembro ou outubro", "novembro ou dezembro"]
e = html.escape


def uteis(ini, fim):
    out, x = [], ini
    while x <= fim:
        if x.weekday() < 5 and x.isoformat() not in FERIADOS:
            out.append(x)
        x += dt.timedelta(days=1)
    return out


def preparar(dados):
    ps = []
    for p in dados["parcelas"]:
        ini, fim = d(p["ini"]), d(p["fim"])
        if p.get("por_nascimento"):
            dias, conf = [d(x) for x in p["por_nascimento"]], True
        else:
            u = uteis(ini, fim)
            dias, conf = (u if len(u) == 6 else None), False
        ps.append({**p, "ini_d": ini, "fim_d": fim, "dias": dias, "confirmado": conf})
    return ps


def noticias_pdm(limite=8):
    itens = []
    for arq in glob.glob(os.path.join(RAIZ, "noticias", "*.html")):
        slug = os.path.basename(arq)[:-5]
        if slug.startswith("guia-"):
            continue
        t = open(arq, encoding="utf-8").read()
        if 'name="robots" content="noindex' in t:
            continue
        chip = re.search(r'<span class="chip">([^<]*)</span>', t)
        if not chip or html.unescape(chip.group(1)).strip() != "Pé-de-Meia":
            continue
        h1 = re.search(r"<h1>(.*?)</h1>", t, re.S)
        pub = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})', t)
        if not h1 or not pub:
            continue
        titulo = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
        itens.append((pub.group(1), slug, titulo))
    itens.sort(reverse=True)
    return itens[:limite]


def janela(p):
    a, b = p["ini_d"], p["fim_d"]
    if a.month == b.month:
        return f"{a.day} a {b.day} de {MESES[b.month - 1]}"
    return f"{data_longa(a)} a {data_longa(b)}"


CSS_PDM = """
  <style>
  .pm-proximo { background: linear-gradient(135deg, #5b21b6, #7c3aed 60%, #a855f7); box-shadow: 0 8px 26px rgba(124, 58, 237, .25); }
  .pm-meses { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .pm-meses button { min-height: 44px; border: 0; border-radius: 12px; background: rgba(255, 255, 255, .18); color: #fff; font: inherit; font-size: .95rem; font-weight: 700; cursor: pointer; text-transform: capitalize; }
  .pm-meses button:hover { background: rgba(255, 255, 255, .3); }
  .pm-meses button[aria-pressed="true"] { background: #fff; color: #5b21b6; }
  .pm-meses button:focus-visible { outline: 3px solid #fff; outline-offset: 2px; }
  .pm-tab td small { display: block; color: #6b7a8c; font-size: .8rem; }
  .pm-tab td, .pm-tab th { white-space: normal; }
  </style>
"""

JS = r"""
<script>
(function () {
  var PM = __DADOS__;
  var MESES = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
  var DIAS = ["domingo","segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado"];
  function hoje() {
    try {
      return new Intl.DateTimeFormat("en-CA", {timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit"}).format(new Date());
    } catch (e) { var d = new Date(); d.setHours(d.getHours() - 3); return d.toISOString().slice(0, 10); }
  }
  function dt(s) { var p = s.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function longa(s) { var x = dt(s); return x.getDate() + " de " + MESES[x.getMonth()]; }
  function janela(p) { var a = dt(p.ini), b = dt(p.fim); return a.getMonth() === b.getMonth() ? a.getDate() + " a " + b.getDate() + " de " + MESES[b.getMonth()] : longa(p.ini) + " a " + longa(p.fim); }
  var h = hoje();
  var atual = null;
  for (var i = 0; i < PM.parcelas.length; i++) { if (PM.parcelas[i].fim >= h) { atual = PM.parcelas[i]; break; } }
  var elD = document.getElementById("bf-proximo-data"), elQ = document.getElementById("bf-proximo-quem");
  if (!atual) {
    elD.textContent = "Conclusão e Enem: " + longa(PM.conclusao.ini) + " a " + longa(PM.conclusao.fim);
    elQ.textContent = "Parcela de R$ 1.000 pela aprovação e R$ 200 do Enem.";
  } else {
    elD.textContent = (atual.ini <= h ? "Pagando agora: " : "") + janela(atual);
    elQ.textContent = atual.n + "ª parcela de R$ 200" + (atual.ref ? ", referente à frequência de " + atual.ref : "") + ".";
  }
  var resp = document.getElementById("bf-resposta");
  var bs = document.querySelectorAll(".pm-meses button");
  function escolher(m) {
    bs.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-mes") === String(m) ? "true" : "false"); });
    if (!atual) { resp.textContent = "As parcelas mensais de 2026 terminaram. A próxima data é a da conclusão e do Enem."; return; }
    var g = Math.floor((+m - 1) / 2);
    var t = "Quem nasceu em " + MESES[+m - 1] + ": ";
    if (atual.dias) {
      var x = atual.dias[g];
      var passou = x < h;
      var wd = dt(x).getDay(); t += "a " + atual.n + "ª parcela " + (passou ? "já caiu " : "cai <strong>") + (wd === 0 || wd === 6 ? "no " : "na ") + DIAS[wd] + ", " + longa(x) + (passou ? "" : "</strong>") + ".";
      if (!atual.confirmado) t += " É a previsão pela ordem de sempre da Caixa, que confirma a tabela perto da data.";
    } else {
      t += "a " + atual.n + "ª parcela cai entre <strong>" + janela(atual) + "</strong>. A Caixa divulga o dia exato de cada mês de nascimento perto da data.";
    }
    resp.innerHTML = t;
    try { localStorage.setItem("pja-pdm", String(m)); } catch (e) {}
  }
  bs.forEach(function (b) { b.addEventListener("click", function () { escolher(b.getAttribute("data-mes")); }); });
  try { var s = localStorage.getItem("pja-pdm"); if (s) escolher(s); } catch (e) {}
})();
</script>
"""


def montar(hoje):
    with open(DADOS, encoding="utf-8") as f:
        dados = json.load(f)
    v = dados["valores"]
    ps = preparar(dados)
    molde = open(MOLDE, encoding="utf-8").read()
    m_head = re.search(r"(  <!-- ADSENSE -->.*?)</head>", molde, re.S)
    m_topo = re.search(r"<body>(.*?)<main>", molde, re.S)
    m_rodape = re.search(r"</main>(.*?)<script src=\"site\.js[^\"]*\"></script>", molde, re.S)
    assert m_head and m_topo and m_rodape, "molde guias.html mudou: revisar regex"
    site_js = re.search(r'<script src="site\.js[^"]*"></script>', molde).group(0)
    css_v = re.search(r'styles\.css\?v=\d+', molde).group(0)

    atual = next((p for p in ps if p["fim_d"] >= hoje), None)
    con_ini, con_fim = d(dados["conclusao"]["ini"]), d(dados["conclusao"]["fim"])
    if atual:
        titulo = f"Pé-de-Meia 2026: {atual['n']}ª parcela de {janela(atual)}, calendário e valores"
        descricao = (f"A {atual['n']}ª parcela do Pé-de-Meia é paga de {janela(atual)}. Veja o dia pelo mês de "
                     f"nascimento, o calendário de 2026, quanto o estudante recebe, a conclusão e o Enem em 2027 "
                     f"e as últimas notícias do programa.")
        fb_data = ("Pagando agora: " if atual["ini_d"] <= hoje else "") + janela(atual)
        fb_quem = f"{atual['n']}ª parcela de R$ {v['frequencia']}" + (f", referente à frequência de {atual['ref']}." if atual["ref"] else ".")
    else:
        titulo = "Pé-de-Meia: calendário de pagamentos, valores e últimas notícias"
        descricao = "Calendário do Pé-de-Meia, valores, conclusão e Enem e as notícias mais recentes do programa."
        fb_data = f"Conclusão e Enem: {data_longa(con_ini)} a {data_longa(con_fim)}"
        fb_quem = "Parcela de R$ 1.000 pela aprovação e R$ 200 do Enem."

    linhas = []
    for p in ps:
        cls = ' class="bf-pago"' if p["fim_d"] < hoje else (' class="bf-hoje"' if p is atual else "")
        ref = f"<small>frequência de {e(p['ref'])}</small>" if p["ref"] and p["n"] >= 5 else ""
        st = "paga" if p["fim_d"] < hoje else ("pagando agora" if p["ini_d"] <= hoje else ("próxima" if p is atual else "prevista"))
        linhas.append(f'<tr{cls}><td>{p["n"]}ª parcela{ref}</td><td>{janela(p)} de {p["fim_d"].year}</td><td>{st}</td></tr>')
    tabela = ('<div class="bf-tabela-wrap"><table class="bf-tabela pm-tab"><thead><tr><th>Parcela</th><th>Janela de pagamento</th>'
              '<th>Situação</th></tr></thead><tbody>' + "".join(linhas)
              + f'<tr><td>Aprovação + Enem</td><td>{data_longa(con_ini)} a {data_longa(con_fim)} de {con_fim.year}</td><td>prevista</td></tr>'
              + '</tbody></table></div>')

    tab_nasc = ""
    if atual and atual["dias"]:
        rot = "Dia confirmado pela Caixa" if atual["confirmado"] else "Dia previsto"
        ls = "".join(f'<tr><td>{PARES[i].capitalize()}</td><td>{data_curta(x)}</td><td>{DIAS[x.weekday()]}</td></tr>'
                     for i, x in enumerate(atual["dias"]))
        aviso = ("" if atual["confirmado"] else
                 f'<p class="bf-nota">As datas por mês de nascimento da {atual["n"]}ª parcela seguem a ordem que a Caixa usou nas '
                 f'parcelas anteriores. A tabela oficial sai perto da data, e esta página é atualizada quando ela for divulgada.</p>')
        tab_nasc = (f'<h2 id="nascimento">Dia da {atual["n"]}ª parcela pelo mês de nascimento</h2>\n'
                    f'<p>Dentro de cada janela, a Caixa paga primeiro quem nasceu em janeiro e fevereiro e por último quem nasceu em novembro e dezembro, um par de meses por dia útil.</p>\n'
                    f'<div class="bf-tabela-wrap"><table class="bf-tabela"><thead><tr><th>Nasceu em</th><th>{rot}</th><th>Dia</th></tr></thead>'
                    f'<tbody>{ls}</tbody></table></div>\n{aviso}')
    elif atual:
        tab_nasc = (f'<h2 id="nascimento">Dia da {atual["n"]}ª parcela pelo mês de nascimento</h2>\n'
                    f'<p>A {atual["n"]}ª parcela cai entre {janela(atual)}. Como a janela tem feriado no meio, a Caixa ainda vai '
                    f'divulgar em que dia cada mês de nascimento recebe. Esta página é atualizada quando a tabela sair.</p>\n')

    noticias = noticias_pdm()
    lis = "".join(
        f'<li><a href="noticias/{s}.html"><img src="img/{s}.png" alt="" loading="lazy" width="112" height="63">'
        f'<span>{e(t)}<small>{data_extenso_curto(d(pub))}</small></span></a></li>'
        for pub, s, t in noticias)
    atualizado = data_extenso_curto(d(dados["atualizado_em"]))
    titulo_share = quote(titulo)
    aj = d(dados["prazo_ajuste_2025"])

    faq = [
        ("Por que a parcela de um mês paga a frequência de outro?",
         "Porque a escola precisa mandar os dados de presença ao Ministério da Educação, que confere tudo antes de "
         "gerar o depósito. Por isso a parcela de novembro, por exemplo, corresponde à frequência de setembro."),
        ("Caiu o dinheiro, mas não consigo sacar. Por quê?",
         "A conta é aberta pela Caixa no nome do estudante. Quem tem menos de 18 anos só movimenta o dinheiro depois "
         "que o responsável legal autoriza na Caixa. O valor não se perde enquanto isso: continua guardado na conta."),
        ("Quando sai a parcela de R$ 1.000?",
         f"A parcela pela aprovação do ano, de R$ 1.000, e a do Enem, de R$ {v['enem']} para quem fez os dois "
         f"dias de prova no 3º ano, têm a primeira data de pagamento entre {data_longa(con_ini)} e "
         f"{data_longa(con_fim)} de {con_fim.year}. O valor da aprovação fica guardado e só pode ser sacado quando o "
         f"estudante conclui o ensino médio."),
        ("Quem tem direito ao Pé-de-Meia?",
         f"Estudante do ensino médio da rede pública, de 14 a 24 anos no ensino regular ou de 19 a 24 anos na EJA, de "
         f"família inscrita no CadÚnico com renda de até meio salário mínimo por pessoa (R$ {v['renda_valor']} em 2026), "
         f"com CPF regular e frequência mínima de 80%. A inclusão é automática."),
        ("A parcela não caiu. Ainda dá para receber?",
         f"Se o problema foi dado errado enviado pela escola, sim: as parcelas corrigidas de 2026 podem ser pagas de "
         f"{dados['correcao']}. Para parcelas de 2025, a rede de ensino tem até {aj.day} de {MESES[aj.month - 1]} de "
         f"{aj.year} para fazer o ajuste. Não pague ninguém para liberar: procure um profissional de sua confiança se "
         f"precisar de ajuda com o caso."),
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
        "about": {"@type": "GovernmentService", "name": "Programa Pé-de-Meia",
                  "provider": {"@type": "GovernmentOrganization", "name": "Ministério da Educação"}},
        "author": {"@type": "Person", "@id": "https://portaljuniorarrais.com.br/sobre.html#autor",
                   "name": "Júnior Arrais", "url": "https://portaljuniorarrais.com.br/sobre.html#autor",
                   "jobTitle": "Editor responsável"},
        "publisher": {"@type": "NewsMediaOrganization", "@id": "https://portaljuniorarrais.com.br/sobre.html#organizacao",
                      "name": "Portal Júnior Arrais",
                      "logo": {"@type": "ImageObject", "url": "https://portaljuniorarrais.com.br/img/logo-portal.png"}},
        "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Início", "item": "https://portaljuniorarrais.com.br/"},
            {"@type": "ListItem", "position": 2, "name": "Pé-de-Meia", "item": URL}]},
    }
    fontes_html = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a></li>' for u, t in dados["fontes"])
    js_dados = json.dumps({
        "parcelas": [{"n": p["n"], "ini": p["ini"], "fim": p["fim"], "ref": p["ref"],
                      "dias": [x.isoformat() for x in p["dias"]] if p["dias"] else None,
                      "confirmado": p["confirmado"]} for p in ps],
        "conclusao": dados["conclusao"]}, ensure_ascii=False, separators=(",", ":"))
    botoes = "".join(f'<button type="button" data-mes="{i + 1}" aria-pressed="false" aria-label="{m}">{m[:3]}</button>'
                     for i, m in enumerate(MESES))

    lead = (f'<p>O Pé-de-Meia é a poupança do governo federal para o estudante de baixa renda terminar o ensino médio. '
            f'Em 2026, o aluno do ensino regular recebe <strong>R$ {v["frequencia"]} por mês</strong> de frequência, em até '
            f'{v["parcelas_frequencia"]} parcelas, além de R$ {v["matricula"]} pela matrícula, R$ {v["conclusao"]} por ano '
            f'aprovado e R$ {v["enem"]} pelo Enem. '
            + (f'A próxima parcela, a {atual["n"]}ª, cai de <strong>{janela(atual)}</strong>. ' if atual else '')
            + 'Aqui você vê o dia pelo mês de nascimento, o calendário do ano inteiro, os valores e as notícias mais '
              'recentes, atualizadas todos os dias.</p>')

    corpo = f"""
    <article class="artigo">
      <p class="bf-trilha"><a href="/">Início</a> › Pé-de-Meia</p>
      <div><span class="chip">Pé-de-Meia</span></div>
      <h1>{e(titulo)}</h1>
      <div class="meta"><img src="img/junior-avatar.png" alt="Júnior Arrais" class="autor-foto"> Por <a href="sobre.html#autor" class="autor-link">Júnior Arrais</a> &middot; Atualizado em {atualizado}</div>

      <section class="bf-proximo pm-proximo" aria-live="polite">
        <span class="bf-proximo-rotulo">Próxima parcela do Pé-de-Meia</span>
        <span class="bf-proximo-data" id="bf-proximo-data">{e(fb_data)}</span>
        <span class="bf-proximo-quem" id="bf-proximo-quem">{e(fb_quem)}</span>
        <div class="bf-seletor">
          <span class="bf-seletor-rotulo">Toque no mês de aniversário do estudante:</span>
          <div class="pm-meses" role="group" aria-label="Mês de nascimento">{botoes}</div>
          <p class="bf-resposta" id="bf-resposta"></p>
        </div>
      </section>

      <div class="artigo-conteudo">
{lead}
{tab_nasc}
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
<h2 id="calendario">Calendário do Pé-de-Meia de 2026</h2>
<p>Estas são as janelas oficiais do Ministério da Educação para o ensino médio regular. Cada parcela de frequência corresponde à presença de cerca de dois meses antes, porque a escola precisa enviar os dados primeiro. Na EJA, as parcelas do 2º semestre seguem as mesmas janelas de setembro a dezembro.</p>
{tabela}
<p>Se algum dado da escola impediu o pagamento, as parcelas de 2026 corrigidas podem ser liberadas de {e(dados['correcao'])}.</p>
<h2 id="valores">Quanto o estudante recebe</h2>
<ul class="bf-valores">
<li><strong>R$ {v['frequencia']}</strong>por mês de frequência, até {v['parcelas_frequencia']} parcelas no ano</li>
<li><strong>R$ {v['matricula']}</strong>pela matrícula, uma vez por ano</li>
<li><strong>R$ {v['conclusao']:,}</strong>por ano aprovado, guardado até o fim do ensino médio</li>
<li><strong>R$ {v['enem']}</strong>pelos dois dias do Enem, no 3º ano</li>
</ul>
<p>Somando os três anos, o ensino regular pode chegar a <strong>R$ {e(v['total_3_anos'])}</strong> por estudante. Na Educação de Jovens e Adultos (EJA), são até {v['eja_parcelas']} parcelas de R$ {v['eja_frequencia']}, quatro por semestre. Para receber cada parcela, o estudante precisa de pelo menos 80% de presença no mês de referência. As regras completas estão no <a href="noticias/guia-pe-de-meia-regras-valores-e-calendario.html">guia do Pé-de-Meia</a>.</p>
<h2 id="conta">Por que o dinheiro fica travado</h2>
<p>A Caixa abre a conta sozinha, no nome do estudante. Como a maioria tem menos de 18 anos, o saldo aparece, mas o jovem só consegue sacar ou pagar depois que o responsável legal autoriza a movimentação na Caixa. Enquanto isso, o dinheiro fica guardado e não se perde. A parcela de R$ {v['conclusao']:,} por ano aprovado é diferente: ela só pode ser retirada quando o estudante termina o ensino médio, e reprovar ou abandonar a escola compromete esse valor.</p>
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
<h2 id="noticias">Últimas notícias do Pé-de-Meia</h2>
<ul class="bf-noticias">{lis}</ul>
<p><a href="noticias.html?cat=P%C3%A9-de-Meia">Ver todas as notícias do Pé-de-Meia</a></p>
<h2 id="outros">Outros benefícios</h2>
<div class="bf-outros">
<a href="bolsa-familia.html">Bolsa Família<small>calendário pelo final do NIS</small></a>
<a href="gas-do-povo.html">Gás do Povo<small>quando sai o próximo vale</small></a>
<a href="inss.html">INSS<small>calendário de aposentados e pensionistas</small></a>
<a href="noticias/guia-cadunico-o-que-e-quem-pode-e-quando-atualizar.html">CadÚnico<small>quem pode entrar e quando atualizar</small></a>
</div>
<h2 id="perguntas">Perguntas frequentes</h2>
{faq_html}<h2>Cuidado com golpe</h2>
<p>Programa voltado a adolescente atrai golpista que fala direto com o jovem, longe dos pais. As mensagens prometem "destravar a parcela", "antecipar o depósito", "sacar os R$ 1.000 agora" ou "fazer a inscrição no programa", e pedem senha, código recebido por SMS ou foto do documento. Não existe inscrição, não existe taxa, e o depósito cai sozinho na conta da Caixa na data do calendário.</p>
<p>Nenhum órgão do governo cobra taxa nem pede Pix, senha ou dados do cartão para liberar parcela. Se o valor não caiu, sumiu da conta ou ficou bloqueado, converse com a família e não entregue dinheiro a quem promete resolver: procure um profissional de sua confiança para analisar o caso.</p>
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
          <p class="autor-box-links"><a href="mailto:contato@portaljuniorarrais.com.br?subject=Correcao: pe-de-meia">Encontrou um erro? Avise a redação</a></p>
        </div>
      </div>
      <!-- FIM AUTOR -->

      <div class="share-bar">
        <span class="share-titulo">Compartilhe com quem tem estudante em casa:</span>
        <div class="share-botoes">
          <a class="share-btn share-wa" target="_blank" rel="noopener" href="https://api.whatsapp.com/send?text={titulo_share}%0A%0A{URL}">WhatsApp</a>
          <button class="share-btn share-fb" type="button" onclick="pjaFacebook(this)">Facebook</button>
          <a class="share-btn share-tg" target="_blank" rel="noopener" href="https://t.me/share/url?url={URL}&amp;text={titulo_share}">Telegram</a>
          <button class="share-btn share-copiar" type="button" onclick="pjaCopiarLink(this)">Copiar link</button>
        </div>
      </div>
      <!-- fim COMPARTILHAR -->
    </article>
""".replace("R$ 1,000", "R$ 1.000").replace("R$ 1000", "R$ 1.000")

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
  <meta property="og:image" content="https://portaljuniorarrais.com.br/img/guia-pe-de-meia-regras-valores-e-calendario.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="favicon.png">
  <link rel="stylesheet" href="{css_v}">
  <script type="application/ld+json">{json.dumps(page_ld, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>
{m_head.group(1).rstrip()}
{CSS}{CSS_PDM}</head>
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
