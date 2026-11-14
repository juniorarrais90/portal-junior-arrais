"""Manda notificação no navegador (OneSignal) quando entra matéria nova no portal.

Criado em 14/11/2026. Roda pelo workflow .github/workflows/avisar-push.yml.

Como funciona:
- olha todas as matérias de noticias/ que NÃO têm noindex;
- o que não estiver em data/push-enviados.json é novidade;
- avisa no máximo 1 matéria por rodada (a mais nova) e no máximo LIMITE_DIA por dia,
  para não encher o celular do leitor; as outras ficam marcadas como "pulada";
- entre 22h e 7h (Brasília) a notificação é agendada para as 7h30.

Precisa de:
- ONESIGNAL_APP_ID: lido do site.js (é público);
- ONESIGNAL_REST_KEY: segredo do repositório no GitHub (nunca no código).
Sem os dois, o script só atualiza a lista e não manda nada.

Uso:  python scripts/avisar_push.py            (manda de verdade)
      python scripts/avisar_push.py --semear   (marca tudo que existe como já enviado)
      python scripts/avisar_push.py --teste    (mostra o que mandaria, sem mandar)
"""
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESTADO = RAIZ / "data" / "push-enviados.json"
LIMITE_DIA = 4
BRT = dt.timezone(dt.timedelta(hours=-3))


def meta(texto, prop):
    m = re.search(r'<meta property="%s" content="([^"]*)"' % re.escape(prop), texto)
    return html.unescape(m.group(1)).strip() if m else ""


def materias():
    for f in sorted((RAIZ / "noticias").glob("*.html")):
        t = f.read_text(encoding="utf-8", errors="ignore")
        if re.search(r'<meta name="robots" content="[^"]*noindex', t):
            continue
        titulo = meta(t, "og:title")
        url = meta(t, "og:url")
        if not titulo or not url:
            continue
        dp = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})', t)
        yield {"arquivo": f.name, "titulo": titulo, "texto": meta(t, "og:description"),
               "imagem": meta(t, "og:image"), "url": url,
               "data": dp.group(1) if dp else ""}


def app_id():
    m = re.search(r"var ONESIGNAL_APP_ID = '([^']*)'", (RAIZ / "site.js").read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def enviar(aid, chave, m, quando):
    corpo = {
        "app_id": aid,
        "target_channel": "push",
        "included_segments": ["Total Subscriptions"],
        "headings": {"en": m["titulo"][:90], "pt": m["titulo"][:90]},
        "contents": {"en": (m["texto"] or "Toque para ler.")[:160], "pt": (m["texto"] or "Toque para ler.")[:160]},
        "web_url": m["url"] + "?utm_source=onesignal&utm_medium=push",
        "chrome_web_image": m["imagem"],
        "chrome_web_icon": "https://portaljuniorarrais.com.br/img/junior-avatar.png",
    }
    if quando:
        corpo["send_after"] = quando.isoformat()
    req = urllib.request.Request(
        "https://api.onesignal.com/notifications?c=push",
        data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json; charset=utf-8",
                 "Authorization": "Key " + chave},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode() or "{}")


def main():
    semear = "--semear" in sys.argv
    teste = "--teste" in sys.argv
    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {"enviados": {}}
    env = estado["enviados"]
    agora = dt.datetime.now(BRT)
    if "--hoje" in sys.argv:  # só para teste: --hoje AAAA-MM-DDTHH:MM
        agora = dt.datetime.fromisoformat(sys.argv[sys.argv.index("--hoje") + 1]).replace(tzinfo=BRT)
    hoje = agora.date().isoformat()

    novas = [m for m in materias() if m["arquivo"] not in env]
    if semear:
        for f in (RAIZ / "noticias").glob("*.html"):
            env.setdefault(f.name, "semente")
        ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("MUDOU")
        return
    if not novas:
        print("igual")
        return

    aid, chave = app_id(), os.environ.get("ONESIGNAL_REST_KEY", "")
    enviados_hoje = sum(1 for v in env.values() if isinstance(v, str) and v.startswith("push " + hoje))
    # matéria antiga que só agora perdeu o noindex não vira notificação
    corte = (agora.date() - dt.timedelta(days=3)).isoformat()
    for m in [m for m in novas if m["data"] < corte]:
        env[m["arquivo"]] = "antiga " + hoje
    novas = [m for m in novas if m["data"] >= corte]
    if not novas:
        if teste:
            print("só matérias antigas; nada a avisar")
            return
        ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("MUDOU")
        return
    novas.sort(key=lambda m: m["data"], reverse=True)
    escolhida, resto = novas[0], novas[1:]

    quando = None
    if agora.hour >= 22 or agora.hour < 7:
        alvo = agora if agora.hour < 7 else agora + dt.timedelta(days=1)
        quando = alvo.replace(hour=7, minute=30, second=0, microsecond=0)

    if not aid or not chave:
        print("OneSignal ainda não configurado: só registro, sem enviar.")
        marca = "sem-config " + hoje
        for m in novas:
            env[m["arquivo"]] = marca
    elif enviados_hoje >= LIMITE_DIA:
        print(f"Limite de {LIMITE_DIA} avisos hoje atingido; {len(novas)} matéria(s) puladas.")
        for m in novas:
            env[m["arquivo"]] = "pulada " + hoje
    else:
        print("Avisando:", escolhida["titulo"], "| agendado para" if quando else "| agora", quando or "")
        if teste:
            print(json.dumps(escolhida, ensure_ascii=False, indent=1))
            return
        r = enviar(aid, chave, escolhida, quando)
        print("Resposta:", json.dumps(r, ensure_ascii=False)[:300])
        env[escolhida["arquivo"]] = "push " + hoje + " " + str(r.get("id", ""))
        for m in resto:
            env[m["arquivo"]] = "pulada " + hoje
    if teste:
        return
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("MUDOU")


if __name__ == "__main__":
    main()
