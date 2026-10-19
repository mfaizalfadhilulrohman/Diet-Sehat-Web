"""Pengambil foto makanan dari web (TANPA gambar buatan AI).

Urutan sumber untuk tiap makanan (berhenti di foto pertama yang lolos pemeriksaan):
  0. file di static/gambar (foto Anda sendiri; JIKA ADA, internet TIDAK PERNAH dicari lagi). Nama berkas boleh memakai nama makanan
     atau slug dalam huruf besar/kecil apa pun, spasi atau garis, mis. "Beras Merah Matang.JPG" atau "beras-merah-matang.png".
     Isi folder tidak dibaca; hanya daftar nama berkasnya (dicek ulang otomatis setiap beberapa detik).
  1. gambar_manual.json  : {"slug": "https://alamat-foto"} buatan Anda sendiri
  2. Pexels (opsional, jika PEXELS_API_KEY diisi di .env)  -> foto makanan berkualitas
  3. Wikimedia Commons (pencarian berkas)
  4. Openverse (gabungan banyak situs foto berlisensi terbuka)
  5. Wikipedia (gambar utama artikel)
Pemeriksaan: nama berkas/judul/tag harus memuat kata kunci makanan (bahasa Inggris, kolom `en` di dataset), tidak memuat
kata terlarang (bunga, pohon, logo, peta, ilustrasi, dst.), ukuran minimal 300 px, dan rasio gambar wajar.
Ini yang mencegah "apel" menjadi foto bunga."""
import os, re, json, time, threading, logging, unicodedata
from concurrent.futures import ThreadPoolExecutor
import requests


