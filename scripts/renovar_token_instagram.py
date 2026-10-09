#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
renovar_token_instagram.py — Portal Júnior Arrais

Renova o token de longa duração do Instagram (IG_TOKEN) antes que ele vença.

INCIDENTE DE 08/10/2026: o token gerado em 09/08 venceu sozinho depois de 60
dias. Três publicações falharam ("Session has expired", código 190) e a fila
ficou pausada até o Júnior gerar um token novo à mão no painel da Meta.
Token VENCIDO não pode ser renovado — só substituído manualmente. Por isso esta
renovação roda toda semana: cada renovação devolve mais 60 dias de validade.

Regras da Meta (API do Instagram com login do Instagram):
  - GET graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token
  - o token precisa ter pelo menos 24 h e ainda estar válido;
  - a resposta traz access_token e expires_in (segundos).

O token novo é gravado no arquivo indicado em --saida (nunca impresso). O
workflow decide se precisa regravar o segredo IG_TOKEN no GitHub.

Saídas gravadas no GITHUB_OUTPUT: mudou=sim|nao e dias=<validade>. O token
novo é mascarado no log com ::add-mask:: antes de qualquer outra coisa.
Em erro, avisa no Telegram e sai com código 1.

Variáveis de ambiente: IG_TOKEN, TG_TOKEN e TG_CHAT_ID.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

URL = "https://graph.instagram.com/refresh_access_token"


def telegram(texto):
    token, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT_ID")
    if not token or not chat:
        print("Telegram não configurado. Aviso não enviado.", file=sys.stderr)
        return
    dados = urllib.parse.urlencode({"chat_id": chat, "text": texto}).encode()
    try:
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage", dados, timeout=20)
    except Exception as e:  # o aviso é acessório; o erro já sai no log
        print(f"Falha ao avisar no Telegram: {e}", file=sys.stderr)


def falhar(motivo):
    print(f"::error::{motivo}", file=sys.stderr)
    telegram("⚠️ Não consegui renovar o token do Instagram do portal.\n\n"
             f"{motivo}\n\n"
             "Se nada for feito, o robô para de postar quando o token vencer. "
             "Gerar token novo em developers.facebook.com → app Portal Junior "
             "Arrais → Casos de uso → Personalizar → Configuração da API com "
             "login do Instagram → Gerar token, e colar no segredo IG_TOKEN.")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", required=True, help="arquivo onde gravar o token novo")
    args = ap.parse_args()

    atual = os.environ.get("IG_TOKEN", "").strip()
    if not atual:
        falhar("Segredo IG_TOKEN vazio.")

    qs = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": atual})
    try:
        with urllib.request.urlopen(f"{URL}?{qs}", timeout=30) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", "replace")
        falhar(f"A Meta recusou a renovação (HTTP {e.code}): {corpo[:400]}")
    except Exception as e:
        falhar(f"Erro de rede ao renovar: {e}")

    novo = (resp.get("access_token") or "").strip()
    if not novo:
        falhar(f"Resposta sem access_token: {json.dumps(resp)[:400]}")

    print(f"::add-mask::{novo}")
    with open(args.saida, "w", encoding="utf-8") as f:
        f.write(novo)

    dias = int(resp.get("expires_in", 0)) // 86400
    saidas = os.environ.get("GITHUB_OUTPUT")
    if saidas:
        with open(saidas, "a", encoding="utf-8") as f:
            f.write(f"mudou={'sim' if novo != atual else 'nao'}\n")
            f.write(f"dias={dias}\n")
    print(f"Token renovado. Validade: {dias} dias. Mudou: {novo != atual}.")


if __name__ == "__main__":
    main()
