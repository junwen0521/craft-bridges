@echo off
set PYTHONUTF8=1
if "%PHOTOCRAFT_CONTROL_PORT%"=="" (set _PCPORT=47615) else (set _PCPORT=%PHOTOCRAFT_CONTROL_PORT%)
"C:\Users\wuyou\AppData\Local\Programs\Python\Python312\python.exe" "%~dp0pc" --port %_PCPORT% %*
