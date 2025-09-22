# run_agent_weekly.ps1 (fixed)
# Launch netflow agent, log output, and push changes if any.

# --- Settings ---
$RepoPath = "C:\Users\achat\documents\crypto-ai-analytics"
$CsvTotal = "data\netflow_daily_total_2025-05-01__2025-06-05.csv"
$Win = 7
$Z = 2.0
$Memory = ".agent_memory\netflow_agent.json"
$OutDocs = "docs"
$LogDir = "logs"
$LogFile = Join-Path $RepoPath "$LogDir\weekly_run.log"
$MaxLogBytes = 2MB   # rotate if bigger than this

# --- Prep ---
Set-Location $RepoPath

if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }
if (!(Test-Path ".agent_memory")) { New-Item -ItemType Directory -Force -Path ".agent_memory" | Out-Null }
if (!(Test-Path $OutDocs)) { New-Item -ItemType Directory -Force -Path $OutDocs | Out-Null }

# Simple log helper
function Write-Log($msg) {
  $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  "$ts | $msg" | Tee-Object -FilePath $LogFile -Append | Out-Host
}

# Rotate log if too large
if (Test-Path $LogFile) {
  $size = (Get-Item $LogFile).Length
  if ($size -gt $MaxLogBytes) {
    $stamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
    $bak = Join-Path $RepoPath "$LogDir\weekly_run_$stamp.log"
    Move-Item -Force $LogFile $bak
    Write-Host "Rotated log to $bak"
  }
}

Write-Log "=== Netflow weekly run started ==="
Write-Log "Python: $(python --version 2>$null)"
Write-Log "Git: $(git --version 2>$null)"
Write-Log "CSV total path: $CsvTotal"

# --- Run agent directly (no nested PowerShell, no backticks needed) ---
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$ErrorActionPreference = "Stop"
$exitCode = 0

try {
  $args = @(
    "agents\netflow_agent.py",
    "--csv", $CsvTotal,
    "--win", $Win,
    "--z", $Z,
    "--memory", $Memory,
    "--out_docs", $OutDocs
  )
  Write-Log ("Running: python " + ($args -join " "))
  & python @args 2>&1 | ForEach-Object { Write-Log $_ }
} catch {
  $exitCode = 1
  Write-Log "ERROR while running agent: $($_.Exception.Message)"
}

$sw.Stop()
Write-Log "Agent finished in $($sw.Elapsed.ToString()) with exitCode=$exitCode"

# --- Commit & push if changes ---
try {
  $status = git status --porcelain $OutDocs $Memory
  if ($status) {
    Write-Log "Changes detected:`n$status"
    git add $OutDocs $Memory | Out-Null
    git commit -m "agent: weekly report" | ForEach-Object { Write-Log $_ }
    git push origin main | ForEach-Object { Write-Log $_ }
    Write-Log "Pushed changes to origin/main."
  } else {
    Write-Log "No changes to commit."
  }
} catch {
  Write-Log "ERROR during git commit/push: $($_.Exception.Message)"
  $exitCode = 1
}

Write-Log "=== Netflow weekly run ended ===`n"
exit $exitCode
