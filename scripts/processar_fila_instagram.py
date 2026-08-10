#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
processar_fila_instagram.py — Portal Júnior Arrais

Lê instagram/fila.json, publica o PRIMEIRO item pendente cujo horário já venceu
e marca como publicado. Feito para rodar sozinho pelo GitHub Actions.

Regras de segurança embutidas:
  - publica no máximo UM item por execução, mesmo que vários tenham vencido.
    Assim uma falha de agendamento não vira enxurrada de posts;
  - respeita o intervalo mínimo entre publicações (INTERVALO_MIN);
  - se o item já estiver publicado, nunca republica;
  - sem itens vencidos, encerra em silêncio e não altera nada.

Variáveis de ambiente: IG_TOKEN e IG_USER_ID.
Saída: código 0 sempre que não houver erro real, para não poluir o painel do
Actions com falha quando simplesmente não há nada a publicar.
"""

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILA = os.path.join(RAIZ, "instagram", "fila.json")
LEGENDAS = os.path.join(RAIZ, "instagram", "legendas")
INTERVALO_MIN = 60           # minutos mínimos entre duas publicações
ATRASO_GRAVE = 45            # atraso a partir do qual se assume falha do agendador
INTERVALO_RECUPERACAO = 20   # intervalo usado para drenar a fila atrasada
ATRASO_CRITICO = 120         # atraso a partir do qual avisa no Telegram


def agora():
    return datetime.now(timezone.utc)


def ler(iso):
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def alertar_travamento(vencidos, atraso):
    """Avisa no Telegram que a fila travou, para não descobrir só no dia seguinte."""
    token = os.environ.get("TG_TOKEN")
    chat = os.environ.get("TG_CHAT_ID")
    if not token or not chat:
        return
    nomes = "\n".join(f"• {f.get('titulo', f['slug'])}" for f in vencidos[:5])
    txt = (f"⚠️ A fila do Instagram está atrasada em {int(atraso)} minutos.\n\n"
           f"{len(vencidos)} post(s) esperando:\n{nomes}\n\n"
           f"O agendador do GitHub pode ter falhado. Dá para destravar entrando em "
           f"Actions e clicando em Run workflow.")
    dados = urllib.parse.urlencode(
        {"chat_id": chat, "text": txt, "disable_web_page_preview": "true"}).encode()
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage", data=dados),
            timeout=30)
        print("Alerta de travamento enviado no Telegram.")
    except Exception as e:
        print(f"Não consegui alertar no Telegram: {e}")


def main():
    if not os.path.exists(FILA):
        print("Sem fila. Nada a fazer.")
        return 0

    dados = json.load(open(FILA, encoding="utf-8"))
    fila = dados.get("fila", [])

    vencidos = [f for f in fila
                if f.get("status") == "pendente" and ler(f["publicar_em"]) <= agora()]

    # MODO RECUPERAÇÃO: se o item mais antigo está atrasado além de ATRASO_GRAVE,
    # o agendador falhou (foi o que houve em 09/08/2026, com o cron parando por
    # horas). Nesse caso o intervalo mínimo cai, para a fila drenar mais rápido
    # em vez de arrastar o atraso por mais um dia.
    atraso = 0
    if vencidos:
        mais_antigo = min(ler(f["publicar_em"]) for f in vencidos)
        atraso = (agora() - mais_antigo).total_seconds() / 60
    intervalo = INTERVALO_RECUPERACAO if atraso > ATRASO_GRAVE else INTERVALO_MIN
    if atraso > ATRASO_GRAVE:
        print(f"Modo recuperação: atraso de {int(atraso)} min. "
              f"Intervalo reduzido para {intervalo} min.")

    # respeita o intervalo mínimo desde a última publicação
    publicados = [f for f in fila if f.get("status") == "publicado" and f.get("publicado_em")]
    if publicados:
        ultimo = max(ler(f["publicado_em"]) for f in publicados)
        faltam = (ultimo + timedelta(minutes=intervalo)) - agora()
        if faltam.total_seconds() > 0:
            print(f"Intervalo mínimo não cumprido. Faltam {int(faltam.total_seconds()/60)} min.")
            if atraso > ATRASO_CRITICO:
                alertar_travamento(vencidos, atraso)
            return 0

    if not vencidos:
        pend = [f for f in fila if f.get("status") == "pendente"]
        print(f"Nada vencido. {len(pend)} item(ns) pendente(s).")
        if pend:
            prox = min(pend, key=lambda f: ler(f["publicar_em"]))
            print(f"Próximo: {prox['slug']} em {prox.get('horario_brasilia')}")
        return 0

    item = min(vencidos, key=lambda f: ler(f["publicar_em"]))
    print(f"Publicando: {item['slug']} (agendado para {item.get('horario_brasilia')})")

    legenda = os.path.join(LEGENDAS, f"{item['slug']}.txt")
    if not os.path.exists(legenda):
        print(f"ERRO: legenda não encontrada: {legenda}")
        return 1

    cmd = [sys.executable, os.path.join(RAIZ, "scripts", "publicar_instagram.py"),
           "--slug", item["slug"], "--legenda", legenda]
    if item.get("alt_text"):
        cmd += ["--alt-text", item["alt_text"]]

    r = subprocess.run(cmd, capture_output=True, text=True)
    saida = r.stdout + r.stderr
    tok = os.environ.get("IG_TOKEN", "")
    if tok:
        saida = saida.replace(tok, "***")
    print(saida)

    if r.returncode != 0:
        print("Falhou. O item continua pendente e será tentado na próxima rodada.")
        return 1

    link = ""
    for linha in saida.splitlines():
        if "link:" in linha:
            link = linha.split("link:")[-1].strip()

    item["status"] = "publicado"
    item["publicado_em"] = agora().strftime("%Y-%m-%dT%H:%M:%SZ")
    if link:
        item["link"] = link
    json.dump(dados, open(FILA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"OK. Marcado como publicado. {link}")

    # aviso no Telegram com a arte de story. Falha aqui NÃO invalida a publicação:
    # o post já saiu, e o aviso é só o lembrete do story manual.
    try:
        sys.path.insert(0, os.path.join(RAIZ, "scripts"))
        from avisar_telegram import avisar
        avisar(item["slug"], item.get("titulo", item["slug"]), link)
    except Exception as e:
        print(f"Aviso do Telegram falhou (post já publicado, sem prejuízo): {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
