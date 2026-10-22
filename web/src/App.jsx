import { useEffect, useRef, useState } from 'react'

// Antarmuka "tempel link lalu jalan". Semua kerja berat (unduh Drive, ambil
// frame, susun PDF, nilai kata & visual lewat Claude) ada di backend Flask;
// di sini cuma kirim link, pantau log, dan tampilkan hasilnya.

export default function App() {
  const [link, setLink] = useState('')
  const [pratinjau, setPratinjau] = useState(false)
  const [nilai, setNilai] = useState(true)
  const [laporan, setLaporan] = useState(null) // { path, teks }
  const [tersalin, setTersalin] = useState(false)
  const [jalan, setJalan] = useState(false)
  const [baris, setBaris] = useState([])
  const [hasil, setHasil] = useState(null) // { folder, pdf }
  const [galat, setGalat] = useState('')
  const [tersimpan, setTersimpan] = useState([])
  const logRef = useRef(null)
  const jobRef = useRef(null)
  const timerRef = useRef(null)
  const gagalRef = useRef(0) // poll gagal berturut-turut

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [baris])

  useEffect(() => () => clearInterval(timerRef.current), [])

  // Muat daftar hasil tersimpan saat buka, dan tiap kali satu kurasi selesai.
  async function muatHasil() {
    try {
      const r = await fetch('/api/hasil')
      const d = await r.json()
      setTersimpan(d.hasil || [])
    } catch (e) { /* diam - panel cuma pelengkap */ }
  }
  useEffect(() => { muatHasil() }, [])

  async function mulai() {
    if (!link.trim()) { setGalat('Tempel link folder / video Drive-nya dulu.'); return }
    jalankanJob('/api/mulai', { link, pratinjau, nilai })
  }

  // Nilai ulang kata & visual untuk hasil yang sudah ada (tanpa unduh ulang).
  function nilaiUlang(path) {
    jalankanJob('/api/nilai', { path })
  }

  async function jalankanJob(url, body) {
    setGalat('')
    setHasil(null)
    setLaporan(null)
    setBaris([])
    setJalan(true)
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const d = await r.json()
      if (!r.ok) { setGalat(d.pesan || 'Gagal memulai.'); setJalan(false); return }
      jobRef.current = d.job
      gagalRef.current = 0
      clearInterval(timerRef.current)
      timerRef.current = setInterval(pantau, 1000)
    } catch (e) {
      setGalat('Tidak bisa menghubungi server. Pastikan server berjalan.')
      setJalan(false)
    }
  }

  async function pantau() {
    if (!jobRef.current) return
    try {
      const r = await fetch(`/api/status/${jobRef.current}`)
      const d = await r.json()
      if (!r.ok) throw new Error(d.pesan || 'status gagal')
      gagalRef.current = 0
      setBaris(d.baris || [])
      if (d.selesai) {
        clearInterval(timerRef.current)
        setJalan(false)
        if (d.pdf) setHasil({ folder: d.folder, pdf: d.pdf })
        if (d.laporan) muatLaporan(d.laporan)
        if (d.kode && d.kode !== 0 && !d.pdf && !d.laporan) setGalat('Proses berhenti - lihat log di bawah.')
        muatHasil()
      }
    } catch (e) {
      // Satu-dua gagal (server sibuk sesaat) dimaafkan; baru menyerah
      // setelah 10 kali berturut-turut (~10 detik).
      gagalRef.current += 1
      if (gagalRef.current < 10) return
      clearInterval(timerRef.current)
      setJalan(false)
      setGalat('Koneksi ke server terputus. Proses mungkin masih berjalan di server - muat ulang halaman nanti.')
    }
  }

  async function muatLaporan(path) {
    try {
      const r = await fetch(`/api/berkas?path=${encodeURIComponent(path)}`)
      setLaporan({ path, teks: await r.text() })
      setTersalin(false)
    } catch (e) { setGalat('Laporan kurasi tidak bisa dimuat.') }
  }

  async function salin() {
    try {
      await navigator.clipboard.writeText(laporan.teks)
      setTersalin(true)
    } catch (e) { setGalat('Gagal menyalin - pilih teksnya lalu Ctrl+C.') }
  }

  function bukaPdf() {
    if (hasil?.pdf) window.open(`/api/berkas?path=${encodeURIComponent(hasil.pdf)}`, '_blank')
  }
  async function bukaFolder() {
    if (hasil?.folder) {
      await fetch('/api/buka', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: hasil.folder }),
      })
    }
  }
  function bukaBerkas(path) {
    window.open(`/api/berkas?path=${encodeURIComponent(path)}`, '_blank')
  }
  async function bukaFolderPath(path) {
    await fetch('/api/buka', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    })
  }
  async function hapus(path, label) {
    if (!window.confirm(`Hapus "${label}"? Tindakan ini permanen dan tidak bisa dibatalkan.`)) return
    try {
      const r = await fetch('/api/hapus', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      const d = await r.json()
      if (!r.ok) { setGalat(d.pesan || 'Gagal menghapus.'); return }
      setGalat('')
      muatHasil()
    } catch (e) {
      setGalat('Tidak bisa menghubungi server untuk menghapus.')
    }
  }

  return (
    <div className="wrap">
      <header>
        <div className="logo">●</div>
        <div>
          <h1>Kurasi Visual</h1>
          <p className="sub">Lacon&nbsp;WA — tinjau visual &amp; kata-kata video dari satu folder Drive</p>
        </div>
      </header>

      <div className="card">
        <label className="lbl">Link folder atau video Google Drive</label>
        <input
          className="inp"
          type="text"
          placeholder="https://drive.google.com/drive/folders/..."
          value={link}
          onChange={(e) => setLink(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !jalan) mulai() }}
          disabled={jalan}
          spellCheck={false}
        />

        <label className="cek">
          <input type="checkbox" checked={pratinjau}
                 onChange={(e) => setPratinjau(e.target.checked)} disabled={jalan} />
          Pratinjau saja — cuma daftar video, tidak mengunduh / tidak buat PDF
        </label>

        <label className="cek">
          <input type="checkbox" checked={nilai && !pratinjau}
                 onChange={(e) => setNilai(e.target.checked)} disabled={jalan || pratinjau} />
          Nilai otomatis kata, visual &amp; info (Claude) — kata ambigu/tidak nyambung,
          teks nabrak/terpotong, gambar tidak sesuai, dan kebenaran informasi
          di teks layar &amp; narasi suara
        </label>

        <button className="btn" onClick={mulai} disabled={jalan}>
          {jalan ? 'Sedang berjalan…' : (pratinjau ? 'Lihat daftar' : 'Jalankan kurasi')}
        </button>

        {galat && <div className="galat">{galat}</div>}
      </div>

      {(baris.length > 0 || jalan) && (
        <div className="card">
          <div className="lbl">Log</div>
          <pre className="log" ref={logRef}>{baris.join('\n') || 'Memulai…'}</pre>
        </div>
      )}

      {hasil && (
        <div className="card hasil">
          <div className="ok">✓ Selesai. PDF tinjauan siap.</div>
          <div className="aksi">
            <button className="btn" onClick={bukaPdf}>Buka PDF tinjauan</button>
            <button className="btn ghost" onClick={bukaFolder}>Buka folder hasil</button>
          </div>
          <p className="catatan">
            Laporan otomatis tetap perlu dicek mata sebelum dikirim ke editor —
            cocokkan dengan PDF-nya. Durasi &amp; ukuran tidak dinilai di sini.
          </p>
        </div>
      )}

      {laporan && (
        <div className="card">
          <div className="lap-kepala">
            <div className="lbl">Kurasi kata, visual &amp; info</div>
            <button className="btn kecil" onClick={salin}>
              {tersalin ? '✓ Tersalin' : 'Salin semua'}
            </button>
          </div>
          <pre className="laporan">{laporan.teks}</pre>
        </div>
      )}

      {tersimpan.length > 0 && (
        <div className="card">
          <div className="lbl">Hasil tersimpan</div>
          <div className="simpan">
            {tersimpan.map((h) => (
              <div className="simpan-item" key={h.path}>
                <div className="simpan-kepala">
                  <span className="simpan-nama">{h.folder}</span>
                  <span className="simpan-aksi">
                    <button className="tautan" disabled={jalan}
                            onClick={() => nilaiUlang(h.path)}
                            title="Nilai kata, visual & info dari PDF (dan transkrip narasi) yang sudah ada, tanpa unduh ulang">
                      nilai ulang
                    </button>
                    <button className="tautan" onClick={() => bukaFolderPath(h.path)}>
                      buka folder
                    </button>
                    <button className="tautan bahaya" disabled={jalan}
                            onClick={() => hapus(h.path, `folder ${h.folder}`)}>
                      hapus folder
                    </button>
                  </span>
                </div>
                <div className="simpan-pdf">
                  {h.pdf.map((p) => (
                    <span className="pil-grup" key={p.path}>
                      <button className="pil"
                              onClick={() => (p.nama.endsWith('.txt') ? muatLaporan(p.path) : bukaBerkas(p.path))}
                              title={p.nama}>
                        {p.nama}
                      </button>
                      <button className="pil-x" disabled={jalan} onClick={() => hapus(p.path, p.nama)}
                              title="Hapus berkas ini">×</button>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <footer>127.0.0.1 — berjalan lokal di komputer ini saja</footer>
    </div>
  )
}
