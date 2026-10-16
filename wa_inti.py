# -*- coding: utf-8 -*-
"""Pondasi bersama lacon-wa.

Config, login Google, akses Drive, pembaca tanggal, indeks berkas, dan
argumen jendela Chrome. SEMUA modul lain mengimpor dari sini - jangan
menyalin logikanya ke tempat lain.

Repo ini SENGAJA berdiri sendiri, terpisah dari Lacon. Akibatnya sebagian
logika di sini kembaran dengan yang ada di Lacon (tools/lacon_storymotion.py).
Kalau suatu hari aturan di Lacon berubah - saringan Return, peta awalan
brand, nama bulan - PERUBAHANNYA TIDAK IKUT KE SINI dengan sendirinya.
Itu harga dari memisahkan repo, dan sudah disepakati.
"""
import datetime as dt
import io
import json
import os
import re
import sys

AKAR = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(AKAR, "config.json")
SECRETS = os.path.join(AKAR, ".secrets")
CLIENT_SECRET = os.path.join(SECRETS, "client_secret.json")
TOKEN = os.path.join(SECRETS, "token.json")
PROFIL_AKAR = os.path.join(AKAR, ".chrome")
INDEKS = os.path.join(AKAR, "indeks_drive.json")
LOG = os.path.join(AKAR, "riwayat.log")
UNDUHAN = os.path.join(AKAR, "unduhan")
KURASI = os.path.join(AKAR, "kurasi")

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


# ----------------------------------------------------------------- layar

def info(t):
    print(t)


def gagal(t):
    print("\nBerhenti: %s" % t)
    sys.exit(1)


def catat(baris):
    """Satu baris per tindakan. Ini yang dipercaya, bukan ingatan.

    Log tugas cuma memuat yang sempat tercetak sebelum prosesnya mati;
    berkas ini ditulis begitu tindakannya diterima.
    """
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                               baris))


def baca_config():
    if not os.path.isfile(CONFIG):
        gagal("config.json tidak ada di %s" % AKAR)
    return json.load(io.open(CONFIG, encoding="utf-8"))


# ----------------------------------------------------------------- Google

