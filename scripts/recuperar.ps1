Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Write-Host 'Recuperação manual: examine git status e git log; não sobrescreva alterações locais.'
git status --short --branch
git log --oneline -5
