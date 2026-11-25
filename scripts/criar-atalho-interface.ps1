Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw 'Ambiente Python não encontrado.' }
$desktop = [Environment]::GetFolderPath('Desktop')
$link = Join-Path $desktop 'Jarvis Interface.lnk'
if (Test-Path -LiteralPath $link) { throw 'O atalho já existe; nada foi sobrescrito.' }
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = '-m jarvis.desktop'
$shortcut.WorkingDirectory = $root
$shortcut.Description = 'Interface desktop do Jarvis'
$shortcut.Save()
Write-Host "Atalho criado: $link"
