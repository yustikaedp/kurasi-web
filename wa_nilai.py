# -*- coding: utf-8 -*-
"""Penilaian otomatis hasil kurasi: tiap contact sheet dibaca Claude (lewat
Claude Code CLI, 'claude -p', memakai langganan yang sudah login - tanpa API
key terpisah), lalu temuannya ditulis ke laporan teks berformat:

    <nama video> > kata "a" bisa diganti "b"; kata "c" bisa dihapus saja

Yang dinilai (permintaan user 17 Oktober 2026 - bukan cuma visual, dan
HANYA yang fatal/urgent; hal minor/selera dilewati):
  - KATA: kata/kalimat di layar yang ambigu, terlalu kaku/jarang dipakai,
    tidak nyambung, salah tulis, istilah yang tak dipahami awam, atau klaim
    tambahan yang tak perlu -> saran ganti / hapus.
  - VISUAL: teks terpotong / nabrak / tak terbaca, komponen tidak jelas, dan
    gambar yang tidak sesuai dengan teksnya.
  - INFO (permintaan user 19 Oktober 2026): kebenaran informasi yang
    disampaikan - teks di layar DAN narasi suara (ditranskrip lokal lewat
    filter whisper ffmpeg, lihat transkrip()). Fakta/aturan salah, klaim
    berlebihan, isi yang saling bertentangan. Claude boleh WebSearch kalau ragu.
Durasi & ukuran tetap TIDAK dinilai.

    python wa.py nilai <folder hasil di kurasi/>
"""
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor

import wa_inti as inti

MODEL = os.environ.get("KURASI_MODEL", "sonnet")
PARALEL = 3          # panggilan Claude bersamaan - dijaga kecil supaya RAM aman
BATAS_DETIK = 300

PROMPT = """Kamu kurator konten video promosi pendek (Bahasa Indonesia) untuk calon customer awam.
Baca a.jpg lalu b.jpg dengan tool Read. Keduanya {n} frame video "{label}" berurutan
(kiri-atas ke kanan-bawah; {susunan}).

NARASI suara video (transkrip otomatis - bisa ada salah dengar/salah eja, mis. "nun sehu" untuk
"nuwun sewu"; JANGAN menilai ejaan transkrip, nilai ISINYA):
<narasi>{narasi}</narasi>

Tandai HANYA yang FATAL/URGENT: yang pasti membuat customer salah paham, salah menangkap pesan,
atau mendapat info yang salah. Hal minor (kata kurang pas, bisa lebih enak, selera, gaya) DILEWATI.
Sebagian besar video seharusnya bersih - jangan mencari-cari kesalahan. Maksimal 3 temuan per video.

1. KATA (teks di layar) - hanya yang fatal; ganti dengan kata sehari-hari yang sama pendeknya.
   UJI WAJIB tiap kata/kalimat: "Kalau customer awam membaca ini, apakah dia tetap paham maksudnya?"
   Kalau YA (walau kata itu kurang pas, kaku, atau bisa lebih bagus) -> JANGAN dimasukkan.
   Hanya masukkan kalau jawabannya TIDAK, atau customer akan menangkap maksud yang salah:
   - kata yang bisa ditafsirkan berlawanan / menyesatkan sehingga pesan inti video jadi salah tangkap
     (contoh: "diundi" padahal maksudnya "dipilih acak");
   - kalimat inti yang tidak bisa dipahami awam sama sekali / tidak nyambung dengan topik video;
   - salah ketik yang mengubah makna;
   - klaim yang tak bisa dipertanggungjawabkan -> hapus (contoh: "sejak 2016", "dan ada garansi kepuasan").
   JANGAN tandai: kata yang cuma kurang pas tapi maknanya masih tertangkap, istilah yang sudah dijelaskan
   lewat gambar/konteks (mis. "lebur", "dengung", "harakat"), gaya santai/gaul ("nggak", "udah", "diliat",
   "kelewat", "ketuker", "ngira", "ngulang", "mantul") - jangan membakukan kata santai, atau penggalan kalimat
   yang dilanjutkan di frame berikutnya.
2. VISUAL - hanya yang fatal:
   - teks jelas terpotong tepi layar / bertumpuk dengan teks lain sampai susah dibaca (bukan sekadar sedang beranimasi);
   - label/teks yang tidak cocok dengan gambarnya (mis. huruf A diberi label huruf B);
   - footage/gambar yang bertentangan dengan teksnya.
   JANGAN tandai: frame kosong/setengah muncul karena transisi, kartu penutup/pertanyaan tanpa header atau logo
   (itu desain yang disengaja), posisi elemen agak geser, bentuk ikon, selera foto, atau patah baris.

3. INFO - apakah informasi yang disampaikan (teks layar + narasi) BENAR. Hanya yang fatal:
   - fakta / aturan / pengertian yang salah (mis. hukum tajwid keliru, nama/jumlah huruf salah, arti kata
     atau tata krama daerah yang dijelaskan keliru, angka/tanggal/harga salah);
   - klaim yang berlebihan atau tak bisa dibuktikan (hasil dijamin pasti, "satu-satunya", "terbukti",
     statistik tanpa sumber);
   - isi yang saling bertentangan di dalam video, atau narasi yang bertentangan dengan teks layar.
   Pakai pengetahuanmu. Kalau ragu soal fakta yang bisa dicek, boleh WebSearch (maksimal 2 kali).
   Kalau tetap tidak yakin, JANGAN tandai. JANGAN tandai: ajakan/opini wajar khas promosi ("seru", "mudah"),
   penyederhanaan untuk awam yang tidak sampai salah, salah dengar transkrip, atau info tentang brand/layanan
   sendiri yang tak bisa kamu periksa.

Tulis ringkas. Balas HANYA satu objek JSON, tanpa teks lain:
{{"kata": [{{"dari": "kata persis di layar", "ke": "pengganti singkat, atau \\"\\" kalau sebaiknya dihapus"}}],
  "visual": ["frame N: uraian maksimal 15 kata"],
  "info": [{{"klaim": "isi yang keliru, singkat", "koreksi": "yang benar / kenapa keliru, maksimal 20 kata"}}]}}
Kalau video bersih: {{"kata": [], "visual": [], "info": []}}. Jangan mengarang; kalau ragu, jangan ditandai."""


