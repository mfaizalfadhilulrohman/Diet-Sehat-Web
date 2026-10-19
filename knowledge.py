"""Basis pengetahuan Diet Sehat: frame makanan, production rules (BMI, kalori, rencana berat badan), dan penyaring menu. Tanpa AI."""
import re, math

AKTIVITAS = {"Sangat ringan (duduk seharian)": 1.2, "Ringan (olahraga 1-3x/minggu)": 1.375,
             "Sedang (olahraga 3-5x/minggu)": 1.55, "Berat (olahraga 6-7x/minggu)": 1.725}
TUJUAN = ["Menjaga berat badan", "Menurunkan berat badan", "Menaikkan berat badan"]
PREFERENSI = ["Tidak ada pantangan", "Vegetarian", "Vegan", "Pescatarian"]
# Waktu makan yang bisa dicentang pengguna: (id, nama tampilan, waktu, bagian dari kalori harian)
SLOT_MENU = [("sarapan", "Sarapan", "Pagi", .22), ("camilan1", "Cemilan siang", "Menjelang siang", .08),
             ("siang", "Makan siang", "Siang", .28), ("camilan2", "Cemilan sore", "Sore", .08),
             ("malam", "Makan malam", "Malam", .24), ("camilan3", "Cemilan malam", "Larut malam", .10)]
SLOT_ID = [x[0] for x in SLOT_MENU]
SLOT_NAMA = {x[0]: x[1] for x in SLOT_MENU}
BIAYA_BAWAAN = 75000   # Rupiah per hari
KONDISI = []  # kondisi khusus dihapus: tanpa AI, sistem hanya menangani alergi, preferensi, dan rencana berat badan
ALERGI = ["Kacang tanah", "Kacang pohon", "Telur", "Susu", "Kedelai", "Ikan", "Udang", "Seafood", "Gluten", "Wijen"]  # pilihan alergi (sama dengan label alergen di dataset)
ALERGI_NILAI = [a.lower() for a in ALERGI]
TIDAK_SUKA = ["Pare", "Terong", "Jamur", "Bayam", "Brokoli", "Kangkung", "Wortel", "Tauge", "Tomat", "Tahu", "Tempe", "Ikan", "Telur", "Kacang"]  # pilihan populer
TIDAK_SUKA_NILAI = [a.lower() for a in TIDAK_SUKA]
L3, JENIS = ("rendah", "sedang", "tinggi"), ("nabati", "telur_susu", "ikan", "hewani")
DEFAULT = dict(usia=25, jk="Perempuan", tinggi=165, berat=60, jaga=False, target=55, waktu=12, satuan="minggu", ak=list(AKTIVITAS)[1],
               kondisi=[], lain="", alergi=[], pref=PREFERENSI[0], tidak_suka="", slot=list(SLOT_ID), biaya=BIAYA_BAWAAN)
SATUAN = {"minggu": 1, "bulan": 4.345}
BMI_MIN, BMI_MAX = 18.5, 25.0          # rentang normal (Kemenkes RI / WHO)
LAJU_TURUN, LAJU_NAIK = 1.0, 0.5       # batas aman kg per minggu (turun maks. 1% berat badan)
KKAL_PER_KG = 7700

def frame(nama, kat, porsi, kkal, protein, karbo, lemak, serat, ig="rendah", na="rendah", pu="rendah", ko="rendah",
          la="aman", je="nabati", al=()):
    """Satu frame makanan: atribut + nilai atribut (kenyang adalah nilai turunan)."""
    f = dict(nama=nama, kat=kat, porsi=porsi, kkal=kkal, protein=protein, karbo=karbo, lemak=lemak, serat=serat,
             ig=ig, na=na, pu=pu, ko=ko, la=la, je=je, al=list(al))
    f["kenyang"] = "tinggi" if serat >= 3.5 or protein >= 15 else "sedang" if serat >= 1.5 or protein >= 6 else "rendah"
    return f


