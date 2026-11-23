#!/usr/bin/env python3
"""Gera as imagens da grade do Portal pela API do Gemini (sem ChatGPT nem Gemini manual).

Entrada: um JSON com {"regras": "<REGRAS GERAIS>", "imagens": {"1": "<cena 1>", "2": "<cena 2>", ...}}
Saída:   <saida>/NN.png em 3:4 (1792x2400), uma por número, na ordem.

Chave: arquivo com a chave da API (padrão ~/.pj/gemini). O Júnior guarda uma cópia em
"Meu Drive/Imagens - Portal Junior Arrais/gemini.txt". O custo sai dos créditos mensais do
Google Developer Program (plano Google AI PRO) aplicados na conta "My Billing Account".

Uso:
  python3 scripts/gerar_imagens_gemini.py --prompts ~/w/prompts.json --saida ~/w/master
  python3 scripts/gerar_imagens_gemini.py --prompts ... --saida ... --so 3,7   # refazer só algumas
Limite de segurança: no máximo --max imagens por execução (padrão 24).
"""
import argparse, base64, json, os, sys, time, urllib.request, urllib.error

MODELO_PADRAO = 'gemini-3.1-flash-image'
URL = 'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent'


def gerar(chave, modelo, texto, tentativas=3):
    corpo = json.dumps({
        'contents': [{'parts': [{'text': texto}]}],
        'generationConfig': {'responseModalities': ['IMAGE'],
                             'imageConfig': {'aspectRatio': '3:4', 'imageSize': '2K'}},
    }).encode()
    for t in range(tentativas):
        req = urllib.request.Request(URL.format(m=modelo), data=corpo, method='POST',
                                     headers={'x-goog-api-key': chave, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            for p in d['candidates'][0]['content']['parts']:
                if 'inlineData' in p:
                    return base64.b64decode(p['inlineData']['data'])
            raise RuntimeError('resposta sem imagem: ' + json.dumps(d)[:300])
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, KeyError) as e:
            msg = e.read().decode()[:300] if isinstance(e, urllib.error.HTTPError) else str(e)
            print(f'  tentativa {t + 1} falhou: {msg}', file=sys.stderr)
            time.sleep(5 * (t + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prompts', required=True)
    ap.add_argument('--saida', required=True)
    ap.add_argument('--chave', default=os.path.expanduser('~/.pj/gemini'))
    ap.add_argument('--modelo', default=MODELO_PADRAO)
    ap.add_argument('--so', default='', help='números separados por vírgula')
    ap.add_argument('--max', type=int, default=24)
    a = ap.parse_args()
    chave = open(a.chave).read().strip()
    p = json.load(open(a.prompts, encoding='utf-8'))
    regras = p.get('regras', '')
    nums = sorted(p['imagens'], key=int)
    if a.so:
        nums = [n for n in nums if n in a.so.split(',')]
    if len(nums) > a.max:
        sys.exit(f'{len(nums)} imagens passam do limite de {a.max}; use --max se for de propósito')
    os.makedirs(a.saida, exist_ok=True)
    falhas = []
    for n in nums:
        texto = f'{regras}\n\nIMAGEM {n}:\n{p["imagens"][n]}'
        print(f'IMAGEM {n}...', flush=True)
        img = gerar(chave, a.modelo, texto)
        if not img:
            falhas.append(n); continue
        open(os.path.join(a.saida, f'{int(n):02d}.png'), 'wb').write(img)
    print('ok' if not falhas else f'falharam: {",".join(falhas)}')


if __name__ == '__main__':
    main()
