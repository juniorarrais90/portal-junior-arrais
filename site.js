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
  (navigator.clipboard ? navigator.clipboard.writeText(d.url) : Promise.reject()).then(function(){
    var o = btn.textContent; btn.textContent = 'Link copiado!';
    setTimeout(function(){ btn.textContent = o; }, 2000);
  }).catch(function(){ prompt('Copie o link:', d.url); });
}
function pjaStories(btn){
  var d = pjaDadosNoticia();
  // tenta a arte 9:16 (img/stories/slug.png); se não existir, usa a capa
  var slug = d.url.split('/').pop().replace('.html','');
  var candidata = d.img.replace('/img/' + slug + '.png', '/img/stories/' + slug + '.png');
  function compartilharImagem(url, fallback){
    fetch(url).then(function(r){ if(!r.ok) throw 0; return r.blob(); }).then(function(b){
      var f = new File([b], slug + '.png', {type:'image/png'});
      if (navigator.canShare && navigator.canShare({files:[f]})) {
        return navigator.share({files:[f], title:d.titulo, text:d.titulo + '\n' + d.url});
      }
      throw 0;
    }).catch(function(){
      if (fallback) return compartilharImagem(fallback, null);
      if (navigator.share) { navigator.share({title:d.titulo, text:d.titulo, url:d.url}); }
      else { pjaCopiarLink(btn); }
    });
  }
  compartilharImagem(candidata, d.img);
}
