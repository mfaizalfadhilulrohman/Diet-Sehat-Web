"""Lapisan AI: Gemini (Google) dan Claude (Anthropic) dengan satu antarmuka.

Pengaturan lewat berkas .env (lihat .env.example) atau variabel lingkungan:
  GEMINI_API_KEY      kunci Google. Kunci berawalan "AQ." adalah kunci Vertex AI Express dan OTOMATIS memakai mode Vertex;
                      kunci berawalan "AIza" memakai Gemini API biasa.
  ANTHROPIC_API_KEY   kunci Claude (opsional).
  AI_PROVIDER         auto (default: Gemini dulu, lalu Claude) | gemini | claude
  GEMINI_MODEL        daftar model dipisah koma; model yang tidak ada dilewati otomatis.
  CLAUDE_MODEL        default claude-sonnet-5-5
"""
import os, re, json, time, threading, logging

log = logging.getLogger("ai")


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


def _cfg(nama, bawaan=""):
    return os.environ.get(nama, bawaan).strip()


class GalatAI(Exception):
    """Galat yang pesannya aman ditampilkan ke pengguna. `jenis`: kunci | kuota | sibuk | model | jaringan | lain."""
    def __init__(self, pesan, jenis="lain", detail=""):
        super().__init__(pesan)
        self.jenis, self.detail = jenis, detail


PESAN = {
    "kunci": "Kunci API ditolak. Periksa GEMINI_API_KEY / ANTHROPIC_API_KEY di berkas .env.",
    "izin": "Kunci dikenali tetapi tidak punya izin memakai model ini (API belum diaktifkan, penagihan belum aktif, atau wilayah tidak didukung). Buka /ai-cek untuk detailnya.",
    "kuota": "Kuota AI habis atau terlalu banyak permintaan. Tunggu sebentar lalu coba lagi.",
    "sibuk": "Layanan AI sedang sibuk. Coba lagi beberapa detik lagi.",
    "model": "Model AI yang dipilih tidak tersedia untuk kunci ini.",
    "jaringan": "Tidak bisa terhubung ke layanan AI. Periksa koneksi internet.",
    "lain": "Layanan AI gagal menjawab.",
}


def klasifikasi(e):
    """Ubah error SDK menjadi jenis yang ramah pengguna."""
    kode = getattr(e, "code", None) or getattr(e, "status_code", None)
    t = f"{type(e).__name__} {e}".lower()
    if kode == 403 or "permission_denied" in t or "has not been used" in t or "billing" in t: return "izin"
    if kode == 401 or "api key not valid" in t or "api_key_invalid" in t or "authentication" in t:
        return "kunci"
    if kode == 400 and ("api key" in t or "expired" in t): return "kunci"
    if kode == 404 or "not_found" in t or "is not found" in t or "not found for api version" in t: return "model"
    if kode == 429 or "resource_exhausted" in t or "rate limit" in t or "quota" in t: return "kuota"
    if kode in (500, 502, 503, 504, 529) or "unavailable" in t or "overloaded" in t or "deadline" in t: return "sibuk"
    if "timeout" in t or "timed out" in t: return "sibuk"
    if "connect" in t or "resolve" in t or "network" in t or "ssl" in t: return "jaringan"
    return "lain"


# ------------------------------------------------------------------ Gemini
_klien_g, _kunci_g = None, threading.Lock()
_model_mati = set()


def kunci_gemini(): return _cfg("GEMINI_API_KEY")
def kunci_claude(): return _cfg("ANTHROPIC_API_KEY")


def _klien_gemini():
    """Satu Client dipakai bersama (Client sekali pakai ikut ditutup saat di-garbage-collect -> error 'client has been closed')."""
    global _klien_g
    with _kunci_g:
        if _klien_g is None:
            from google import genai
            from google.genai import types
            kunci = kunci_gemini()
            vertex = _cfg("GEMINI_VERTEX").lower() in ("1", "true", "ya") or (_cfg("GEMINI_VERTEX") == "" and kunci.startswith("AQ."))
            opsi = types.HttpOptions(timeout=45_000)
            _klien_g = genai.Client(vertexai=True, api_key=kunci, http_options=opsi) if vertex else genai.Client(api_key=kunci, http_options=opsi)
        return _klien_g


def _reset_gemini():
    global _klien_g
    with _kunci_g: _klien_g = None


