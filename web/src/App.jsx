import { useEffect, useRef, useState } from 'react'

// Antarmuka "tempel link lalu jalan". Semua kerja berat (unduh Drive, ambil
// frame, susun PDF) ada di backend Flask; di sini cuma kirim link, pantau
// log, dan buka hasilnya.

export default function App() {
  const [link, setLink] = useState('')
  const [pratinjau, setPratinjau] = useState(false)
  const [jalan, setJalan] = useState(false)
  const [baris, setBaris] = useState([])
  const [hasil, setHasil] = useState(null) // { folder, pdf }
  const [galat, setGalat] = useState('')
  const logRef = useRef(null)
  const jobRef = useRef(null)
  const timerRef = useRef(null)

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [baris])

  useEffect(() => () => clearInterval(timerRef.current), [])

  async function mulai() {
    setGalat('')
    setHasil(null)
    setBaris([])
    if (!link.trim()) { setGalat('Tempel link folder Drive-nya dulu.'); return }
    setJalan(true)
    try {
      const r = await fetch('/api/mulai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ link, pratinjau }),
      })
      const d = await r.json()
      if (!r.ok) { setGalat(d.pesan || 'Gagal memulai.'); setJalan(false); return }
      jobRef.current = d.job
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
      setBaris(d.baris || [])
      if (d.selesai) {
        clearInterval(timerRef.current)
        setJalan(false)
        if (d.pdf) setHasil({ folder: d.folder, pdf: d.pdf })
        if (d.kode && d.kode !== 0 && !d.pdf) setGalat('Proses berhenti - lihat log di bawah.')
      }
    } catch (e) {
      clearInterval(timerRef.current)
      setJalan(false)
      setGalat('Koneksi ke server terputus.')
    }
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

  return (
    <div className="wrap">
      <header>
        <div className="logo">●</div>
        <div>
          <h1>Kurasi Visual</h1>
          <p className="sub">Lacon&nbsp;WA — tinjau komponen &amp; teks video dari satu folder Drive</p>
        </div>
      </header>

      <div className="card">
        <label className="lbl">Link folder Google Drive</label>
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
            Penilaian tetap kerja mata — buka PDF-nya, tandai video yang
            komponennya tidak jelas atau teksnya nabrak. Durasi &amp; ukuran
            tidak dinilai di sini.
          </p>
        </div>
      )}

      <footer>127.0.0.1 — berjalan lokal di komputer ini saja</footer>
    </div>
  )
}
