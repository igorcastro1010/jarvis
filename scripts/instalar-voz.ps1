Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
uv venv --python 3.12 .venv
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível criar o ambiente Python 3.12.' }
uv pip install --python .venv\Scripts\python.exe -r requirements-voice.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências.' }
.\.venv\Scripts\python.exe -m piper.download_voices pt_BR-faber-medium --data-dir data\models\piper
if ($LASTEXITCODE -ne 0) { throw 'Falha ao baixar a voz Piper.' }
.\.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=4)"
if ($LASTEXITCODE -ne 0) { throw 'Falha ao baixar o modelo Whisper.' }
Write-Host 'Instale Ollama e execute ollama pull qwen2.5:3b se ainda não estiver disponível.'
