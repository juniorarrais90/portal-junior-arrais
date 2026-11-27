"""Manda para o WhatsApp pessoal do Júnior a matéria nova do portal, pronta para
encaminhar ao Canal do WhatsApp (arte do feed + texto com título, resumo e link).

Criado em 27/11/2026. Roda pelo workflow .github/workflows/avisar-whatsapp.yml.

Regras (mesmas do aviso por push):
- matéria sem noindex, publicada nos últimos 3 dias e que ainda não foi enviada;
- 1 matéria por rodada (a mais antiga pendente), até 3 por dia;
- entre 22h e 7h (Brasília) não manda nada; fica para a próxima rodada da manhã;
- só marca como enviada se a Lero confirmar; falha não consome a vez.

Precisa de (segredos do GitHub; eu nunca vejo os valores):
- LERO_CLIENTES_API_TOKEN: token do workspace Clientes da Lero (QR, sem a janela de
  24h do WhatsApp oficial);
- JUNIOR_WHATSAPP: celular do Júnior com DDD (só dígitos, com ou sem 55).
Sem os dois, o script só mostra o que mandaria.

Uso:  python scripts/avisar_whatsapp_junior.py            (manda de verdade)
      python scripts/avisar_whatsapp_junior.py --teste    (mostra, sem mandar)
      python scripts/avisar_whatsapp_junior.py --semear   (marca tudo que existe como já enviado)
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from avisar_push import RAIZ, materias  # noqa: E402

API = "https://api.lero.pro/functions/v1/api-whatsapp-handler/v1/whatsapp/send-message"
ESTADO = RAIZ / "data" / "whatsapp-junior-enviados.json"
LIMITE_DIA = 3
DIAS = 3
BRT = dt.timezone(dt.timedelta(hours=-3))


def carregar():
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return {"enviados": [], "por_dia": {}}


def salvar(est):
    ESTADO.parent.mkdir(exist_ok=True)
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


def mensagem(m):
    resumo = m["texto"].strip()
    if len(resumo) > 220:
        resumo = resumo[:217].rsplit(" ", 1)[0] + "..."
    return "📰 *%s*\n\n%s\n\n👉 Leia completo: %s" % (m["titulo"], resumo, m["url"])


def arte(m):
    """Arte do feed (4:5) se existir no site; senão a capa da matéria (og:image)."""
    slug = m["arquivo"].removesuffix(".html")
    url = "https://portaljuniorarrais.com.br/img/feed45/%s.png" % slug
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=15)
        return url
    except Exception:  # noqa: BLE001
        return m["imagem"]


def telefone():
    d = re.sub(r"\D", "", os.environ.get("JUNIOR_WHATSAPP", ""))
    if d and not d.startswith("55"):
        d = "55" + d
    return d


def _post(token, corpo):
    req = urllib.request.Request(
        API, data=json.dumps(corpo).encode(), method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            resp = json.loads(r.read() or b"{}")
            return resp.get("success") is not False, str(resp)[:200]
    except urllib.error.HTTPError as e:
        return False, "HTTP %s %s" % (e.code, e.read()[:200])
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def enviar(token, fone, m):
    """Manda a arte e, logo depois, o texto em mensagem à parte.

    A legenda junto da imagem não chegou no teste de 27/11/2026 (veio só a imagem),
    então o texto vai separado. Devolve (imagem_ok, texto_ok, detalhe).
    """
    ok_img, det_img = _post(token, {"phone": fone, "media_url": arte(m), "media_type": "image"})
    if not ok_img:
        return False, False, "imagem: " + det_img
    ok_txt, det_txt = _post(token, {"phone": fone, "text": mensagem(m)})
    return True, ok_txt, "imagem: %s | texto: %s" % (det_img, det_txt)


def main():
    est = carregar()
    feitos = set(est["enviados"])
    todas = list(materias())
    if "--semear" in sys.argv:
        est["enviados"] = sorted(feitos | {m["arquivo"] for m in todas})
        salvar(est)
        print("Marcadas como enviadas: %d" % len(est["enviados"]))
        return
    agora = dt.datetime.now(BRT)
    hoje = agora.date().isoformat()
    limite = (agora.date() - dt.timedelta(days=DIAS)).isoformat()
    novas = sorted((m for m in todas if m["arquivo"] not in feitos and m["data"] and m["data"] >= limite),
                   key=lambda m: m["data"])
    if not novas:
        print("Nenhuma matéria nova.")
        return
    m = novas[0]
    token = os.environ.get("LERO_CLIENTES_API_TOKEN", "")
    fone = telefone()
    if "--teste" in sys.argv or not token or not fone:
        print("(sem envio) mandaria %d matéria(s); a próxima:\n%s\nArte: %s" % (len(novas), mensagem(m), arte(m)))
        return
    if not (7 <= agora.hour < 22):
        print("Fora do horário (22h–7h); fica para a manhã.")
        return
    if est["por_dia"].get(hoje, 0) >= LIMITE_DIA:
        print("Limite de %d por dia atingido." % LIMITE_DIA)
        return
    ok_img, ok_txt, detalhe = enviar(token, fone, m)
    print("Lero: imagem %s, texto %s | %s" % ("OK" if ok_img else "FALHOU", "OK" if ok_txt else "FALHOU", detalhe))
    if not ok_img:
        sys.exit(1)
    # A imagem já saiu: marca como enviada para não repetir a arte; se o texto falhou, o log mostra.
    est["enviados"] = sorted(feitos | {m["arquivo"]})
    est["por_dia"] = {hoje: est["por_dia"].get(hoje, 0) + 1}
    salvar(est)
    if not ok_txt:
        sys.exit(1)


if __name__ == "__main__":
    main()
