"""Tanya jawab gizi TANPA AI: jawaban dari dataset proyek; jika makanan belum ada, ditelusuri di web lalu disimpan ke dataset.

Alur untuk setiap pertanyaan:
  1. Pertanyaan umum yang bisa dijawab sistem (target kalori, cemilan sehat, tetap kenyang) dihitung dari profil dan dataset.
  2. Nama makanan dicari di dataset makanan inti + makanan hasil penelusuran sebelumnya.
  3. Jika belum ada: Open Food Facts (nilai gizi per 100 g) dan Wikipedia Indonesia (penjelasan) ditelusuri. Jika nilai gizi ketemu,
     makanan itu ditambahkan ke dataset (dataset_web.json) sehingga pertanyaan berikutnya langsung dijawab dari dataset.
  4. Jika tidak ketemu atau pertanyaannya bukan soal makanan: "Maaf, saya tidak bisa menjelaskan."
Semua permintaan web berbatas waktu 8 detik dan galatnya ditangkap, jadi aplikasi tidak pernah macet karena internet."""
import re, os, json, threading
import requests
import knowledge as kb
import dataset as ds

TIDAK_BISA = "Maaf, saya tidak bisa menjelaskan."
UA = {"User-Agent": "DietSehat/2.0 (aplikasi belajar diet)"}
BATAS = 8
BERKAS_CATATAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catatan_web.json")
_kunci = threading.Lock()

STOP = set("""berapa kalori kalorinya kandungan gizi gizinya nutrisi manfaat manfaatnya khasiat khasiatnya apa apakah saja dalam di dari itu boleh
sehat tidak ga gak nggak harga harganya kah ya dong tolong jelaskan jelasin tentang untuk diet satu 1 porsi per 100 gram g cara makan
bagaimana gimana kenapa mengapa yang ini mau ingin tahu info informasi bisa kira berapakah sih deh adalah punya ada makanan nilai
bagus baik aman cocok buat saya aku kamu minta lihat tampilkan sebutkan berikan dan atau""".split())
KATA_PANGAN = ("makanan", "hidangan", "buah", "sayur", "kuliner", "minuman", "bahan", "biji", "kacang", "tumbuhan", "ikan", "daging", "masakan",
               "olahan", "gizi", "kalori", "pangan", "camilan", "kudapan", "tanaman", "umbi", "rempah", "sup", "kue", "roti", "nasi", "telur", "susu")


def _bersih(q):
    return re.sub(r"[^\w\s\-]", " ", (q or "").lower()).strip()


def istilah(q):
    """Ambil nama makanan dari pertanyaan dengan membuang kata tanya dan kata bantu."""
    return " ".join(w for w in _bersih(q).split() if w not in STOP)


def _rp(x): return ds.rupiah(x) if x else "belum ada data harga"


def _g(x): return f"{x:g}"


def format_makanan(f, sumber=None):
    """Satu baris satu informasi (kalori dulu, lalu yang lain ke bawah)."""
    baris = [f"{f['nama']} ({f['porsi']})",
             f"Kalori : {_g(f['kkal'])} kkal", f"Protein : {_g(f['protein'])} g", f"Karbohidrat : {_g(f['karbo'])} g",
             f"Lemak : {_g(f['lemak'])} g", f"Serat : {_g(f['serat'])} g", f"Harga : {_rp(f.get('harga'))}"]
    if f.get("web"):
        baris.append(f"Sumber : {f.get('sumber', 'web')} (data dari penelusuran web, belum diverifikasi)")
        if f.get("deskripsi"): baris.append(f"Penjelasan : {f['deskripsi']}")
    else:
        baris += [f"Alasan sehat : {f['alasan']}", f"Saran memakannya : {f['saran']}"]
    return "\n".join(baris)


