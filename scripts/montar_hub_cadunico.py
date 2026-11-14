#!/usr/bin/env python3
"""Monta a página central do CadÚnico (cadunico.html).

Sem calendário de pagamento: a página traz duas ferramentas (calculadora de
renda por pessoa, com os limites de cada programa, e "até quando vale o seu
cadastro") e reúne as regras e as notícias. As notícias saem das matérias
sem noindex que têm "CadÚnico"/"Cadastro Único" no título ou "cadunico" no
endereço. Reaproveita o visual da página do Bolsa Família. Criado em 14/11/2026.

Os limites de renda acompanham o salário mínimo: ao mudar o mínimo, atualizar
SALARIO_MINIMO e LIMITES abaixo (e a data ATUALIZADO).

Uso:  python scripts/montar_hub_cadunico.py [--hoje AAAA-MM-DD]
"""
import glob
import html
import json
import os
import re
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from montar_hub_bolsa_familia import (CSS, MESES, MOLDE, RAIZ, d,  # noqa: E402
                                      data_extenso_curto, hoje_brasilia)

SAIDA = os.path.join(RAIZ, "cadunico.html")
URL = "https://portaljuniorarrais.com.br/cadunico.html"
ATUALIZADO = "2026-11-14"
PUBLICADO = "2026-11-14"
SALARIO_MINIMO = 1621.00
# programa, limite mínimo por pessoa (exclusivo), limite máximo por pessoa (inclusivo), observação, link
LIMITES = [
    ("CadÚnico", 0, 810.50, "pode se inscrever", "#quem-pode"),
    ("Bolsa Família", 0, 218.00, "renda até R$ 218 por pessoa", "bolsa-familia.html"),
    ("BPC/LOAS", 0, 405.25, "só para idoso com 65 anos ou mais ou pessoa com deficiência", "bpc-loas.html"),
    ("Gás do Povo", 0, 810.50, "prioridade para quem recebe Bolsa Família", "gas-do-povo.html"),
    ("Pé-de-Meia", 0, 810.50, "só para estudante do ensino médio público", "pe-de-meia.html"),
    ("Tarifa Social de energia", 0, 810.50, "desconto na conta de luz", "noticias/guia-conta-de-luz-tarifa-social-luz-do-povo-e-desconto-social.html"),
    ("Desconto Social de energia", 810.50, 1621.00, "faixa entre meio e um salário mínimo por pessoa", "noticias/guia-conta-de-luz-tarifa-social-luz-do-povo-e-desconto-social.html"),
]
e = html.escape


def brl(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def noticias_cad(limite=8):
    itens = []
    for arq in glob.glob(os.path.join(RAIZ, "noticias", "*.html")):
        slug = os.path.basename(arq)[:-5]
        if slug.startswith("guia-"):
            continue
        t = open(arq, encoding="utf-8").read()
        if 'name="robots" content="noindex' in t:
            continue
        h1 = re.search(r"<h1>(.*?)</h1>", t, re.S)
        pub = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})', t)
        if not h1 or not pub:
            continue
        titulo = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
        if "cadunico" not in slug and "CadÚnico" not in titulo and "Cadastro Único" not in titulo:
            continue
        itens.append((pub.group(1), slug, titulo))
    itens.sort(reverse=True)
    return itens[:limite]


