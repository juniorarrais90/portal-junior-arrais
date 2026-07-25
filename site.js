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
  try {
    if (localStorage.getItem('pja-cookies') === 'ok') return;
  } catch(e) { return; }
  var bar = document.createElement('div');
  bar.className = 'cookie-bar';
  bar.innerHTML = '<p>Usamos cookies para melhorar sua experiência e exibir conteúdo e anúncios personalizados. Ao continuar navegando, você concorda com a nossa <a href="' + (location.pathname.indexOf('/noticias/')>-1 ? '../' : '') + 'politica-de-privacidade.html">Política de Privacidade</a>.</p><button type="button">Aceitar e fechar</button>';
  bar.querySelector('button').addEventListener('click', function(){
    try { localStorage.setItem('pja-cookies','ok'); } catch(e){}
    bar.remove();
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
