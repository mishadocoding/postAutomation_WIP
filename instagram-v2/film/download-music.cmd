@echo off
cd /d "%~dp0"
curl.exe -L --fail --retry 3 --output "assets\music\electro-cabello.mp3" "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Electro%%20Cabello.mp3"
if errorlevel 1 (
  echo Download failed. Please send Codex the error above.
) else (
  echo Music downloaded. Tell Codex it is ready.
)
pause
