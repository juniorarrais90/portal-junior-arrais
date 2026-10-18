#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conferir_conflito.py — Portal Júnior Arrais

Rodar ANTES de publicar uma pauta quente durante a semana (fora da grade do domingo).
Faz duas checagens:

1. TEMA: procura as palavras-chave nos títulos/slugs
   - das matérias JÁ PUBLICADAS (noticias.html) e
   - das matérias AGENDADAS que ainda vão sair (agendadas/agenda.json, status pendente).
   Se a pauta quente bate com uma agendada, NÃO publicar outra página sobre o mesmo
   assunto: ou se adianta/atualiza a agendada, ou se cancela a agendada
   (status "cancelado" no agenda.json + itens das filas + post do YouTube).

2. HORÁRIO: lista os horários já ocupados no Instagram e no Facebook no dia e sugere
   horários livres com pelo menos 60 minutos de distância de qualquer post
   (o robô do Instagram recusa intervalo menor).

Uso:
    python3 scripts/conferir_conflito.py "salario minimo" "piso" --dia 2026-10-14
"""
import argparse, json, os, re, unicodedata
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def norm(s):
    s = unicodedata.normalize('NFD', s.lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('palavras', nargs='+')
    ap.add_argument('--dia', default=(datetime.now(timezone.utc) - timedelta(hours=3)).strftime('%Y-%m-%d'),
                    help='dia (Brasília) em que a pauta quente vai sair')
    a = ap.parse_args()
    chaves = [norm(p) for p in a.palavras]

    print('== TEMA ==')
    arq = open(os.path.join(RAIZ, 'noticias.html'), encoding='utf-8').read()
    pub = re.findall(r'<a class="card"[^>]*href="noticias/([^"]+)\.html".*?<h3[^>]*>(.*?)</h3>.*?class="meta">([^<]*)<', arq, re.S)
    ag_p = os.path.join(RAIZ, 'agendadas', 'agenda.json')
    ag = json.load(open(ag_p, encoding='utf-8'))['agenda'] if os.path.exists(ag_p) else []
    achou = False
    for slug, tit, data in pub:
        alvo = norm(slug + ' ' + re.sub('<.*?>', '', tit))
        if any(c in alvo for c in chaves):
            print(f'  PUBLICADA  {data.strip():>20}  {slug}'); achou = True
    for i in ag:
        if i.get('status') != 'pendente':
            continue
        alvo = norm(i['slug'] + ' ' + i['titulo'])
        if any(c in alvo for c in chaves):
            print(f'  AGENDADA   {i["horario_brasilia"]:>20}  {i["slug"]}   <-- CONFLITO COM A GRADE'); achou = True
    if not achou:
        print('  nenhuma matéria publicada ou agendada com essas palavras')

    print(f'\n== HORÁRIOS em {a.dia} (Brasília) ==')
    dia = datetime.strptime(a.dia, '%Y-%m-%d')
    ocupados = []
    for rede in ('instagram', 'facebook'):
        fila = json.load(open(os.path.join(RAIZ, rede, 'fila.json'), encoding='utf-8'))['fila']
        for it in fila:
            t = datetime.strptime(it['publicar_em'], '%Y-%m-%dT%H:%M:%SZ') - timedelta(hours=3)
            if t.date() == dia.date():
                ocupados.append((t, rede, it['slug'][:50], it.get('status')))
    for t, rede, s, st in sorted(ocupados):
        print(f'  {t:%H:%M}  {rede:<9} {st:<10} {s}')
    ig = [t for t, r, _, _ in ocupados if r == 'instagram']
    livres = []
    t = dia.replace(hour=8)
    while t <= dia.replace(hour=21, minute=30):
        if all(abs((t - o).total_seconds()) >= 3600 for o in ig):
            livres.append(t.strftime('%H:%M'))
        t += timedelta(minutes=30)
    print('\n  Horários livres para o Instagram (Facebook 15 min depois):', ', '.join(livres) or 'nenhum')
    print('  Site: pode publicar a qualquer hora, mas evite 8h, 14h e 18h (horário do robô da grade).')


if __name__ == '__main__':
    main()