CSS_CAD = """
  <style>
  .cu-proximo { background: linear-gradient(135deg, #0e7490, #0891b2 60%, #06b6d4); box-shadow: 0 8px 26px rgba(8, 145, 178, .25); }
  .cu-campos { display: grid; grid-template-columns: 1.4fr 1fr; gap: 10px; margin-bottom: 12px; align-items: end; }
  .cu-campos label { display: block; font-weight: 700; font-size: .92rem; margin-bottom: 6px; }
  .cu-campos input, .cu-validade select { width: 100%; box-sizing: border-box; height: 48px; border: 0; border-radius: 12px; padding: 0 12px; font: inherit; font-size: 1.1rem; font-weight: 700; color: #0e3a47; background: #fff; }
  .cu-campos input:focus, .cu-validade select:focus { outline: 3px solid #fff; outline-offset: 1px; }
  .cu-res { margin-top: 6px; }
  .cu-res:empty { display: none; }
  .cu-pc { font-size: 1.05rem; font-weight: 700; margin: 0 0 10px; }
  .cu-pc strong { font-size: 1.5rem; display: block; }
  .cu-lista { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
  .cu-lista li { display: flex; gap: 10px; align-items: flex-start; background: rgba(255, 255, 255, .14); border-radius: 10px; padding: 9px 12px; font-size: .95rem; line-height: 1.3; }
  .cu-lista li b { flex: none; width: 22px; height: 22px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: .85rem; background: rgba(255, 255, 255, .25); }
  .cu-lista li.ok b { background: #fff; color: #0e7490; }
  .cu-lista li.nao { opacity: .7; }
  .cu-lista a { color: #fff !important; font-weight: 800; }
  .cu-lista small { display: block; opacity: .85; }
  .cu-aviso { font-size: .85rem; opacity: .9; margin: 10px 0 0; }
  .cu-validade { background: #ecfeff; border: 1px solid #a5f3fc; border-radius: 14px; padding: 16px; margin: 0 0 18px; }
  .cu-validade .cu-sel { display: grid; grid-template-columns: 1.3fr 1fr; gap: 10px; margin: 10px 0; }
  .cu-validade select { background: #fff; border: 1px solid #a5f3fc; font-size: 1rem; }
  .cu-validade p { margin: 0; }
  #cu-val-res { font-weight: 700; margin-top: 8px; }
  #cu-val-res.ok { color: #17803d; } #cu-val-res.atencao { color: #a16207; } #cu-val-res.vencido { color: #a3361f; }
  @media (max-width: 480px) { .cu-campos, .cu-validade .cu-sel { grid-template-columns: 1fr 1fr; } }
  </style>
"""

JS = r"""
<script>
(function () {
  var C = __DADOS__;
  function brl(v) { return v.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2}); }
  function num(s) { s = (s || "").replace(/[^\d,\.]/g, ""); if (s.indexOf(",") >= 0) s = s.replace(/\./g, "").replace(",", "."); else if (/^\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, ""); return parseFloat(s); }
  var elR = document.getElementById("cu-renda"), elP = document.getElementById("cu-pessoas"), out = document.getElementById("cu-res");
  function calc() {
    var r = num(elR.value), p = parseInt(elP.value, 10);
    if (isNaN(r) || !p || p < 1) { out.innerHTML = ""; return; }
    var pc = r / p, h = '<p class="cu-pc">Renda por pessoa<strong>R$ ' + brl(pc) + '</strong></p><ul class="cu-lista">';
    C.limites.forEach(function (l) {
      var ok = pc > l[1] && pc <= l[2];
      h += '<li class="' + (ok ? "ok" : "nao") + '"><b>' + (ok ? "✓" : "–") + '</b><span><a href="' + l[4] + '">' + l[0] + '</a>' +
        (ok ? " — dentro do limite de renda" : " — fora da faixa de renda") + '<small>' + l[3] + '</small></span></li>';
    });
    h += '</ul><p class="cu-aviso">A renda é só uma das regras: cada programa tem outras exigências, e quem decide é o órgão responsável.</p>';
    out.innerHTML = h;
  }
  elR.addEventListener("input", calc); elP.addEventListener("input", calc);
  // validade do cadastro
  var MESES = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
  var sm = document.getElementById("cu-mes"), sa = document.getElementById("cu-ano"), vr = document.getElementById("cu-val-res");
  var hoje = new Date(); var A = hoje.getFullYear(), M = hoje.getMonth() + 1;
  for (var y = A; y >= A - 6; y--) { var o = document.createElement("option"); o.value = y; o.textContent = y; sa.appendChild(o); }
  function val() {
    var m = +sm.value, a = +sa.value;
    if (!m || !a) { vr.textContent = ""; vr.className = ""; return; }
    var meses = (A - a) * 12 + (M - m);
    if (meses < 0) { vr.textContent = "Essa data ainda não chegou."; vr.className = ""; return; }
    var vm = (m - 1 + 24) % 12 + 1, va = a + Math.floor((m - 1 + 24) / 12);
    if (meses >= 48) { vr.textContent = "O cadastro está sem atualização há " + meses + " meses. Com 48 meses, ele pode ser excluído da base: a atualização é urgente."; vr.className = "vencido"; }
    else if (meses >= 24) { vr.textContent = "O prazo de 24 meses venceu em " + MESES[vm - 1] + " de " + va + ". Quem recebe benefício pode ter bloqueio: atualize o quanto antes."; vr.className = "vencido"; }
    else if (meses >= 18) { vr.textContent = "Vale até " + MESES[vm - 1] + " de " + va + ". Já passou de 18 meses, quando a convocação para revisão costuma chegar."; vr.className = "atencao"; }
    else { vr.textContent = "Em dia: vale até " + MESES[vm - 1] + " de " + va + ", se nada mudar na família antes disso."; vr.className = "ok"; }
  }
  sm.addEventListener("change", val); sa.addEventListener("change", val);
})();
</script>
"""


