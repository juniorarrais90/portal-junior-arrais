# Facebook — legendas e fila

- `legendas/<slug>.txt`: legenda do post da página no Facebook. Mesmo texto do Instagram, com o **link clicável da matéria** no lugar do "link nos stories" e no máximo 3 hashtags.
- `fila.json`: fila no mesmo formato da do Instagram (`publicar_em` em UTC, `status` `pendente`), com `arte` apontando para a 4:5 (`img/feed45/<slug>.png`, 1080x1350 — formato vertical recomendado pela Meta para o feed do Facebook) e `link` da matéria. Ainda **não há robô** lendo esta fila: os posts são feitos à mão na página, com a arte 4:5 e a legenda daqui. Quando houver robô, ele marca `publicado` como o do Instagram.