# ---------------------------------------------------------------- dataset
def cari_lokal(q, term):
    """Cari makanan di dataset: nama persis ada di pertanyaan > semua kata istilah ada di nama > istilah ada di nama."""
    teks = " " + _bersih(q) + " "
    daftar = list(ds.DATASET)
    dalam = [f for f in daftar if f" {f['nama'].lower()} " in teks or f" {f['nama'].lower()}nya " in teks]
    if dalam: return max(dalam, key=lambda f: len(f["nama"]))
    kata = [w for w in term.split() if len(w) >= 3]
    if not kata: return None
    def kena(f, semua):
        n = f["nama"].lower().split()
        cocok = [any(x.startswith(w) or w.startswith(x) and len(x) >= 4 for x in n) for w in kata]
        return all(cocok) if semua else (len(term) >= 4 and term in f["nama"].lower())
    for semua in (True, False):
        c = [f for f in daftar if kena(f, semua)]
        if c: return min(c, key=lambda f: (len(f["nama"]), f.get("web", False)))
    return None


# ---------------------------------------------------------------- web
def _get(url, **kw):
    kw.setdefault("timeout", BATAS)
    kw.setdefault("headers", UA)
    r = requests.get(url, **kw)
    r.raise_for_status()
    return r.json()


def _cocok(term, nama):
    n = (nama or "").lower()
    kata = [w for w in term.split() if len(w) >= 3]
    return bool(kata) and all(w in n for w in kata)


def web_gizi(term):
    """Nilai gizi per 100 g dari Open Food Facts, atau None."""
    d = _get("https://world.openfoodfacts.org/cgi/search.pl", params={
        "search_terms": term, "search_simple": 1, "action": "process", "json": 1, "page_size": 15,
        "fields": "product_name,generic_name,nutriments"})
    for x in d.get("products", []):
        n = x.get("nutriments") or {}
        nama = (x.get("product_name") or "") + " " + (x.get("generic_name") or "")
        kkal = n.get("energy-kcal_100g")
        if kkal is None and n.get("energy_100g") is not None: kkal = float(n["energy_100g"]) / 4.184
        try: kkal = float(kkal)
        except (TypeError, ValueError): continue
        if not _cocok(term, nama) or not 0 < kkal < 950: continue
        ambil = lambda k: round(float(n.get(k + "_100g") or 0), 1)
        return dict(kkal=round(kkal), protein=ambil("proteins"), karbo=ambil("carbohydrates"), lemak=ambil("fat"), serat=ambil("fiber"))
    return None