# Knowledge base contoh (untuk dijelaskan di PPT); data hidangan lengkap berasal dari AI dalam format frame yang sama.
KB_CONTOH = [
    frame("Beras merah matang", "Karbohidrat", "150 g", 165, 4, 35, 1.3, 2.7, ig="sedang"),
    frame("Beras putih matang", "Karbohidrat", "150 g", 195, 4, 42, 0.5, 0.6, ig="tinggi"),
    frame("Dada ayam panggang", "Protein hewani", "100 g", 165, 31, 0, 3.6, 0, pu="sedang", ko="sedang", je="hewani"),
    frame("Udang rebus", "Protein hewani", "100 g", 100, 20, 0.2, 1.7, 0, na="sedang", pu="tinggi", ko="tinggi", je="ikan", al=("udang", "seafood")),
    frame("Tofu panggang", "Protein nabati", "100 g", 90, 9, 2, 5.5, 1, pu="sedang", al=("kedelai",)),
    frame("Sup ayam sayur", "Hidangan", "1 mangkuk", 120, 12, 9, 4, 2, na="sedang", pu="sedang", ko="sedang", je="hewani"),
]


def hitung(p):
    """Production rules: BMI, BMR (Mifflin-St Jeor), TDEE, lalu rencana berat badan.
    Tujuan TIDAK dipilih pengguna; ia diturunkan dari berat sekarang, berat yang diinginkan, dan waktu. Jika permintaan
    tidak sehat/masuk akal, sistem mengganti tujuan atau memperpanjang waktu, lalu menjelaskannya di `ganti`."""
    bb, tb = p["berat"], p["tinggi"] / 100
    bmi = bb / tb ** 2
    laki, k = p["jk"] == "Laki-laki", [x.lower() for x in p["kondisi"]]
    bmr = 10 * bb + 6.25 * p["tinggi"] - 5 * p["usia"] + (5 if laki else -161)
    tdee = bmr * AKTIVITAS.get(p["ak"], 1.375)
    bb_min, bb_maks = BMI_MIN * tb ** 2, BMI_MAX * tb ** 2
    bmi_t = lambda x: x / tb ** 2
    ganti, cat = [], []
    pesan = lambda m: (ganti.append(m), cat.append(m))

    jaga = p.get("jaga") or p.get("target") is None or abs(p["target"] - bb) < 0.1
    minta = 0 if jaga else (1 if p["target"] > bb else -1)   # arah yang diminta pengguna
    target, minggu = (bb if jaga else p["target"]), (p.get("minggu") or 0)

    def sasaran(arah):
        """Sasaran awal yang aman: turun sampai batas atas normal (maks. 10% dulu), naik sampai BMI 20 (maks. 10% dulu)."""
        return max(bb_maks, bb * .90) if arah < 0 else min(20 * tb ** 2, bb * 1.10)

    terkunci = p["usia"] < 18 or "hamil" in k or "menyusui" in k
    if terkunci:
        sebab = ("usiamu masih di bawah 18 tahun dan tubuhmu masih bertumbuh" if p["usia"] < 18 else
                 "kamu sedang hamil dan kebutuhan energi ibu serta janin harus terpenuhi" if "hamil" in k else
                 "kamu sedang menyusui dan kebutuhan energi serta cairan meningkat")
        if minta: pesan(f"Permintaan mengubah berat badan saya ganti menjadi 'menjaga berat badan' karena {sebab}. Konsultasikan kebutuhan gizimu dengan dokter atau ahli gizi.")
        arah, target = 0, bb
    else:
        arah = minta
        if jaga:  # ingin menjaga, tetapi kondisi tubuh menyarankan hal lain
            if bmi >= 27:
                arah = -1; pesan(f"Kamu ingin menjaga berat badan, tetapi indeks massa tubuhmu {bmi:.1f} tergolong obesitas. Saya mengganti tujuanmu menjadi 'menurunkan berat badan' secara bertahap karena menjaga berat badan di kondisi ini tidak menurunkan risiko penyakit.")
            elif bmi > BMI_MAX:
                arah = -1; pesan(f"Kamu ingin menjaga berat badan, tetapi indeks massa tubuhmu {bmi:.1f} tergolong berat badan lebih. Saya mengganti tujuanmu menjadi 'menurunkan berat badan' secara bertahap.")
            elif bmi < BMI_MIN:
                arah = 1; pesan(f"Kamu ingin menjaga berat badan, tetapi indeks massa tubuhmu {bmi:.1f} tergolong kurang. Saya mengganti tujuanmu menjadi 'menaikkan berat badan' secara bertahap.")
        elif arah < 0:
            if bmi < BMI_MIN:
                arah = 1; pesan(f"Kamu ingin turun ke {target:g} kg, tetapi indeks massa tubuhmu sekarang {bmi:.1f} (kurang). Saya mengganti tujuanmu menjadi 'menaikkan berat badan' agar tidak kekurangan gizi.")
            elif bmi_t(target) < BMI_MIN:
                if bmi > BMI_MAX:
                    pesan(f"Target {target:g} kg setara indeks massa tubuh {bmi_t(target):.1f} (di bawah normal), jadi tidak sehat. Saya menyesuaikan target agar tetap menurunkan berat badan, tetapi ke batas yang aman.")
                else:
                    arah = 0; pesan(f"Target {target:g} kg setara indeks massa tubuh {bmi_t(target):.1f} (di bawah batas normal {BMI_MIN}). Berat badanmu sudah ideal, jadi saya mengganti tujuanmu menjadi 'menjaga berat badan'.")
        else:
            if bmi > BMI_MAX:
                arah = -1; pesan(f"Kamu ingin naik ke {target:g} kg, tetapi indeks massa tubuhmu sekarang {bmi:.1f} (berat badan lebih/obesitas). Saya mengganti tujuanmu menjadi 'menurunkan berat badan'.")
            elif bmi_t(target) > BMI_MAX:
                if bmi < BMI_MIN:
                    pesan(f"Target {target:g} kg setara indeks massa tubuh {bmi_t(target):.1f} (di atas normal), jadi tidak sehat. Saya menyesuaikan target agar tetap menaikkan berat badan, tetapi ke batas yang aman.")
                else:
                    arah = 0; pesan(f"Target {target:g} kg setara indeks massa tubuh {bmi_t(target):.1f} (di atas batas normal {BMI_MAX:g}). Berat badanmu sudah ideal, jadi saya mengganti tujuanmu menjadi 'menjaga berat badan'.")
        # target pengguna dipakai apa adanya hanya jika arahnya sama dan masih sehat; selain itu pakai sasaran aman
        if arah == 0: target = bb
        elif arah != minta or (arah < 0 and bmi_t(target) < BMI_MIN) or (arah > 0 and bmi_t(target) > BMI_MAX):
            target = sasaran(arah)

    delta = target - bb
    kal, laju = tdee, 0.0
    if arah != 0:
        maks = min(LAJU_TURUN, .01 * bb) if arah < 0 else LAJU_NAIK
        minta_laju = abs(delta) / minggu if minggu else maks
        laju = min(minta_laju, maks)
        if arah < 0:
            kal = max(tdee - min(laju * KKAL_PER_KG / 7, 1000), 1500 if laki else 1200)
            laju = (tdee - kal) * 7 / KKAL_PER_KG
        else:
            kal = tdee + min(laju * KKAL_PER_KG / 7, 500)
            laju = (kal - tdee) * 7 / KKAL_PER_KG
        minggu_efektif = max(1, round(abs(delta) / laju)) if laju > 0 else 0
        if minggu and arah == minta and minggu_efektif > minggu * 1.05 and abs(target - p["target"]) < .05:
            pesan(f"Waktu {minggu:g} minggu terlalu singkat untuk {'turun' if arah < 0 else 'naik'} {abs(delta):.1f} kg secara sehat (batas aman sekitar {maks:.1f} kg per minggu). Saya memperpanjang perkiraannya menjadi ±{minggu_efektif} minggu.")
    else:
        minggu_efektif = 0
    cat.append("Aplikasi ini tidak menilai kondisi kesehatan khusus (penyakit atau kehamilan). Jika kamu memilikinya, konsultasikan rencana dietmu dengan dokter atau ahli gizi.")
    ginjal = "penyakit ginjal" in k
    if ginjal: cat.append("Penyakit ginjal: atur diet bersama dokter/ahli gizi.")
    if arah != 0 and k: cat.append("Kamu punya kondisi khusus: konsultasikan rencana mengubah berat badan dengan dokter.")
    tujuan = TUJUAN[1] if arah < 0 else TUJUAN[2] if arah > 0 else TUJUAN[0]
    prot = None if ginjal else round(bb * (1.2 if p["usia"] >= 60 or arah != 0 else .9))
    kat = ("anak/remaja" if p["usia"] < 18 else "Kurang" if bmi < BMI_MIN else "Normal" if bmi <= BMI_MAX
           else "Lebih" if bmi <= 27 else "Obesitas")
    return dict(bmi=round(bmi, 1), kat=kat, bmr=round(bmr), tdee=round(tdee), kal=round(kal), prot=prot, tujuan=tujuan, arah=arah,
                target=round(target, 1), minggu=minggu_efektif, laju=round(laju, 2), selisih=round(delta, 1), cat=cat, ganti=ganti,
                bb_sehat=(round(bb_min, 1), round(bb_maks, 1)))


