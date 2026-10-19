# Diet Sehat — versi pembaruan

## Isi
- `app.py`: aplikasi web Flask.
- `dataset.py`, `knowledge.py`: dataset inti, frame dan aturan.
- `dataset_makanan_249.csv`: ekspor dataset inti untuk ditinjau.
- `templates/`, `static/`: antarmuka dan CSS custom.
- `Dokumentasi_Proyek_Diet_Sehat_Terbaru.docx` dan `.pdf`: dokumentasi terbaru.
- `Presentasi_Diet_Sehat_Terbaru.pptx`: presentasi 12 slide.

## Menjalankan
1. Pasang Python 3.10+.
2. Buka terminal pada folder ini.
3. Buat environment opsional: `python -m venv .venv`
4. Aktifkan environment, lalu jalankan `pip install -r requirements.txt`.
5. Atur API key pada konfigurasi proyek jika fitur AI digunakan.
6. Jalankan `flask --app app run`, lalu buka alamat lokal yang tercetak.

## Catatan data
Dataset inti berisi 249 item setelah entri “Beras putih matang” dihapus karena duplikasi konseptual dengan “Nasi putih”. Harga adalah estimasi per porsi, bukan harga pasar real-time. Nilai gizi bersifat perkiraan dan sebaiknya diverifikasi dengan sumber komposisi pangan tepercaya.

## Perubahan utama
- Bootstrap dihapus dari tampilan; styling menggunakan CSS custom.
- Layout responsif untuk desktop, tablet, dan ponsel.
- Pilihan “Keseluruhan” putih saat belum dipilih.
- Navigasi pencarian diberi nama “Cari Menu”.
- Rincian gizi ditampilkan pada baris terpisah.
- Harga ekstrem per porsi dinormalisasi.
