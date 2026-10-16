# -*- coding: utf-8 -*-
"""Kurasi visual: unduh video dari satu folder Drive, ambil enam frame per
video jadi satu contact sheet, lalu susun semuanya ke PDF untuk ditinjau mata.

YANG DINILAI: komponen jelas dan teks nabrak - itu kerja mata, bukan angka.
DURASI DAN UKURAN SENGAJA TIDAK DIPERIKSA DI SINI. Keputusan user 16 Oktober
2026: "jangan kurasi durasi video sama sizenya, cukup cek visual". Batas
Status WhatsApp (30 detik / 16 MB) tetap dijaga di wa_status waktu kirim -
itu urusan terpisah, bukan urusan kurasi.

BAWAANNYA PRATINJAU. Tanpa --tulis cuma mendata videonya; tidak mengunduh,
tidak membuat berkas. Mengunduh itu read-only ke Drive, tapi tetap digerbang
--tulis supaya seragam dengan perintah lain.

FOLDER RETURN tidak disentuh. Alat ini hanya MEMBACA folder yang diberikan
dan menulis hasilnya ke ./kurasi lokal. Butuh ffmpeg/ffprobe di PATH.
"""
import io
import os
import re
import shutil
import subprocess
import tempfile

import wa_inti as inti

ULANG = 6          # frame per contact sheet
NISBAH = 0.375     # lebar:tinggi sheet (tile 2x3 dari video 9:16)


# ----------------------------------------------------------------- bantu

def _ada_ffmpeg():
    for alat in ("ffmpeg", "ffprobe"):
        try:
            subprocess.run([alat, "-version"], capture_output=True)
        except FileNotFoundError:
            inti.gagal("%s tidak ada di PATH. Pasang ffmpeg dulu - dipakai "
                       "untuk mengambil frame video." % alat)


def id_dari_link(s):
    """Terima link Drive atau id telanjang, kembalikan id folder."""
    s = (s or "").strip()
    m = re.search(r"/folders/([A-Za-z0-9_\-]+)", s)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([A-Za-z0-9_\-]+)", s)
    if m:
        return m.group(1)
    return s


def nama_aman(nama, jalur=""):
    base = re.sub(r"\.(mp4|mov|m4v)$", "", nama or "", flags=re.I)
    pre = "sub__" if (jalur or "").strip("/") else ""
    return pre + (inti.rapi(base) or "x")


def kumpulkan(drive, folder_id):
    """Semua video di folder (bertingkat), diurut jalur lalu nama."""
    antre, vids = [(folder_id, "")], []
    while antre:
        fid, jalur = antre.pop(0)
        hal = None
        while True:
            r = drive.files().list(
                q="'%s' in parents and trashed=false" % fid,
                fields="nextPageToken, files(id,name,mimeType)",
                pageSize=1000, pageToken=hal,
                supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
            for f in r.get("files", []):
                if f["mimeType"] == "application/vnd.google-apps.folder":
                    antre.append((f["id"], jalur + "/" + f["name"]))
                elif f["name"].lower().endswith((".mp4", ".mov", ".m4v")):
                    vids.append({"id": f["id"], "nama": f["name"], "jalur": jalur})
            hal = r.get("nextPageToken")
            if not hal:
                break
    return sorted(vids, key=lambda v: (v["jalur"], v["nama"]))


def _durasi(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def contact_sheet(video_path, keluar):
    """Enam frame merata -> satu gambar tile 2x3. Bukan pemeriksaan durasi:
    durasi cuma dipakai menebar jarak antar-frame."""
    d = _durasi(video_path) or 24.0
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path,
         "-vf", "fps=%f,scale=540:-1,tile=2x3" % (ULANG / d),
         "-frames:v", "1", "-q:v", "3", keluar],
        capture_output=True, text=True)


def _unduh(drive, fid, tujuan):
    from googleapiclient.http import MediaIoBaseDownload
    req = drive.files().get_media(fileId=fid, supportsAllDrives=True)
    with io.FileIO(tujuan, "wb") as fh:
        dl = MediaIoBaseDownload(fh, req, chunksize=8 * 1024 * 1024)
        selesai = False
        while not selesai:
            _, selesai = dl.next_chunk()


# ----------------------------------------------------------------- PDF

_GANTI = {"–": "-", "—": "-", "‘": "'", "’": "'",
          "“": '"', "”": '"', "•": "-", "·": "-",
          "…": "...", "→": "->", "×": "x"}


def _teks(s):
    """fpdf font inti cuma latin-1. Rapikan tanda baca pintar dulu."""
    s = s or ""
    for a, b in _GANTI.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def _para(pdf, h, s):
    """Satu paragraf multi-baris. set_x wajib: multi_cell fpdf2 memindah
    kursor ke kanan, dan lebar 0 dari tepi kanan = nol -> galat."""
    from fpdf.enums import XPos, YPos
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, h, _teks(s), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def review_pdf(judul, items, keluar):
    """Buku tinjauan: satu halaman satu video (sampul + contact sheet).

    items: list (label, jalur_sheet).
    """
    from fpdf import FPDF
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(False)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    _para(pdf, 10, judul)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    _para(pdf, 6,
        "%d video. Satu halaman satu video - enam frame, kiri-atas ke "
        "kanan-bawah. Tinjau: komponen jelas semua, dan tidak ada teks "
        "yang nabrak / terpotong / ketutupan." % len(items))

    for i, (label, sheet) in enumerate(items, 1):
        pdf.add_page()
        pdf.set_xy(10, 10)
        pdf.set_font("Helvetica", "B", 12)
        _para(pdf, 7, "%d. %s" % (i, label))
        if sheet and os.path.exists(sheet):
            y = pdf.get_y() + 2
            tinggi = 297 - y - 10
            lebar = tinggi * NISBAH
            pdf.image(sheet, x=(210 - lebar) / 2, y=y, w=lebar, h=tinggi)
    pdf.output(keluar)
    return keluar


