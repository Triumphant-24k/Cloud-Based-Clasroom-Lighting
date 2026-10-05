$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Create .venv and install requirements as described in README.md first.' }
$taskNode = (Get-Command node -ErrorAction Stop).Source
$taskVite = Join-Path $PSScriptRoot 'frontend\node_modules\vite\bin\vite.js'
if (-not (Test-Path -LiteralPath $taskVite)) { throw 'Run npm install in frontend first.' }
$taskLogDirectory = Join-Path $PSScriptRoot 'data'
New-Item -ItemType Directory -Path $taskLogDirectory -Force | Out-Null
Start-Process -FilePath $taskPython -ArgumentList @('-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskLogDirectory 'backend.log') -RedirectStandardError (Join-Path $taskLogDirectory 'backend-error.log')
Start-Process -FilePath $taskNode -ArgumentList @('"'+$taskVite+'"','--host','127.0.0.1') -WorkingDirectory (Join-Path $PSScriptRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskLogDirectory 'frontend.log') -RedirectStandardError (Join-Path $taskLogDirectory 'frontend-error.log')
Write-Host 'Demo launched. Open http://127.0.0.1:5173. Logs are in data/. Close these processes when finished.'