def masalah_rencana(p):
    """Pemeriksaan rencana diet. Jika hasilnya tidak kosong, jadwal makan TIDAK boleh ditampilkan dan pengguna diminta mengganti isian di profil."""
    if p.get("jaga") or p.get("target") is None: return []
    bb, tb = p["berat"], p["tinggi"] / 100
    bb_min = BMI_MIN * tb ** 2
    pesan = []
    if p["target"] < bb_min - 0.05:
        pesan.append(f"Berat badan yang diinginkan ({p['target']:g} kg) tidak masuk akal dan tidak sehat untuk tinggi {p['tinggi']:g} cm "
                     f"(indeks massa tubuh {p['target'] / tb ** 2:.1f}, batas normal minimal {BMI_MIN}). Silakan ganti berat badan yang diinginkan di profil. "
                     f"Berat badan minimum yang disarankan: {bb_min:.1f} kg."
                     + (" Berat badanmu saat ini sudah di bawah normal, jadi diet penurunan berat badan tidak disarankan." if bb < bb_min else ""))
        return pesan  # waktu diperiksa lagi setelah berat badan yang diinginkan diperbaiki
    selisih = bb - p["target"]
    laju = min(LAJU_TURUN, .01 * bb)  # kilogram per minggu yang masih aman
    minimal = math.ceil(selisih / laju) if selisih > 0 else 0
    if selisih > 0 and p["minggu"] < minimal:
        pesan.append(f"Waktu yang diinginkan ({p['waktu']:g} {p['satuan']}) tidak masuk akal untuk menurunkan {selisih:.1f} kg secara sehat "
                     f"(batas aman sekitar {laju:.2f} kg per minggu). Silakan ganti waktu di profil. "
                     f"Waktu minimum yang disarankan: {minimal} minggu (sekitar {minimal / SATUAN['bulan']:.1f} bulan).")
    return pesan


