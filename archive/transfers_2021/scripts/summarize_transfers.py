﻿#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
summarize_transfers.py
----------------------
Lit un CSV de transferts LPT (ERC-20 Livepeer), calcule des stats (count, sum, mean, max),
gÃ©nÃ¨re un rÃ©sumÃ© Markdown et 3 graphiques PNG.

Usage (depuis la racine du projet):
  python scripts/summarize_transfers.py --csv "data/lpt_transfers_binance_hotwallet20.csv" --out "docs/summary_day2.md"
"""

import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def make_charts(df: pd.DataFrame, out_dir: str):
    """GÃ©nÃ¨re 3 graphiques PNG dans le dossier out_dir."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1) Volume quotidien (somme LPT par jour)
    daily = df.groupby(df["date"].dt.date)["value_LPT"].sum()
    plt.figure(figsize=(10, 4))
    daily.plot()  # (ne pas forcer de couleurs)
    plt.title("Daily LPT Volume (sum)")
    plt.xlabel("Date")
    plt.ylabel("LPT")
    plt.tight_layout()
    plt.savefig(out / "volume_daily_lpt.png", dpi=150)
    lines.append("- `img/volume_daily_lpt.png`")

    # 2) Top 10 transferts (barres)
    top10 = df.nlargest(10, "value_LPT")[["hash", "value_LPT"]].copy()
    top10["hash_short"] = top10["hash"].str.slice(0, 10) + "â€¦" + top10["hash"].str.slice(-6)
    plt.figure(figsize=(10, 4))
    plt.bar(top10["hash_short"], top10["value_LPT"])
    plt.title("Top 10 Transfers (LPT)")
    plt.xlabel("Tx (short)")
    plt.ylabel("LPT")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(out / "top10_transfers_lpt.png", dpi=150)
    plt.close()

    # 3) Histogramme des tailles de transferts
    plt.figure(figsize=(10, 4))
    df["value_LPT"].plot(kind="hist", bins=30)
    plt.title("Transfer Size Distribution (LPT)")
    plt.xlabel("LPT")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(out / "transfer_size_hist.png", dpi=150)
    plt.close()

def summarize(csv_path: str, out_path: str):
    """Lit le CSV, calcule les stats, gÃ©nÃ¨re le Markdown + graphiques."""
    df = pd.read_csv(csv_path)
    out_md = Path(out_path)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    if df.empty:
        out_md.write_text("# ðŸ“Š LPT Transfers Summary\n\n_Empty CSV â€“ no transfers found._\n", encoding="utf-8")
        print(f"âš ï¸ CSV vide. Rapport Ã©crit (minimal) dans {out_md}")
        return

    # PrÃ©parer la colonne date (timestamp UNIX -> datetime)
    df["date"] = pd.to_datetime(df["timeStamp"], unit="s")

    # Stats globales
    n_transfers = len(df)
    total_volume = df["value_LPT"].sum()
    avg_transfer = df["value_LPT"].mean()
    max_transfer = df["value_LPT"].max()

    # Top 5 transferts
    top5 = df.nlargest(5, "value_LPT")[["hash", "from", "to", "value_LPT"]]

    # Volume par jour
    daily_volume = df.groupby(df["date"].dt.date)["value_LPT"].sum()

    # GÃ©nÃ©rer graphiques
    make_charts(df, out_md.parent.as_posix())

    # Contenu Markdown
    lines = []
    lines.append("# ðŸ“Š LPT Transfers Summary\n")
    lines.append(f"- **Transfers count:** {n_transfers}")
    lines.append(f"- **Total LPT volume:** {total_volume:,.2f}")
    lines.append(f"- **Average per transfer:** {avg_transfer:,.2f}")
    lines.append(f"- **Largest transfer:** {max_transfer:,.2f}\n")

    lines.append("## ðŸ” Top 5 transfers\n")
    lines.append(top5.to_markdown(index=False))

    lines.append("\n## ðŸ“† Daily volume (LPT)\n")
    lines.append(daily_volume.to_markdown())

    lines.append("\n## ðŸ–¼ï¸ Charts\n")
    lines.append("- `img/volume_daily_lpt.png`")
    lines.append("- `docs/top10_transfers_lpt.png`")
    lines.append("- `docs/transfer_size_hist.png`")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"âœ… RÃ©sumÃ© gÃ©nÃ©rÃ© dans {out_md}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Chemin du fichier CSV Ã  analyser")
    ap.add_argument("--out", default="docs/summary_day2.md", help="Chemin de sortie du rÃ©sumÃ© Markdown")
    args = ap.parse_args()
    summarize(args.csv, args.out)

if __name__ == "__main__":
    main()

