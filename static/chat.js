// Tanya jawab gizi: kirim pertanyaan ke server; jawaban dari dataset atau penelusuran web (teks biasa, tiap informasi satu baris).
const log = document.getElementById('log'), input = document.getElementById('i');
let hist = [], sibuk = false;

function gelembung(kelas, teks) {
  const d = document.createElement('div');
  d.className = 'bubble ' + kelas;
  d.style.whiteSpace = 'pre-wrap';
  if (teks) d.textContent = teks;
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
  return d;
}

async function kirim(teksUser) {
  if (sibuk) return;
  sibuk = true;
  hist.push({role: 'user', content: teksUser});
  gelembung('me', teksUser);
  const tunggu = gelembung('bot', 'Sedang menyiapkan jawaban...');
  try {
    const r = await fetch('/api/chat', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({pesan: hist.slice(-12)})});
    const d = await r.json();
    tunggu.textContent = d.teks || 'Tidak ada jawaban.';
    if (r.ok && d.teks) hist.push({role: 'assistant', content: d.teks}); else hist.pop();
  } catch (e) {
    tunggu.textContent = 'Koneksi gagal. Coba lagi.';
    hist.pop();
  }
  sibuk = false;
  log.scrollTop = log.scrollHeight;
}

document.getElementById('f').onsubmit = e => {
  e.preventDefault();
  const t = input.value.trim();
  if (!t) return;
  input.value = '';
  kirim(t);
};
document.querySelectorAll('.cepat').forEach(b => b.onclick = () => kirim(b.textContent));