# Pola kata (Indonesia/Inggris) untuk tiap pilihan "tidak disukai", agar "Tahu" juga menyaring "Tofu scramble" tetapi "Telur" tidak menyaring "eggplant".
SINONIM = {"tahu": r"\btahu|\btofu", "tempe": r"\btempe", "jamur": r"\bjamur|\bmushroom", "bayam": r"\bbayam|\bspinach",
           "brokoli": r"\bbrokoli|\bbroccoli", "wortel": r"\bwortel|\bcarrot", "kangkung": r"\bkangkung", "pare": r"\bpare\b|bitter melon",
           "tauge": r"\btauge|bean sprout", "terong": r"\bterong|\beggplant|ratatouille",
           "tomat": r"\btomat|\btomato|shakshuka|ratatouille|minestrone", "kacang": r"\bkacang|\bpeanut",
           "telur": r"\btelur|\beggs?\b|omelet|orak-arik",
           "ikan": r"\bikan|\bfish\b|salmon|tuna|tilapia|sarden|makerel|sardine|mackerel|\bcod\b|trout|haddock|sea bass"}


def tidak_suka_cocok(s, f):
    """True jika makanan f memuat bahan yang tidak disukai (nama, nama Inggris, sinonim, atau label alergen)."""
    teks = (f["nama"] + " " + str(f.get("en", ""))).lower().replace("water spinach", "kangkung")
    return bool(re.search(SINONIM.get(s, r"\b" + re.escape(s)), teks)) or any(s in a for a in f["al"])


def lolos(p, f):
    """Memeriksa satu frame makanan terhadap profil; mengembalikan daftar pelanggaran (kosong = lolos)."""
    v = []
    teks = " ".join([f["nama"]] + f["al"] + f["bahan"]).lower()
    v += [f"terkait alergi '{a}'" for a in p["alergi"] if a in teks]
    v += ["tidak disukai" for s in p["tidak_suka"].lower().split(",") if s.strip() and tidak_suka_cocok(s.strip(), f)]
    if p["pref"] == "Vegetarian" and f["je"] not in ("nabati", "telur_susu"): v.append("tidak vegetarian")
    if p["pref"] == "Vegan" and f["je"] != "nabati": v.append("tidak vegan")
    if p["pref"] == "Pescatarian" and f["je"] == "hewani": v.append("tidak pescatarian")
    return v
