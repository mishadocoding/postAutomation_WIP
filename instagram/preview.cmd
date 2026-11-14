@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -Command "fnm env --shell powershell | Out-String | Invoke-Expression; $env:HYPERFRAMES_BROWSER_PATH='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'; npx.cmd --offline hyperframes preview --background"
