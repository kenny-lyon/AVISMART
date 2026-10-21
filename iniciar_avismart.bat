@echo off
rem Levanta AviSmart en segundo plano (sin ventanas) y abre el login. Para apagarlo: detener_avismart.bat
start "" wscript.exe "%~dp0iniciar_avismart.vbs"