def web_teks(term):
    """Penjelasan singkat dari Wikipedia Indonesia (hanya jika artikelnya soal pangan), atau None."""
    d = _get("https://id.wikipedia.org/w/api.php", params={"action": "query", "list": "search", "srsearch": term, "srlimit": 3, "format": "json"})
    for hit in d.get("query", {}).get("search", []):
        judul = hit.get("title", "")
        if not any(w in judul.lower() for w in term.split() if len(w) >= 3): continue
        e = _get("https://id.wikipedia.org/w/api.php", params={"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                                                                "exsentences": 3, "titles": judul, "format": "json", "redirects": 1})
        for pg in e.get("query", {}).get("pages", {}).values():
            teks = re.sub(r"\s+", " ", pg.get("extract") or "").strip()
            if teks and any(k in teks.lower() for k in KATA_PANGAN): return teks[:600]
    return None


def _catatan():
    try:
        with open(BERKAS_CATATAN, encoding="utf-8") as fh: return json.load(fh)
    except (OSError, ValueError):
        return {}


def _simpan_catatan(term, teks):
    with _kunci:
        d = _catatan()
        d[term] = teks
        with open(BERKAS_CATATAN, "w", encoding="utf-8") as fh: json.dump(d, fh, ensure_ascii=False, indent=1)


def tanya_web(term):
    """Telusuri web untuk makanan yang belum ada. Mengembalikan (teks, ditambah_ke_dataset) atau (None, False)."""
    if not term or len(term) < 3 or len(term.split()) > 5: return None, False
    gizi = teks = None
    galat = False
    try: gizi = web_gizi(term)
    except Exception: galat = True
    try: teks = _catatan().get(term) or web_teks(term)
    except Exception: galat = True
    if gizi:
        f = ds.tambah_web(dict(nama=term.capitalize(), en=term, sumber="Open Food Facts" + (" dan Wikipedia" if teks else ""), deskripsi=teks or "", **gizi))
        return (format_makanan(f) if f else None), bool(f)
    if teks:
        _simpan_catatan(term, teks)
        return f"{term.capitalize()}\nPenjelasan : {teks}\nNilai gizi per porsi belum ditemukan di web, jadi belum saya masukkan ke dataset.", False
    return (TIDAK_BISA + " Penelusuran web gagal, periksa koneksi internet." if galat else None), False


# ---------------------------------------------------------------- pertanyaan umum
def _daftar(p, f_ok, urut, n=5):
    c = sorted([f for f in ds.DATASET if not f.get("web") and not kb.lolos(p, f) and f_ok(f)], key=urut)[:n]
    return "\n".join(f"- {f['nama']} ({f['porsi']}) : {_g(f['kkal'])} kkal, {_rp(f['harga'])}" for f in c)


def umum(q, p, h):
    t = _bersih(q)
    if re.search(r"\b(halo|hai|hi|selamat (pagi|siang|sore|malam))\b", t) and len(t.split()) <= 4:
        return "Halo! Tanyakan kalori, gizi, manfaat, atau harga sebuah makanan, misalnya: berapa kalori nasi goreng? Jadwal menu lengkap ada di halaman Jadwal."
    if "target kalori" in t or re.search(r"kenapa.*(kalori|target)", t):
        arah = {1: "ditambah", -1: "dikurangi", 0: "dipertahankan"}[h["arah"]]
        return (f"Target kalori kamu : {h['kal']} kkal per hari\nKebutuhan energi (TDEE) : {h['tdee']} kkal per hari\nEnergi saat istirahat (BMR) : {h['bmr']} kkal\n"
                f"BMI : {h['bmi']} ({h['kat']})\nTujuan : {h['tujuan'].lower()}\n"
                f"Penjelasan : BMR dihitung dengan rumus Mifflin-St Jeor dari usia, jenis kelamin, tinggi, dan berat badan, lalu dikalikan tingkat aktivitas menjadi "
                f"kebutuhan energi. Karena tujuanmu {h['tujuan'].lower()}, kalori {arah} secukupnya sehingga perubahan berat badan tetap aman "
                f"(sekitar {h['laju']:g} kg per minggu).")
    if "camilan" in t or "cemilan" in t or "ngemil" in t:
        return "Cemilan sehat yang cocok dengan profilmu (kalori rendah, mengenyangkan, harga terjangkau):\n" + _daftar(
            p, lambda f: f["k"] in "BLP" and f["kkal"] <= 130 and f["kenyang"] != "rendah", lambda f: (f["harga"], f["kkal"]))
    if "kenyang" in t or "lapar" in t:
        return ("Makanan yang lama mengenyangkan (tinggi serat atau protein) dan cocok dengan profilmu:\n" + _daftar(
            p, lambda f: f["kenyang"] == "tinggi" and f["kkal"] <= 200, lambda f: (f["harga"], -f["serat"] - f["protein"] / 3)) +
            "\nTips : makan sayur lebih dulu, kunyah pelan, minum air putih sebelum makan, dan jangan melewatkan sarapan.")
    return None


def jawab(q, p, h):
    """Jawaban untuk satu pertanyaan: dict(teks, sumber, ditambah). sumber: sistem | dataset | web | None."""
    q = (q or "").strip()[:300]
    if not q: return dict(teks=TIDAK_BISA, sumber=None, ditambah=False)
    u = umum(q, p, h)
    if u: return dict(teks=u, sumber="sistem", ditambah=False)
    term = istilah(q)
    f = cari_lokal(q, term)
    if f: return dict(teks=format_makanan(f), sumber="dataset", ditambah=False)
    teks, tambah = tanya_web(term)
    if teks: return dict(teks=teks, sumber="web", ditambah=tambah)
    return dict(teks=TIDAK_BISA, sumber=None, ditambah=False)
