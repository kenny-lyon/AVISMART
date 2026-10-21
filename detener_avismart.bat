@echo off
rem Apaga AviSmart: detiene lo que escucha en los puertos 8000 (backend) y 5173 (web).
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
echo AviSmart detenido.
timeout /t 2 /nobreak >nul
