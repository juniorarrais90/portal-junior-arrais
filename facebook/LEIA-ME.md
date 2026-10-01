# Facebook — legendas, fila e robô de publicação

- `legendas/<slug>.txt`: legenda do post da página no Facebook. Mesmo texto do Instagram, com o **link clicável da matéria** no lugar do "link nos stories" e no máximo 3 hashtags.
- `fila.json`: fila no mesmo formato da do Instagram (`publicar_em` em UTC, `status` `pendente`), com `arte` apontando para a 4:5 (`img/feed45/<slug>.png`, 1080x1350 — formato vertical recomendado pela Meta para o feed do Facebook) e `link` da matéria. Cada item fica 15 minutos depois do post correspondente do Instagram.

## O robô

O workflow **Publicar no Facebook** (`.github/workflows/publicar-facebook.yml`) roda nos minutos 6, 21, 36 e 51 de cada hora e chama `scripts/processar_fila_facebook.py`, que:

1. publica **no máximo um** item vencido por execução, sempre o mais antigo, com `scripts/publicar_facebook.py` (Graph API, `POST /{FB_PAGE_ID}/photos` com a arte 4:5 e a legenda daqui);
2. respeita 60 minutos entre posts. Se a fila atrasar mais de 45 minutos, o intervalo cai para 20 minutos até ela se normalizar. Com mais de 120 minutos de atraso, avisa no Telegram;
3. no sucesso, grava `status: "publicado"`, `publicado_em` (UTC) e `link_post` (o post na página). O campo `link` continua sendo o da matéria;
4. grava a fila de volta em `main` com o commit `Facebook: marca item como publicado [skip ci]`.

Antes de publicar, o script confere se a arte está no ar (espera até 10 minutos pelo GitHub Pages), se é imagem, se tem até 8 MB e se mede 1080x1350. Na legenda, confere se não está vazia, se cabe no limite do Facebook, se traz o link da matéria e se não tem os termos proibidos ("grátis", "de graça", "gratuit…", "garantid…", "WhatsApp", "direct"). Se algo falhar, **nada é publicado**.

## Status de um item

| status | significado |
|---|---|
| `pendente` | aguardando o horário; é o único status que o robô publica |
| `publicado` | publicado pelo robô (`publicado_em`, `link_post`) |
| `publicado_manual` | postado à mão pelo Júnior; o robô nunca toca e não conta para o intervalo |
| `expirado` | passou de **24 horas** de atraso e o robô **não** publicou, para não postar matéria velha de uma vez (por exemplo, ao ligar o robô ou depois de uma pane longa). O motivo fica em `motivo` e o aviso chega no Telegram. Para publicar mesmo assim, volte para `pendente` com um `publicar_em` novo |

## Secrets (GitHub → Settings → Secrets and variables → Actions)

- `FB_PAGE_ID`: ID da Página do portal.
- `FB_PAGE_TOKEN`: token **da página** (não o de usuário), com `pages_manage_posts`, `pages_read_engagement` e `pages_show_list`.
- `TG_TOKEN` e `TG_CHAT_ID`: os mesmos do robô do Instagram. Os avisos do Facebook começam com "Facebook:".

O `IG_TOKEN` do Instagram **não serve** para a Página: são produtos diferentes da Meta. Token nenhum é gravado em arquivo ou impresso no log; nas mensagens ele aparece como `***`.

## Pausar e retomar

- **Pausar:** acrescente no topo de `fila.json`, ao lado de `"fila"`:
  `"pausado": true, "pausa_motivo": "por que pausei"`. O robô para, encerra sem erro e imprime o motivo.
- **Pausa automática:** na 3ª falha seguida no mesmo item, ou na hora se a Meta bloquear a página por spam (código 368), o próprio robô grava `pausado` e avisa no Telegram.
- **Retomar:** apague as chaves `pausado` e `pausa_motivo`. Se o item que falhou ficou com `falhas`/`ultima_falha`, pode apagar também.

## Diagnóstico

- **Página e permissões:** com as variáveis definidas, rode
  `python scripts/publicar_facebook.py --checar-pagina`. O comando mostra o nome da página, o tipo do token (precisa ser `PAGE`), se ele vence e se as três permissões estão concedidas. Não publica nada.
- **Teste sem publicar:** `python scripts/publicar_facebook.py --slug <slug> --legenda facebook/legendas/<slug>.txt --dry-run`. Valida a arte e a legenda, não precisa de token e não publica.
- **Logs:** GitHub → Actions → Publicar no Facebook → abra a execução → passo "Processar a fila". Os erros conhecidos vêm com uma linha "O que fazer:":
  - 190: token vencido ou inválido. Gere um token novo da página;
  - 200 ou 10: falta permissão no app (`pages_manage_posts`);
  - 368: página bloqueada por spam. A fila pausa sozinha;
  - 4, 17 ou 32: limite de chamadas. O robô tenta de novo sozinho;
  - 324 ou 9004: a Meta não conseguiu baixar a arte. O robô tenta de novo após 30, 60, 120 e 180 s.
- **Disparo manual:** Actions → Publicar no Facebook → Run workflow. Um serviço externo também pode disparar com `repository_dispatch` do tipo `publicar-facebook`.