def montar(hoje):
    molde = open(MOLDE, encoding="utf-8").read()
    m_head = re.search(r"(  <!-- ADSENSE -->.*?)</head>", molde, re.S)
    m_topo = re.search(r"<body>(.*?)<main>", molde, re.S)
    m_rodape = re.search(r"</main>(.*?)<script src=\"site\.js[^\"]*\"></script>", molde, re.S)
    assert m_head and m_topo and m_rodape, "molde guias.html mudou: revisar regex"
    site_js = re.search(r'<script src="site\.js[^"]*"></script>', molde).group(0)
    css_v = re.search(r'styles\.css\?v=\d+', molde).group(0)

    meio = brl(SALARIO_MINIMO / 2)
    titulo = "CadÚnico 2026: quem pode entrar, calculadora de renda e prazo de atualização"
    descricao = (f"Veja se a renda da sua família cabe no CadÚnico (até R$ {meio} por pessoa) e em cada programa, "
                 f"até quando vale o seu cadastro, a revisão cadastral de 2026, a biometria e as últimas notícias.")
    noticias = noticias_cad()
    lis = "".join(
        f'<li><a href="noticias/{s}.html"><img src="img/{s}.png" alt="" loading="lazy" width="112" height="63">'
        f'<span>{e(t)}<small>{data_extenso_curto(d(pub))}</small></span></a></li>'
        for pub, s, t in noticias)
    atualizado = data_extenso_curto(d(ATUALIZADO))
    titulo_share = quote(titulo)

    linhas_prog = "".join(
        f'<tr><td><a href="{h}">{e(n)}</a></td><td>'
        + (f"de R$ {brl(a)} até R$ {brl(b)}" if a else f"até R$ {brl(b)}")
        + f'</td><td>{e(o)}</td></tr>' for n, a, b, o, h in LIMITES[1:])
    tabela_prog = ('<div class="bf-tabela-wrap"><table class="bf-tabela" style="white-space:normal"><thead><tr><th>Programa</th>'
                   '<th>Renda por pessoa</th><th>Observação</th></tr></thead><tbody>' + linhas_prog
                   + '</tbody></table></div>').replace('white-space: nowrap', '')

    faq = [
        ("Estar no CadÚnico garante algum benefício?",
         "Não. O CadÚnico é o cadastro que permite pedir os benefícios, não um benefício. Cada programa tem a "
         "própria regra de renda e outras exigências, e a seleção é feita pelo órgão responsável por ele."),
        ("De quanto em quanto tempo preciso atualizar?",
         "No máximo a cada 24 meses, mesmo que nada tenha mudado, e na hora sempre que algo muda: nascimento, "
         "morte, alguém que entra ou sai da casa, mudança de endereço, emprego, renda ou escola das crianças."),
        ("O que acontece se eu não atualizar?",
         "Na revisão cadastral de 2026, quem foi convocado e não atualizou pode ter o Bolsa Família bloqueado por "
         "até dois meses e depois cancelado, perder a Tarifa Social de energia e, no BPC, ter o pagamento "
         "suspenso. Cadastro com 48 meses sem atualização pode ser excluído da base."),
        ("Quem mora sozinho precisa receber visita em casa?",
         "A visita no domicílio para atualizar famílias de uma pessoa só que recebem Bolsa Família, e para quem "
         "recebe BPC, ficou adiada para 1º de julho de 2027 pela Portaria MDS nº 1.199/2026. Ela continua "
         "obrigatória para entrar no Bolsa Família e para famílias em averiguação cadastral."),
        ("Preciso fazer biometria?",
         "A Portaria Conjunta nº 23/2026 fixou 31 de dezembro de 2026 como prazo para o cadastro biométrico de "
         "quem é elegível ao Bolsa Família e de quem pede alguns benefícios do INSS e do trabalho. Quem já tem "
         "biometria na Justiça Eleitoral, na CNH ou no passaporte segue a regra anterior."),
    ]
    faq_html = "".join(f"<h3>{e(pq)}</h3>\n<p>{e(rp)}</p>\n" for pq, rp in faq)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": pq,
                              "acceptedAnswer": {"@type": "Answer", "text": rp}} for pq, rp in faq]}
    page_ld = {
        "@context": "https://schema.org", "@type": "WebPage", "name": titulo, "description": descricao,
        "url": URL, "inLanguage": "pt-BR", "datePublished": PUBLICADO, "dateModified": ATUALIZADO,
        "isPartOf": {"@type": "WebSite", "name": "Portal Júnior Arrais", "url": "https://portaljuniorarrais.com.br/"},
        "about": {"@type": "GovernmentService", "name": "Cadastro Único para Programas Sociais (CadÚnico)",
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
            {"@type": "ListItem", "position": 2, "name": "CadÚnico", "item": URL}]},
    }
    fontes = [
        ("https://www.gov.br/mds/pt-br/acoes-e-programas/cadastro-unico", "MDS: página oficial do Cadastro Único"),
        ("https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/lei/l15077.htm", "Lei nº 15.077/2024 (validade de 24 meses das informações)"),
        ("https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2022/decreto/d11016.htm", "Decreto nº 11.016/2022 (regulamenta o Cadastro Único)"),
        ("https://www.gov.br/mds/pt-br/acesso-a-informacao/legislacao/instrucoes/in-ave-rev/AnexoINConjunta2_2026EdioAgosto.pdf",
         "MDS: Instrução Normativa Conjunta nº 2/2026 (revisão cadastral e Portaria nº 1.199/2026)"),
    ]
    fontes_html = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a></li>' for u, t in fontes)
    js_dados = json.dumps({"limites": LIMITES}, ensure_ascii=False)
    opcoes_mes = "".join(f'<option value="{i + 1}">{m}</option>' for i, m in enumerate(MESES))

    corpo = f"""
    <article class="artigo">
      <p class="bf-trilha"><a href="/">Início</a> › CadÚnico</p>
      <div><span class="chip">CadÚnico</span></div>
      <h1>{e(titulo)}</h1>
      <div class="meta"><img src="img/junior-avatar.png" alt="Júnior Arrais" class="autor-foto"> Por <a href="sobre.html#autor" class="autor-link">Júnior Arrais</a> &middot; Atualizado em {atualizado}</div>

      <section class="bf-proximo cu-proximo">
        <span class="bf-proximo-rotulo">Calculadora de renda</span>
        <span class="bf-proximo-data">A sua família cabe no CadÚnico?</span>
        <span class="bf-proximo-quem">Some tudo o que entra na casa por mês e conte quem mora junto.</span>
        <div class="bf-seletor">
          <div class="cu-campos">
            <div><label for="cu-renda">Renda total da casa (R$)</label><input id="cu-renda" inputmode="decimal" autocomplete="off" placeholder="ex.: 1.500"></div>
            <div><label for="cu-pessoas">Pessoas na casa</label><input id="cu-pessoas" type="number" min="1" max="20" inputmode="numeric" placeholder="ex.: 4"></div>
          </div>
          <div class="cu-res" id="cu-res" aria-live="polite"></div>
        </div>
      </section>

      <div class="artigo-conteudo">
<p>O <strong>Cadastro Único</strong>, o CadÚnico, é o registro das famílias de baixa renda nas bases do governo federal e a porta de entrada de quase todo benefício social do país, do Bolsa Família ao Pé-de-Meia. Ele não é um benefício: é o cadastro que permite pedir os benefícios. Aqui você calcula a renda por pessoa da sua família, descobre até quando vale o seu cadastro e entende a revisão cadastral de 2026, com as notícias mais recentes, atualizadas todos os dias.</p>
<div class="cu-validade" id="validade">
<p><strong>Até quando vale o seu cadastro?</strong> Escolha o mês e o ano da última atualização:</p>
<div class="cu-sel">
<select id="cu-mes" aria-label="Mês da última atualização"><option value="">Mês</option>{opcoes_mes}</select>
<select id="cu-ano" aria-label="Ano da última atualização"><option value="">Ano</option></select>
</div>
<p id="cu-val-res" aria-live="polite"></p>
</div>
<h2 id="quem-pode">Quem pode se inscrever</h2>
<p>Pode entrar a família com renda de até <strong>meio salário mínimo por pessoa, R$ {meio}</strong> em 2026. Para chegar a esse número, soma-se tudo o que os moradores da casa recebem no mês e divide-se pelo número de pessoas. Famílias com renda maior também podem ser incluídas quando estão ligadas a algum programa que usa o cadastro. O cadastro é feito por família, e uma pessoa com pelo menos 16 anos, de preferência mulher, assume o papel de responsável familiar.</p>
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
<h2 id="programas">Os programas que usam o CadÚnico</h2>
<p>Estar no cadastro é condição para todos estes programas, mas não garante nenhum. Cada um tem o seu limite de renda por pessoa:</p>
{tabela_prog}
<p>A lista vai além: Minha Casa Minha Vida na faixa subsidiada, Fies Social, isenção de taxa de concurso e de Enem, carteira do idoso e tarifa social de água também usam o cadastro.</p>
<h2 id="prazos">Os dois prazos de atualização</h2>
<ul>
<li><strong>a cada 24 meses</strong>, mesmo que nada tenha mudado: a Lei nº 15.077/2024 fixou esse limite para quem recebe benefício, e a convocação costuma chegar a partir dos 18 meses;</li>
<li><strong>na hora, sempre que algo muda</strong>: nascimento, morte, alguém que entra ou sai da casa, novo endereço, emprego ou renda diferente, criança que troca de escola.</li>
</ul>
<p>Como vários programas leem a mesma base, um cadastro desatualizado pode derrubar o Bolsa Família e o desconto na conta de luz ao mesmo tempo. Detalhes em <a href="noticias/cadunico-quando-e-obrigatorio-atualizar-o-cadastro.html">quando é obrigatório atualizar</a>.</p>
<h2 id="revisao">A revisão cadastral de 2026</h2>
<p>O Ministério do Desenvolvimento e Assistência Social convocou cerca de <strong>11,3 milhões de famílias</strong> para atualizar os dados: cadastros sem atualização desde dezembro de 2023 ou antes e famílias com Bolsa Família, BPC ou Tarifa Social cuja última atualização foi entre janeiro de 2024 e janeiro de 2025. Quem não responde no prazo do seu grupo tem o Bolsa Família bloqueado por até dois meses e depois cancelado, perde a Tarifa Social e, no BPC, pode ter o pagamento suspenso. As exclusões de cadastro estavam previstas para começar em novembro de 2026.</p>
<p>A convocação verdadeira chega pelos canais oficiais: mensagem no aplicativo do Cadastro Único, aviso no extrato do Bolsa Família e, na Tarifa Social, recado impresso na conta de luz. Veja <a href="noticias/cadunico-revisao-convoca-11-milhoes-bloqueios-novembro.html">o que acontece com cada benefício</a>.</p>
<h2 id="unipessoal">Quem mora sozinho e a biometria</h2>
<p>A visita em casa para atualizar o cadastro de quem mora sozinho e recebe Bolsa Família, e de quem recebe BPC, foi adiada para <strong>1º de julho de 2027</strong> pela Portaria MDS nº 1.199/2026. Ela continua obrigatória para entrar no Bolsa Família e para famílias em averiguação. Já a biometria tem prazo até <strong>31 de dezembro de 2026</strong> para quem é elegível ao Bolsa Família e para quem pede alguns benefícios do INSS e do trabalho, pela Portaria Conjunta nº 23/2026; quem já tem biometria no título de eleitor, na CNH ou no passaporte segue a regra anterior. O caminho é a nova Carteira de Identidade Nacional, cuja primeira via é emitida sem cobrança.</p>
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
<h2 id="noticias">Últimas notícias do CadÚnico</h2>
<ul class="bf-noticias">{lis}</ul>
<p>As regras completas estão no <a href="noticias/guia-cadunico-o-que-e-quem-pode-e-quando-atualizar.html">guia do CadÚnico</a>.</p>
<h2 id="outros">Calendários dos benefícios</h2>
<div class="bf-outros">
<a href="bolsa-familia.html">Bolsa Família<small>data pelo final do NIS</small></a>
<a href="bpc-loas.html">BPC/LOAS<small>data pelo final do cartão</small></a>
<a href="gas-do-povo.html">Gás do Povo<small>quando sai o próximo vale</small></a>
<a href="pe-de-meia.html">Pé-de-Meia<small>dia pelo mês de aniversário</small></a>
</div>
<h2 id="perguntas">Perguntas frequentes</h2>
{faq_html}<h2>Cuidado com golpe</h2>
<p>A revisão cadastral virou isca. Circulam mensagens dizendo que o cadastro "será excluído hoje", com link para "atualizar pelo celular", e falsos agentes que batem na porta ou ligam pedindo dinheiro para "regularizar o CadÚnico" ou "garantir a vaga" em algum programa. Há também quem venda "inscrição" em benefício, o que não existe: a seleção é automática, feita pelo governo a partir do cadastro.</p>
<p>Nenhum órgão do governo cobra taxa nem pede Pix, senha ou foto do cartão para fazer ou atualizar o cadastro. Se a família foi bloqueada, cortada de algum programa ou ficou com dúvida sobre como declarar a renda, não pague quem promete resolver por fora: procure um profissional de sua confiança para analisar a situação.</p>
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
          <p class="autor-box-links"><a href="mailto:contato@portaljuniorarrais.com.br?subject=Correcao: cadunico">Encontrou um erro? Avise a redação</a></p>
        </div>
      </div>
      <!-- FIM AUTOR -->

      <div class="share-bar">
        <span class="share-titulo">Compartilhe com quem precisa atualizar o cadastro:</span>
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
  <meta property="og:image" content="https://portaljuniorarrais.com.br/img/guia-cadunico-o-que-e-quem-pode-e-quando-atualizar.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="favicon.png">
  <link rel="stylesheet" href="{css_v}">
  <script type="application/ld+json">{json.dumps(page_ld, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>
{m_head.group(1).rstrip()}
{CSS}{CSS_CAD}</head>
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
