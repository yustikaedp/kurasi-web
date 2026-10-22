import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' supaya aset dimuat dengan jalur relatif saat disajikan Flask dari '/'.
// Build keluar ke web/dist, lalu kurasi_server.py menyajikannya.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: { outDir: 'dist', emptyOutDir: true },
  // npm run dev: teruskan /api ke backend Flask (python kurasi_server.py)
  server: { proxy: { '/api': { target: 'http://127.0.0.1:8733', changeOrigin: true } } },
})