WHISPER = os.environ.get("KURASI_WHISPER") or os.path.join(
    inti.AKAR, "model", "ggml-small-q5_1.bin")


def _jalur_filter(p):
    """Jalur Windows untuk opsi filter ffmpeg: 'C\\:/a/b' dalam kutip."""
    return "'%s'" % os.path.abspath(p).replace("\\", "/").replace(":", "\\:")


def transkrip(video_path):
    """Suara narasi video -> teks, lewat filter whisper bawaan ffmpeg
    (whisper.cpp, jalan lokal di CPU). '' kalau model tak ada / tanpa suara."""
    if not os.path.isfile(WHISPER):
        return ""
    kerja = tempfile.mkdtemp(prefix="narasi_")
    keluar = os.path.join(kerja, "narasi.txt")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-nostats", "-i", video_path, "-vn", "-af",
             "whisper=model=%s:language=id:queue=20:destination=%s:format=text"
             % (_jalur_filter(WHISPER), _jalur_filter(keluar)),
             "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=BATAS_DETIK)
        if not os.path.isfile(keluar):
            return ""
        with open(keluar, encoding="utf-8", errors="replace") as f:
            return " ".join(f.read().split())
    except Exception:
        return ""
    finally:
        shutil.rmtree(kerja, ignore_errors=True)


def _claude():
    exe = shutil.which("claude")
    if not exe:
        inti.gagal("Claude Code CLI ('claude') tidak ada di PATH - dibutuhkan "
                   "untuk penilaian otomatis.")
    return exe


def _belah(sheet, folder):
    """Sheet -> a.jpg (separuh baris atas) dan b.jpg (sisanya) supaya teks
    kecil tetap terbaca jelas. Tata letak ditebak dari nisbah gambar (sel 9:16):
    3x4 (12 frame, sekarang) atau 2x3 (6 frame, hasil kurasi lama).
    Kembalikan (jumlah frame, uraian susunan) untuk prompt."""
    from PIL import Image
    im = Image.open(sheet).convert("RGB")
    w, h = im.size
    kol, bar = min(((3, 4), (2, 3)),
                   key=lambda t: abs(w / float(h) - t[0] * 9.0 / (t[1] * 16.0)))
    atas = (bar + 1) // 2
    potong = h * atas // bar
    im.crop((0, 0, w, potong)).save(os.path.join(folder, "a.jpg"), quality=88)
    im.crop((0, potong, w, h)).save(os.path.join(folder, "b.jpg"), quality=88)
    n, na = kol * bar, kol * atas
    susunan = ("tiap gambar %d kolom; a.jpg = frame 1-%d (%d baris), "
               "b.jpg = frame %d-%d (%d baris)"
               % (kol, na, atas, na + 1, n, bar - atas))
    return n, susunan


