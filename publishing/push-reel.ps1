param(
    [Parameter(Mandatory=$true)][string]$Video,
    [Parameter(Mandatory=$true)][string]$CaptionFile,
    [switch]$Publish,
    [string]$At
)
$ErrorActionPreference = 'Stop'
$pushArgs = @((Join-Path $PSScriptRoot 'push_reel.py'), '--video', $Video, '--caption-file', $CaptionFile)
if ($Publish) { $pushArgs += '--publish' }
if ($At) { $pushArgs += @('--at', $At) }
& python @pushArgs
exit $LASTEXITCODE
