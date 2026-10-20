"""Diet Sehat (Flask). Pasang: pip install -r requirements.txt. Jalankan: flask --app app run
Jadwal makan dibuat oleh sistem aturan dari dataset (tanpa AI), disesuaikan dengan waktu makan yang dicentang dan biaya per hari.
Tanya jawab gizi memakai dataset dan penelusuran web (webdata.py). Foto makanan: static/gambar lebih dulu, baru web (gambar.py)."""
import os, random
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash, send_file, abort
import knowledge as kb
import dataset as ds
import webdata
from gambar import Pengambil

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ganti-dengan-teks-acak")
GAMBAR_DIR = os.path.join(app.root_path, "static", "gambar")
FOTO = Pengambil(GAMBAR_DIR, ds.BY_SLUG, os.path.join(app.root_path, "gambar_manual.json"))
app.jinja_env.filters["rp"] = ds.rupiah


@app.before_request
def _mulai_unduh_foto():
    """Opsional: FOTO_PREFETCH=1 mengunduh semua foto yang BELUM ada di latar belakang. Foto yang sudah ada di static/gambar tidak dicari lagi."""
    if os.environ.get("FOTO_PREFETCH") == "1" and request.endpoint not in ("static", "gambar", "gambar_status"): FOTO.prefetch_semua()


# ---------------------------------------------------------------- Gambar
@app.route("/gambar/<nama>")
def gambar(nama):
    """Menyajikan foto: file di static/gambar dipakai langsung (tanpa internet). Jika belum ada, pengambilan dimulai di latar belakang dan 404 dikembalikan."""
    if nama not in ds.BY_SLUG: abort(404)
    j = FOTO.jalur(nama)
    if not j:
        FOTO.minta(nama)
        r = app.response_class("", 404)
        r.headers["Cache-Control"] = "no-store"
        return r
    r = send_file(j, max_age=0, conditional=True)
    r.headers["Cache-Control"] = "no-cache"  # browser selalu cek ETag: foto yang Anda ganti langsung terlihat
    return r


@app.route("/gambar-status")
def gambar_status():
    """Status foto untuk browser: {slug: ok|proses|gagal}. Dipakai jadwal.js agar foto muncul begitu siap."""
    slugs = [x for x in request.args.get("s", "").split(",") if x in ds.BY_SLUG][:40]
    for x in slugs: FOTO.minta(x)
    return jsonify({x: FOTO.keadaan(x) for x in slugs})


# ---------------------------------------------------------------- Profil
def _angka_rupiah(teks):
    """'75.000', '75000', 'Rp 75.000' -> 75000."""
    bersih = "".join(c for c in str(teks) if c.isdigit())
    if not bersih: raise ValueError("kosong")
    return int(bersih)


def _pilihan(f, nama, sah):
    """Nilai kotak centang (huruf kecil) yang termasuk pilihan sah."""
    return sorted({v.strip().lower() for v in f.getlist(nama)} & set(sah))


def baca_profil(f):
    """Mengembalikan (profil, pesan_galat); salah satunya None."""
    try:
        jaga = f.get("jaga") == "on"
        slot = f.getlist("slot")
        slot = list(kb.SLOT_ID) if "semua" in slot else [i for i in kb.SLOT_ID if i in slot]
        p = dict(usia=int(f["usia"]), jk=f["jk"], tinggi=float(f["tinggi"]), berat=float(f["berat"]), jaga=jaga, target=None, waktu=None,
                 satuan="minggu", minggu=None, ak=f["ak"], pref=f["pref"], kondisi=[], lain="",
                 alergi=_pilihan(f, "alergi", kb.ALERGI_NILAI),
                 tidak_suka=", ".join(_pilihan(f, "tidak_suka", kb.TIDAK_SUKA_NILAI)),
                 slot=slot, biaya=_angka_rupiah(f["biaya"]))
        if not jaga:
            p.update(target=float(f["target"]), waktu=float(f["waktu"]), satuan=f.get("satuan", "minggu"))
            p["minggu"] = p["waktu"] * kb.SATUAN[p["satuan"]]
    except (KeyError, ValueError):
        return None, "Isian belum lengkap atau salah. Periksa kembali semua kolom."
    if not (10 <= p["usia"] <= 100 and 100 <= p["tinggi"] <= 220 and 25 <= p["berat"] <= 250):
        return None, "Periksa usia (10-100 tahun), tinggi (100-220 cm), dan berat badan (25-250 kg)."
    if not (p["jk"] in ("Perempuan", "Laki-laki") and p["ak"] in kb.AKTIVITAS and p["pref"] in kb.PREFERENSI):
        return None, "Ada pilihan yang tidak valid. Muat ulang halaman lalu isi lagi."
    if not p["slot"]:
        return None, "Pilih minimal satu waktu makan (atau centang Keseluruhan)."
    if not 1000 <= p["biaya"] <= 10_000_000:
        return None, "Biaya per hari harus antara Rp 1.000 dan Rp 10.000.000."
    if not p["jaga"]:
        if p["target"] > p["berat"]:
            return None, "Berat badan yang diinginkan tidak boleh lebih dari berat badan saat ini. Aplikasi ini khusus untuk diet (menurunkan atau menjaga berat badan)."
        if not 25 <= p["target"] <= 250: return None, "Berat badan yang diinginkan harus antara 25 dan 250 kg."
        if not 1 <= p["minggu"] <= 104: return None, "Waktu yang diinginkan harus antara 1 minggu dan 2 tahun."
    return p, None


