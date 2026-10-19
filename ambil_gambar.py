"""Unduh semua foto makanan sekarang (opsional; aplikasi juga mengunduhnya sendiri di latar belakang).
Pemakaian:  python ambil_gambar.py            -> unduh yang belum ada
            python ambil_gambar.py apel       -> ambil ulang satu makanan (hapus foto lama dulu)
Jika ada yang gagal atau fotonya kurang tepat: letakkan foto Anda sendiri sebagai static/gambar/<slug>.jpg,
atau isi gambar_manual.json, mis. {"apel": "https://alamat-foto.jpg"}."""
import os, sys, logging
import dataset as ds
from gambar import Pengambil  # gambar.py ikut memuat .env

logging.basicConfig(level=logging.INFO, format="%(message)s")
folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "gambar")
p = Pengambil(folder, ds.BY_SLUG, os.path.join(os.path.dirname(os.path.abspath(__file__)), "gambar_manual.json"))
daftar = [ds.slug(a) for a in sys.argv[1:]] or list(ds.BY_SLUG)
for s in daftar:
    if sys.argv[1:] and p.jalur(s): os.remove(p.jalur(s))
gagal = []
for i, s in enumerate(daftar, 1):
    ada = p.jalur(s) or p.ambil(s)
    print(f"[{i}/{len(daftar)}] {ds.BY_SLUG[s]['nama']}: {'ok' if ada else 'GAGAL'}")
    if not ada: gagal.append(s)
print(f"\nSelesai. Berhasil {len(daftar) - len(gagal)}, gagal {len(gagal)}." + (f"\nGagal: {', '.join(gagal)}" if gagal else ""))