def muat_env(path):
    """Pembaca .env sederhana (tanpa dependensi tambahan). Variabel lingkungan yang sudah ada tidak ditimpa."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            for baris in f:
                baris = baris.strip()
                if not baris or baris.startswith("#") or "=" not in baris: continue
                k, v = baris.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v: os.environ.setdefault(k.strip(), v)
    except OSError:
        pass


muat_env(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
EKSTENSI_LOKAL = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".jfif", ".bmp")


def kunci_nama(teks):
    """Kunci pencocokan nama berkas: huruf kecil, tanpa aksen, tanpa spasi/garis/tanda baca, tanpa akhiran salinan seperti ' (1)' atau '-copy'."""
    t = unicodedata.normalize("NFKD", teks or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\s*\(\d+\)$|[ _-]copy$|[ _-]\d+$", "", t.strip())
    return re.sub(r"[^a-z0-9]+", "", t)

log = logging.getLogger("gambar")
UA = {"User-Agent": "DietSehat/1.1 (aplikasi belajar diet; kontak: pemilik aplikasi)"}
EKSTENSI = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

# kata yang menandakan foto BUKAN makanan jadi/buahnya (bunga, pohon, logo, ilustrasi, orang, hewan, kemasan, dst.)
TERLARANG = set("""blossom blossoms flower flowers flowering tree trees plant plants seedling sapling leaf leaves foliage orchard
garden farm farmer field fields harvest harvesting market vendor vendors stall shop store supermarket package packaging label
nutrition chart infographic poster logo icon map diagram drawing painting illustration vector cartoon clipart sketch engraving
watercolor lithograph stamp coin flag statue sculpture museum portrait person people man woman girl boy child children baby
animal cat dog bird insect bee butterfly bug toy mascot costume tattoo fashion dress art artwork pattern wallpaper texture
disease pest fungus mold blight tractor truck ship boat building house street road city village temple church
newspaper book cover screenshot logo symbol emoji flowerbed bouquet cake pie dessert cocktail jam jelly juice""".split())
# kata pelengkap yang tidak dihitung sebagai kata kunci makanan
UMUM = set("cooked boiled steamed grilled baked roasted roast seared sauteed poached fresh whole plain bowl glass slice slices of the a and with in on".split())


GENERIK = set("fruit nuts nut food soup salad vegetable vegetables fillet steak breast meat bowl".split())


def kata_kunci(en):
    return [w for w in re.findall(r"[a-z]+", en.lower()) if w not in UMUM]


def bentuk(w):
    """Bentuk tunggal/jamak sederhana dari satu kata Inggris, agar 'cherries' cocok dengan 'cherry'."""
    b = {w, w + "s", w + "es", w.rstrip("s")}
    if w.endswith("ies"): b.add(w[:-3] + "y")
    if w.endswith("es"): b.add(w[:-2])
    if w.endswith("y"): b.add(w[:-1] + "ies")
    return b


def _bersih(teks):
    return re.sub(r"[^a-z]+", " ", (teks or "").lower())


def lolos_judul(en, *teks, wajib=True):
    """True jika teks (judul berkas/tag) memuat kata kunci makanan dan tidak memuat kata terlarang."""
    kk = kata_kunci(en)
    kata = set(" ".join(_bersih(t) for t in teks).split())
    milik = set().union(*(bentuk(w) for w in re.findall(r"[a-z]+", en.lower()))) if en else set()
    if kata & (TERLARANG - milik): return False
    if not kk: return True
    cocok = [w for w in kk if bentuk(w) & kata]
    inti = [w for w in kk if w not in GENERIK]
    if inti and not any(w in cocok for w in inti): return False       # kata inti (apple, chicken, ...) wajib ada
    if not inti: return len(cocok) == len(kk)                           # semua kata generik: harus lengkap
    return len(cocok) >= (max(1, (len(kk) + 1) // 2) if wajib else 1)


def ukuran_ok(w, h):
    return bool(w and h and w >= 300 and h >= 200 and .55 <= w / h <= 2.3)


# ------------------------------------------------------------------ sumber
def _get(url, **kw):
    kw.setdefault("timeout", 10)
    kw.setdefault("headers", UA)
    return requests.get(url, **kw)


def cari_pexels(en):
    kunci = os.environ.get("PEXELS_API_KEY", "").strip()
    if not kunci: return []
    r = _get("https://api.pexels.com/v1/search", params={"query": en + " food", "per_page": 10, "orientation": "landscape"},
             headers={**UA, "Authorization": kunci}).json()
    return [(p["src"].get("large") or p["src"]["medium"], p.get("alt", "")) for p in r.get("photos", [])
            if lolos_judul(en, p.get("alt", ""), wajib=False) and ukuran_ok(p.get("width"), p.get("height"))]


def cari_commons(en):
    r = _get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": 25,
        "gsrsearch": f"{en} filetype:bitmap", "prop": "imageinfo", "iiprop": "url|size|mime", "iiurlwidth": 640}).json()
    hasil = []
    for pg in sorted((r.get("query", {}).get("pages", {})).values(), key=lambda x: x.get("index", 99)):
        info = (pg.get("imageinfo") or [{}])[0]
        judul = re.sub(r"^File:|\.\w+$", "", pg.get("title", ""))
        if info.get("mime") in EKSTENSI and ukuran_ok(info.get("width"), info.get("height")) and lolos_judul(en, judul):
            hasil.append((info.get("thumburl") or info.get("url"), judul))
    return hasil


def cari_openverse(en):
    r = _get("https://api.openverse.org/v1/images/", params={"q": en, "page_size": 20, "category": "photograph",
                                                              "license_type": "all", "mature": "false"}).json()
    hasil = []
    for x in r.get("results", []):
        tag = " ".join(t.get("name", "") for t in x.get("tags", []) or [])
        if ukuran_ok(x.get("width"), x.get("height")) and lolos_judul(en, x.get("title", "")) and lolos_judul(en, x.get("title", ""), tag, wajib=False):
            hasil.append((x.get("thumbnail") or x.get("url"), x.get("title", "")))
    return hasil


def cari_wikipedia(en):
    hasil = []
    for bhs in ("en",):
        r = _get(f"https://{bhs}.wikipedia.org/w/api.php", params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": en, "gsrlimit": 3, "prop": "pageimages",
            "piprop": "thumbnail", "pithumbsize": 640}).json()
        for pg in sorted((r.get("query", {}).get("pages", {})).values(), key=lambda x: x.get("index", 99)):
            th = pg.get("thumbnail") or {}
            nama_berkas = (th.get("source") or "").rsplit("/", 1)[-1]
            if th.get("source") and ukuran_ok(th.get("width"), th.get("height")) and lolos_judul(en, pg.get("title", "")) and lolos_judul(en, nama_berkas, wajib=False):
                hasil.append((th["source"], pg.get("title", "")))
    return hasil


SUMBER = [("pexels", cari_pexels), ("commons", cari_commons), ("openverse", cari_openverse), ("wikipedia", cari_wikipedia)]


# ------------------------------------------------------------------ penyimpanan
class Pengambil:
    def __init__(self, folder, dataset_by_slug, berkas_manual=None):
        self.folder, self.data, self.manual_path = folder, dataset_by_slug, berkas_manual
        os.makedirs(folder, exist_ok=True)
        self.kunci = {}
        self.status = {}           # slug -> "proses" | "gagal"
        self._url_cache = {}       # URL foto eksternal; tidak perlu menulis file pada serverless/Vercel
        self.gagal_sampai = {}     # slug -> waktu boleh dicoba lagi
        self.mendesak = ThreadPoolExecutor(max_workers=3, thread_name_prefix="gambar-mendesak")
        self.latar = ThreadPoolExecutor(max_workers=2, thread_name_prefix="gambar-latar")
        self._mulai = False
        self._l = threading.Lock()
        self._li, self._idx, self._mt, self._cek = threading.Lock(), {}, None, 0
        self.web_aktif = os.environ.get("FOTO_WEB", "1").strip() != "0"   # FOTO_WEB=0 di .env: tidak pernah mengunduh foto dari internet

    def _indeks(self):
        """{kunci_nama: jalur berkas} dari DAFTAR NAMA berkas di folder gambar (isi berkas tidak dibaca). Dibangun ulang jika folder berubah
        atau sudah lebih dari 5 detik, sehingga foto yang baru Anda masukkan langsung terbaca tanpa menjalankan ulang aplikasi."""
        try: mt = os.stat(self.folder).st_mtime_ns
        except OSError: return {}
        sekarang = time.time()
        with self._li:
            if mt != self._mt or sekarang - self._cek > 5:
                idx = {}
                try:
                    for nama in sorted(os.listdir(self.folder)):
                        stem, ext = os.path.splitext(nama)
                        j = os.path.join(self.folder, nama)
                        if ext.lower() in EKSTENSI_LOKAL and not nama.endswith(".tmp") and os.path.isfile(j) and os.path.getsize(j) > 200:
                            idx.setdefault(kunci_nama(stem), j)
                except OSError:
                    pass
                self._idx, self._mt, self._cek = idx, mt, sekarang
            return self._idx

    def jalur(self, slug):
        """Jalur foto lokal untuk satu makanan, atau None. Dicocokkan lewat slug, nama makanan, dan nama Inggrisnya."""
        f, idx = self.data.get(slug), self._indeks()
        for kunci in (slug, f and f.get("nama"), f and f.get("en")):
            j = idx.get(kunci_nama(kunci)) if kunci else None
            if j: return j

    def _manual(self):
        try:
            with open(self.manual_path, encoding="utf-8") as f: return json.load(f)
        except Exception:
            return {}

    def _simpan(self, slug, url):
        r = _get(url, timeout=15)
        tipe = r.headers.get("content-type", "").split(";")[0].strip().lower()
        if not r.ok or tipe not in EKSTENSI or len(r.content) < 4000: return None
        j = os.path.join(self.folder, slug + EKSTENSI[tipe])
        with open(j + ".tmp", "wb") as f: f.write(r.content)
        os.replace(j + ".tmp", j)
        return j

    def url_langsung(self, slug):
        """Cari URL foto eksternal tanpa mengunduh/menulis file; cocok untuk deployment serverless seperti Vercel."""
        if self.jalur(slug):
            return None
        if slug in self._url_cache:
            return self._url_cache[slug]
        f = self.data.get(slug)
        if not f or not self.web_aktif:
            return None
        url = self._manual().get(slug)
        if url and url.startswith(("https://", "http://")):
            self._url_cache[slug] = url
            return url
        for nama, fungsi in SUMBER:
            try:
                for kandidat, judul in fungsi(f["en"])[:4]:
                    if kandidat.startswith(("https://", "http://")):
                        self._url_cache[slug] = kandidat
                        return kandidat
            except Exception as e:
                log.info("pencarian URL foto %s gagal dari %s: %s", slug, nama, str(e)[:100])
        return None

    def ambil(self, slug):
        """Cari dan simpan foto satu makanan. Mengembalikan jalur berkas atau None."""
        f = self.data.get(slug)
        if not f: return None
        with self._l: kunci = self.kunci.setdefault(slug, threading.Lock())
        with kunci:
            j = self.jalur(slug)
            if j: return j
            if not self.web_aktif:
                self.status[slug] = "gagal"
                self.gagal_sampai[slug] = time.time() + 86400
                return None
            self.status[slug] = "proses"
            try:
                url = self._manual().get(slug)
                if url:
                    j = self._simpan(slug, url)
                    if j: return j
                for nama, fungsi in SUMBER:
                    try:
                        for url, judul in fungsi(f["en"])[:4]:
                            j = self._simpan(slug, url)
                            if j:
                                log.info("foto %s <- %s: %s", f["nama"], nama, judul)
                                return j
                    except Exception as e:
                        log.info("sumber %s gagal untuk %s: %s", nama, f["nama"], str(e)[:120])
                    time.sleep(.2)
                return None
            finally:
                if self.jalur(slug): self.status.pop(slug, None)
                else:
                    self.status[slug] = "gagal"
                    self.gagal_sampai[slug] = time.time() + 6 * 3600   # jangan terus mencari tiap beberapa menit (hemat kuota)

    def minta(self, slug, mendesak=True):
        """Mulai pengambilan di latar belakang (tidak menunggu). Aman dipanggil berulang."""
        st = self.status.get(slug)
        if not self.web_aktif or self.jalur(slug) or st == "proses" or (st == "antri" and not mendesak) or self.gagal_sampai.get(slug, 0) > time.time(): return
        self.status[slug] = "proses" if mendesak else "antri"
        (self.mendesak if mendesak else self.latar).submit(self.ambil, slug)

    def keadaan(self, slug):
        if self.jalur(slug): return "ok"
        if not self.web_aktif: return "gagal"
        s = self.status.get(slug)
        return "gagal" if s == "gagal" and self.gagal_sampai.get(slug, 0) > time.time() else "proses"

    def prefetch_semua(self):
        """Unduh semua foto yang belum ada, pelan-pelan di latar belakang (dimulai sekali saat aplikasi dipakai)."""
        with self._l:
            if self._mulai: return
            self._mulai = True
        for slug in self.data: self.minta(slug, mendesak=False)