def _gemini(sistem, pesan, json_mode):
    from google.genai import types
    isi = [types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part(text=m["content"])]) for m in pesan]
    cfg = types.GenerateContentConfig(system_instruction=sistem, temperature=.6,
                                      **({"response_mime_type": "application/json"} if json_mode else {}))
    galat = None
    for model in [m.strip() for m in _cfg("GEMINI_MODEL", "gemini-2.5-flash,gemini-2.5-flash-lite").split(",") if m.strip()]:
        if model in _model_mati: continue
        for percobaan in range(2):
            try:
                r = _klien_gemini().models.generate_content(model=model, contents=isi, config=cfg)
                teks = (r.text or "").strip()
                if teks: return teks
                galat = GalatAI(PESAN["lain"], "lain", "jawaban kosong")
                break
            except Exception as e:
                jenis = klasifikasi(e)
                galat = GalatAI(PESAN[jenis], jenis, f"{model}: {str(e)[:300]}")
                log.warning("Gemini %s gagal (%s): %s", model, jenis, str(e)[:300])
                if "closed" in str(e).lower(): _reset_gemini(); continue
                if jenis == "model": _model_mati.add(model); break
                if jenis == "sibuk" and percobaan == 0: time.sleep(1.5); continue
                if jenis in ("kunci", "jaringan", "izin"): raise galat
                break
    raise galat or GalatAI(PESAN["lain"])


# ------------------------------------------------------------------ Claude
_klien_c = None


def _claude(sistem, pesan, json_mode):
    global _klien_c
    import anthropic
    if _klien_c is None:
        _klien_c = anthropic.Anthropic(api_key=kunci_claude(), timeout=45, max_retries=1)
    try:
        r = _klien_c.messages.create(model=_cfg("CLAUDE_MODEL", "claude-sonnet-5-5"), max_tokens=1800, system=sistem, messages=pesan)
    except Exception as e:
        jenis = klasifikasi(e)
        log.warning("Claude gagal (%s): %s", jenis, str(e)[:300])
        raise GalatAI(PESAN[jenis], jenis, str(e)[:300])
    teks = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
    if not teks: raise GalatAI(PESAN["lain"], "lain", "jawaban kosong")
    return teks


# ------------------------------------------------------------------ antarmuka
def penyedia():
    """Daftar penyedia yang bisa dipakai, berurutan sesuai AI_PROVIDER."""
    ada = {"gemini": (kunci_gemini(), _gemini), "claude": (kunci_claude(), _claude)}
    pilih = _cfg("AI_PROVIDER", "auto").lower()
    urut = [pilih] if pilih in ada else ["gemini", "claude"]
    return [(n, ada[n][1]) for n in urut if ada[n][0]]


def siap():
    return bool(penyedia())


def tanya(sistem, pesan, json_mode=False):
    """Kirim percakapan [{role, content}] ke penyedia berurutan. Mengembalikan (teks, nama_penyedia) atau melempar GalatAI."""
    daftar = penyedia()
    if not daftar: raise GalatAI("Belum ada kunci API. Isi GEMINI_API_KEY atau ANTHROPIC_API_KEY di berkas .env.", "kunci")
    galat = None
    for nama, fungsi in daftar:
        try:
            return fungsi(sistem, pesan, json_mode), nama
        except GalatAI as e:
            galat = e
        except ImportError as e:
            galat = GalatAI(f"Pustaka untuk {nama} belum terpasang di Python yang menjalankan aplikasi. Jalankan setup.bat (atau: python -m pip install -r requirements.txt).", "lain", str(e))
        except Exception as e:
            jenis = klasifikasi(e)
            galat = GalatAI(PESAN[jenis] if jenis != "lain" else f"{nama}: {type(e).__name__}", jenis, str(e)[:300])
            log.warning("%s gagal: %s", nama, e)
    raise galat


def ekstrak_json(teks):
    teks = re.sub(r"^```(?:json)?|```$", "", teks.strip(), flags=re.M).strip()
    return json.loads(teks[teks.find("{"): teks.rfind("}") + 1])


def diagnosa():
    """Uji singkat tiap penyedia; hasilnya dipakai halaman /ai-cek untuk mencari tahu kenapa AI gagal."""
    hasil = {"penyedia_aktif": [n for n, _ in penyedia()], "gemini_mode": None, "tes": {}}
    if kunci_gemini():
        k = kunci_gemini()
        hasil["gemini_mode"] = "vertex-express" if (_cfg("GEMINI_VERTEX").lower() in ("1", "true", "ya") or (not _cfg("GEMINI_VERTEX") and k.startswith("AQ."))) else "gemini-api"
    for nama, fungsi in penyedia():
        t = time.time()
        try:
            teks = fungsi("Jawab satu kata.", [{"role": "user", "content": "Balas dengan kata: siap"}], False)
            hasil["tes"][nama] = dict(ok=True, jawaban=teks[:60], detik=round(time.time() - t, 1))
        except GalatAI as e:
            hasil["tes"][nama] = dict(ok=False, jenis=e.jenis, pesan=str(e), detail=e.detail, detik=round(time.time() - t, 1))
        except Exception as e:
            hasil["tes"][nama] = dict(ok=False, jenis=klasifikasi(e), pesan=type(e).__name__, detail=str(e)[:300])
    return hasil
