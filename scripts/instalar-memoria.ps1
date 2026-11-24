Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path 'data\graphify-venv\Scripts\python.exe')) {
    uv venv --python 3.12 data\graphify-venv
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível criar ambiente isolado do Graphify.' }
}
uv pip install --python data\graphify-venv\Scripts\python.exe 'graphifyy[ollama]==0.9.112'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar Graphify local.' }
Write-Host 'Graphify isolado instalado. Instale e inicie Ollama com qwen2.5:3b para gerar grafos.'
