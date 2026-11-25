param([Parameter(Mandatory=$true)][ValidateSet('Habilitar','Desabilitar','Status')][string]$Acao)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$link = Join-Path ([Environment]::GetFolderPath('Startup')) 'Jarvis Interface.lnk'
$shell = New-Object -ComObject WScript.Shell
if (Test-Path -LiteralPath $link) {
    $existing = $shell.CreateShortcut($link)
    if ($existing.TargetPath -ne $pythonw -or $existing.Arguments -ne '-m jarvis.desktop') {
        throw 'Atalho com mesmo nome pertence a outra aplicação; nada foi alterado.'
    }
}
switch ($Acao) {
    'Habilitar' {
        if (-not (Test-Path -LiteralPath $pythonw)) { throw 'Ambiente Python não encontrado.' }
        $shortcut = $shell.CreateShortcut($link)
        $shortcut.TargetPath = $pythonw
        $shortcut.Arguments = '-m jarvis.desktop'
        $shortcut.WorkingDirectory = $root
        $shortcut.Save()
        Write-Output 'Inicialização da interface habilitada.'
    }
    'Desabilitar' {
        if (Test-Path -LiteralPath $link) { Remove-Item -LiteralPath $link }
        Write-Output 'Inicialização da interface desabilitada.'
    }
    'Status' { Write-Output $(if (Test-Path -LiteralPath $link) { 'Habilitada' } else { 'Desabilitada' }) }
}
