#!/usr/bin/env bash
set -euo pipefail

# 1) LICENSE (MIT)
cat > LICENSE <<'MIT'
MIT License

Copyright (c) 2025 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
MIT

# 2) requirements (versions épinglées)
cat > requirements.txt <<'REQ'
pandas==2.2.2
numpy==1.26.4
matplotlib==3.8.4
requests==2.32.3
python-dotenv==1.0.1
plotly==5.24.1
pytest==8.2.1
REQ

# 3) .gitignore (dont agent memory)
grep -qxF '.env' .gitignore 2>/dev/null || echo '.env' >> .gitignore
grep -qxF '.agent_memory/' .gitignore 2>/dev/null || echo '.agent_memory/' >> .gitignore
grep -qxF '.agent_memory/netflow_agent.json' .gitignore 2>/dev/null || echo '.agent_memory/netflow_agent.json' >> .gitignore
grep -qxF 'logs/' .gitignore 2>/dev/null || echo 'logs/' >> .gitignore
mkdir -p logs .agent_memory docs

# 4) README — lien visuels + bloc Automation (ajoute si absent)
touch README.md
if ! grep -q '## Visualisations' README.md; then
cat >> README.md <<'RDME'

## Visualisations
- Voir `docs/top_netflow_zscore.md` pour les explications et visuels (section **Visualisations**).

RDME
fi
if ! grep -q '## Automation (Weekly)' README.md; then
cat >> README.md <<'RDME'

## Automation (Weekly)
- **planif** : dimanche 10:00 UTC  
- **log** : `logs/weekly_run.log`  
- **script** : `run_agent_weekly.ps1`

RDME
fi

# 5) Script weekly (PowerShell)
cat > run_agent_weekly.ps1 <<'PWSH'
# Runs weekly pipeline and appends logs
param([int]$Days = 400)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONUNBUFFERED = "1"
$log = Join-Path $root "logs/weekly_run.log"
Write-Host "Starting weekly run..."
python $root/src/lpt/lpt_pipeline.py --days $Days *>> $log
Write-Host "Done."
PWSH

# 6) S’assurer que l’agent memory n’est pas suivi
git rm --cached .agent_memory/netflow_agent.json 2>/dev/null || true

# 7) Commit unique
git add LICENSE requirements.txt .gitignore README.md run_agent_weekly.ps1
git commit -m "chore(repo): hygiene pass (MIT, pinned reqs, automation, ignore agent memory)"
