# lacon-wa

Menayangkan video Story Motion dan Daily Insight sebagai **Status WhatsApp**,
otomatis, lewat WhatsApp Web.

Sumber kontennya sheet **Jadwal Up Konten** dan folder Drive
**creative-makers** - dua tempat yang sudah dipakai tim selama ini. Alat ini
membaca sheetnya, mengunduh berkasnya dari Drive, lalu memposting ke Status
nomor WhatsApp brand yang bersangkutan.

---

## Yang harus dipahami sebelum menyentuh apa pun

**1. Satu brand satu nomor, satu nomor satu folder profil Chrome.**
Sesi WhatsApp disimpan di penyimpanan browser milik alamat web.whatsapp.com.
Dua *tab* di satu profil membuka nomor yang **sama**. Yang memisahkan nomor
itu folder profilnya, bukan tabnya.

**2. WhatsApp tidak punya penjadwalan.** Tidak ada tombolnya, manual pun
sama. Yang ada cuma terbit sekarang, jadi perintah kirim dijalankan tepat
waktu kontennya mau tayang.

**2b. Jam tayang tidak ditentukan alat ini.** Kolom jam di sheet dibaca
sebagai keterangan saja, dan baris yang jamnya masih kosong tetap ikut
diunduh. **Tim CS yang menetapkan kapan tayangnya.**

**3. Risikonya nomor, bukan jadwal.** WhatsApp paling keras soal otomasi di
antara semua platform yang dipakai tim. Kalau sebuah nomor kena, yang hilang
nomor itu beserta seluruh chat di dalamnya. Yang biasanya ditindak adalah
pengiriman massal dan aplikasi tiruan - memposting Status sendiri bukan itu -
tapi risikonya tetap ada dan harus diketahui sebelum dipakai.

**4. Jangan pernah dua profil jalan bersamaan.** Dua sesi otomasi dari satu
komputer dan satu IP adalah pola yang paling gampang dibaca sebagai mesin.
Perintah `slot` sudah mengerjakan brand satu per satu - jangan diakali supaya
paralel demi cepat.

**5. Bawaannya pratinjau.** Tanpa `--tulis` tidak ada yang diunduh dan tidak
ada Status yang terbit. Itu disengaja. Jangan menambahkan `--tulis` hanya
karena ingin "mencoba".

---

## Pasang

Butuh Python 3.10 ke atas, dan `ffmpeg` kalau ingin durasi video diperiksa
atau memakai perintah `kurasi` (yang mengambil frame video).

    pip install playwright google-api-python-client google-auth-oauthlib fpdf2
    playwright install chromium

`fpdf2` cuma dipakai perintah `kurasi` untuk menyusun PDF. Kalau tidak dipakai,
boleh dilewati.

Chrome biasa harus terpasang - alat ini memakai Chrome, bukan Chromium bawaan
Playwright, supaya sesi WhatsApp-nya wajar.

### Kunci Google

Alat ini membaca satu sheet dan satu folder Drive, jadi perlu izin Google.

1. Google Cloud Console > Credentials > Create OAuth client ID > tipe
   **Desktop**
2. Unduh berkasnya, taruh di `.secrets/client_secret.json`
3. Jalankan perintah apa pun yang menyentuh Google, misalnya
   `python wa.py rencana 7/10/2026`. Browser terbuka minta izin sekali,
   lalu tokennya disimpan sendiri di `.secrets/token.json`.

Akun Google yang dipakai harus punya akses baca ke sheet Jadwal Up Konten dan
ke folder creative-makers.

`.secrets/` tidak pernah ikut repo - lihat `.gitignore`.

---

## Sekali di awal: login tiap brand

Kerjakan **satu brand pada satu waktu**. Jangan membuka beberapa jendela
sekaligus - semua halaman login WhatsApp tampilannya sama persis, jadi tidak
ada cara membedakan jendela mana milik siapa. Di proyek sebelahnya hal ini
sudah empat kali terjadi dan akibatnya konten brand satu tayang di akun brand
lain.

    python wa.py login edufio

