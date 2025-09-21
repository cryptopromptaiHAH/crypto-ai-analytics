# -*- coding: utf-8 -*-
"""
topk_netflow_days.py
Lister les top-k jours de netflow par |z-score| (total + par exchange).
"""

import argparse
import pandas as pd
from pathlib import Path

def compute_z(df: pd.DataFrame, win: int):
    df = df.sort_values("date").reset_index(drop=True)
    df["roll_mean"] = df["netflow"].rolling(win, min_periods=max(3, win//2)).mean()
    df["roll_std"]  = df["netflow"].rolling(win, min_periods=max(3, win//2)).std(ddof=0)
    df["zscore"]    = (df["netflow"] - df["roll_mean"]) / df["roll_std"]
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--total_csv", required=True, help="CSV netflow_daily_total")
    ap.add_argument("--by_csv",    required=True, help="CSV netflow_daily_by_exchange")
    ap.add_argument("--k", type=int, default=10, help="nombre de jours à garder")
    ap.add_argument("--win", type=int, default=7, help="fenêtre rolling (jours)")
    ap.add_argument("--out_data", required=True, help="répertoire de sortie CSV")
    ap.add_argument("--out_md",   required=True, help="répertoire de sortie Markdown")
    args = ap.parse_args()

    out_data = Path(args.out_data)
    out_md   = Path(args.out_md)
    out_data.mkdir(parents=True, exist_ok=True)
    out_md.mkdir(parents=True, exist_ok=True)

    # --- Total ---
    dft = pd.read_csv(args.total_csv, parse_dates=["date"])
    dft = compute_z(dft, args.win)
    top_total = dft.reindex(dft["zscore"].abs().sort_values(ascending=False).index).head(args.k)
    top_total.to_csv(out_data/"topk_netflow_total.csv", index=False)

    # --- Par exchange ---
    dfb = pd.read_csv(args.by_csv, parse_dates=["date"])
    dfs = []
    for ex, grp in dfb.groupby("exchange"):
        g2 = compute_z(grp.copy(), args.win)
        top_ex = g2.reindex(g2["zscore"].abs().sort_values(ascending=False).index).head(args.k)
        top_ex["exchange"] = ex
        dfs.append(top_ex)
    top_by = pd.concat(dfs, ignore_index=True)
    top_by.to_csv(out_data/"topk_netflow_by_exchange.csv", index=False)

    # --- Markdown résumé ---
    md = []
    md.append("# Top-k jours de netflow (par |z|)\n")
    md.append("## Total\n")
    md.append(top_total[["date","netflow","zscore"]].to_markdown(index=False))
    md.append("\n\n## Par exchange\n")
    md.append(top_by[["date","exchange","netflow","zscore"]].to_markdown(index=False))

    mdfile = out_md/"top_netflow_zscore.md"
    mdfile.write_text("\n".join(md), encoding="utf-8")

    print(f"[OK] top_total -> {out_data/'topk_netflow_total.csv'}")
    print(f"[OK] top_by    -> {out_data/'topk_netflow_by_exchange.csv'}")
    print(f"[OK] Markdown  -> {mdfile}")

if __name__ == "__main__":
    main()
