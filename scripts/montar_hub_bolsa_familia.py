#!/usr/bin/env python3
"""Monta a página central do Bolsa Família (bolsa-familia.html).

Fonte dos dados: data/bolsa-familia.json (calendário oficial, calendário
especial, cidades com pagamento unificado e valores). As últimas notícias saem
das matérias de noticias/ com o chip "Bolsa Família" e sem noindex.

Rodar sempre que mudar o JSON. O robô .github/workflows/hub-bolsa-familia.yml
roda todo dia, para atualizar o "próximo pagamento" e as notícias.

Uso:  python scripts/montar_hub_bolsa_familia.py [--hoje AAAA-MM-DD]
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

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(RAIZ, "data", "bolsa-familia.json")
MOLDE = os.path.join(RAIZ, "guias.html")
SAIDA = os.path.join(RAIZ, "bolsa-familia.html")
URL = "https://portaljuniorarrais.com.br/bolsa-familia.html"

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
MESES_CURTOS = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.",
                "set.", "out.", "nov.", "dez."]
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]
FINAIS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
UFS = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
       "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
       "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
       "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
       "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
       "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia",
       "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe",
       "TO": "Tocantins"}

e = html.escape


def d(s):
    return dt.date.fromisoformat(s)


def data_longa(x):
    return f"{x.day} de {MESES[x.month - 1]}"


def data_curta(x):
    return f"{x.day:02d}/{x.month:02d}"


def data_extenso_curto(x):
    return f"{x.day} de {MESES_CURTOS[x.month - 1]} de {x.year}"


def lista_finais(fs):
    fs = [str(f) for f in fs]
    if len(fs) == 1:
        return f"NIS final {fs[0]}"
    return "NIS finais " + ", ".join(fs[:-1]) + " e " + fs[-1]


def hoje_brasilia():
    for i, a in enumerate(sys.argv):
        if a == "--hoje":
            return d(sys.argv[i + 1])
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).date()


def carregar():
    with open(DADOS, encoding="utf-8") as f:
        dados = json.load(f)
    folhas = {}  # "2026-11" -> {"datas": [date x10], "oficial": [...], "especial": motivo|None}
    for ano, cal in dados["calendario"].items():
        for mes, datas in cal["meses"].items():
            esp = cal.get("especial", {}).get(mes)
            efetivas = esp["datas"] if esp else datas
            assert len(efetivas) == 10 and len(datas) == 10, (ano, mes)
            folhas[f"{ano}-{mes}"] = {
                "datas": [d(x) for x in efetivas],
                "oficial": [d(x) for x in datas],
                "especial": esp,
                "ano": int(ano), "mes": int(mes),
            }
    return dados, dict(sorted(folhas.items()))


def folha_atual(folhas, hoje):
    for k, f in folhas.items():
        if max(f["datas"]) >= hoje:
            return k
    return None


def proximo(folha, hoje):
    futuras = sorted({x for x in folha["datas"] if x >= hoje})
    if not futuras:
        return None, []
    p = futuras[0]
    return p, [FINAIS[i] for i, x in enumerate(folha["datas"]) if x == p]


def noticias_bf(limite=8):
    itens = []
    for arq in glob.glob(os.path.join(RAIZ, "noticias", "*.html")):
        slug = os.path.basename(arq)[:-5]
        if slug.startswith("guia-"):
            continue
        t = open(arq, encoding="utf-8").read()
        if 'name="robots" content="noindex' in t:
            continue
        chip = re.search(r'<span class="chip">([^<]*)</span>', t)
        if not chip or "Bolsa Fam" not in html.unescape(chip.group(1)):
            continue
        h1 = re.search(r"<h1>(.*?)</h1>", t, re.S)
        pub = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})', t)
        if not h1 or not pub:
            continue
        titulo = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
        itens.append((pub.group(1), slug, titulo))
    itens.sort(reverse=True)
    return itens[:limite]


def tabela_mes(folha, hoje, destacar=True):
    linhas = []
    for i, x in enumerate(folha["datas"]):
        cls = ""
        if destacar and x == hoje:
            cls = ' class="bf-hoje"'
        elif destacar and x < hoje:
            cls = ' class="bf-pago"'
        linhas.append(
            f'<tr{cls}><td>Final {FINAIS[i]}</td><td>{data_curta(x)}</td>'
            f'<td>{DIAS[x.weekday()]}</td></tr>')
    return ('<div class="bf-tabela-wrap"><table class="bf-tabela">'
            '<thead><tr><th>Final do NIS</th><th>Data</th><th>Dia</th></tr></thead>'
            '<tbody>' + "".join(linhas) + '</tbody></table></div>')


def bloco_mes(k, folha, dados, hoje, atual):
    nome = f"{MESES[folha['mes'] - 1]} de {folha['ano']}"
    ds = folha["datas"]
    ini, fim = min(ds), max(ds)
    partes = [f'<h2 id="calendario-{k}">Calendário do Bolsa Família de {nome}</h2>']
    if folha["especial"]:
        grupo = [FINAIS[i] for i, x in enumerate(ds) if x == fim]
        partes.append(
            f'<p>O pagamento de {MESES[folha["mes"] - 1]} vai de <strong>{data_longa(ini)}</strong> '
            f'a <strong>{data_longa(fim)}</strong>. O mês está no calendário especial que o '
            f'Ministério do Desenvolvimento e Assistência Social (MDS) criou por causa do El Niño: '
            f'o final 1 recebe no primeiro dia, o final 2 no segundo e os finais {grupo[0]} a {grupo[-1]} '
            f'recebem todos juntos no terceiro dia. Pelo cartaz original, o último grupo só '
            f'receberia em {data_longa(max(folha["oficial"]))}.</p>')
    else:
        partes.append(
            f'<p>O pagamento de {MESES[folha["mes"] - 1]} começa em <strong>{data_longa(ini)}</strong> '
            f'e termina em <strong>{data_longa(fim)}</strong>, um final do NIS por dia útil.</p>')
    partes.append(tabela_mes(folha, hoje, destacar=atual))
    un = dados["unificado"].get(k)
    if un:
        partes.append(
            f'<p class="bf-nota">Em {un["total"]} cidades com emergência ou calamidade reconhecida '
            f'pelo governo federal, todo mundo recebe no primeiro dia, {data_longa(d(un["data"]))}, '
            f'sem olhar o final do NIS. <a href="#unificado-{k}">Veja os estados</a>.</p>')
    return "\n".join(partes)


def bloco_unificado(k, un):
    mes = MESES[int(k[5:]) - 1]
    linhas = "".join(
        f'<tr><td>{e(UFS.get(uf, uf))}</td><td>{n}</td></tr>'
        for uf, n in sorted(un["por_uf"].items(), key=lambda x: (-x[1], UFS.get(x[0], x[0]))))
    return (
        f'<h2 id="unificado-{k}">Cidades com pagamento unificado em {mes}</h2>\n'
        f'<p>Quando uma cidade tem situação de emergência ou estado de calamidade pública '
        f'reconhecido pelo governo federal, por seca, enchente ou outro evento climático, o MDS '
        f'costuma liberar o Bolsa Família de todos os moradores no primeiro dia do calendário. '
        f'Em {mes}, isso vale para <strong>{un["total"]} municípios</strong>, que recebem em '
        f'{data_longa(d(un["data"]))}:</p>\n'
        f'<div class="bf-tabela-wrap"><table class="bf-tabela bf-uf"><thead><tr><th>Estado</th>'
        f'<th>Municípios</th></tr></thead><tbody>{linhas}'
        f'<tr class="bf-total"><td>Total</td><td>{un["total"]}</td></tr></tbody></table></div>\n'
        + lista_cidades(un) +
        f'<p>A lista muda de um mês para o outro: a cidade entra quando o reconhecimento federal '
        f'é publicado e o município pede a medida, e sai quando a situação acaba. Fonte: '
        f'<a href="{e(un["fonte"])}" target="_blank" rel="noopener">comunicado oficial do mês</a>'
        f'{(" e " + e(un["fonte_lista"][0].lower() + un["fonte_lista"][1:])) if un.get("fonte_lista") else ""}.</p>')


def lista_cidades(un):
    cid = un.get("cidades")
    if not cid:
        return ""
    partes = ['<p>Procure a sua cidade na lista abaixo, organizada por estado:</p>']
    for uf, nomes in sorted(cid.items(), key=lambda x: (-len(x[1]), UFS.get(x[0], x[0]))):
        partes.append(f'<h3>{e(UFS.get(uf, uf))} ({len(nomes)})</h3>\n'
                      f'<p class="bf-cidades">{e(", ".join(nomes))}.</p>')
    return "\n".join(partes) + "\n"


def tabela_ano(ano, folhas):
    cab = "".join(f"<th>{f}</th>" for f in FINAIS)
    linhas = []
    for k, f in folhas.items():
        if f["ano"] != ano:
            continue
        marca = " *" if f["especial"] else ""
        cels = "".join(f"<td>{x.day:02d}</td>" for x in f["datas"])
        linhas.append(f'<tr><th scope="row">{MESES[f["mes"] - 1].capitalize()}{marca}</th>{cels}</tr>')
    return (f'<div class="bf-tabela-wrap"><table class="bf-tabela bf-ano"><thead><tr><th>Mês</th>{cab}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def dados_js(folhas, dados):
    js = {"folhas": {}, "unificado": {}}
    for k, f in folhas.items():
        js["folhas"][k] = [x.isoformat() for x in f["datas"]]
    for k, u in dados["unificado"].items():
        js["unificado"][k] = {"total": u["total"], "data": u["data"]}
    return json.dumps(js, ensure_ascii=False, separators=(",", ":"))


CSS = """
  <style>
  .bf-trilha { font-size: .85rem; color: var(--text-muted); margin-bottom: 14px; }
  .bf-trilha a { color: var(--text-muted); }
  .bf-proximo { margin: 4px 0 26px; padding: 20px; border-radius: 16px; background: linear-gradient(135deg, #1e5fb0, #2c89e7 60%, #2bb5e8); color: #fff; box-shadow: 0 8px 26px rgba(44, 137, 231, .25); }
  .bf-proximo-rotulo { display: block; font-size: .78rem; font-weight: 800; letter-spacing: 1.4px; text-transform: uppercase; opacity: .9; }
  .bf-proximo-data { display: block; font-size: clamp(1.7rem, 6vw, 2.3rem); font-weight: 800; line-height: 1.15; margin: 4px 0 2px; }
  .bf-proximo-quem { display: block; font-size: 1rem; opacity: .95; }
  .bf-seletor { margin-top: 18px; padding-top: 16px; border-top: 1px solid rgba(255, 255, 255, .3); }
  .bf-seletor-rotulo { display: block; font-weight: 700; margin-bottom: 10px; }
  .bf-botoes { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
  .bf-botoes button { height: 48px; border: 0; border-radius: 12px; background: rgba(255, 255, 255, .18); color: #fff; font: inherit; font-size: 1.25rem; font-weight: 800; cursor: pointer; }
  .bf-botoes button:hover { background: rgba(255, 255, 255, .3); }
  .bf-botoes button[aria-pressed="true"] { background: #fff; color: #1e5fb0; }
  .bf-botoes button:focus-visible { outline: 3px solid #fff; outline-offset: 2px; }
  .bf-resposta { margin-top: 14px; min-height: 1.5em; font-size: 1.05rem; font-weight: 600; }
  .bf-resposta strong { font-weight: 800; }
  .bf-resposta:empty { display: none; }
  .bf-tabela-wrap { overflow-x: auto; margin: 0 0 18px; border: 1px solid var(--border); border-radius: 12px; }
  .bf-tabela { width: 100%; border-collapse: collapse; font-size: .98rem; background: #fff; }
  .bf-tabela th, .bf-tabela td { padding: 10px 12px; border-bottom: 1px solid var(--border); text-align: left; white-space: nowrap; }
  .bf-tabela thead th { background: #f0f6fd; font-size: .78rem; text-transform: uppercase; letter-spacing: .6px; color: #3b4a5c; }
  .bf-tabela tbody tr:last-child td, .bf-tabela tbody tr:last-child th { border-bottom: 0; }
  .bf-tabela tr.bf-pago td { color: #8a97a8; }
  .bf-tabela tr.bf-hoje td { background: #fff6c2; font-weight: 800; }
  .bf-tabela tr.bf-total td { font-weight: 800; border-top: 2px solid var(--text); }
  .bf-ano th, .bf-ano td { padding: 8px 9px; text-align: center; font-size: .92rem; }
  .bf-ano tbody th { text-align: left; font-weight: 700; }
  .bf-cidades { font-size: .98rem; line-height: 1.6; }
  .bf-nota { font-size: .95rem; background: #f0f6fd; border-left: 4px solid #2c89e7; border-radius: 8px; padding: 10px 14px; }
  .bf-valores { list-style: none; padding: 0; margin: 0 0 18px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .bf-valores li { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px; font-size: .92rem; line-height: 1.35; }
  .bf-valores strong { display: block; font-size: 1.35rem; color: #1e5fb0; }
  @media (max-width: 480px) { .bf-valores { grid-template-columns: 1fr; } }
  .bf-noticias { list-style: none; padding: 0; margin: 0 0 18px; }
  .bf-noticias li { border-bottom: 1px solid var(--border); }
  .bf-noticias a { display: flex; gap: 12px; align-items: center; padding: 10px 0; text-decoration: none !important; color: var(--text) !important; }
  .bf-noticias img { width: 112px; height: 63px; object-fit: cover; border-radius: 8px; flex: none; background: #e8eef5; }
  .bf-noticias span { font-weight: 700; line-height: 1.3; font-size: .98rem; }
  .bf-noticias small { display: block; font-weight: 400; color: var(--text-muted); margin-top: 3px; }
  .bf-outros { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 0 0 18px; }
  .bf-outros a { display: block; padding: 12px 14px; border: 1px solid var(--border); border-radius: 12px; background: #fff; font-weight: 700; text-decoration: none !important; color: var(--text) !important; }
  .bf-outros a small { display: block; font-weight: 400; color: var(--text-muted); font-size: .85rem; }
  @media (max-width: 480px) { .bf-outros { grid-template-columns: 1fr; } }
  </style>
"""

JS = r"""
<script>
(function () {
  var BF = __DADOS__;
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
    var dif = Math.round((dt(s) - dt(h)) / 86400000);
    if (dif === 1) return "amanhã";
    return DIAS[dt(s).getDay()] + ", " + longa(s);
  }
  function naData(s, h) {
    var q = quando(s, h);
    if (q === "hoje" || q === "amanhã") return q;
    return (dt(s).getDay() === 0 || dt(s).getDay() === 6 ? "no " : "na ") + q;
  }
  function finais(lista) {
    if (lista.length === 1) return "NIS final " + lista[0];
    return "NIS finais " + lista.slice(0, -1).join(", ") + " e " + lista[lista.length - 1];
  }
  var h = hoje();
  var chaves = Object.keys(BF.folhas).sort();
  var atual = null, seguinte = null;
  for (var i = 0; i < chaves.length; i++) {
    var ds = BF.folhas[chaves[i]].slice().sort();
    if (ds[ds.length - 1] >= h) { atual = chaves[i]; seguinte = chaves[i + 1] || null; break; }
  }
  var elData = document.getElementById("bf-proximo-data");
  var elQuem = document.getElementById("bf-proximo-quem");
  if (!atual) {
    elData.textContent = "Calendário de " + (+h.slice(0, 4) + (h.slice(5, 7) === "12" ? 1 : 0)) + " ainda não saiu";
    elQuem.textContent = "Assim que o governo divulgar, o portal atualiza esta página.";
  } else {
    var datas = BF.folhas[atual];
    var futuras = datas.filter(function (x) { return x >= h; }).sort();
    var p = futuras[0];
    var quem = [];
    datas.forEach(function (x, i) { if (x === p) quem.push(FINAIS[i]); });
    var q = quando(p, h);
    elData.textContent = q.charAt(0).toUpperCase() + q.slice(1) + (q === "hoje" || q === "amanhã" ? " (" + longa(p) + ")" : "");
    var txt = "Recebe: " + finais(quem);
    var u = BF.unificado[atual];
    if (u && u.data === p) txt += " e moradores das " + u.total + " cidades com pagamento unificado";
    elQuem.textContent = txt + ".";
  }
  var resp = document.getElementById("bf-resposta");
  var botoes = document.querySelectorAll(".bf-botoes button");
  function escolher(f) {
    botoes.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-final") === String(f) ? "true" : "false"); });
    if (!atual) { resp.textContent = "O calendário do próximo ano ainda não foi divulgado."; return; }
    var idx = FINAIS.indexOf(+f);
    var mes = MESES[+atual.slice(5, 7) - 1];
    var dia = BF.folhas[atual][idx];
    if (dia >= h) {
      resp.innerHTML = "Final " + f + ": o Bolsa Família de " + mes + " cai <strong>" + naData(dia, h) + "</strong>.";
    } else {
      var t = "Final " + f + ": o pagamento de " + mes + " já saiu em " + longa(dia) + ".";
      if (seguinte) {
        var d2 = BF.folhas[seguinte][idx];
        t += " O de " + MESES[+seguinte.slice(5, 7) - 1] + " cai <strong>" + naData(d2, h) + "</strong>.";
      } else {
        t += " As datas do próximo ano ainda não foram divulgadas.";
      }
      resp.innerHTML = t;
    }
    try { localStorage.setItem("pja-nis", String(f)); } catch (e) {}
  }
  botoes.forEach(function (b) { b.addEventListener("click", function () { escolher(b.getAttribute("data-final")); }); });
  try { var salvo = localStorage.getItem("pja-nis"); if (salvo !== null && salvo !== "") escolher(salvo); } catch (e) {}
})();
</script>
"""


def montar(hoje):
    dados, folhas = carregar()
    v = dados["valores"]
    k = folha_atual(folhas, hoje)
    molde = open(MOLDE, encoding="utf-8").read()
    m_head = re.search(r"(  <!-- ADSENSE -->.*?)</head>", molde, re.S)
    m_topo = re.search(r"<body>(.*?)<main>", molde, re.S)
    m_rodape = re.search(r"</main>(.*?)<script src=\"site\.js[^\"]*\"></script>", molde, re.S)
    assert m_head and m_topo and m_rodape, "molde guias.html mudou: revisar regex"
    site_js = re.search(r'<script src="site\.js[^"]*"></script>', molde).group(0)
    css_v = re.search(r'styles\.css\?v=\d+', molde).group(0)

    if k:
        fa = folhas[k]
        nome_mes = MESES[fa["mes"] - 1]
        p, quem = proximo(fa, hoje)
        titulo = f"Bolsa Família 2026: calendário de {nome_mes}, valor e últimas notícias"
        ini, fim = min(fa["datas"]), max(fa["datas"])
        descricao = (f"Calendário do Bolsa Família de {nome_mes} de {fa['ano']} por final do NIS "
                     f"({data_curta(ini)} a {data_curta(fim)}), próximas datas, cidades com pagamento "
                     f"unificado, valores de 2026 e as notícias mais recentes do programa.")
        q = "hoje" if p == hoje else ("amanhã" if p == hoje + dt.timedelta(days=1) else f"{DIAS[p.weekday()]}, {data_longa(p)}")
        fallback_data = (q[0].upper() + q[1:]) + (f" ({data_longa(p)})" if q in ("hoje", "amanhã") else "")
        fallback_quem = f"Recebe: {lista_finais(quem)}."
        lead = (f'<p>O Bolsa Família de <strong>{nome_mes}</strong> é pago entre '
                f'<strong>{data_longa(ini)}</strong> e <strong>{data_longa(fim)}</strong>, de acordo com o '
                f'último número do NIS do responsável familiar. Nesta página você encontra a data de '
                f'cada final, o calendário do ano inteiro, as cidades que recebem tudo no primeiro dia, '
                f'quanto o programa paga em 2026 e as notícias mais recentes, atualizadas todos os dias.</p>')
    else:
        nome_mes = ""
        titulo = "Bolsa Família: calendário de pagamento, valor e últimas notícias"
        descricao = "Calendário do Bolsa Família por final do NIS, valores e as notícias mais recentes do programa."
        fallback_data = "Calendário do próximo ano ainda não saiu"
        fallback_quem = "Assim que o governo divulgar, o portal atualiza esta página."
        lead = ('<p>O calendário do Bolsa Família do próximo ano ainda não foi divulgado. Assim que sair, '
                'esta página traz a data de cada final do NIS.</p>')

    blocos_mes = []
    if k:
        chaves = list(folhas)
        i = chaves.index(k)
        blocos_mes.append(bloco_mes(k, folhas[k], dados, hoje, True))
        if i + 1 < len(chaves):
            k2 = chaves[i + 1]
            blocos_mes.append(bloco_mes(k2, folhas[k2], dados, hoje, False))

    unificados = []
    for chave in sorted(dados["unificado"], reverse=True):
        if k and chave <= k:
            unificados.append(bloco_unificado(chave, dados["unificado"][chave]))
        if len(unificados) == 1:
            break

    anos = sorted({f["ano"] for f in folhas.values()})
    ano = anos[-1]
    especiais = [MESES[f["mes"] - 1] for f in folhas.values() if f["ano"] == ano and f["especial"]]
    nota_especial = ""
    if especiais:
        nota_especial = (f'<p class="bf-nota">* Em {", ".join(especiais[:-1])} e {especiais[-1]}, a tabela já mostra '
                         f'o calendário especial do El Niño (finais 3 a 0 juntos no terceiro dia). As '
                         f'demais datas são as do cartaz oficial do MDS.</p>' if len(especiais) > 1 else
                         f'<p class="bf-nota">* Em {especiais[0]}, a tabela já mostra o calendário especial.</p>')

    noticias = noticias_bf()
    lis = "".join(
        f'<li><a href="noticias/{s}.html"><img src="img/{s}.png" alt="" loading="lazy" width="112" height="63">'
        f'<span>{e(t)}<small>{data_extenso_curto(d(pub))}</small></span></a></li>'
        for pub, s, t in noticias)

    atualizado = data_extenso_curto(d(dados["atualizado_em"]))
    titulo_share = quote(titulo)

    faq = [
        ("Onde vejo o final do meu NIS?",
         "É o último algarismo do Número de Identificação Social do responsável familiar, impresso no "
         "cartão do Bolsa Família e no aplicativo do programa. É esse número, e não o do CPF, que define "
         "o dia do pagamento."),
        ("Por que o calendário mudou no fim de 2026?",
         "Por causa do El Niño. A Portaria MDS nº 1.221, de 16 de outubro de 2026, concentrou os pagamentos "
         "de outubro, novembro e dezembro em três dias: final 1 no primeiro, final 2 no segundo e os demais "
         "no terceiro. O governo disse que a ideia é deixar o dinheiro mais cedo com as famílias diante do "
         "risco de seca e de enchente."),
        ("O que é pagamento unificado?",
         "É quando todas as famílias de uma cidade recebem no primeiro dia do calendário, sem seguir o final "
         "do NIS. Acontece em municípios com emergência ou calamidade pública reconhecida pelo governo "
         "federal, e a lista muda todo mês."),
        ("Quanto o Bolsa Família paga em 2026?",
         f"Desde {v['vigencia']}, nenhuma família recebe menos de R$ {v['piso']}. A conta parte de "
         f"R$ {v['por_pessoa']} por pessoa, e entram por cima R$ {v['primeira_infancia']} por criança de "
         f"0 a 6 anos e R$ {v['variavel']} por criança ou adolescente de 7 a 17 anos, gestante ou mãe que "
         f"amamenta. Tem direito a família com renda de até R$ {v['renda_limite']} por pessoa."),
        ("O dinheiro não caiu na data. E agora?",
         "Primeiro, confira se a sua cidade não está no pagamento unificado e se a data é mesmo a do seu "
         "final. Se a data passou e nada apareceu, pode haver bloqueio por cadastro desatualizado ou revisão. "
         "Não pague ninguém para destravar: procure um profissional de sua confiança para olhar o caso."),
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
        "about": {"@type": "GovernmentService", "name": "Programa Bolsa Família",
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
            {"@type": "ListItem", "position": 2, "name": "Bolsa Família", "item": URL}]},
    }

    fontes = [
        (dados["calendario"][str(ano)]["fonte"], f"MDS: cartaz oficial do calendário do Bolsa Família de {ano}"),
        ("https://www.gov.br/mds/pt-br/noticias/pagamentos-de-outubro-do-bolsa-familia-comecam-nesta-segunda-feira-19-10-1",
         "MDS: calendário especial de outubro a dezembro (Portaria nº 1.221/2026)"),
        ("https://radiogov.ebc.com.br/programas/e-noticia/bolsa-familia-de-novembro-comeca-a-ser-pago-na-proxima-segunda-feira-16",
         "Rádio Gov (EBC): pagamento de novembro e as 112 cidades com pagamento unificado"),
        ("https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2023/lei/l14601.htm",
         "Lei nº 14.601/2023 (regras do Programa Bolsa Família)"),
        ("https://www.gov.br/mds/pt-br/acoes-e-programas/bolsa-familia", "MDS: página oficial do Bolsa Família"),
    ]
    fontes_html = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a></li>' for u, t in fontes)

    corpo = f"""
    <article class="artigo">
      <p class="bf-trilha"><a href="/">Início</a> › Bolsa Família</p>
      <div><span class="chip">Bolsa Família</span></div>
      <h1>{e(titulo)}</h1>
      <div class="meta"><img src="img/junior-avatar.png" alt="Júnior Arrais" class="autor-foto"> Por <a href="sobre.html#autor" class="autor-link">Júnior Arrais</a> &middot; Atualizado em {atualizado}</div>

      <section class="bf-proximo" aria-live="polite">
        <span class="bf-proximo-rotulo">Próximo pagamento</span>
        <span class="bf-proximo-data" id="bf-proximo-data">{e(fallback_data)}</span>
        <span class="bf-proximo-quem" id="bf-proximo-quem">{e(fallback_quem)}</span>
        <div class="bf-seletor">
          <span class="bf-seletor-rotulo">Toque no último número do seu NIS:</span>
          <div class="bf-botoes" role="group" aria-label="Final do NIS">
            {"".join(f'<button type="button" data-final="{f}" aria-pressed="false">{f}</button>' for f in FINAIS)}
          </div>
          <p class="bf-resposta" id="bf-resposta"></p>
        </div>
      </section>

      <div class="artigo-conteudo">
{lead}
{blocos_mes[0] if blocos_mes else ""}
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
{"".join(blocos_mes[1:])}
{"".join(unificados)}
<h2 id="valores">Quanto o Bolsa Família paga em 2026</h2>
<p>Os valores foram reajustados em 15,04% e valem desde {v['vigencia']}, pelo {e(v['norma'])}. O benefício soma uma parte por pessoa da casa com adicionais para crianças, gestantes e mães que amamentam:</p>
<ul class="bf-valores">
<li><strong>R$ {v['piso']}</strong>valor mínimo por família</li>
<li><strong>R$ {v['por_pessoa']}</strong>por pessoa da família</li>
<li><strong>R$ {v['primeira_infancia']}</strong>a mais por criança de 0 a 6 anos</li>
<li><strong>R$ {v['variavel']}</strong>a mais por criança de 7 a 17 anos, gestante ou nutriz</li>
</ul>
<p>Para entrar no programa, a renda da família dividida por todos os moradores tem de ficar em até <strong>R$ {v['renda_limite']} por pessoa</strong>. Para saber o valor da sua casa, use a <a href="calculadora-bolsa-familia.html">calculadora do Bolsa Família</a>. As regras completas, como a regra de proteção para quem arruma emprego, estão no <a href="noticias/guia-bolsa-familia-quem-tem-direito-valores-e-regras.html">guia do Bolsa Família</a>.</p>
<h2 id="calendario-{ano}">Calendário completo do Bolsa Família de {ano}</h2>
<p>Cada coluna é um final do NIS e cada número é o dia do pagamento naquele mês. Os pagamentos acontecem sempre nos últimos dez dias úteis, por isso o começo muda de mês para mês, e dezembro é adiantado por causa das festas.</p>
{tabela_ano(ano, folhas)}
{nota_especial}
      <!-- ADSENSE: espaço de anúncio -->
      <div class="ad-slot"><!-- Cole aqui o bloco de anúncio do AdSense --></div>
<h2 id="noticias">Últimas notícias do Bolsa Família</h2>
<ul class="bf-noticias">{lis}</ul>
<p><a href="noticias.html?cat=Bolsa%20Fam%C3%ADlia">Ver todas as notícias do Bolsa Família</a></p>
<h2 id="outros">Outros benefícios</h2>
<div class="bf-outros">
<a href="noticias/guia-cadunico-o-que-e-quem-pode-e-quando-atualizar.html">CadÚnico<small>quem pode entrar e quando atualizar</small></a>
<a href="noticias/guia-bpc-loas-quem-tem-direito-renda-e-avaliacao.html">BPC/LOAS<small>renda, avaliação e o que faz parar</small></a>
<a href="noticias/guia-gas-do-povo-como-funciona-quem-recebe-e-prazos.html">Gás do Povo<small>quem recebe e de quanto em quanto tempo</small></a>
<a href="noticias/guia-pe-de-meia-regras-valores-e-calendario.html">Pé-de-Meia<small>quanto o estudante recebe e quando</small></a>
</div>
<h2 id="perguntas">Perguntas frequentes</h2>
{faq_html}<h2>Cuidado com golpe</h2>
<p>Mudança de calendário é prato cheio para golpista. Nestas semanas circulam mensagens oferecendo "antecipar a parcela", "liberar o 13º do Bolsa Família" ou "confirmar o novo dia de pagamento" por um link, sempre pedindo dados do cartão, senha ou um Pix de "taxa". O calendário especial é automático e ninguém precisa se cadastrar para receber na data nova.</p>
<p>Nenhum órgão do governo cobra taxa nem pede Pix, senha ou foto do cartão para pagar o benefício. Se o valor vier menor, sumir ou ficar bloqueado, não entregue dinheiro a quem promete resolver: procure um profissional de sua confiança para analisar a situação da família.</p>
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
          <p class="autor-box-links"><a href="mailto:contato@portaljuniorarrais.com.br?subject=Correcao: bolsa-familia">Encontrou um erro? Avise a redação</a></p>
        </div>
      </div>
      <!-- FIM AUTOR -->

      <div class="share-bar">
        <span class="share-titulo">Compartilhe o calendário com quem recebe:</span>
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
  <meta property="og:image" content="https://portaljuniorarrais.com.br/img/guia-bolsa-familia-quem-tem-direito-valores-e-regras.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="favicon.png">
  <link rel="stylesheet" href="{css_v}">
  <script type="application/ld+json">{json.dumps(page_ld, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>
{m_head.group(1).rstrip()}
{CSS}</head>
<body>"""

    pagina = (head + m_topo.group(1) + "<main>\n" + corpo + "  </main>" + m_rodape.group(1)
              + site_js + "\n" + JS.replace("__DADOS__", dados_js(folhas, dados)) + "</body>\n</html>\n")
    return pagina


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
