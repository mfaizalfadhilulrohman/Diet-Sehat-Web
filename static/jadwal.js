// Foto makanan: foto di static/gambar langsung dipakai; hanya yang belum ada diambil server dari web di latar belakang. Browser menanyakan statusnya tiap 3 detik dan memasang foto
// begitu siap (tidak ada permintaan gambar yang menggantung, jadi menu lain tetap cepat dibuka).
(function () {
  const pending = {};
  document.querySelectorAll('.foto[data-slug]').forEach(el => { if (el.querySelector('.noimg')) (pending[el.dataset.slug] = pending[el.dataset.slug] || []).push(el); });
  let putaran = 0;
  async function cek() {
    const slugs = Object.keys(pending);
    if (!slugs.length || putaran++ > 60) return;
    try {
      const r = await fetch('/gambar-status?s=' + encodeURIComponent(slugs.join(',')));
      const d = await r.json();
      for (const s of slugs) {
        if (d[s] === 'ok') {
          pending[s].forEach(el => { const im = new Image(); const nm = el.parentElement.querySelector('.fw-bold'); im.alt = nm ? nm.textContent : ''; im.src = '/gambar/' + s; el.replaceChildren(im); });
          delete pending[s];
        } else if (d[s] === 'gagal') {
          pending[s].forEach(el => el.querySelector('.noimg').classList.remove('tunggu'));
          delete pending[s];
        }
      }
    } catch (e) { /* coba lagi pada putaran berikutnya */ }
    if (Object.keys(pending).length) setTimeout(cek, 3000);
  }
  if (Object.keys(pending).length) setTimeout(cek, 1500);
})();
