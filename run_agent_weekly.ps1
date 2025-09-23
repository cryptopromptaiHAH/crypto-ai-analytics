# run_agent_weekly.ps1 (pro-minimale + dernier CSV par LastWriteTime)

$RepoPath = "C:\Users\achat\documents\crypto-ai-analytics"
Set-Location $RepoPath

# Log simple unique
$LogFile = "logs\weekly_run.log"
if (!(Test-Path "logs")) { New-Item -ItemType Directory -Force -Path "logs" | Out-Null }
function Log($m) { $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"); "$ts | $m" | Tee-Object -FilePath $LogFile -Append }

Log "=== weekly run ==="
Log "Python: $(python --version 2>$null) | Git: $(git --version 2>$null)"

# 1) Dernier CSV total PAR DATE DE MODIF (LastWriteTime)
$latest = Get-ChildItem -Path "data" -Filter "netflow_daily_total_*.csv" -File |
          Sort-Object LastWriteTime |
          Select-Object -Last 1
if (-not $latest) { Log "ERROR: no netflow_daily_total_*.csv found in data/"; exit 1 }
$CsvTotal = $latest.FullName
Log "Using CSV (LastWriteTime): $CsvTotal"

# 2) Run agent
$args = @(
  "agents\netflow_agent.py",
  "--csv", $CsvTotal,
  "--win", 7,
  "--z", 2.0,
  "--memory", ".agent_memory\netflow_agent.json",
  "--out_docs", "docs"
)
Log ("Running: python " + ($args -join " "))
& python @args 2>&1 | ForEach-Object { Log $_ }

# 3) Git pull/rebase + push si changements
git pull --rebase origin main | ForEach-Object { Log $_ }
$status = git status --porcelain docs .agent_memory
if ($status) {
  git add docs .agent_memory
  git commit -m "agent: weekly report"
  git push origin main | ForEach-Object { Log $_ }
  Log "Committed & pushed."
} else {
  Log "No changes to commit."
}

Log "=== end ===`n"
