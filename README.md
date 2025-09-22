# Crypto AI Analytics — LPT Netflow Anomalies

## 📌 Overview
This project analyzes **Livepeer (LPT) token flows across centralized exchanges (CEX)** to detect early signals of **buying/selling pressure**.  
We use **daily netflow aggregation + anomaly detection (z-score)** and generate automated reports.

---

## 📂 Repository Structure

crypto-ai-analytics/
├── agents/ # autonomous monitoring agents  
│   └── netflow_agent.py # detects anomalies, writes reports  
├── archive/ # older transfer datasets (2021)  
│   └── transfers_2021/...  
├── data/ # processed CSV summaries (tracked)  
│   ├── top_netflow_anomalies_z2.csv  
│   ├── topk_netflow_total.csv  
│   └── topk_netflow_by_exchange.csv  
├── docs/ # published results  
│   ├── img/ # generated charts  
│   ├── top_netflow_zscore.md  
│   ├── summary_2025-05_focus.md  
│   └── ANALYSE_LPT_MAI-JUIN-2025.md  
└── scripts/ # processing scripts  
    ├── flag_netflow_anomalies.py  
    ├── netflow_multi_cex.py  
    ├── plot_netflow_zscore.py  
    └── topk_netflow_days.py  

---

## 🛠 How to Run

### 1) Prepare your data
Place your cleaned transfer CSVs under `data/`.  
Raw blockchain dumps are ignored by Git; only **processed daily or merged datasets** should be committed.

### 2) Generate netflow metrics
```bash
python scripts/netflow_multi_cex.py   --in data/lpt_transfers_all_2025-05-01__2025-06-05.csv   --out data/
```

### 3) Flag anomalies
```bash
python scripts/flag_netflow_anomalies.py   --csv_total data/netflow_daily_total_2025-05-01__2025-06-05.csv   --win 7 --z 2.0   --out data/netflow_daily_total_2025-05-01__2025-06-05_ANOM.csv
```

### 4) Plot results
```bash
python scripts/plot_netflow_zscore.py   --csv_total data/netflow_daily_total_2025-05-01__2025-06-05.csv   --win 7 --z 2.0   --out_img docs/img   --out_csv data/top_netflow_anomalies_z2.csv
```

### 5) Rank Top-K anomaly days
```bash
python scripts/topk_netflow_days.py   --total_csv data/netflow_daily_total_2025-05-01__2025-06-05.csv   --by_csv    data/netflow_daily_by_exchange_2025-05-01__2025-06-05.csv   --k 10   --win 7   --out_data data   --out_md   docs
```

---

## 🤖 Netflow Agent
We also provide an autonomous monitoring agent (`agents/netflow_agent.py`).  
It reads the latest daily totals, computes z-scores, and writes Markdown reports while avoiding duplicates via JSON memory.

### Batch vs Continuous Mode
- **Batch** (one-time run) → useful for daily cron/Task Scheduler jobs  
- **Continuous** (`--loop`) → stays alive and re-checks every N seconds  

### Example Run (PowerShell)
```powershell
PS C:\Users\you\crypto-ai-analytics> python agents/netflow_agent.py `
    --csv data/netflow_daily_total_2025-05-01__2025-06-05.csv `
    --win 7 --z 2.0 `
    --memory .agent_memory/netflow_agent.json `
    --out_docs docs
[ALERT] 4 new anomalies. Report: docs\agent_report_2025-09-22_182847Z.md

PS C:\Users\you\crypto-ai-analytics> python agents/netflow_agent.py `
    --csv data/netflow_daily_total_2025-05-01__2025-06-05.csv `
    --win 7 --z 2.0 `
    --memory .agent_memory/netflow_agent.json `
    --out_docs docs
[OK] No new anomalies.
```

---

## 📑 Reports
- `docs/top_netflow_zscore.md` → Top Netflow Z-Score Days  
- `docs/summary_2025-05_focus.md` → May–June 2025 Focus Summary  
- `docs/ANALYSE_LPT_MAI-JUIN-2025.md` → Detailed Analysis (May–June 2025)  

---

✍️ **Author:** cryptopromptaiHAH  
📅 **Period analyzed:** May–June 2025
