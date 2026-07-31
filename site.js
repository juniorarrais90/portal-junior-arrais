/* ============================================
   Canal do Junior Arrais — lógica do site
   (usada apenas para a vitrine de vídeos)
   ============================================ */

const PLAY_SVG = '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';

async function iniciarVideos() {
  try {
    const resp = await fetch('data/videos.json');
    if (!resp.ok) return;
    const dados = await resp.json();

    const vg = document.getElementById('grid-videos');
    if (vg) {
      vg.innerHTML = dados.videos.map(v => `
        <a class="video-card" href="https://www.youtube.com/watch?v=${v.videoId}" target="_blank" rel="noopener">
          <div class="video-thumb">
            <img src="https://img.youtube.com/vi/${v.videoId}/hqdefault.jpg" alt="" loading="lazy">
            <div class="play-overlay"><div class="play-btn">${PLAY_SVG}</div></div>
          </div>
          <h3>${v.titulo}</h3>
        </a>`).join('');
    }

    document.querySelectorAll('[data-canal-url]').forEach(el => {
      el.href = dados.canalUrl;
    });
  } catch (e) {
    console.error(e);
  }
}

document.addEventListener('DOMContentLoaded', iniciarVideos);


/* ---------- Aviso de cookies (LGPD) ---------- */
(function(){
  var CHAVE = 'pja-cookies';

  function liberar(){
    if (typeof window.gtag !== 'function') return;
    window.gtag('consent', 'update', {
      'ad_storage': 'granted',
      'ad_user_data': 'granted',
      'ad_personalization': 'granted',
      'analytics_storage': 'granted'
    });
  }

  var escolha = null;
  try { escolha = localStorage.getItem(CHAVE); } catch(e) { return; }

  if (escolha === 'ok') { liberar(); return; }   // ja aceitou antes
  if (escolha === 'nao') return;                  // ja recusou antes

  var prefixo = location.pathname.indexOf('/noticias/') > -1 ? '../' : '';
  var bar = document.createElement('div');
  bar.className = 'cookie-bar';
  bar.innerHTML = '<p>Usamos cookies para medir quantas pessoas visitam o portal e melhorar o conteúdo. ' +
    'Você decide: nada é medido enquanto não autorizar. Veja a nossa ' +
    '<a href="' + prefixo + 'politica-de-privacidade.html">Política de Privacidade</a>.</p>' +
    '<div class="cookie-botoes">' +
    '<button type="button" class="cookie-recusar">Agora não</button>' +
    '<button type="button" class="cookie-aceitar">Aceitar</button>' +
    '</div>';

  function guardar(valor){
    try { localStorage.setItem(CHAVE, valor); } catch(e){}
    bar.remove();
  }

  bar.querySelector('.cookie-aceitar').addEventListener('click', function(){
    guardar('ok');
    liberar();
  });
  bar.querySelector('.cookie-recusar').addEventListener('click', function(){
    guardar('nao');
  });

  document.body.appendChild(bar);
})();

/* ---------- Busca e filtro por categoria (noticias.html) ---------- */
(function(){
  if (!/noticias\.html/.test(location.pathname)) return;
  var params = new URLSearchParams(location.search);
  var q = (params.get('q')||'').trim().toLowerCase();
  var cat = (params.get('cat')||'').trim().toLowerCase();
  if (!q && !cat) return;
  var titulo = document.querySelector('.section-head h2');
  if (titulo) titulo.textContent = q ? ('Resultados para: "' + (params.get('q')||'') + '"') : ('Notícias de ' + params.get('cat'));
  var alguma = false;
  document.querySelectorAll('.grid .card').forEach(function(card){
    var chip = (card.querySelector('.chip')||{}).textContent || '';
    var texto = card.textContent.toLowerCase();
    var ok = q ? texto.indexOf(q) > -1 : chip.trim().toLowerCase() === cat;
    if (!ok) card.style.display = 'none'; else alguma = true;
  });
  if (!alguma) {
    var g = document.querySelector('.grid');
    if (g) g.insertAdjacentHTML('beforebegin', '<p style="color:#5a6b7f; margin: 6px 0 18px">Nenhuma notícia encontrada. <a href="noticias.html">Ver todas</a>.</p>');
  }
})();

