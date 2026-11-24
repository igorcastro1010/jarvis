param([Parameter(Mandatory=$true)][ValidateSet('Habilitar', 'Desabilitar', 'Status')][string]$Acao)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$startup = [Environment]::GetFolderPath('Startup')
$link = Join-Path $startup 'Jarvis Assistente.lnk'
$shell = New-Object -ComObject WScript.Shell
if (Test-Path -LiteralPath $link) {
    $existing = $shell.CreateShortcut($link)
    if ($existing.TargetPath -ne $pythonw -or $existing.Arguments -ne '-m jarvis.tray') {
        throw 'Existe um atalho com o mesmo nome que não pertence a este projeto; nenhuma alteração foi feita.'
    }
}
switch ($Acao) {
    'Habilitar' {
        if (-not (Test-Path -LiteralPath $pythonw)) { throw 'Instale o assistente antes de habilitar.' }
        $shortcut = $shell.CreateShortcut($link)
        $shortcut.TargetPath = $pythonw
        $shortcut.Arguments = '-m jarvis.tray'
        $shortcut.WorkingDirectory = $root
        $shortcut.Description = 'Jarvis assistente pessoal'
        $shortcut.Save()
        Write-Host 'Inicialização habilitada para o usuário atual.'
    }
    'Desabilitar' {
        if (Test-Path -LiteralPath $link) { Remove-Item -LiteralPath $link }
        Write-Host 'Inicialização desabilitada para o usuário atual.'
    }
    'Status' { Write-Host $(if (Test-Path -LiteralPath $link) { 'Habilitada' } else { 'Desabilitada' }) }
}
