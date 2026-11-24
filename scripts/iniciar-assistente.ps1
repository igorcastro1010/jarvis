Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw 'Execute scripts\instalar-assistente.ps1 primeiro.' }
Start-Process -FilePath $pythonw -ArgumentList '-m', 'jarvis.tray' -WorkingDirectory $root -WindowStyle Hidden
