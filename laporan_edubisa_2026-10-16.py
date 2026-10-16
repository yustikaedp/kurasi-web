# -*- coding: utf-8 -*-
"""Susun PDF hasil kurasi visual Edubisa, 16 Oktober 2026.

Temuan diambil dari pemeriksaan frame (contact sheet) tiap video. Untuk 6
video bertanda, frame-nya dicek ulang rapat + resolusi tinggi (folder verif).
Durasi & ukuran TIDAK dinilai - permintaan user hari itu.

Jalankan ulang: python laporan_edubisa_2026-10-16.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
import wa_inti as inti
import wa_kurasi as kurasi

FR = os.path.join(inti.AKAR, "kurasi_frames")
VR = os.path.join(FR, "verif")
OUT = os.path.join(inti.KURASI, "edubisa")
os.makedirs(OUT, exist_ok=True)


def main():
    ringkas = [
        "Folder: Edubisa (link Drive) - 48 video utama + 7 video uji suara.",
        "Yang dinilai: komponen jelas semua, dan teks nabrak/terpotong/ketutupan.",
        "Durasi & ukuran TIDAK dinilai (permintaan user 16 Okt 2026).",
        "",
        "Ringkas: 3 video teks nabrak/tidak terbaca, 3 video kontras lemah,",
        "3 catatan konsistensi. 44 video sisanya bersih secara visual & teks.",
        "Subfolder _uji suara cewek: pemilihan suara harus didengar manusia -",
        "di luar jangkauan kurasi visual ini.",
    ]

    temuan = [
        {"video": "#07 CPNS  -  TEKS NABRAK", "tingkat": "nabrak",
         "sheet": os.path.join(VR, "edubisa07cpns.jpg"),
         "catatan":
            "Paling banyak masalah. (1) Judul besar 'PENGAJAR YANG "
            "BERPENGALAMAN' terpotong di tepi kiri, menimpa rumus papan tulis, "
            "dan sebagian ketutupan HP di tripod. (2) Teks 'LENGKAP "
            "BERKUALITAS' menimpa badan pengajar. (3) Pertanyaan 'Bagaimana "
            "cara hidup stabil dan sejahtera?' kontras rendah di footage gelap. "
            "(4) Ikon kartun (orang + koin) nyelip di atas footage asli - gaya "
            "tidak nyambung."},
        {"video": "#11 Copywriting  -  TEKS NABRAK", "tingkat": "nabrak",
         "sheet": os.path.join(VR, "edubisa11copywriting.jpg"),
         "catatan":
            "Kata besar terbalik/mirror '...WRITING / INFOR...' plus paragraf "
            "teks dummy transparan membanjiri frame dan menimpa subjek - "
            "berantakan, terkesan belum jadi. Transisi 'ECKOUT / Favorite / "
            "bintang' dengan teks terpotong & glitch."},
        {"video": "#20 Menggambar  -  TEKS NABRAK", "tingkat": "nabrak",
         "sheet": os.path.join(VR, "edubisa20menggambar.jpg"),
         "catatan":
            "Headline animasi 'TIDAK ADA Yang Tercipta Menjadi Ahli Dalam "
            "Semalam' ke-wash-out oleh latar putih terang - kata Yang/Dalam/"
            "Semalam nyaris tak terbaca, dan bertabrakan dengan caption 'Siapa "
            "pun bisa menggambar'."},
        {"video": "#02 Tahfidz  -  KONTRAS LEMAH", "tingkat": "sedang",
         "sheet": os.path.join(VR, "edubisa02tahfidz.jpg"),
         "catatan":
            "Daftar bernomor '1.. 2.. 3..' tulisannya kecil, tipis, kontras "
            "rendah di atas latar terang/bermotif - sulit dibaca."},
        {"video": "#09 BUMN  -  KONTRAS LEMAH", "tingkat": "sedang",
         "sheet": os.path.join(VR, "edubisa09bumn.jpg"),
         "catatan":
            "Caption putih di frame akhir ('Info persiapan tes BUMN' / 'ada di "
            "edubisa.com') nempel di atas sticky note kuning terang - kontras "
            "lemah."},
        {"video": "#12 Renang  -  KONTRAS LEMAH", "tingkat": "sedang",
         "sheet": os.path.join(VR, "edubisa12renang.jpg"),
         "catatan":
            "Grafik statistik (bar Stamina/Kebugaran + ring '86 Percaya diri') "
            "menumpuk; judul bar sempat ketutupan logo tengah dan buram - "
            "kurang terbaca."},
        {"video": "#01 Bahasa Arab  -  KONSISTENSI", "tingkat": "konsistensi",
         "sheet": os.path.join(FR, "edubisa01bahasaarab.jpg"),
         "catatan":
            "Judul teal 'Bahasa Arab Susah?' di tengah menduplikasi caption "
            "putih 'Bahasa Arab susah?' di frame yang sama (dua teks makna "
            "sama)."},
        {"video": "#13 Calistung & #18 Jarimatika  -  KONSISTENSI",
         "tingkat": "konsistensi",
         "sheet": os.path.join(FR, "edubisa13calistung.jpg"),
         "catatan":
            "Mencampur animasi kartun dengan footage live-action - gaya tidak "
            "konsisten antar scene (ikon kartun kecil juga muncul di #37 "
            "Jerman dan #07 CPNS)."},
        {"video": "Kartu CTA / logo: dua gaya  -  KONSISTENSI",
         "tingkat": "konsistensi",
         "sheet": os.path.join(FR, "edubisa19piano.jpg"),
         "catatan":
            "Sebagian video pakai badge/CTA besar (mis. #19 Piano, #22 Biola, "
            "#23 Drum), mayoritas badge kecil - tidak seragam. Sebaiknya "
            "disamakan satu gaya."},
    ]

    lap = kurasi.laporan_pdf(
        "Hasil Kurasi Visual - Edubisa",
        "16 Oktober 2026  |  lacon-wa  |  metode: contact sheet 6 frame, "
        "6 video bertanda dicek ulang rapat",
        ringkas, temuan,
        os.path.join(OUT, "kurasi-edubisa-2026-10-16.pdf"))
    inti.info("Laporan : %s" % lap)

    # Buku tinjauan semua video utama (dari sheet yang sudah ada).
    items = []
    for i in range(1, 49):
        for f in sorted(os.listdir(FR)):
            if f.lower().endswith(".jpg") and f.startswith("edubisa%02d" % i):
                items.append(("#%02d  %s" % (i, f[:-4]), os.path.join(FR, f)))
                break
    buku = kurasi.review_pdf("Buku Tinjauan - Edubisa (48 video utama)",
                             items, os.path.join(OUT, "review-edubisa.pdf"))
    inti.info("Buku    : %s (%d halaman video)" % (buku, len(items)))


if __name__ == "__main__":
    main()
