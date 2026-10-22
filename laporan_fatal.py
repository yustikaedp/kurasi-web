# -*- coding: utf-8 -*-
"""Laporan kurasi visual FATAL-ONLY, SERAGAM untuk brand yang berbagi template.

Edubisa, Edumoka, Eduraya memakai template video yang SAMA (48 topik identik,
beda nama/warna/logo). Maka cacatnya level TEMPLATE - muncul persis sama di
ketiga brand - dan hasil kurasinya dibuat sama rata. Keputusan user 17 Okt 2026:
laporkan HANYA yang fatal/urgent (yang pasti disadari penonton); minor dilewati.

Frame tiap video bermasalah diambil langsung dari review-<brand>.pdf (pymupdf),
ke folder sementara, lalu DIHAPUS - tidak ada jpg longgar. Durasi & ukuran
tidak dinilai.

Jalankan: python laporan_fatal.py
"""
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
import pymupdf

import wa_inti as inti
import wa_kurasi as kurasi

TGL = "17 Oktober 2026"
BRANDS = ["edubisa", "edumoka", "eduraya"]

# Cacat LEVEL TEMPLATE - sama di semua brand. (nomor = nomor video = halaman PDF)
FATAL = [
    (7, "#07 CPNS  -  TEKS NABRAK",
     "Judul besar 'PENGAJAR YANG BERPENGALAMAN' terpotong di tepi kiri dan "
     "menimpa rumus papan tulis; teks 'LENGKAP BERKUALITAS' menindih tubuh "
     "pengajar; ikon kartun (orang + koin) nyelip di atas footage asli. "
     "Terlihat jelas berantakan - penonton pasti sadar."),
    (11, "#11 Copywriting  -  TEKS NABRAK",
     "Kata besar ter-mirror/terbalik ('...WRITING / INFOR') ketimpa paragraf "
     "teks dummy (placeholder) transparan yang membanjiri frame dan menindih "
     "subjek - terkesan belum jadi. Teks placeholder tayang = langsung ketahuan."),
    (20, "#20 Menggambar  -  TEKS NABRAK",
     "Headline 'TIDAK ADA Yang Tercipta Menjadi Ahli Dalam Semalam' ke-wash-out "
     "(teks pudar di latar putih terang) dan bertabrakan dengan caption - pesan "
     "inti nyaris tak terbaca."),
]

RINGKAS = [
    "Edubisa, Edumoka, dan Eduraya memakai TEMPLATE video yang sama - 48 topik "
    "identik, beda nama/warna/logo brand saja.",
    "Karena itu cacatnya level TEMPLATE: muncul PERSIS SAMA di ketiga brand. "
    "Satu laporan ini berlaku untuk KETIGANYA.",
    "",
    "Saringan: HANYA yang fatal/urgent - yang pasti disadari penonton. Hal minor "
    "(kontras tipis, overlay statistik, selera, konsistensi gaya kartun/CTA) "
    "sengaja TIDAK dilaporkan. Durasi & ukuran juga tidak dinilai.",
    "",
    "3 video WAJIB diperbaiki di ketiga brand: #07 CPNS, #11 Copywriting, "
    "#20 Menggambar. 45 video lainnya aman untuk tayang.",
    "",
    "Contoh frame di bawah diambil dari Eduraya; tampilannya sama persis di "
    "Edubisa dan Edumoka (sudah dicek silang).",
]

# Brand sumber frame contoh (ketiga halaman ter-ekstrak bersih di sini).
SUMBER = "eduraya"


def ambil(doc, nomor, tmp):
    imgs = doc[nomor].get_images()
    if not imgs:
        return None
    d = doc.extract_image(imgs[0][0])
    p = os.path.join(tmp, "%02d.%s" % (nomor, d["ext"]))
    with open(p, "wb") as f:
        f.write(d["image"])
    return p


def main():
    review = os.path.join(inti.KURASI, SUMBER, "review-%s.pdf" % SUMBER)
    if not os.path.isfile(review):
        inti.gagal("review-%s.pdf belum ada - jalankan kurasi %s dulu." % (SUMBER, SUMBER))
    doc = pymupdf.open(review)
    out = os.path.join(inti.KURASI, "tiga-brand")
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="lapfatal_")
    try:
        temuan = [{"video": judul, "tingkat": "nabrak", "catatan": cat,
                   "sheet": ambil(doc, nomor, tmp)}
                  for nomor, judul, cat in FATAL]
        lap = kurasi.laporan_pdf(
            "Hasil Kurasi Visual - Edubisa, Edumoka, Eduraya",
            "%s  |  lacon-wa  |  template sama, cacat identik  |  hanya "
            "fatal/urgent" % TGL,
            RINGKAS, temuan,
            os.path.join(out, "kurasi-tiga-brand-fatal.pdf"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    inti.info("OK  laporan gabungan 3 brand -> %s" % lap)


if __name__ == "__main__":
    main()