Jendela Chrome terbuka. Di HP: WhatsApp > Perangkat tertaut > Tautkan
perangkat, lalu scan. Sesudah daftar chat muncul, **tutup jendelanya**.

Lalu buktikan nomornya benar:

    python wa.py akun edufio

Perintah ini membaca Nama bisnis dari panel Profil. Kalau yang muncul bukan
brand yang dimaksud, **tukar nama foldernya** di `.chrome/` - isi profilnya
tidak perlu disentuh.

Kalau nama akunnya memang tidak memuat nama brand (misalnya tertulis
"Akselera Tech" untuk brand edufio), daftarkan di `config.json`:

    "nama_akun": { "edufio": "Nama Persis Yang Terbaca" }

Selama belum didaftarkan, perintah `status` akan menolak jalan. Itu disengaja.

---

## Sehari-hari

### 1. Unduh kontennya

    python wa.py unduh 7/10/2026            lihat dulu
    python wa.py unduh 7/10/2026 --tulis    benar-benar unduh

Hasilnya di `unduhan/WA Story 7 Oktober 2026/`, nama berkasnya diawali nomor
urut, misalnya `07 - edufio-la-ak10-saringkelas.mp4`. Kalau kolom jam di
sheet kebetulan sudah diisi, jamnya ikut di nama berkas
(`07 - 12.00 - edufio-...`). Jangan mengganti nama berkasnya - brand dibaca
dari situ.

Baris yang **sudah ditandai tayang di kolom D sheet** otomatis dilewati, dan
disebut di layar. Itu penjaga anti-dobel milik tim sendiri.

### 2. Kirim, waktu tim CS bilang kirim

    python wa.py kirim 7/10/2026            lihat dulu
    python wa.py kirim 7/10/2026 --tulis    benar-benar posting

Satu brand saja:

    python wa.py kirim 7/10/2026 --brand edufio --tulis

Brand dikerjakan **berurutan**, berjeda 20 detik, satu profil sekali jalan.
Kalau satu brand gagal, sisanya tetap lanjut dan kegagalannya disebut di
layar - tidak dilewati diam-diam.

Kalau suatu saat tim menetapkan jam di sheet, ada juga:

    python wa.py slot 7/10/2026 12.00 --tulis

tapi itu cuma jalan untuk berkas yang jamnya sudah ada di namanya.

### Satu berkas saja

    python wa.py status edufio "unduhan/.../01 - 12.00 - edufio-....mp4" --tulis

Tambahkan `--teks "keterangan"` kalau Statusnya perlu caption.

---

## Kalau ada kode yang tidak ketemu di Drive

    python wa.py indeks

Menelusuri ulang seluruh folder Drive, sekitar lima menit. **Jalankan ini
dulu sebelum melapor bahwa sebuah konten tidak ada.** Indeks yang basi
menyamar jadi "stok habis", dan itu sudah pernah bikin laporan salah selama
seminggu.

---

## Kurasi visual sebuah folder

    python wa.py kurasi <link-folder-Drive>            lihat dulu
    python wa.py kurasi <link-folder-Drive> --tulis     unduh + buat PDF

Mengambil **enam frame per video** jadi satu *contact sheet*, lalu menyusun
semuanya ke satu **PDF tinjauan** - satu halaman satu video. Gunanya memeriksa
dengan mata: komponennya jelas semua, dan **tidak ada teks yang nabrak,
terpotong, atau ketutupan**. Linknya boleh link folder utuh atau id-nya saja.

Hasilnya di `kurasi/<nama-folder>/`: contact sheet tiap video plus
`review-<folder>.pdf`.

**Yang dinilai perintah ini cuma visual.** Durasi dan ukuran **sengaja tidak
diperiksa di sini** - keputusan user 16 Oktober 2026 ("cukup cek visual").
Batas 30 detik / 16 MB tetap dijaga `wa_status` waktu *kirim*; itu urusan
terpisah, bukan urusan kurasi.

