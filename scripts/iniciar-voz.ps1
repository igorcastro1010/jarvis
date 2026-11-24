param([switch]$PushToTalk)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Execute scripts\instalar-voz.ps1 primeiro.' }
if ($PushToTalk) { & .\.venv\Scripts\python.exe -m jarvis.voice --push-to-talk }
else { & .\.venv\Scripts\python.exe -m jarvis.voice }
exit $LASTEXITCODE