def _json(teks):
    m = re.search(r"\{.*\}", teks or "", re.S)
    if not m:
        raise ValueError("balasan tanpa JSON")
    d = json.loads(m.group(0))
    kata = [k for k in d.get("kata", []) if isinstance(k, dict) and k.get("dari")]
    visual = [str(v) for v in d.get("visual", []) if v]
    info = [i for i in d.get("info", []) if isinstance(i, dict) and i.get("klaim")]
    return {"kata": kata, "visual": visual, "info": info}


def nilai_video(exe, sheet, label, narasi=""):
    """Satu video -> {'kata': [...], 'visual': [...], 'info': [...]} atau
    {'galat': str}. narasi: transkrip suara video ('' kalau tak ada)."""
    kerja = tempfile.mkdtemp(prefix="nilai_")
    try:
        n, susunan = _belah(sheet, kerja)
        prompt = PROMPT.format(
            label=label, n=n, susunan=susunan,
            narasi=(narasi or "(tidak ada narasi / tidak ditranskrip)")[:4000])
        galat = ""
        for _ in range(2):                       # satu kali coba ulang
            try:
                p = subprocess.run(
                    [exe, "-p", prompt, "--model", MODEL,
                     "--allowedTools", "Read,WebSearch", "--output-format", "json"],
                    cwd=kerja, capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=BATAS_DETIK)
                out = json.loads(p.stdout)
                return _json(out.get("result", ""))
            except Exception as e:
                galat = str(e)[:100]
        return {"galat": galat}
    finally:
        shutil.rmtree(kerja, ignore_errors=True)


def judul(label):
    """'sub/Les X - 01 - Judul.mp4' -> 'Les X - 01 - Judul'."""
    nama = label.replace("\\", "/").split("/")[-1]
    return re.sub(r"\.(mp4|mov|m4v)$", "", nama, flags=re.I).strip()


def baris(label, h):
    bag = []
    for k in h.get("kata", []):
        ke = (k.get("ke") or "").strip()
        if ke:
            bag.append('kata "%s" bisa diganti "%s"' % (k["dari"].strip(), ke))
        else:
            bag.append('kata "%s" bisa dihapus saja' % k["dari"].strip())
    for v in h.get("visual", []):
        bag.append("visual: %s" % v.strip())
    for i in h.get("info", []):
        kor = (i.get("koreksi") or "").strip()
        bag.append('info "%s" keliru%s' % (i["klaim"].strip(), (" - " + kor) if kor else ""))
    if h.get("galat"):
        bag.append("BELUM DINILAI (%s) - cek manual" % h["galat"])
    return "%s > %s" % (judul(label), "; ".join(bag)) if bag else None


def nilai_banyak(items, nama, keluar, narasi=None):
    """items: list (label, jalur_sheet); narasi: list transkrip sejajar items
    (boleh None). Tulis laporan teks, kembalikan jalurnya."""
    exe = _claude()
    narasi = narasi or [""] * len(items)
    inti.info("\nPenilaian otomatis kata, visual & info (Claude %s), %d video..."
              % (MODEL, len(items)))
    hasil = [None] * len(items)

    def kerja(i):
        label, sheet = items[i]
        hasil[i] = nilai_video(exe, sheet, label, narasi[i])
        h = hasil[i]
        status = ("galat" if h.get("galat") else
                  "%d kata, %d visual, %d info"
                  % (len(h["kata"]), len(h["visual"]), len(h["info"])))
        inti.info("  nilai %02d/%d  %s  (%s)" % (i + 1, len(items), judul(label), status))

    with ThreadPoolExecutor(PARALEL) as ex:
        list(ex.map(kerja, range(len(items))))

    temuan = [b for b in (baris(l, h) for (l, _), h in zip(items, hasil)) if b]
    aman = len(items) - len(temuan)
    with open(keluar, "w", encoding="utf-8") as f:
        f.write("Kurasi kata, visual & info - %s\n" % nama)
        f.write("%d video dinilai, %d perlu perbaikan, %d aman.\n\n"
                % (len(items), len(temuan), aman))
        f.write("\n".join(temuan) + ("\n" if temuan else ""))
    inti.catat("nilai %s: %d video, %d perlu perbaikan -> %s"
               % (nama, len(items), len(temuan), keluar))
    inti.info("\n%d dari %d video perlu perbaikan." % (len(temuan), len(items)))
    inti.info("Laporan kurasi: %s" % keluar)
    return keluar