def peringatan_rencana(p):
    """Berat badan, waktu, atau biaya tidak masuk akal: tampilkan notifikasi dan kembalikan True (jadwal makan tidak boleh tampil)."""
    masalah = kb.masalah_rencana(p)
    if not masalah: masalah = ds.masalah_biaya(p, kb.hitung(p))
    for m in masalah: flash(m, "danger")
    return bool(masalah)


def ambil_profil():
    p = session.get("profil")
    if p:  # profil lama dilengkapi/dibersihkan otomatis
        p["kondisi"], p["lain"] = [], ""
        p["alergi"] = [a for a in p.get("alergi", []) if a in kb.ALERGI_NILAI]
        p["tidak_suka"] = ", ".join(t for t in p.get("tidak_suka", "").split(", ") if t in kb.TIDAK_SUKA_NILAI)
        p["slot"] = [i for i in kb.SLOT_ID if i in p.get("slot", kb.SLOT_ID)] or list(kb.SLOT_ID)
        p["biaya"] = int(p.get("biaya") or kb.BIAYA_BAWAAN)
    return p


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        p, galat = baca_profil(request.form)
        if p:
            session["profil"] = p
            return redirect(url_for("profil" if peringatan_rencana(p) else "jadwal"))
        flash(galat, "danger")
    elif ambil_profil():
        return redirect(url_for("jadwal"))
    return render_template("index.html", p=kb.DEFAULT, kb=kb)


@app.route("/jadwal")
def jadwal():
    p = ambil_profil()
    if not p: return redirect(url_for("index"))
    if peringatan_rencana(p): return redirect(url_for("profil"))  # rencana/biaya tidak masuk akal: jadwal tidak ditampilkan
    seed = request.args.get("s", type=int)
    if seed is None: return redirect(url_for("jadwal", s=random.randint(1, 10 ** 6)))
    h = kb.hitung(p)
    j = ds.susun_jadwal_biaya(p, h, seed)
    for b in j["baris"]:
        for i in b["items"]:
            i["foto"] = FOTO.jalur(i["slug"]) is not None
            if not i["foto"]: FOTO.minta(i["slug"])  # hanya jika fotonya BELUM ada di static/gambar
    lo, hi = ds.rentang_biaya(p, h)
    return render_template("jadwal.html", h=h, j=j, p=p, kb=kb, seed=seed, baru=random.randint(1, 10 ** 6), lo=lo, hi=hi,
                           nama_slot=[kb.SLOT_NAMA[i] for i in ds.pilihan_slot(p)])


@app.route("/chat")
def chat():
    p = ambil_profil()
    return render_template("chat.html", h=kb.hitung(p)) if p else redirect(url_for("index"))


@app.route("/profil", methods=["GET", "POST"])
def profil():
    p = ambil_profil()
    if not p: return redirect(url_for("index"))
    if request.method == "POST":
        baru, galat = baca_profil(request.form)
        if baru:
            session["profil"] = baru
            if not peringatan_rencana(baru): flash("Profil diperbarui. Jadwal dan target kalori sudah memakai data terbaru.", "success")
            return redirect(url_for("profil"))
        flash(galat, "danger")
    return render_template("profil.html", p=p, h=kb.hitung(p), kb=kb)


@app.route("/reset", methods=["GET", "POST"])
def reset():
    # GET hanya mengarahkan kembali ke beranda; sesi hanya dihapus melalui POST.
    if request.method == "POST":
        session.clear()
    return redirect(url_for("index"))


@app.post("/api/chat")
def api_chat():
    """Tanya jawab gizi dari dataset dan penelusuran web (bukan AI). Data yang ditemukan di web ditambahkan ke dataset."""
    p, d = ambil_profil(), request.get_json(silent=True) or {}
    pesan = d.get("pesan")
    teks = next((str(m.get("content", "")) for m in reversed(pesan) if isinstance(m, dict) and m.get("role") == "user"), "") if isinstance(pesan, list) else ""
    if not p or not teks.strip(): return jsonify(teks="Isi profil dan tulis pertanyaan dulu."), 400
    try:
        return jsonify(webdata.jawab(teks, p, kb.hitung(p)))
    except Exception:
        app.logger.exception("Tanya jawab gagal")
        return jsonify(teks=webdata.TIDAK_BISA), 200