Penilaiannya sendiri tetap kerja **mata** - alat ini cuma menyiapkan
bahannya. Butuh `ffmpeg` (ambil frame) dan `fpdf2` (susun PDF). Folder yang
dibaca cuma yang diberikan; `Return` tidak disentuh.

Contoh menyusun laporan temuan jadi PDF (narasi + sheet yang bermasalah) ada
di `laporan_edubisa_2026-10-16.py` - memakai `wa_kurasi.laporan_pdf`.

### Lewat aplikasi web (tinggal tempel link)

Buat yang tidak mau mengetik perintah, ada antarmuka web: **klik dua kali
`Kurasi-Web.bat`**, browser terbuka ke `http://127.0.0.1:8733`, tempel link
folder Drive, tekan Jalankan. Di belakangnya memanggil `kurasi` yang sama,
menampilkan log berjalan, lalu tombol buka PDF / folder hasil.

Frontend React (folder `web/`, di-*build* dengan Vite jadi file statis),
backend Flask (`kurasi_server.py`). Sekali di awal:

    cd web
    npm install
    npm run build

Lalu cukup `python kurasi_server.py` (atau `Kurasi-Web.bat`) untuk seterusnya.

**Aman secara bawaan:** server hanya mendengar di `127.0.0.1` (tidak
terjangkau dari jaringan), link divalidasi jadi id folder sebelum dipakai dan
pipeline dipanggil tanpa shell (tak ada injeksi perintah), dan berkas hanya
disajikan dari dalam folder `kurasi/`. Butuh `flask` (`pip install flask`)
dan Node.js untuk tahap build frontend.

---

## Penjaga yang ada di dalamnya

Alat ini berhenti, bukan melewati diam-diam, kalau:

- berkasnya lebih dari 30 detik atau 16 MB - Status WhatsApp menolak atau
  memotongnya
- nama berkas tidak menyebut brand mana pun, atau menyebut lebih dari satu
- **nama berkas milik brand lain daripada sasarannya** - ini yang mencegah
  video Edufio naik ke nomor Edubisa
- nama akun WhatsApp tidak cocok dengan brandnya
- berkas yang sama sudah pernah naik, menurut `riwayat.log`
- pratinjau tidak muncul dalam 120 detik
- tombol kirim tidak ketemu

Dua saringan lagi berjalan diam-diam waktu mencocokkan berkas Drive:

- **hanya folder brand.** Di creative-makers ada folder yang bukan folder
  brand tapi isinya berawalan nama brand juga.
- **nama yang ada di folder Return disaring keluar**, walau salinannya ada di
  folder brand. Return isinya berkas yang **tidak lolos kurasi**. Tim
  menyalin berkas tolakan ke sana tanpa menghapus aslinya, jadi menyaring
  lewat jalur saja tidak cukup.

**Jangan melonggarkan dua saringan itu karena stok kelihatan menipis.** Stok
yang tersaring itu urusan tim kurasi - laporkan angkanya.

**Folder Return tidak boleh disentuh sama sekali.** Namanya cuma dibaca dari
indeks untuk menyaring keluar.

---

## Menyembunyikan jendelanya

    set LACON_WA_SEMBUNYI=1

Jendela Chrome turun ke taskbar. Bukan mode headless - headless justru lebih
gampang dikenali halaman web, dan tidak sepadan risikonya di sini.

---

## Isi repo

| Berkas | Isinya |
|---|---|
| `wa.py` | perintah |
| `wa_inti.py` | pondasi - config, login Google, indeks, tanggal, brand, jendela |
| `wa_konten.py` | baca sheet, cocokkan ke Drive, unduh |
| `wa_status.py` | posting ke Status WhatsApp |
| `config.json` | id sheet, id folder Drive, nama akun per brand |

Aturannya sama seperti proyek induknya: **yang dipakai bersama tinggal di
`wa_inti.py`, jangan disalin ke modul lain.** Kalau disalin, suatu hari
kolom di sheet digeser dan cuma sebagian salinan yang diperbarui.
