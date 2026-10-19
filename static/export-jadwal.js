(function () {
  const status = document.getElementById('export-status');
  const buttons = document.querySelectorAll('[data-export]');
  if (!buttons.length) return;
  const txt = (el, selector) => (el.querySelector(selector)?.innerText || '').trim().replace(/\s+/g, ' ');
  function getRows() {
    const rows = [['Waktu', 'Waktu makan', 'Nama menu', 'Porsi / keterangan', 'Kalori (kkal)', 'Protein (g)', 'Karbohidrat (g)', 'Lemak (g)', 'Serat (g)', 'Harga (Rp)']];
    document.querySelectorAll('.slot').forEach(slot => {
      const time = slot.dataset.waktu || txt(slot, '.waktu');
      const meal = slot.dataset.judul || txt(slot, 'h3');
      slot.querySelectorAll('.menu').forEach(menu => {
        const detail = txt(menu, '.rinci');
        const name = txt(menu, '.rinci > .fw-bold');
        const portion = txt(menu, '.rinci .small');
        const matches = [...detail.matchAll(/(Kalori|Protein|Karbohidrat|Lemak|Serat)\s*:\s*([\d.,]+)/gi)];
        const nums = {};
        matches.forEach(m => nums[m[1].toLowerCase()] = m[2].replace(',', '.'));
        const priceMatch = detail.match(/Harga\s*:\s*Rp\s*([\d.,]+)/i);
        rows.push([time, meal, name, portion, nums.kalori || '', nums.protein || '', nums.karbohidrat || '', nums.lemak || '', nums.serat || '', priceMatch ? priceMatch[1].replace(/\./g, '') : '']);
      });
    });
    const total = document.querySelector('.total');
    if (total) rows.push([], ['Ringkasan', txt(total, '.fw-bold'), ...[...total.querySelectorAll(':scope > div')].slice(1).map(x => x.innerText.trim())]);
    return rows;
  }
  function download(blob, name) {
    const url = URL.createObjectURL(blob); const a = document.createElement('a');
    a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1200);
  }
  function csvText(rows, separator = ',') {
    return '\ufeff' + rows.map(row => row.map(v => {
      const s = String(v ?? ''); return '"' + s.replace(/"/g, '""') + '"';
    }).join(separator)).join('\r\n');
  }
  async function xlsx(rows) {
    if (!window.XLSX) {
      status.textContent = 'Memuat dukungan Excel…';
      await new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js';
        script.onload = resolve; script.onerror = reject; document.head.appendChild(script);
      });
    }
    if (!window.XLSX) throw new Error('Pustaka Excel tidak tersedia');
    const book = XLSX.utils.book_new();
    const sheet = XLSX.utils.aoa_to_sheet(rows);
    sheet['!cols'] = [{wch:18},{wch:18},{wch:32},{wch:28},{wch:14},{wch:14},{wch:16},{wch:12},{wch:12},{wch:14}];
    XLSX.utils.book_append_sheet(book, sheet, 'Jadwal Makan');
    XLSX.writeFile(book, 'jadwal-diet-sehat.xlsx');
  }
  buttons.forEach(button => button.addEventListener('click', async () => {
    const type = button.dataset.export; const rows = getRows();
    try {
      if (type === 'pdf') { status.textContent = 'Pilih “Simpan sebagai PDF” pada dialog cetak browser.'; window.print(); }
      else if (type === 'csv') { download(new Blob([csvText(rows)], {type:'text/csv;charset=utf-8;'}), 'jadwal-diet-sehat.csv'); status.textContent = 'File CSV berhasil disiapkan.'; }
      else if (type === 'json') { download(new Blob([JSON.stringify({judul:'Jadwal Diet Sehat', dibuat:new Date().toISOString(), data:rows.slice(1).filter(r => r.length)}, null, 2)], {type:'application/json;charset=utf-8;'}), 'jadwal-diet-sehat.json'); status.textContent = 'File JSON berhasil disiapkan.'; }
      else if (type === 'xlsx') { await xlsx(rows); status.textContent = 'File Excel berhasil disiapkan.'; }
    } catch (err) {
      if (type === 'xlsx') {
        download(new Blob([csvText(rows, ';')], {type:'text/csv;charset=utf-8;'}), 'jadwal-diet-sehat-excel.csv');
        status.textContent = 'Pustaka Excel tidak dapat dimuat. File CSV kompatibel dengan Excel sudah diunduh.';
      } else status.textContent = 'Ekspor gagal. Coba lagi atau gunakan opsi CSV.';
    }
  }));
})();
