Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'inicializacao-windows.ps1') -Acao Desabilitar
Write-Host 'Inicialização removida. Use Sair na bandeja para encerrar; dados, modelos e ambiente foram preservados.'
