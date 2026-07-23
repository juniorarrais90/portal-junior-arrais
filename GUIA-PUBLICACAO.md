# Guia de Publicação — Portal Júnior Arrais (v3)

Portal de notícias otimizado para o Google (SEO), com página do serviço de empréstimo e já preparado para o Google AdSense.

---

## Etapa 1 — Publicar no GitHub Pages (gratuito)

1. Crie uma conta em https://github.com (se ainda não tiver).
2. Clique em **New repository**. Nome: `canal-junior-arrais`. Marque **Public**. Clique em **Create repository**.
3. Clique em **uploading an existing file** e arraste TODOS os arquivos e pastas deste pacote (mantendo as pastas `data` e `noticias` com esses nomes).
4. Clique em **Commit changes**.
5. Vá em **Settings → Pages**. Em **Source**: `Deploy from a branch`; **Branch**: `main`, pasta `/ (root)`. Salve.
6. Em 1 a 2 minutos o site estará em `https://SEU_USUARIO.github.io/canal-junior-arrais/`.

---

## Etapa 2 — Domínio próprio (Registro.br, ~R$ 40/ano) — OBRIGATÓRIO para o AdSense

1. Domínio registrado: `portaljuniorarrais.com.br` (aprovado).
2. No painel do Registro.br, abra o domínio → **Editar zona DNS → Modo avançado** e crie:

   | Tipo  | Nome | Valor |
   |-------|------|-------|
   | A     | (raiz) | 185.199.108.153 |
   | A     | (raiz) | 185.199.109.153 |
   | A     | (raiz) | 185.199.110.153 |
   | A     | (raiz) | 185.199.111.153 |
   | CNAME | www  | SEU_USUARIO.github.io |

3. No GitHub: **Settings → Pages → Custom domain** → digite o domínio → salve. Depois da propagação (30 min a 24 h), marque **Enforce HTTPS**.
4. O domínio `portaljuniorarrais.com.br` já está configurado em todas as páginas, no sitemap e no robots.txt.

---

## Etapa 3 — Aparecer no Google (Search Console)

1. Acesse https://search.google.com/search-console e adicione a propriedade com o seu domínio.
2. Verifique a propriedade (o Registro.br tem integração direta com o Google — é o caminho mais fácil).
3. Em **Sitemaps**, envie: `https://portaljuniorarrais.com.br/sitemap.xml`.
4. Pronto: a cada notícia nova, o sitemap atualizado avisa o Google automaticamente.

**Dicas para rankear melhor:** publique com frequência (o ideal é todo dia), escreva títulos com as palavras que as pessoas pesquisam, use imagens próprias e mantenha as matérias com pelo menos 300 palavras.

---

## Etapa 4 — Google AdSense (ganhar com anúncios)

O site já está preparado: tem as páginas obrigatórias (Sobre, Contato, Política de Privacidade) e os espaços de anúncio marcados no código com `<!-- ADSENSE -->`.

1. **Antes de se inscrever**, tenha: domínio próprio configurado (Etapa 2) e pelo menos 15 a 30 notícias originais publicadas. Sites recém-criados e com pouco conteúdo são reprovados.
2. Acesse https://adsense.google.com e inscreva o site.
3. O AdSense fornece um código (script) para colar no `<head>` das páginas — me envie o código que eu insiro em todas.
4. Ele também pede um arquivo `ads.txt` na raiz do site com uma linha do tipo `google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0` — me envie seu código `pub-` que eu crio o arquivo.
5. A análise leva de alguns dias a algumas semanas. Aprovado, os anúncios começam a aparecer nos espaços reservados.

**Expectativa realista:** a receita depende do tráfego. Com poucas centenas de visitas/mês, os valores são simbólicos; o jogo muda a partir de milhares de visitas mensais — por isso o foco em SEO e na divulgação das notícias nas suas redes.

---

## Etapa 5 — Publicar notícias no dia a dia (comigo)

Cada notícia é uma página HTML própria na pasta `noticias/`, com URL amigável, meta tags e dados estruturados — o formato que o Google privilegia.

**Fluxo:** me mande o texto (ou o assunto) da notícia + imagem (link ou arquivo) + link do vídeo, se houver. Eu gero:
1. O arquivo da notícia (ex.: `noticias/titulo-da-noticia.html`);
2. O card novo para a página inicial (`index.html`);
3. A linha nova no `sitemap.xml`.

Você só faz o upload dos arquivos no GitHub (ou cola o conteúdo que eu te passo). O site atualiza em 1 a 2 minutos.

---

## Ajustes pendentes (me envie para eu completar)

1. **Vídeos reais** para a vitrine da página inicial (me mande os links de 3 vídeos do YouTube);
3. **Código do AdSense** (script e pub-ID) quando a conta for aprovada.

Já preenchidos: domínio nas páginas, botões de empréstimo apontando para juniorarrais.com (Novo Horizonte Promotora), redes sociais (YouTube, Instagram, TikTok, Kwai, Facebook e Threads) e e-mail de contato (juniorarrais90@gmail.com).
