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
