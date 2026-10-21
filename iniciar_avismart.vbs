' Levanta AviSmart en segundo plano, sin ventanas: backend (puerto 8000) y web (puerto 5173).
' Para apagarlo: doble clic en detener_avismart.bat
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)

sh.CurrentDirectory = base & "\backend"
sh.Run "cmd /c .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > server.out.log 2> server.err.log", 0, False

sh.CurrentDirectory = base & "\frontend"
sh.Run "cmd /c npm run dev -- --host 127.0.0.1 --port 5173 --strictPort > server.out.log 2> server.err.log", 0, False

' Abre el login en el navegador, salvo que se pida lo contrario.
If WScript.Arguments.Count = 0 Then
  WScript.Sleep 6000
  sh.Run "http://127.0.0.1:5173/login"
End If
