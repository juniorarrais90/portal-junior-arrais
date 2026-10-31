"""Vigia da viagem (31/10 a 09/11/2026).

Confere, três vezes por dia, se a gaveta está saindo certa e avisa no Telegram:
- matérias agendadas que já passaram da hora: publicadas na agenda, no ar no site e na home;
- posts do Instagram e do Facebook que já passaram da hora: publicados na fila;
- Caça ao Tesouro: a planilha entrega a letra do dia e a pista do dia aponta para a matéria certa.

A letra NUNCA é impressa nem enviada (o log do Actions é público): só se confere que veio.
Problema = alerta na hora. Na rodada da noite (--resumo) manda também o "tudo certo".

Variáveis de ambiente: TG_TOKEN e TG_CHAT_ID.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SITE = "https://portaljuniorarrais.com.br"
API = ("https://script.google.com/macros/s/AKfycbwxWiEy6dAJQBRXofMBediN2tup-US_Tuz1EcigZzMiKbWvhG5VZ_0p_zJxwy0MOpVv7A/exec")
INICIO_VIAGEM = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
FIM_VIAGEM = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
INICIO_CACA = datetime(2026, 10, 31, 15, 0, tzinfo=timezone.utc)  # 31/10 12h em Brasília
FOLGA = timedelta(minutes=40)  # o robô roda a cada ~15 min; passou disso, atrasou
BRT = timezone(timedelta(hours=-3))
PISTAS = [
    "bolsa-familia-novembro-2026-pagamento-comeca-dia-16",
    "bpc-loas-regras-2026-renda-e-revisao",
    "prova-de-vida-do-inss-o-que-conta-sozinho-e-quando-bloqueia",
    "aposentadoria-por-idade-a-idade-e-o-tempo-minimo-que-valem-hoje",
    "cadunico-quando-e-obrigatorio-atualizar-o-cadastro",
    "aposentadoria-por-incapacidade-e-auxilio-doenca-qual-e-a-diferenca",
    "bolsa-familia-regra-de-protecao-agora-e-de-18-meses",
    "acumulo-de-beneficios-o-que-da-para-receber-junto",
    "tempo-de-contribuicao-por-que-conferir-o-historico-do-inss",
]


def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "vigia-portal", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.status, r.read().decode("utf-8", "replace")


def quando(iso):
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def vencidos(caminho, agora):
    itens = json.load(open(caminho, encoding="utf-8"))
    itens = itens["agenda"] if "agenda" in itens else itens["fila"]
    return [i for i in itens if INICIO_VIAGEM <= quando(i["publicar_em"]) <= agora - FOLGA]


def conferir(agora):
    problemas, ok = [], {}

    # 1. Matérias do site
    materias = vencidos("agendadas/agenda.json", agora)
    _, home = baixar(f"{SITE}/?v={int(agora.timestamp())}")
    for m in materias:
        nome = f"{m['horario_brasilia']} {m['titulo'][:60]}"
        if m.get("status") != "publicado":
            problemas.append(f"Matéria não publicada ({m.get('status')}): {nome}")
            continue
        try:
            st, _ = baixar(f"{SITE}/noticias/{m['slug']}.html")
            if st != 200:
                problemas.append(f"Matéria fora do ar (HTTP {st}): {nome}")
        except Exception as e:
            problemas.append(f"Matéria fora do ar ({e}): {nome}")
        if m in materias[-3:] and m["slug"] not in home:  # a home só mostra as mais recentes
            problemas.append(f"Matéria não apareceu na home: {nome}")
    ok["matérias no site"] = len(materias)

    # 2. Instagram e Facebook
    for rede, caminho in (("Instagram", "instagram/fila.json"), ("Facebook", "facebook/fila.json")):
        posts = vencidos(caminho, agora)
        for p in posts:
            if p.get("status") != "publicado":
                problemas.append(f"{rede} não postou ({p.get('status')}): {p['horario_brasilia']} {p['titulo'][:60]}")
        ok[f"posts no {rede}"] = len(posts)

    # 3. Caça ao Tesouro
    dia = (agora - INICIO_CACA) // timedelta(days=1) + 1
    if 1 <= dia <= len(PISTAS):
        try:
            _, txt = baixar(f"{API}?dia={dia}")
            r = json.loads(txt)
            if not (r.get("ok") and str(r.get("mensagem", "")).strip()):
                problemas.append(f"A planilha NÃO entregou a letra nº {dia} (respondeu ok={r.get('ok')}).")
        except Exception as e:
            problemas.append(f"A planilha da letra nº {dia} não respondeu: {e}")
        try:
            _, pagina = baixar(f"{SITE}/noticias/{PISTAS[dia - 1]}.html")
            if f'data-dia="{dia}"' not in pagina or "caca.js" not in pagina:
                problemas.append(f"A matéria da letra nº {dia} está sem o quadro da letra.")
        except Exception as e:
            problemas.append(f"A matéria da letra nº {dia} não abriu: {e}")
        ok["letra do dia"] = f"nº {dia} entregue pela planilha"
    return problemas, ok


def telegram(txt):
    token, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT_ID")
    if not token or not chat:
        print("Telegram não configurado (TG_TOKEN/TG_CHAT_ID). Aviso não enviado.")
        return
    dados = urllib.parse.urlencode({"chat_id": chat, "text": txt, "disable_web_page_preview": "true"}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=dados), timeout=30)
    except Exception as e:
        print(f"Não consegui avisar no Telegram: {e}")


def main():
    agora = datetime.now(timezone.utc)
    if not INICIO_VIAGEM <= agora <= FIM_VIAGEM:
        print("Fora do período da viagem. Nada a conferir.")
        return 0
    try:
        problemas, ok = conferir(agora)
    except Exception as e:
        problemas, ok = [f"O vigia não conseguiu conferir: {e}"], {}
    hora = agora.astimezone(BRT).strftime("%d/%m %H:%M")
    if problemas:
        telegram(f"⚠️ Vigia do portal ({hora}): {len(problemas)} problema(s)\n\n" +
                 "\n".join(f"• {p}" for p in problemas[:15]))
    elif "--resumo" in sys.argv:
        telegram(f"✅ Vigia do portal ({hora}): tudo certo.\n\n" +
                 "\n".join(f"• {k}: {v}" for k, v in ok.items()))
    print("\n".join(problemas) or "Tudo certo.", ok)
    return 0


if __name__ == "__main__":
    sys.exit(main())