def masuk(paksa=False):
    """Izin Google. Kuncinya TIDAK ikut repo - lihat .gitignore."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(TOKEN) and not paksa:
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token and not paksa:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds or not creds.valid:
            if not os.path.exists(CLIENT_SECRET):
                gagal("Kunci Google belum ada.\n"
                      "  Taruh client_secret.json di: %s\n"
                      "  (Google Cloud Console > Credentials > OAuth client ID "
                      "tipe Desktop)" % SECRETS)
            info("Membuka browser untuk minta izin akses Google...")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0, prompt="consent")
        os.makedirs(SECRETS, exist_ok=True)
        with io.open(TOKEN, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return creds


def layanan():
    """(sheets, drive). supportsAllDrives dipakai di SEMUA panggilan Drive -
    tanpa itu berkas di Shared Drive dijawab 'File not found' seolah tidak ada.
    """
    from googleapiclient.discovery import build
    k = masuk()
    return (build("sheets", "v4", credentials=k, cache_discovery=False),
            build("drive", "v3", credentials=k, cache_discovery=False))


# ----------------------------------------------------------------- tanggal

BULAN_ID = {1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei",
            6: "Juni", 7: "Juli", 8: "Agustus", 9: "September",
            10: "Oktober", 11: "November", 12: "Desember"}
NOMOR_BULAN = {v.lower(): k for k, v in BULAN_ID.items()}
# Tim menulis tanggal di sheet dalam bahasa INGGRIS ("7 October 2026").
# Sebagian bulan ejaannya kebetulan sama di dua bahasa - April, September,
# November - jadi barisnya lolos dan sheetnya kelihatan sehat. Yang ejaannya
# beda JATUH KE None dan barisnya dibuang DIAM-DIAM, tanpa galat. Di Lacon
# ini bikin seluruh Oktober dan Desember tidak terbaca, dan jalur WA terlihat
# seolah tidak punya isi sejak 29 Agustus 2026. Ketahuan 7 Oktober 2026.
NOMOR_BULAN.update({
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
})


def baca_tanggal_sheet(t):
    """'7 October 2026' atau '7 Oktober 2026' -> date. None kalau tidak kenal."""
    m = re.match(r"\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", t or "")
    if not m:
        return None
    b = NOMOR_BULAN.get(m.group(2).lower())
    return dt.date(int(m.group(3)), b, int(m.group(1))) if b else None


def baca_tanggal_perintah(t):
    """'7/10/2026' atau '2026-10-07' -> date."""
    t = (t or "").strip()
    for pola in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(t, pola).date()
        except ValueError:
            pass
    gagal("Tanggal tidak terbaca: %r. Pakai 7/10/2026 atau 2026-10-07." % t)


def nama_folder_tanggal(hari):
    return "WA Story %d %s %d" % (hari.day, BULAN_ID[hari.month], hari.year)


# ----------------------------------------------------------------- brand

# Awalan nama berkas per brand. 'edb' milik EDUBIA, bukan Edubisa - kalau
# ditebak, video Edubia naik ke nomor Edubisa.
AWALAN = {
    "edubia": ("edubia", "edb"),
    "edufio": ("edufio",),
    "edumisi": ("edumisi",),
    "eduraya": ("eduraya",),
    "edumoka": ("edumoka",),
    "edupoint": ("edupoint",),
    "edusora": ("edusora",),
    "edubisa": ("edubisa",),
    "eduosmo": ("eduosmo",),
    "arabi": ("arabi",),
    "edulob": ("edulob",),
}

# DAFTAR PUTIH, bukan daftar hitam. Dipasang sebagai daftar terlarang dulu,
# lalu folder akar baru yang belum terdaftar otomatis lolos - dan memang ada
# yang lolos (/mengaji, /eduprima). Dengan daftar putih, brand baru yang
# belum disebut akan terbaca stok nol - diamnya berbunyi.
FOLDER_BRAND = tuple(sorted(set(list(AWALAN) + ["lilo"])))


def rapi(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def brand_berkas(nama):
    """Brand pemilik berkas ini menurut AWALAN.

    None kalau tidak ada yang cocok, list kalau cocok ke lebih dari satu.
    Dua-duanya harus menghentikan pekerjaan, bukan ditebak.
    """
    n = os.path.basename(nama or "").lower()
    kena = []
    for b, awalan in AWALAN.items():
        for a in awalan:
            if re.search(r"(^|[^a-z])" + re.escape(a) + r"[^a-z]", n):
                kena.append(b)
                break
    kena = sorted(set(kena))
    if not kena:
        return None
    return kena[0] if len(kena) == 1 else kena


# ----------------------------------------------------------------- indeks

def dari_folder_brand(jalur):
    ruas = [r for r in (jalur or "").split("/") if r.strip()]
    return bool(ruas) and ruas[0].strip().lower() in FOLDER_BRAND


def muat_indeks(diam=False):
    """Peta nama berkas -> entri Drive, HANYA yang lolos kurasi.

    DUA SARINGAN, dan keduanya mahal harganya.

    1. Hanya folder brand. Di creative-makers ada folder yang bukan folder
       brand tapi isinya juga berawalan nama brand - /Other Ouput, /mengaji,
       /eduprima. Berkas di situ di luar putaran motion.

    2. NAMA YANG ADA DI RETURN ikut disaring, walau salinannya di folder
       brand. Return isinya berkas yang TIDAK LOLOS KURASI, menunggu
       dibetulkan tim produksi. Tim menyalin berkas tolakan ke Return dan
       aslinya tidak dihapus dari folder brand, jadi saringan jalur saja
       tidak akan pernah menangkapnya - dibuktikan lewat md5, 6 dari 9
       berkas kembar di jadwal 13-14 September 2026 identik dengan salinan
       Return-nya, dan 16 berkas tolakan sempat tayang.

       Sengaja memakai NAMA, bukan isi: indeks tidak menyimpan md5, dan versi
       revisi biasanya kembali dengan nama yang sama. Selama namanya masih
       ada di Return, dianggap belum lolos.

    JANGAN dilonggarkan karena stok kelihatan menipis. Stok yang tersaring
    itu urusan tim kurasi - laporkan angkanya, jangan dibuka.

    FOLDER RETURN TIDAK BOLEH DISENTUH. Namanya cuma DIBACA dari indeks
    untuk menyaring keluar - itu menjauhkan, bukan memakai.
    """
    if not os.path.isfile(INDEKS):
        gagal("Indeks Drive belum ada. Jalankan dulu: python wa.py indeks")
    isi = json.load(io.open(INDEKS, encoding="utf-8"))

    di_return = set()
    for v in isi:
        ruas = [r for r in (v.get("jalur") or "").split("/") if r.strip()]
        if ruas and ruas[0].strip().lower() == "return":
            di_return.add(v["nama"].lower())

    peta, dibuang, revisi = {}, 0, 0
    for v in isi:
        if not dari_folder_brand(v.get("jalur", "")):
            dibuang += 1
            continue
        if v["nama"].lower() in di_return:
            revisi += 1
            continue
        kunci = rapi(re.sub(r"\.mp4$", "", v["nama"], flags=re.I))
        peta.setdefault(kunci, []).append(v)
    if not diam:
        if dibuang:
            info("  %d berkas dilewati - di luar %d folder brand"
                 % (dibuang, len(FOLDER_BRAND)))
        if revisi:
            info("  %d berkas folder brand dilewati - namanya juga ada di "
                 "Return, berarti belum lolos kurasi" % revisi)
    return peta


def kode_saja(nama):
    """Buang judulnya, sisakan kodenya.

    Tim kadang salah tulis JUDUL di sheet - tertulis
    'eduraya-tu19-n219-serah-terima-buku' padahal berkasnya
    'eduraya-tu19-n219-serah-terima'. Yang tidak pernah salah kodenya.

    Aturannya: ambil semua ruas sampai ruas TERAKHIR yang mengandung angka.
    """
    ruas = re.sub(r"\.mp4$", "", nama or "", flags=re.I).split("-")
    akhir = -1
    for i, r in enumerate(ruas):
        if any(c.isdigit() for c in r):
            akhir = i
    return rapi("-".join(ruas[:akhir + 1])) if akhir >= 0 else None


def cocokkan(peta, kode):
    """Entri Drive untuk satu kode konten. None kalau tidak jelas."""
    kena = peta.get(rapi(re.sub(r"\.mp4$", "", kode)), [])
    if not kena:
        awalan = kode_saja(kode)
        if awalan:
            calon = []
            for k, vs in peta.items():
                if k.startswith(awalan):
                    calon += vs
            # Kalau kodenya menunjuk ke dua JUDUL berbeda, itu bukan typo -
            # itu dua konten. Berhenti, jangan ditebak.
            judul = {rapi(re.sub(r"\.mp4$", "", v["nama"], flags=re.I))
                     for v in calon}
            if len(judul) > 1:
                info("     kode %s menunjuk ke %d judul berbeda - tidak "
                     "ditebak, betulkan dulu di sheet." % (awalan, len(judul)))
                return None
            if calon:
                info("     judul di sheet beda, dicocokkan lewat kode %s" % awalan)
                kena = calon
    if not kena:
        return None
    # Yang paling baru menang kalau namanya kembar di beberapa folder.
    return sorted(kena, key=lambda v: v.get("id", ""))[-1]


# ----------------------------------------------------------------- Chrome

def argumen_jendela():
    """Argumen peluncuran Chrome. LACON_WA_SEMBUNYI=1 menyembunyikan jendela.

    BUKAN headless. Mode headless justru lebih gampang dikenali halaman web,
    dan di permukaan seperti WhatsApp harganya mahal. Yang dipakai Chrome
    biasa, cuma jendelanya diturunkan ke taskbar - lihat kecilkan_jendela().
    Ini bukan penyamaran: tidak ada sidik jari yang dipalsukan.

    Dua flag anti-tidur wajib ikut waktu disembunyikan. Chrome menidurkan
    halaman yang dianggap tidak terlihat - timer diperlambat, render
    dihentikan - dan kalau itu terjadi, unggahan media menggantung tanpa
    pesan apa pun.
    """
    if os.environ.get("LACON_WA_SEMBUNYI", "").strip() not in ("", "0"):
        return ["--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=Translate"]
    return ["--start-maximized", "--disable-features=Translate"]


def kecilkan_jendela(ktx, hal):
    """Turunkan jendela ke taskbar lewat CDP.

    Flag --window-position TIDAK bekerja: Chrome memulihkan posisi jendela
    terakhir dari profilnya dan itu menang atas flag baris perintah. Flag
    cuma MENAWARKAN posisi awal; yang memerintah jendela yang sudah jadi
    itu DevTools Protocol.
    """
    if os.environ.get("LACON_WA_SEMBUNYI", "").strip() in ("", "0"):
        return
    try:
        cdp = ktx.new_cdp_session(hal)
        w = cdp.send("Browser.getWindowForTarget")
        cdp.send("Browser.setWindowBounds",
                 {"windowId": w["windowId"], "bounds": {"windowState": "minimized"}})
        info("  jendela diperkecil (LACON_WA_SEMBUNYI)")
    except Exception as e:
        info("  jendela tidak bisa diperkecil: %s" % str(e)[:80])


def profil_brand(brand):
    """SATU BRAND SATU FOLDER PROFIL.

    Sesi WhatsApp disimpan di IndexedDB milik alamat web.whatsapp.com, jadi
    dua TAB di satu profil membuka nomor yang SAMA. Yang memisahkan nomor
    itu folder profilnya.
    """
    return os.path.join(PROFIL_AKAR, "wa-" + (brand or "").lower())
