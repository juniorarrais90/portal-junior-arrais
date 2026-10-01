#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
processar_fila_facebook.py — Portal Júnior Arrais

Lê facebook/fila.json, publica o item pendente mais antigo cujo horário já
venceu e marca como publicado. Cópia da lógica de processar_fila_instagram.py,
adaptada à Página do Facebook. Feito para rodar sozinho pelo GitHub Actions.

Regras de segurança embutidas (as mesmas do Instagram, mais a de expiração):
  - publica no máximo UM item por execução, sempre o mais antigo;
  - respeita o intervalo mínimo entre publicações (INTERVALO_MIN), com modo
    recuperação quando a fila atrasa;
  - só publica item com status "pendente". "publicado", "publicado_manual"
    (postado à mão pelo Júnior) e "expirado" nunca são tocados, e
    "publicado_manual" não conta para o intervalo;
  - item pendente com mais de EXPIRA_HORAS de atraso NÃO é publicado: vira
    "expirado" e o robô avisa no Telegram. Isso evita que, ao ligar o robô ou
    depois de uma pane longa, ele poste de uma vez matérias velhas que o
    Júnior já publicou à mão;
  - respeita a chave "pausado": true no topo do arquivo;
  - falha de publicação avisa no Telegram e, na terceira seguida no mesmo item,
    pausa a fila sozinha. Bloqueio por spam da Meta (código 368) pausa na hora.

PÁGINA JÚNIOR ARRAIS ADVOGADO (segunda página, opcional):
  o mesmo post (arte e legenda) sai também na página do escritório, ADV_ATRASO
  minutos depois de sair no portal — post idêntico em duas páginas no mesmo
  minuto parece spam para a Meta. O andamento fica em item["advogado"]
  ({"status", "publicado_em", "link_post", ...}) e a pausa própria em
  "pausado_advogado": um problema numa página não para a outra. Sem os
  secrets FB_ADV_PAGE_ID/FB_ADV_PAGE_TOKEN, essa parte fica desligada.
  O perfil pessoal NÃO entra: a Meta não permite publicar em perfil por API.
  O aviso de sucesso do portal traz o link para compartilhar no perfil à mão.

