param([string]$Python='python')
$ErrorActionPreference='Stop'
& $Python -m venv (Join-Path $PSScriptRoot '.venv')
if($LASTEXITCODE -ne 0){throw 'Python 3.10-3.12 is required.'}
& (Join-Path $PSScriptRoot '.venv/Scripts/python.exe') -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
if($LASTEXITCODE -ne 0){throw 'Dependency installation failed.'}