def laporan_pdf(judul, subjudul, ringkas, temuan, keluar):
    """Laporan hasil kurasi (narasi + sheet yang bermasalah).

    temuan: list dict {video, tingkat, catatan, sheet?}.
       tingkat: 'nabrak' | 'sedang' | 'konsistensi' (mewarnai judul saja).
    """
    from fpdf import FPDF
    warna = {"nabrak": (190, 30, 30), "sedang": (200, 120, 0),
             "konsistensi": (60, 90, 160)}
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=12)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    _para(pdf, 9, judul)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90)
    _para(pdf, 6, subjudul)
    pdf.set_text_color(0)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    for baris in ringkas:
        _para(pdf, 6, baris or " ")

    for t in temuan:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*warna.get(t.get("tingkat"), (0, 0, 0)))
        _para(pdf, 7, t["video"])
        pdf.set_text_color(0)
        pdf.set_font("Helvetica", "", 11)
        _para(pdf, 6, t["catatan"])
        sheet = t.get("sheet")
        if sheet and os.path.exists(sheet):
            h = 110.0
            if pdf.get_y() + h > 285:
                pdf.add_page()
            w = h * NISBAH
            pdf.image(sheet, x=(210 - w) / 2, y=pdf.get_y() + 1, w=w, h=h)
            pdf.set_y(pdf.get_y() + h + 3)
    pdf.output(keluar)
    return keluar


# ----------------------------------------------------------------- perintah

def cmd_kurasi(folder_arg, tulis=False):
    """Siapkan bahan kurasi visual dari satu folder Drive.

    PRATINJAU dulu (tanpa --tulis): cuma mendata video. Dengan --tulis:
    unduh tiap video, buat contact sheet, lalu susun buku tinjauan PDF.
    """
    _ada_ffmpeg()
    drive = inti.layanan()[1]
    fid = id_dari_link(folder_arg)
    try:
        nama_folder = drive.files().get(
            fileId=fid, fields="name", supportsAllDrives=True).execute()["name"]
    except Exception as e:
        inti.gagal("Folder tidak terbaca: %s\n  Pastikan linknya benar dan akun "
                   "Google alat ini punya akses." % str(e)[:120])

    vids = kumpulkan(drive, fid)
    inti.info("Folder: %s" % nama_folder)
    inti.info("%d video ditemukan" % len(vids))
    for v in vids:
        pre = (v["jalur"].strip("/") + "/") if v["jalur"].strip("/") else ""
        inti.info("  %s%s" % (pre, v["nama"]))
    if not vids:
        inti.gagal("Tidak ada video (.mp4/.mov/.m4v) di folder itu.")

    if not tulis:
        inti.info("\nPRATINJAU. Belum ada yang diunduh. Tambahkan --tulis untuk "
                  "mengunduh, membuat contact sheet, dan menyusun PDF tinjauan.")
        return None

    tujuan = os.path.join(inti.KURASI, inti.rapi(nama_folder) or "folder")
    os.makedirs(tujuan, exist_ok=True)
    pdf = os.path.join(tujuan, "review-%s.pdf" % (inti.rapi(nama_folder) or "folder"))

    # Video dan contact sheet CUMA sementara: dibuat di folder temp, di-embed
    # ke PDF, lalu dihapus. Yang tersisa di ./kurasi hanya PDF - permintaan
    # user 16 Oktober 2026 ("langsung jadi pdf, tanpa simpan jpg dan video").
    kerja = tempfile.mkdtemp(prefix="kurasi_")
    tmp = os.path.join(kerja, "_tmp.mp4")
    items = []
    inti.info("")
    try:
        for i, v in enumerate(vids, 1):
            pre = (v["jalur"].strip("/") + "/") if v["jalur"].strip("/") else ""
            label = pre + v["nama"]
            sheet = os.path.join(kerja, "%03d-%s.jpg" % (i, nama_aman(v["nama"], v["jalur"])))
            try:
                _unduh(drive, v["id"], tmp)
                contact_sheet(tmp, sheet)
                items.append((label, sheet))
                inti.info("  %02d/%d  %s" % (i, len(vids), label))
            except Exception as e:
                inti.info("  %02d/%d  GAGAL %s : %s" % (i, len(vids), label, str(e)[:70]))
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
        review_pdf("Kurasi visual - %s" % nama_folder, items, pdf)
    finally:
        shutil.rmtree(kerja, ignore_errors=True)   # tak menyisakan jpg/video

    inti.catat("kurasi %s: %d video -> %s" % (nama_folder, len(items), pdf))
    inti.info("\nSelesai. %d video langsung jadi PDF (jpg & video tidak disimpan)." % len(items))
    inti.info("Buku tinjauan PDF: %s" % pdf)
    inti.info("Folder hasil: %s" % tujuan)
    return tujuan, pdf
