$ErrorActionPreference = "Stop"
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 'Python 3.10 or newer is required.')"
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install .
$ConfigDir = Join-Path $env:APPDATA "lego-element-lookup"
$CacheDir = Join-Path $env:LOCALAPPDATA "lego-element-lookup\cache"
New-Item -ItemType Directory -Force -Path $ConfigDir, $CacheDir | Out-Null
$ConfigPath = Join-Path $ConfigDir "config.json"
if (-not (Test-Path $ConfigPath)) { Copy-Item config.example.json $ConfigPath }
Write-Host "Edit $ConfigPath and replace YOUR_API_KEY_HERE with your Rebrickable API key."
$Answer = Read-Host "Download set 76344-1 now after editing the config? [y/N]"
if ($Answer -match '^[Yy]') { & .\.venv\Scripts\lego-lookup.exe download 76344-1 }
Write-Host "Start with: .\.venv\Scripts\Activate.ps1; lego-lookup"
