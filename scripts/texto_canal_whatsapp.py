"""Prepara o texto pronto para colar no Canal do WhatsApp do portal.

O WhatsApp não tem API para postar em Canal, então o envio é manual:
este script só lista as matérias novas e monta a mensagem de cada uma.

Uso:  python scripts/texto_canal_whatsapp.py             (mostra as pendentes, mais antiga primeiro)
      python scripts/texto_canal_whatsapp.py --marcar    (marca as mostradas como já postadas)
      python scripts/texto_canal_whatsapp.py --semear    (marca tudo que existe como já postado)

Estado em data/canal-whatsapp-enviados.json. Só considera matéria sem noindex
e publicada nos últimos 3 dias.
"""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from avisar_push import RAIZ, materias  # noqa: E402

ESTADO = RAIZ / "data" / "canal-whatsapp-enviados.json"
DIAS = 3


def carregar():
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return {"enviados": []}


def salvar(est):
    ESTADO.parent.mkdir(exist_ok=True)
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


def mensagem(m):
    resumo = m["texto"].strip()
    if len(resumo) > 220:
        resumo = resumo[:217].rsplit(" ", 1)[0] + "..."
    return "📰 *%s*\n\n%s\n\n👉 Leia completo: %s" % (m["titulo"], resumo, m["url"])


def main():
    est = carregar()
    feitos = set(est["enviados"])
    todas = list(materias())
    if "--semear" in sys.argv:
        est["enviados"] = sorted(feitos | {m["arquivo"] for m in todas})
        salvar(est)
        print("Marcadas como postadas: %d" % len(est["enviados"]))
        return
    limite = (dt.date.today() - dt.timedelta(days=DIAS)).isoformat()
    novas = [m for m in todas
             if m["arquivo"] not in feitos and m["data"] and m["data"] >= limite]
    novas.sort(key=lambda m: m["data"])
    if not novas:
        print("Nenhuma matéria nova para o canal.")
        return
    for i, m in enumerate(novas, 1):
        print("=" * 60)
        print("%d/%d  (%s)  imagem: %s" % (i, len(novas), m["data"], m["imagem"]))
        print("-" * 60)
        print(mensagem(m))
    if "--marcar" in sys.argv:
        est["enviados"] = sorted(feitos | {m["arquivo"] for m in novas})
        salvar(est)
        print("\nMarcadas como postadas: %d" % len(novas))


if __name__ == "__main__":
    main()
