# Run from repo root after start-backend has created the venv:
# .\seed.ps1 "path\to\companiesmarketcap_com__OG_Master_List.xlsx"
param([string]$ExcelPath)
if (-not $ExcelPath) { Write-Error "Usage: .\seed.ps1 <path-to-excel>"; exit 1 }
Set-Location backend
.\.venv\Scripts\Activate.ps1
python -m app.services.seed_loader $ExcelPath
