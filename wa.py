# -*- coding: utf-8 -*-
"""lacon-wa - Status WhatsApp otomatis untuk Story Motion dan Daily Insight.

    python wa.py siap                          periksa kesiapan, tidak mengubah apa pun
    python wa.py indeks                        susun ulang indeks Drive
    python wa.py kurasi <folder/link> [--tulis] [--nilai]  contact sheet + PDF tinjauan
                                               (--nilai: + laporan kata & visual otomatis)
    python wa.py nilai <folder hasil>          nilai ulang hasil kurasi yang sudah ada
    python wa.py unduh <tgl> [--brand a,b] [--tulis]
    python wa.py login <brand>                 buka jendela untuk scan QR
    python wa.py akun <brand>                  BACA nama akunnya
    python wa.py status <brand> <berkas> [--teks "..."] [--tulis]
    python wa.py teks <brand> "<teks atau link>" [--tulis]
    python wa.py kirim <tgl> [--brand a,b] [--tulis]
    python wa.py slot <tgl> <jam> [--brand a,b] [--tulis]

Tanggal: 7/10/2026 atau 2026-10-07.   Jam: 12.00 atau 12:00.

JAM TAYANG TIDAK DITENTUKAN ALAT INI - tim CS yang menetapkan. Perintah
harian yang dipakai 'kirim'; 'slot' cuma berguna kalau kolom jam di sheet
memang sudah diisi.

BAWAANNYA PRATINJAU. Tanpa --tulis tidak ada yang diunduh dan tidak ada
Status yang terbit.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

import wa_inti as inti
import wa_konten as konten
import wa_kurasi as kurasi
import wa_status as status


def ambil(argv, nama, bawaan=None):
    return argv[argv.index(nama) + 1] if nama in argv else bawaan


def daftar_brand(teks):
    if not teks:
        return None
    nama = {b.strip().lower() for b in teks.split(",") if b.strip()}
    asing = nama - set(inti.AWALAN)
    if asing:
        inti.gagal("Brand tidak dikenal: %s" % ", ".join(sorted(asing)))
    return nama


def cmd_siap():
    """Periksa alat ini siap dipakai atau belum. Tidak mengubah apa pun.

    Dijalankan SEBELUM pemakaian pertama oleh tim baru. Empat hal yang harus
    DITANYAKAN ke tim, bukan ditebak - arahan user 7 Oktober 2026:

        1  login WhatsApp tiap brand        mereka yang scan QR
        2  jam tayangnya                    tim CS yang menetapkan
        3  link folder Drive berkasnya      belum tentu sama dengan punya kita
        4  link sheet jadwal kontennya      belum tentu sama dengan punya kita

    Nilai di config.json sekarang DIAMBIL DARI PROYEK LACON. Kalau tim
    memakai sheet atau folder yang lain, nilai itu salah dan harus diganti.
    """
    import datetime as dt
    cfg = inti.baca_config()
    kurang = []

    inti.info("=== 1. Sumber konten ===")
    sheets, drive = inti.layanan()
    sid = cfg.get("sheet_id")
    try:
        m = sheets.spreadsheets().get(
            spreadsheetId=sid, fields="properties/title,sheets/properties/title").execute()
        tabs = [s["properties"]["title"] for s in m["sheets"]]
        inti.info("  sheet  : %s" % m["properties"]["title"])
        inti.info("           %d tab: %s" % (len(tabs), ", ".join(tabs)))
    except Exception as e:
        inti.info("  sheet  : TIDAK BISA DIBACA - %s" % str(e)[:70])
        kurang.append("sheet_id di config.json - minta link sheetnya ke tim")

    fid = cfg.get("drive_folder_id")
    try:
        f = drive.files().get(fileId=fid, fields="name",
                              supportsAllDrives=True).execute()
        inti.info("  Drive  : %s" % f["name"])
    except Exception as e:
        inti.info("  Drive  : TIDAK BISA DIBACA - %s" % str(e)[:70])
        kurang.append("drive_folder_id di config.json - minta link foldernya ke tim")

    inti.info("\n=== 2. Indeks Drive ===")
    if os.path.isfile(inti.INDEKS):
        import json
        n = len(json.load(open(inti.INDEKS, encoding="utf-8")))
        umur = (dt.datetime.now()
                - dt.datetime.fromtimestamp(os.path.getmtime(inti.INDEKS))).days
        inti.info("  %d video, disusun %d hari lalu" % (n, umur))
        if umur > 7:
            inti.info("  SUDAH TUA. Indeks basi menyamar jadi 'konten tidak "
                      "ketemu' - susun ulang: python wa.py indeks")
    else:
        inti.info("  BELUM ADA - jalankan: python wa.py indeks")
        kurang.append("indeks Drive")

    inti.info("\n=== 3. Login WhatsApp per brand ===")
    nama = cfg.get("nama_akun") or {}
    belum = []
    for b in sorted(inti.AWALAN):
        p = inti.profil_brand(b)
        ada = os.path.isdir(p) and os.listdir(p)
        tanda = "profil ada" if ada else "BELUM LOGIN"
        inti.info("  %-10s %-12s %s" % (b, tanda, nama.get(b, "")))
        if not ada:
            belum.append(b)
    if belum:
        kurang.append("login %d brand: %s" % (len(belum), ", ".join(belum)))

    inti.info("\n=== 4. Jam tayang ===")
    inti.info("  TIDAK ditentukan alat ini. Tanya tim CS, lalu jalankan")
    inti.info("  'kirim' pada jam yang mereka tetapkan.")

    inti.info("\n=== Kesimpulan ===")
    if kurang:
        inti.info("BELUM SIAP. Yang kurang:")
        for k in kurang:
            inti.info("  - %s" % k)
    else:
        inti.info("Siap dipakai. Tetap jalankan 'akun <brand>' sekali untuk")
        inti.info("tiap brand dan BACA nama akunnya sebelum kirim pertama.")


def folder_hari(hari, argv):
    tujuan = os.path.join(inti.UNDUHAN, inti.nama_folder_tanggal(hari))
    if not os.path.isdir(tujuan):
        inti.gagal("Folder %s belum ada.\n  Unduh dulu: python wa.py unduh %s "
                   "--tulis" % (tujuan, argv[2]))
    return tujuan


def berkas_folder(tujuan, brand=None, jam=None):
    """Berkas siap kirim di folder, boleh disaring brand dan jam.

    Brandnya dibaca dari NAMA BERKAS, bukan dari urutan folder. Kalau
    brandnya tidak jelas, berkasnya dilewati dan disebut - jangan ditebak,
    karena salah tebak berarti video brand satu naik ke nomor brand lain.
    """
    pilih = []
    for n in sorted(os.listdir(tujuan)):
        if not n.lower().endswith((".mp4", ".mov", ".m4v")):
            continue
        if jam:
            ruas = [r.strip() for r in n.split(" - ")]
            if len(ruas) < 3 or konten.jam_rapi(ruas[1]) != jam:
                continue
        b = inti.brand_berkas(n)
        if not isinstance(b, str):
            inti.info("  LEWAT %s - brandnya tidak jelas (%s)" % (n, b))
            continue
        if brand and b not in brand:
            continue
        pilih.append((b, os.path.join(tujuan, n)))
    return pilih


def jalankan(pilih, tulis):
    """Kirim satu per satu, BERURUTAN.

    SATU PROFIL SEKALI JALAN. Jangan pernah menjalankan dua rantai
    berbarengan supaya lebih cepat - dua sesi otomasi dari satu komputer dan
    satu IP adalah pola yang paling gampang dibaca sebagai mesin, dan di sini
    taruhannya nomor WhatsApp beserta seluruh chat di dalamnya.
    """
    for b, j in pilih:
        inti.info("  %-10s %s" % (b, os.path.basename(j)))
    if not tulis:
        inti.info("\nPRATINJAU. Tambahkan --tulis untuk benar-benar memposting.")
        return
    for i, (b, j) in enumerate(pilih, 1):
        inti.info("\n=== %d/%d  %s ===" % (i, len(pilih), b))
        try:
            status.cmd_status(b, j, tulis=True)
        except SystemExit:
            # Satu brand gagal tidak boleh menghentikan sisanya, tapi HARUS
            # kelihatan. Jangan dilewati diam-diam.
            inti.info("  %s GAGAL - lihat pesan di atas, lanjut ke berikutnya" % b)
        if i < len(pilih):
            time.sleep(20)   # jangan beruntun


def cmd_kirim(argv):
    """Kirim konten satu tanggal, tanpa peduli jam.

    INI perintah harian yang sebenarnya. Jam tayang TIDAK ditentukan alat
    ini - keputusan user 7 Oktober 2026, tim CS yang menetapkan. Jadi
    perintah ini dijalankan waktu tim CS bilang kirim.
    """
    hari = inti.baca_tanggal_perintah(argv[2])
    tujuan = folder_hari(hari, argv)
    pilih = berkas_folder(tujuan, daftar_brand(ambil(argv, "--brand")))
    if not pilih:
        inti.gagal("Tidak ada berkas di %s" % tujuan)
    inti.info("%d konten, dikerjakan BERURUTAN\n" % len(pilih))
    jalankan(pilih, "--tulis" in argv)


def cmd_slot(argv):
    """Kirim konten pada satu jam saja.

    Cuma berguna kalau kolom jam di sheet memang sudah diisi. Selama tim CS
    belum menetapkan jamnya, pakai 'kirim'.
    """
    hari = inti.baca_tanggal_perintah(argv[2])
    jam = konten.jam_rapi(argv[3])
    if not jam:
        inti.gagal("Jam tidak terbaca: %r. Pakai 12.00 atau 12:00." % argv[3])
    tujuan = folder_hari(hari, argv)
    pilih = berkas_folder(tujuan, daftar_brand(ambil(argv, "--brand")), jam)
    if not pilih:
        inti.gagal("Tidak ada berkas berjam %s di %s.\n"
                   "  Kalau jamnya memang belum ditetapkan, pakai: "
                   "python wa.py kirim %s" % (jam, tujuan, argv[2]))
    inti.info("slot %s, %d konten, dikerjakan BERURUTAN\n" % (jam, len(pilih)))
    jalankan(pilih, "--tulis" in argv)


def main():
    a = sys.argv
    if len(a) < 2:
        print(__doc__)
        return
    p = a[1]
    if p == "siap":
        cmd_siap()
    elif p == "indeks":
        konten.susun_indeks()
    elif p == "kurasi" and len(a) > 2:
        kurasi.cmd_kurasi(a[2], "--tulis" in a, "--nilai" in a)
    elif p == "nilai" and len(a) > 2:
        import wa_nilai
        wa_nilai.cmd_nilai(a[2])
    elif p == "unduh" and len(a) > 2:
        konten.unduh(inti.baca_tanggal_perintah(a[2]),
                     daftar_brand(ambil(a, "--brand")), "--tulis" in a)
    elif p == "rencana" and len(a) > 2:
        konten.unduh(inti.baca_tanggal_perintah(a[2]),
                     daftar_brand(ambil(a, "--brand")), False)
    elif p == "login" and len(a) > 2:
        status.cmd_login(a[2])
    elif p == "akun" and len(a) > 2:
        status.cmd_akun(a[2])
    elif p == "status" and len(a) > 3:
        status.cmd_status(a[2], a[3], ambil(a, "--teks", ""), "--tulis" in a)
    elif p == "teks" and len(a) > 3:
        status.cmd_teks(a[2], a[3], "--tulis" in a)
    elif p == "kirim" and len(a) > 2:
        cmd_kirim(a)
    elif p == "slot" and len(a) > 3:
        cmd_slot(a)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