def jalur_laporan(folder):
    return os.path.join(folder, "kurasi-kata-%s.txt" % os.path.basename(folder))


def jalur_narasi(folder):
    return os.path.join(folder, "narasi-%s.txt" % os.path.basename(folder))


def simpan_narasi(keluar, items, narasi):
    """Transkrip disimpan supaya 'nilai ulang' tetap bisa menilai narasi
    tanpa mengunduh videonya lagi."""
    with open(keluar, "w", encoding="utf-8") as f:
        for (label, _), t in zip(items, narasi):
            f.write("=== %s ===\n%s\n\n" % (judul(label), t or "(tanpa narasi)"))


def baca_narasi(path, items):
    """Kebalikan simpan_narasi -> list sejajar items. Dicocokkan lewat
    urutan kalau jumlahnya sama, kalau tidak lewat judul."""
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        bag = re.findall(r"^=== (.*?) ===\n(.*?)(?=\n\n=== |\Z)", f.read(),
                         re.S | re.M)
    teks = [("" if t.strip() == "(tanpa narasi)" else t.strip()) for _, t in bag]
    if len(bag) == len(items):
        return teks
    per_judul = dict(zip((j for j, _ in bag), teks))
    return [per_judul.get(judul(l), "") for l, _ in items]


def cmd_nilai(folder_arg):
    """Nilai ulang hasil kurasi yang sudah ada (dari review-*.pdf-nya), tanpa
    mengunduh ulang dari Drive."""
    import pymupdf
    folder = folder_arg
    if not os.path.isdir(folder):
        folder = os.path.join(inti.KURASI, folder_arg)
    # Utamakan review-*.pdf (nama baku); hasil lama bernama lain tetap dipakai.
    # Di tiap kelompok, yang terbaru dulu.
    pdfs = sorted((f for f in os.listdir(folder) if f.lower().endswith(".pdf")),
                  key=lambda f: (not f.startswith("review-"),
                                 -os.path.getmtime(os.path.join(folder, f)))
                  ) if os.path.isdir(folder) else []
    if not pdfs:
        inti.gagal("Tidak ada PDF tinjauan di %s - jalankan kurasi dulu." % folder)
    doc = pymupdf.open(os.path.join(folder, pdfs[0]))
    kerja = tempfile.mkdtemp(prefix="nilaipdf_")
    items = []
    try:
        for i in range(1, len(doc)):             # halaman 0 = sampul
            hal = doc[i]
            imgs = hal.get_images()
            if not imgs:
                continue
            # judul panjang terbungkus jadi 2 baris di PDF -> satukan lagi
            label = re.sub(r"^\d+\.\s*", "", " ".join(hal.get_text().split()))
            d = doc.extract_image(imgs[0][0])
            p = os.path.join(kerja, "%03d.%s" % (i, d["ext"]))
            with open(p, "wb") as f:
                f.write(d["image"])
            items.append((label, p))
        doc.close()
        inti.info("Folder: %s (%d video dari %s)" % (folder, len(items), pdfs[0]))
        narasi = baca_narasi(jalur_narasi(folder), items)
        if narasi is None:
            inti.info("Narasi suara belum ada untuk hasil ini - yang dinilai cuma "
                      "teks di layar. Kurasi ulang dari Drive untuk ikut menilai narasi.")
        nilai_banyak(items, os.path.basename(folder), jalur_laporan(folder), narasi)
    finally:
        shutil.rmtree(kerja, ignore_errors=True)
