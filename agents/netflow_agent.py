#!/usr/bin/env python3
"""
Netflow Agent: watches daily total netflow CSV, flags anomalies (|z|>=Z),
deduplicates by date via JSON memory, and writes a small daily report.

Usage:
  python agents/netflow_agent.py --csv data/netflow_daily_total_2025-05-01__2025-06-05.csv \
                                 --win 7 --z 2.0 \
                                 --memory .agent_memory/netflow_agent.json \
                                 --out_docs docs

Tip:
  Schedule via Task Scheduler (Windows) or cron (Linux) to run once per day.
"""
from __future__ import annotations
import argparse, csv, json, time, shutil
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
import math

@dataclass
class Anom:
    date: str
    inflow: float
    outflow: float
    netflow: float
    roll_mean: float
    roll_std: float
    zscore: float

def read_daily_total(csv_path: Path):
    rows = []
    with open(csv_path, newline='', encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            # tolerate different colnames; normalize
            date = row.get("date") or row.get("Date") or row.get("timestamp") or row.get("day")
            inflow = float(row.get("inflow", row.get("Inflow", 0)) or 0)
            outflow = float(row.get("outflow", row.get("Outflow", 0)) or 0)
            netflow = float(row.get("netflow", row.get("Netflow", inflow - outflow)) or 0)
            rows.append({"date": date, "inflow": inflow, "outflow": outflow, "netflow": netflow})
    # sort by date
    rows.sort(key=lambda x: x["date"])
    return rows

def roll_mean_std(vals, win):
    out = []
    for i in range(len(vals)):
        if i+1 < win:
            out.append((None, None))
        else:
            window = vals[i+1-win:i+1]
            m = sum(window)/win
            var = sum((v-m)**2 for v in window)/win
            out.append((m, math.sqrt(var)))
    return out

def compute_zscore(rows, win):
    net = [r["netflow"] for r in rows]
    stats = roll_mean_std(net, win)
    for r, (m, s) in zip(rows, stats):
        r["roll_mean"] = m
        r["roll_std"] = s
        if m is None or (s is None) or s == 0:
            r["zscore"] = None
        else:
            r["zscore"] = (r["netflow"] - m) / s
    return rows

def load_memory(mem_path: Path):
    if mem_path.exists():
        try:
            return json.loads(mem_path.read_text(encoding="utf-8"))
        except Exception:
            return {"seen_dates": []}
    return {"seen_dates": []}

def save_memory(mem_path: Path, mem):
    mem_path.parent.mkdir(parents=True, exist_ok=True)
    mem_path.write_text(json.dumps(mem, indent=2), encoding="utf-8")

def detect_anomalies(rows, z_thresh: float):
    out = []
    for r in rows:
        z = r.get("zscore")
        if z is None:
            continue
        if abs(z) >= z_thresh:
            out.append(Anom(
                date=r["date"],
                inflow=r["inflow"],
                outflow=r["outflow"],
                netflow=r["netflow"],
                roll_mean=r["roll_mean"],
                roll_std=r["roll_std"],
                zscore=z
            ))
    return out

def write_report(anoms: list[Anom], out_docs: Path):
    if not anoms:
        return None
    out_docs.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%SZ")
    md = out_docs / f"agent_report_{ts}.md"
    lines = [
        f"# Netflow Agent Report — {ts} (UTC)",
        "",
        "| date | zscore | netflow | inflow | outflow | roll_mean | roll_std |",
        "|------|--------|---------|--------|---------|-----------|----------|",
    ]
    for a in anoms:
        lines.append(
            f"| {a.date} | {a.zscore:.3f} | {int(a.netflow):,} | {int(a.inflow):,} | {int(a.outflow):,} | "
            f"{int(a.roll_mean):,} | {a.roll_std:.1f} |".replace(",", " ")
        )
    lines += [
        "",
        "> Rule: |zscore| >= threshold triggers an alert. This file was generated automatically by `netflow_agent.py`.",
    ]
    md.write_text("\n".join(lines), encoding="utf-8")
    return md

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True, help="daily total netflow CSV")
    p.add_argument("--win", type=int, default=7)
    p.add_argument("--z", type=float, default=2.0)
    p.add_argument("--memory", default=".agent_memory/netflow_agent.json")
    p.add_argument("--out_docs", default="docs")
    p.add_argument("--loop", action="store_true", help="loop forever (demo)")
    p.add_argument("--sleep", type=int, default=3600, help="sleep seconds when --loop")
    p.add_argument("--rotate-monthly", action="store_true",
                   help="archive memory & reports per month")
    args = p.parse_args()

    csv_path = Path(args.csv)
    mem_path = Path(args.memory)
    out_docs = Path(args.out_docs)

    # Monthly rotation
    if args.rotate_monthly:
        today = datetime.now(UTC)
        ym = today.strftime("%Y-%m")

        # 1) Archive memory
        if mem_path.exists():
            archive_dir = mem_path.parent / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(mem_path, archive_dir / f"netflow_agent_{ym}.json")
            mem_path.unlink()  # reset memory

        # 2) Reports in monthly folder
        out_docs = out_docs / "agent_reports" / ym

    while True:
        rows = read_daily_total(csv_path)
        rows = compute_zscore(rows, args.win)
        anoms = detect_anomalies(rows, args.z)

        mem = load_memory(mem_path)
        seen = set(mem.get("seen_dates", []))
        new_anoms = [a for a in anoms if a.date not in seen]

        if new_anoms:
            report = write_report(new_anoms, out_docs)
            print(f"[ALERT] {len(new_anoms)} new anomalies. Report: {report}")
            for a in new_anoms:
                seen.add(a.date)
            mem["seen_dates"] = sorted(list(seen))
            save_memory(mem_path, mem)
        else:
            print("[OK] No new anomalies.")

        if not args.loop:
            break
        time.sleep(max(args.sleep, 5))

if __name__ == "__main__":
    main()

