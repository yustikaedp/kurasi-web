@echo off
rem Jalankan aplikasi web Kurasi Visual (backend Flask + frontend React).
rem Klik dua kali berkas ini. Browser terbuka sendiri ke 127.0.0.1:8733.
cd /d "%~dp0"
python kurasi_server.py
pause
