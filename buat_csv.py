"""Membuat ulang dataset_250_makanan.csv dari dataset.py (termasuk makanan hasil penelusuran web di dataset_web.json):  python buat_csv.py"""
import csv, os
import dataset as ds
kolom = ["nama", "kategori", "porsi", "kilokalori", "protein_gram", "karbohidrat_gram", "lemak_gram", "serat_gram", "indeks_glikemik",
         "natrium", "purin", "kolesterol", "lambung", "jenis", "alergen", "kenyang", "kata_kunci_gambar", "harga_rp", "alasan_sehat",
         "saran_memakan", "sumber"]
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset_250_makanan.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(kolom)
    for x in ds.DATASET:
        w.writerow([x["nama"], x["kat"], x["porsi"], float(x["kkal"]), float(x["protein"]), float(x["karbo"]), float(x["lemak"]), float(x["serat"]),
                    x["ig"], x["na"], x["pu"], x["ko"], x["la"], x["je"], ",".join(x["al"]) or "-", x["kenyang"], x["en"], x["harga"] or "",
                    x["alasan"], x["saran"], x.get("sumber", "dataset proyek; harga acuan web Oktober 2026")])
print("ditulis", len(ds.DATASET), "baris")
