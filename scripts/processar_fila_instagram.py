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
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILA = os.path.join(RAIZ, "instagram", "fila.json")
LEGENDAS = os.path.join(RAIZ, "instagram", "legendas")
INTERVALO_MIN = 60  # minutos mínimos entre duas publicações


def agora():
    return datetime.now(timezone.utc)


def ler(iso):
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def main():
    if not os.path.exists(FILA):
        print("Sem fila. Nada a fazer.")
        return 0

    dados = json.load(open(FILA, encoding="utf-8"))
    fila = dados.get("fila", [])

    # respeita o intervalo mínimo desde a última publicação
    publicados = [f for f in fila if f.get("status") == "publicado" and f.get("publicado_em")]
    if publicados:
        ultimo = max(ler(f["publicado_em"]) for f in publicados)
        faltam = (ultimo + timedelta(minutes=INTERVALO_MIN)) - agora()
        if faltam.total_seconds() > 0:
            print(f"Intervalo mínimo não cumprido. Faltam {int(faltam.total_seconds()/60)} min.")
            return 0

    vencidos = [f for f in fila
                if f.get("status") == "pendente" and ler(f["publicar_em"]) <= agora()]
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