/* ===== Compartilhamento das matérias ===== */
function pjaDadosNoticia(){
  var t = (document.querySelector('meta[property="og:title"]')||{}).content || document.title;
  var u = (document.querySelector('link[rel="canonical"]')||{}).href || location.href;
  var img = (document.querySelector('meta[property="og:image"]')||{}).content || '';
  return {titulo:t, url:u, img:img};
}
function pjaCopiarLink(btn){
  var d = pjaDadosNoticia();
  var original = btn.getAttribute('data-rotulo') || btn.textContent;
  btn.setAttribute('data-rotulo', original);

  function feedback(txt){
    btn.textContent = txt;
    setTimeout(function(){ btn.textContent = original; }, 2200);
  }

  // Copia com textarea + execCommand('copy'). E SINCRONO: aproveita o gesto do
  // usuario, nao pede permissao, nao depende do foco da janela e funciona nas
  // WebViews do Instagram e do Facebook, de onde vem boa parte do trafego.
  //
  // NAO usar navigator.clipboard.writeText aqui. Ela e assincrona e, quando a
  // aba esta sem foco ou a permissao fica pendente, NAO rejeita: fica pendente
  // para sempre e CONGELA a pagina. Foi o que quebrou este botao antes.
  function copiar(){
    try {
      var ta = document.createElement('textarea');
      ta.value = d.url;
      ta.setAttribute('readonly', '');
      ta.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;opacity:0';
      document.body.appendChild(ta);
      ta.focus(); ta.select(); ta.setSelectionRange(0, ta.value.length); // iOS
      var deu = document.execCommand('copy');
      document.body.removeChild(ta);
      return deu;
    } catch(e){ return false; }
  }

  // Se nao copiar, mostra o link num campo ja selecionado, dentro da barra.
  // Nunca usar prompt() nem alert(): sao modais, travam a pagina e varios
  // navegadores de celular simplesmente ignoram.
  function mostrarCampo(){
    var barra = btn.closest('.share-bar') || btn.parentNode;
    var antigo = barra.querySelector('.share-link-manual');
    if (antigo) antigo.remove();
    var box = document.createElement('div');
    box.className = 'share-link-manual';
    box.style.cssText = 'width:100%;margin-top:10px;display:flex;gap:8px;align-items:center';
    var inp = document.createElement('input');
    inp.type = 'text'; inp.value = d.url; inp.readOnly = true;
    inp.style.cssText = 'flex:1;min-width:0;padding:9px 11px;border:1px solid #cbd6e2;' +
      'border-radius:8px;font-size:14px;color:#1E2A38;background:#fff';
    var dica = document.createElement('span');
    dica.textContent = 'Toque e segure para copiar';
    dica.style.cssText = 'font-size:12px;color:#5a6b7f;white-space:nowrap';
    box.appendChild(inp); box.appendChild(dica);
    barra.appendChild(box);
    inp.focus(); inp.select(); inp.setSelectionRange(0, inp.value.length);
    feedback('Copie o link abaixo');
  }

  if (copiar()) feedback('Link copiado!'); else mostrarCampo();
}

function pjaBaixarArte(btn){
  var d = pjaDadosNoticia();
  var slug = d.url.split('/').pop().replace('.html','');
  var arte = d.img.replace('/img/' + slug + '.png', '/img/stories/' + slug + '.png');
  function baixar(url, fallback){
    fetch(url).then(function(r){ if(!r.ok) throw 0; return r.blob(); }).then(function(b){
      var a = document.createElement('a');
      a.href = URL.createObjectURL(b);
      a.download = 'story-' + slug + '.png';
      document.body.appendChild(a); a.click(); a.remove();
    }).catch(function(){ if (fallback) baixar(fallback, null); });
  }
  baixar(arte, d.img);
}
/* modo arte: aparece só para quem abriu uma vez com ?arte=1 */
(function(){
  try {
    if (/[?&]arte=1/.test(location.search)) localStorage.setItem('pja-arte','1');
    if (localStorage.getItem('pja-arte') === '1') document.documentElement.classList.add('pja-admin');
  } catch(e){}
})();

function pjaFacebook(btn){
  var d = pjaDadosNoticia();
  var sharer = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(d.url);
  var ehCelular = /Android|iPhone|iPad/i.test(navigator.userAgent);
  if (!ehCelular) {
    window.open(sharer, '_blank', 'noopener,width=640,height=580');
    return;
  }
  // celular: abre o compositor DENTRO do app do Facebook (porta semioficial)
  var inicio = Date.now();
  try { location.href = 'fb://faceweb/f?href=' + encodeURIComponent(sharer); } catch(e){}
  setTimeout(function(){
    // se o app não abriu (página continua visível), plano B: folha do sistema
    if (!document.hidden && Date.now() - inicio < 2500) {
      if (navigator.share) { navigator.share({title:d.titulo, url:d.url}); }
      else { location.href = sharer; }
    }
  }, 1400);
}
