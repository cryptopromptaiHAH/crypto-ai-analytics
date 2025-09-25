# scripts/update_readme_lpt.ps1
# Pipeline: génération des assets LPT + update README + commit/push si changements.
# Encodage console UTF-8 pour des accents propres.

param(
    [int]$days = 180,
    [string]$vs = "usd",
    [switch]$Offline,
    [switch]$ForceRefresh,
    [switch]$ParamNames
)

# Forcer la console en UTF-8
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
try { chcp 65001 > $null } catch {}

# Construire les flags Python
$genFlags = @("--days", $days, "--vs", $vs)
if ($Offline)      { $genFlags += "--offline" }
if ($ForceRefresh) { $genFlags += "--force-refresh" }
if ($ParamNames)   { $genFlags += "--param-names" }

Write-Host "=== Étape 1 : Génération des assets LPT ($days jours, vs=$vs) ==="
python scripts\generate_lpt_assets.py @genFlags
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erreur lors de la génération des assets." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "=== Étape 2 : Mise à jour du README.md ==="
python scripts\update_readme_lpt.py $days $vs
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erreur lors de la mise à jour du README." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "=== Étape 3 : Commit Git si changements ==="
# Déterminer s'il y a des changements (README + outputs + data)
git add README.md outputs\*.png data\*.csv
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "[INFO] Aucun changement détecté, pas de commit/push."
    exit 0
}

git commit -m "update LPT assets ($days jours, vs=$vs)" | Out-Null
git push

Write-Host "=== Terminé avec succès ===" -ForegroundColor Green
