"""Best-effort Windows tray notifications for the signed-in local user."""
import json
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess

SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$notice = [Console]::In.ReadToEnd() | ConvertFrom-Json
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$icon = New-Object System.Windows.Forms.NotifyIcon
$icon.Icon = [System.Drawing.SystemIcons]::Information
$icon.Visible = $true
$icon.Text = 'PostAutomation'
$icon.BalloonTipTitle = [string]$notice.title
$icon.BalloonTipText = [string]$notice.message
if ($notice.url -match '^https://www\.instagram\.com/') {
    $script:noticeUrl = [string]$notice.url
    $icon.add_BalloonTipClicked({ Start-Process $script:noticeUrl })
}
try {
    $icon.ShowBalloonTip(10000)
    $end = [DateTime]::UtcNow.AddSeconds(12)
    while ([DateTime]::UtcNow -lt $end) {
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 100
    }
} finally { $icon.Dispose() }
'''


def send(root, title, message, url=None):
    data = {'title': title[:60], 'message': message[:220], 'url': url or '',
            'time_utc': datetime.now(timezone.utc).isoformat()}
    folder = root / '.state' / 'notifications'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'events.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(data) + '\n')
    if os.name != 'nt':
        return False
    try:
        process = subprocess.Popen(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', SCRIPT],
                                   stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        process.communicate(json.dumps(data, ensure_ascii=True), timeout=20)
        return process.returncode == 0
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        return False
    except (OSError, ValueError):
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test', action='store_true', required=True)
    parser.parse_args()
    ok = send(Path(__file__).resolve().parent, 'PostAutomation test',
              'This PC will notify you when an Instagram post succeeds or is held.')
    print('Notification requested.' if ok else 'Notification could not be displayed; event saved locally.')
