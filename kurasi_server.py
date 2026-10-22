# -*- coding: utf-8 -*-
"""Backend web untuk kurasi visual: menyajikan antarmuka React (web/dist) dan
API yang menjalankan perintah 'kurasi'. Tempel link folder Drive di halaman,
sisanya sama persis dengan 'python wa.py kurasi <link> --tulis'.

Yang membuatnya aman:
  - server HANYA mendengar di 127.0.0.1 - tidak terjangkau dari jaringan luar;
  - link divalidasi jadi id folder Drive (hanya [A-Za-z0-9_-]) sebelum dipakai,
    dan pipeline dipanggil sebagai DAFTAR argumen (shell=False) - tak ada celah
    injeksi perintah;
  - berkas hanya disajikan dari DALAM folder kurasi/ dan web/dist (cek
    realpath) - tidak bisa menembus ke berkas lain di disk.

    python kurasi_server.py
"""
import os
import re
import shutil
import subprocess
import sys
import threading
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from flask import Flask, abort, jsonify, request, send_file

import wa_inti as inti
import wa_kurasi as kurasi

DIST = os.path.join(inti.AKAR, "web", "dist")
PORT = 8733
app = Flask(__name__, static_folder=None)

JOBS = {}                                   # job_id -> dict
JOBS_KUNCI = threading.Lock()
SIMPAN_JOB = 10                             # job selesai yang disimpan
ID_OK = re.compile(r"^[A-Za-z0-9_\-]{10,}$")  # id folder Drive yang wajar
HOST_OK = {"127.0.0.1:%d" % PORT, "localhost:%d" % PORT}


@app.before_request
def cek_host():
    # Tolak Host asing: menutup celah DNS rebinding (situs lain yang namanya
    # diarahkan ke 127.0.0.1 lalu memanggil /api/hapus dari browser).
    if request.host not in HOST_OK:
        abort(403)


def _di_dalam(path, akar):
    a = os.path.realpath(akar)
    p = os.path.realpath(path)
    return p == a or p.startswith(a + os.sep)


def _jalankan(job_id, cmd):
    job = JOBS[job_id]
    cmd = [sys.executable, "-u", "wa.py"] + cmd
    try:
        proc = subprocess.Popen(
            cmd, cwd=inti.AKAR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1)
        for line in proc.stdout:
            line = line.rstrip("\n")
            job["baris"].append(line)
            m = re.search(r"Buku tinjauan PDF:\s*(.+)$", line)
            if m:
                job["pdf"] = m.group(1).strip()
            m = re.search(r"Folder hasil:\s*(.+)$", line)
            if m:
                job["folder"] = m.group(1).strip()
            m = re.search(r"Laporan kurasi:\s*(.+)$", line)
            if m:
                job["laporan"] = m.group(1).strip()
        proc.wait()
        job["kode"] = proc.returncode
    except Exception as e:
        job["baris"].append("Server galat: %s" % e)
        job["kode"] = -1
    finally:
        job["selesai"] = True


@app.post("/api/mulai")
def mulai():
    d = request.get_json(silent=True) or {}
    folder_id = kurasi.id_dari_link((d.get("link") or "").strip())
    if not ID_OK.match(folder_id or ""):
        return jsonify(pesan="Link tidak dikenali - pakai link folder Drive "
                             "(/folders/...) atau link video (/file/d/...)."), 400
    cmd = ["kurasi", folder_id]
    if not d.get("pratinjau"):
        cmd.append("--tulis")
        if d.get("nilai", True):
            cmd.append("--nilai")
    return _job_baru(cmd)


def _job_baru(cmd):
    """Mulai job - satu per satu saja: unduh + ffmpeg + Claude paralel itu
    berat, dua sekaligus bisa menghabiskan RAM."""
    with JOBS_KUNCI:
        if any(not j["selesai"] for j in JOBS.values()):
            return jsonify(pesan="Masih ada proses yang berjalan - tunggu "
                                 "sampai selesai."), 409
        # buang job selesai yang lama supaya memori tak terus bertambah
        for lama in list(JOBS)[:max(0, len(JOBS) - SIMPAN_JOB + 1)]:
            del JOBS[lama]
        job_id = uuid.uuid4().hex
        JOBS[job_id] = {"baris": [], "selesai": False, "kode": None,
                        "folder": None, "pdf": None, "laporan": None}
    threading.Thread(target=_jalankan, args=(job_id, cmd), daemon=True).start()
    return jsonify(job=job_id)