Variáveis de ambiente: FB_PAGE_ID, FB_PAGE_TOKEN, FB_ADV_PAGE_ID,
FB_ADV_PAGE_TOKEN, TG_TOKEN e TG_CHAT_ID.
Saída: 0 quando não há nada a fazer ou deu certo; 1 só em erro real.
"""

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILA = os.path.join(RAIZ, "facebook", "fila.json")
LEGENDAS = os.path.join(RAIZ, "facebook", "legendas")
INTERVALO_MIN = 60           # minutos mínimos entre duas publicações
ATRASO_GRAVE = 45            # atraso a partir do qual se assume falha do agendador
INTERVALO_RECUPERACAO = 20   # intervalo usado para drenar a fila atrasada
ATRASO_CRITICO = 120         # atraso a partir do qual avisa no Telegram
EXPIRA_HORAS = 24            # atraso a partir do qual o item expira sem publicar
FALHAS_PARA_PAUSAR = 3       # falhas seguidas no mesmo item que congelam a fila
SAIDA_PAUSAR_FILA = 3        # código de saída do publicar_facebook.py no erro 368
FORMATO = "%Y-%m-%dT%H:%M:%SZ"
ADV_ATRASO = 10              # minutos depois do portal para sair na página do advogado
ADV_INTERVALO = 20           # minutos mínimos entre dois posts na página do advogado
FINAIS = ("publicado", "publicado_manual", "expirado")


def agora():
    return datetime.now(timezone.utc)


def ler(iso):
    return datetime.strptime(iso, FORMATO).replace(tzinfo=timezone.utc)


def mascarar(texto):
    for nome in ("FB_PAGE_TOKEN", "FB_ADV_PAGE_TOKEN", "TG_TOKEN"):
        tok = os.environ.get(nome, "")
        if tok:
            texto = texto.replace(tok, "***")
    return texto


def gravar(dados):
    with open(FILA, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def _telegram(txt):
    """Envia texto simples no Telegram. Nunca derruba o fluxo se falhar."""
    token = os.environ.get("TG_TOKEN")
    chat = os.environ.get("TG_CHAT_ID")
    if not token or not chat:
        print("Telegram não configurado (TG_TOKEN/TG_CHAT_ID). Aviso não enviado.")
        return False
    dados = urllib.parse.urlencode(
        {"chat_id": chat, "text": txt, "disable_web_page_preview": "true"}).encode()
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage", data=dados),
            timeout=30)
        return True
    except Exception as e:
        print(mascarar(f"Não consegui avisar no Telegram: {e}"))
        return False


def alertar_travamento(vencidos, atraso):
    """Avisa no Telegram que a fila travou, para não descobrir só no dia seguinte."""
    nomes = "\n".join(f"• {f.get('titulo', f['slug'])}" for f in vencidos[:5])
    txt = (f"Facebook: ⚠️ a fila está atrasada em {int(atraso)} minutos.\n\n"
           f"{len(vencidos)} post(s) esperando:\n{nomes}\n\n"
           f"O agendador do GitHub pode ter falhado. Dá para destravar entrando em "
           f"Actions → Publicar no Facebook → Run workflow.")
    if _telegram(txt):
        print("Alerta de travamento enviado no Telegram.")


def alertar_expirados(expirados):
    nomes = "\n".join(f"• {f.get('titulo', f['slug'])} ({f.get('horario_brasilia')})"
                      for f in expirados[:10])
    txt = (f"Facebook: ⏰ {len(expirados)} item(ns) passaram de {EXPIRA_HORAS} h de "
           f"atraso e NÃO foram publicados (status \"expirado\"):\n{nomes}\n\n"
           f"Se ainda quiser algum na página, poste à mão ou volte o status "
           f"para \"pendente\" com um horário novo em facebook/fila.json.")
    if _telegram(txt):
        print("Aviso de expiração enviado no Telegram.")


def alertar_falha(item, saida, falhas, pausou):
    """Avisa que a publicação falhou. Sem isso, só o e-mail do GitHub avisava."""
    motivo = ""
    linhas = saida.splitlines()
    for linha in linhas:
        if "O que fazer:" in linha:
            motivo = linha.strip()[:400]
            break
    if not motivo:
        for linha in linhas:
            if "error" in linha.lower() or "Erro da API" in linha or "ERRO" in linha:
                motivo = linha.strip()[:300]
                break
    txt = (f"Facebook: ❌ falha ao publicar (tentativa {falhas}).\n\n"
           f"{item.get('titulo', item['slug'])}\n\n"
           f"{motivo or 'Sem mensagem de erro legível — ver o log do Actions.'}")
    if pausou:
        txt += ("\n\nA fila foi PAUSADA sozinha para não insistir no erro. "
                "Depois de resolver, tirar \"pausado\" de facebook/fila.json.")
    else:
        txt += "\n\nO item continua pendente e será tentado de novo."
    if _telegram(mascarar(txt)):
        print("Aviso de falha enviado no Telegram.")


def arte_do_item(slug):
    """Arte com "LINK NA LEGENDA" (img/feedfb/) se já foi gerada; senão, a do Instagram."""
    fb = f"img/feedfb/{slug}.png"
    return fb if os.path.exists(os.path.join(RAIZ, fb)) else f"img/feed45/{slug}.png"


def executar_publicacao(slug, legenda, arte, env=None):
    """Chama o publicar_facebook.py. Devolve (código de saída, saída de texto).

    env troca as credenciais para publicar em outra página (a do advogado).
    Isolado numa função para os testes trocarem por um stub sem tocar na API.
    """
    cmd = [sys.executable, os.path.join(RAIZ, "scripts", "publicar_facebook.py"),
           "--slug", slug, "--legenda", legenda, "--arte", arte]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env={**os.environ, **(env or {})})
    return r.returncode, r.stdout + r.stderr


def ler_saida(saida):
    """Extrai o link do post e a arte usada da saída do publicar_facebook.py."""
    link = arte_usada = ""
    for linha in saida.splitlines():
        if "link:" in linha:
            link = linha.split("link:")[-1].strip()
        if "arte usada:" in linha:
            arte_usada = linha.split("arte usada:")[-1].strip()
    return link, arte_usada


def registrar_falha(dados, item, saida, pausar_ja=False):
    falhas = item.get("falhas", 0) + 1
    item["falhas"] = falhas
    item["ultima_falha"] = agora().strftime(FORMATO)
    pausou = pausar_ja or falhas >= FALHAS_PARA_PAUSAR
    if pausou:
        dados["pausado"] = True
        if pausar_ja:
            dados["pausa_motivo"] = (
                f"A Meta bloqueou a página por ação considerada spam (código 368) "
                f"ao publicar {item['slug']} ({item['ultima_falha']}). Esperar o "
                f"bloqueio passar e remover esta chave.")
            print("Bloqueio por spam (368). Fila PAUSADA.")
        else:
            dados["pausa_motivo"] = (
                f"{falhas} falhas seguidas em {item['slug']} "
                f"({item['ultima_falha']}). Resolver e remover esta chave.")
            print("Terceira falha seguida. Fila PAUSADA para não insistir no erro.")
    gravar(dados)
    alertar_falha(item, saida, falhas, pausou)
    print("Falhou. O item continua pendente.")
    return 1


def main():
    if not os.path.exists(FILA):
        print("Sem fila. Nada a fazer.")
        return 0

    dados = json.load(open(FILA, encoding="utf-8"))

    if dados.get("pausado"):
        print(f"Fila PAUSADA. Motivo: {dados.get('pausa_motivo', 'não informado')}")
        print("Para retomar, remover \"pausado\" de facebook/fila.json.")
        return 0

    print("== Página do portal ==")
    rc_portal = processar_portal(dados)
    print("\n== Página Júnior Arrais Advogado ==")
    rc_adv = processar_advogado(dados)
    return max(rc_portal, rc_adv)


def processar_portal(dados):
    fila = dados.get("fila", [])

    # EXPIRAÇÃO: pendente com mais de EXPIRA_HORAS de atraso não é publicado.
    limite = agora() - timedelta(hours=EXPIRA_HORAS)
    expirados = [f for f in fila
                 if f.get("status") == "pendente" and ler(f["publicar_em"]) < limite]
    if expirados:
        for f in expirados:
            horas = int((agora() - ler(f["publicar_em"])).total_seconds() / 3600)
            f["status"] = "expirado"
            f["expirado_em"] = agora().strftime(FORMATO)
            f["motivo"] = (f"{horas} h de atraso (limite de {EXPIRA_HORAS} h); "
                           f"não publicado para não postar matéria velha.")
            print(f"Expirado: {f['slug']} ({horas} h de atraso)")
        gravar(dados)
        alertar_expirados(expirados)

    vencidos = [f for f in fila
                if f.get("status") == "pendente" and ler(f["publicar_em"]) <= agora()]

    # MODO RECUPERAÇÃO: atraso acima de ATRASO_GRAVE indica falha do agendador.
    # O intervalo mínimo cai para a fila drenar mais rápido.
    atraso = 0
    if vencidos:
        mais_antigo = min(ler(f["publicar_em"]) for f in vencidos)
        atraso = (agora() - mais_antigo).total_seconds() / 60
    intervalo = INTERVALO_RECUPERACAO if atraso > ATRASO_GRAVE else INTERVALO_MIN
    if atraso > ATRASO_GRAVE:
        print(f"Modo recuperação: atraso de {int(atraso)} min. "
              f"Intervalo reduzido para {intervalo} min.")

    # intervalo mínimo desde a última publicação DO ROBÔ ("publicado_manual" não conta)
    publicados = [f for f in fila if f.get("status") == "publicado" and f.get("publicado_em")]
    if publicados and vencidos:
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
        # conta como falha: sem isso o robô repetiria o erro a cada execução
        # sem nunca pausar nem avisar.
        saida = f"ERRO: legenda não encontrada: facebook/legendas/{item['slug']}.txt"
        print(saida)
        return registrar_falha(dados, item, saida)

    rc, saida = executar_publicacao(item["slug"], legenda, arte_do_item(item["slug"]))
    saida = mascarar(saida)
    print(saida)

    if rc != 0:
        return registrar_falha(dados, item, saida, pausar_ja=(rc == SAIDA_PAUSAR_FILA))

    link, arte_usada = ler_saida(saida)

    # "link" continua sendo o endereço da matéria; o do post vai em "link_post".
    item["status"] = "publicado"
    item["publicado_em"] = agora().strftime(FORMATO)
    item.pop("falhas", None)
    item.pop("ultima_falha", None)
    if link:
        item["link_post"] = link
    if arte_usada:
        # registra qual arte saiu (a do Facebook ou, na falta dela, a do Instagram)
        item["arte"] = arte_usada.split("portaljuniorarrais.com.br/")[-1]
    gravar(dados)
    print(f"OK. Marcado como publicado. {link}")

    # Aviso de sucesso. Falha aqui NÃO invalida a publicação: o post já saiu.
    txt = (f"Facebook: ✅ post publicado na página.\n\n"
           f"{item.get('titulo', item['slug'])}\n\n"
           f"Post: {link or 'link não informado pela Meta'}\n"
           f"Matéria: {item.get('link', '')}")
    if link:
        txt += ("\n\n📤 Compartilhe no seu perfil: abra o link do post, toque em "
                "Compartilhar e escolha \"Compartilhar agora\" no seu perfil.")
    if _telegram(txt):
        print("Aviso de sucesso enviado no Telegram.")
    return 0


def falha_advogado(dados, item, saida, pausar_ja=False):
    """Igual a registrar_falha, mas só para a página do advogado."""
    adv = item.setdefault("advogado", {})
    falhas = adv.get("falhas", 0) + 1
    adv["falhas"] = falhas
    adv["ultima_falha"] = agora().strftime(FORMATO)
    pausou = pausar_ja or falhas >= FALHAS_PARA_PAUSAR
    if pausou:
        dados["pausado_advogado"] = True
        dados["pausa_motivo_advogado"] = (
            ("A Meta bloqueou a página do advogado por spam (código 368)"
             if pausar_ja else f"{falhas} falhas seguidas")
            + f" em {item['slug']} ({adv['ultima_falha']}). Resolver e remover esta chave.")
        print("Página do advogado PAUSADA. A página do portal segue normal.")
    gravar(dados)
    motivo = next((l.strip()[:400] for l in saida.splitlines() if "O que fazer:" in l), "") \
        or next((l.strip()[:300] for l in saida.splitlines()
                 if "Erro da API" in l or "ERRO" in l), "")
    txt = (f"Facebook (Júnior Arrais Advogado): ❌ falha ao publicar "
           f"(tentativa {falhas}).\n\n{item.get('titulo', item['slug'])}\n\n"
           f"{motivo or 'Sem mensagem de erro legível — ver o log do Actions.'}")
    txt += ("\n\nA página do advogado foi PAUSADA. Depois de resolver, tirar "
            "\"pausado_advogado\" de facebook/fila.json." if pausou
            else "\n\nSerá tentado de novo.")
    _telegram(mascarar(txt))
    return 1


def processar_advogado(dados):
    """Repete na página Júnior Arrais Advogado o que já saiu no portal."""
    pid = os.environ.get("FB_ADV_PAGE_ID")
    tok = os.environ.get("FB_ADV_PAGE_TOKEN")
    if not pid or not tok:
        print("Desligada (faltam os secrets FB_ADV_PAGE_ID e FB_ADV_PAGE_TOKEN).")
        return 0
    if dados.get("pausado_advogado"):
        print(f"PAUSADA. Motivo: {dados.get('pausa_motivo_advogado', 'não informado')}")
        return 0

    fila = dados.get("fila", [])
    candidatos = [f for f in fila if f.get("status") == "publicado" and f.get("publicado_em")
                  and f.get("advogado", {}).get("status") not in FINAIS]

    # post do portal com mais de EXPIRA_HORAS não é repetido no advogado
    limite = agora() - timedelta(hours=EXPIRA_HORAS)
    velhos = [f for f in candidatos if ler(f["publicado_em"]) < limite]
    for f in velhos:
        f.setdefault("advogado", {}).update(
            status="expirado", expirado_em=agora().strftime(FORMATO),
            motivo=f"publicado no portal há mais de {EXPIRA_HORAS} h")
        print(f"Expirado no advogado: {f['slug']}")
    if velhos:
        gravar(dados)

    prontos = [f for f in candidatos if f not in velhos
               and ler(f["publicado_em"]) + timedelta(minutes=ADV_ATRASO) <= agora()]
    if not prontos:
        print("Nada a repetir agora.")
        return 0

    feitos = [ler(f["advogado"]["publicado_em"]) for f in fila
              if f.get("advogado", {}).get("status") == "publicado"
              and f["advogado"].get("publicado_em")]
    if feitos:
        faltam = max(feitos) + timedelta(minutes=ADV_INTERVALO) - agora()
        if faltam.total_seconds() > 0:
            print(f"Intervalo mínimo não cumprido. Faltam {int(faltam.total_seconds()/60)} min.")
            return 0

    item = min(prontos, key=lambda f: ler(f["publicado_em"]))
    print(f"Publicando: {item['slug']} (saiu no portal em {item['publicado_em']})")
    legenda = os.path.join(LEGENDAS, f"{item['slug']}.txt")
    if not os.path.exists(legenda):
        saida = f"ERRO: legenda não encontrada: facebook/legendas/{item['slug']}.txt"
        print(saida)
        return falha_advogado(dados, item, saida)

    rc, saida = executar_publicacao(
        item["slug"], legenda, item.get("arte") or arte_do_item(item["slug"]),
        env={"FB_PAGE_ID": pid, "FB_PAGE_TOKEN": tok,
             "FB_NOME_SECRET": "FB_ADV_PAGE_TOKEN"})
    saida = mascarar(saida)
    print(saida)
    if rc != 0:
        return falha_advogado(dados, item, saida, pausar_ja=(rc == SAIDA_PAUSAR_FILA))

    link, _ = ler_saida(saida)
    item["advogado"] = {"status": "publicado",
                        "publicado_em": agora().strftime(FORMATO)}
    if link:
        item["advogado"]["link_post"] = link
    gravar(dados)
    print(f"OK. Publicado na página do advogado. {link}")
    txt = (f"Facebook (Júnior Arrais Advogado): ✅ post publicado.\n\n"
           f"{item.get('titulo', item['slug'])}\n\n"
           f"Post: {link or 'link não informado pela Meta'}")
    if _telegram(txt):
        print("Aviso de sucesso enviado no Telegram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