@app.post("/api/nilai")
def nilai():
    """Nilai ulang (kata & visual) satu folder hasil yang sudah ada di kurasi/."""
    d = request.get_json(silent=True) or {}
    path = (d.get("path") or "").strip()
    if (not path or not _di_dalam(path, inti.KURASI) or not os.path.isdir(path)
            or os.path.realpath(path) == os.path.realpath(inti.KURASI)):
        return jsonify(pesan="Folder hasil tidak dikenali."), 400
    return _job_baru(["nilai", os.path.realpath(path)])


@app.get("/api/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify(pesan="Job tidak ada."), 404
    return jsonify(baris=job["baris"], selesai=job["selesai"], kode=job["kode"],
                   folder=job["folder"], pdf=job["pdf"], laporan=job["laporan"])


@app.get("/api/hasil")
def hasil():
    """Daftar folder yang sudah dikurasi + PDF di dalamnya, terbaru dulu.
    Dipakai panel 'Hasil tersimpan'. Hanya membaca di dalam kurasi/."""
    daftar = []
    if os.path.isdir(inti.KURASI):
        for nama in os.listdir(inti.KURASI):
            fol = os.path.join(inti.KURASI, nama)
            if not os.path.isdir(fol) or not _di_dalam(fol, inti.KURASI):
                continue
            pdfs = []
            for berkas in os.listdir(fol):
                if berkas.lower().endswith((".pdf", ".txt")):
                    p = os.path.join(fol, berkas)
                    pdfs.append({"nama": berkas, "path": p,
                                 "mtime": os.path.getmtime(p)})
            if pdfs:
                pdfs.sort(key=lambda x: x["mtime"], reverse=True)
                daftar.append({"folder": nama, "path": fol, "pdf": pdfs,
                               "mtime": pdfs[0]["mtime"]})
    daftar.sort(key=lambda x: x["mtime"], reverse=True)
    return jsonify(hasil=daftar)


@app.post("/api/hapus")
def hapus():
    """Hapus satu berkas (PDF) atau satu folder hasil - HANYA di dalam kurasi/.
    Folder akar kurasi sendiri dilindungi."""
    d = request.get_json(silent=True) or {}
    path = (d.get("path") or "").strip()
    if not path or not _di_dalam(path, inti.KURASI):
        return jsonify(pesan="Jalur di luar folder kurasi - ditolak."), 400
    if os.path.realpath(path) == os.path.realpath(inti.KURASI):
        return jsonify(pesan="Folder akar kurasi tidak boleh dihapus."), 400
    if any(not j["selesai"] for j in JOBS.values()):
        return jsonify(pesan="Tunggu proses yang berjalan selesai dulu "
                             "sebelum menghapus."), 409
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            os.remove(path)
        else:
            return jsonify(pesan="Berkas/folder tidak ditemukan."), 404
    except Exception as e:
        return jsonify(pesan="Gagal menghapus: %s" % str(e)[:120]), 500
    return jsonify(ok=True)


@app.get("/api/berkas")
def berkas():
    path = request.args.get("path", "")
    if not path or not _di_dalam(path, inti.KURASI) or not os.path.isfile(path):
        abort(404)
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".pdf", ".jpg", ".jpeg", ".png", ".txt"):
        abort(403)
    if ext == ".txt":
        return send_file(path, mimetype="text/plain; charset=utf-8")
    return send_file(path)


@app.post("/api/buka")
def buka():
    d = request.get_json(silent=True) or {}
    path = (d.get("path") or "").strip()
    if path and _di_dalam(path, inti.KURASI) and os.path.isdir(path):
        try:
            os.startfile(path)              # Windows: buka di Explorer
        except Exception:
            pass
    return jsonify(ok=True)


# ----------------------------------------- frontend hasil build (web/dist)

@app.get("/")
def index():
    return send_file(os.path.join(DIST, "index.html"))


@app.get("/<path:nama>")
def statik(nama):
    calon = os.path.join(DIST, nama)
    if _di_dalam(calon, DIST) and os.path.isfile(calon):
        return send_file(calon)
    abort(404)


def main():
    if not os.path.isfile(os.path.join(DIST, "index.html")):
        inti.info("Frontend belum di-build. Jalankan sekali:")
        inti.info("    cd web && npm install && npm run build")
        sys.exit(1)
    import webbrowser
    url = "http://127.0.0.1:%d" % PORT
    inti.info("Kurasi Visual berjalan di %s" % url)
    inti.info("Tekan Ctrl+C untuk berhenti.")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    app.run(host="127.0.0.1", port=PORT, debug=False)


if __name__ == "__main__":
    main()
