#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
summarize_transfers.py
----------------------
Lit un CSV de transferts LPT (ERC-20 Livepeer), calcule des stats (count, sum, mean, max),
génère un résumé Markdown et 3 graphiques PNG.

Usage (depuis la racine du projet) :
  python scripts/summarize_transfers.py --csv "data/lpt_transfers_binance_hotwallet20.csv" --out "docs/summary_day2.md"
"""

import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


IMG_DIR = Path("docs/img")  # unifie tous les visuels ici
IMG_DIR.mkdir(parents=True, exist_ok=True)


def make_charts(df: pd.DataFrame) -> None:
    """Génère 3 graphiques PNG dans docs/img/."""
    # 1) Volume quotidien (somme LPT par jour)
    daily = df.groupby(df["date"].dt.date)["value_LPT"].sum()
    plt.figure(figsize=(10, 4))
    daily.plot()
    plt.title("Daily LPT Volume (sum)")
    plt.xlabel("Date")
    plt.ylabel("LPT")
    plt.tight_layout()
    plt.savefig(IMG_DIR / "volume_daily_lpt.png", dpi=150)
    plt.close()

    # 2) Top 10 transferts (barres)
    top10 = df.nlargest(10, "value_LPT")[["hash", "value_LPT"]].copy()
    top10["hash_short"] = top10["hash"].str.slice(0, 10) + "…" + top10["hash"].str.slice(-6)

    plt.figure(figsize=(10, 4))
    plt.bar(top10["hash_short"], top10["value_LPT"])
    plt.title("Top 10 Transfers (LPT)")
    plt.xlabel("Tx (short)")
    plt.ylabel("LPT")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(IMG_DIR / "top10_transfers_lpt.png", dpi=150)
    plt.close()

    # 3) Histogramme des tailles de transferts
    plt.figure(figsize=(10, 4))
    df["value_LPT"].plot(kind="hist", bins=30)
    plt.title("Transfer Size Distribution (LPT)")
    plt.xlabel("LPT")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(IMG_DIR / "transfer_size_hist.png", dpi=150)
    plt.close()


def summarize(csv_path: str, out_path: str) -> None:
    """Lit le CSV, calcule les stats, génère le Markdown + graphiques."""
    df = pd.read_csv(csv_path)
    out_md = Path(out_path)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    if df.empty:
        out_md.write_text("# 📊 LPT Transfers Summary\n\n_Empty CSV – no transfers found._\n", encoding="utf-8")
        print(f"⚠️ CSV vide. Rapport écrit (minimal) dans {out_md}")
        return

    # Préparer la colonne date (timestamp UNIX -> datetime)
    # (tolère timeStamp en str)
    df["timeStamp"] = pd.to_numeric(df["timeStamp"], errors="coerce")
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

    # Générer graphiques
    make_charts(df)

    # Contenu Markdown
    lines = []
    lines.append("# 📊 LPT Transfers Summary\n")
    lines.append(f"- **Transfers count:** {n_transfers}")
    lines.append(f"- **Total LPT volume:** {total_volume:,.2f}")
    lines.append(f"- **Average per transfer:** {avg_transfer:,.2f}")
    lines.append(f"- **Largest transfer:** {max_transfer:,.2f}\n")

    lines.append("## 🔝 Top 5 transfers\n")
    lines.append(top5.to_markdown(index=False))

    lines.append("\n## 📆 Daily volume (LPT)\n")
    lines.append(daily_volume.to_markdown())

    lines.append("\n## 🖼️ Charts\n")
    lines.append("- `docs/img/volume_daily_lpt.png`")
    lines.append("- `docs/img/top10_transfers_lpt.png`")
    lines.append("- `docs/img/transfer_size_hist.png`")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Résumé généré dans {out_md}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Chemin du fichier CSV à analyser")
    ap.add_argument("--out", default="docs/summary_day2.md", help="Chemin de sortie du résumé Markdown")
    args = ap.parse_args()
    summarize(args.csv, args.out)


if __name__ == "__main__":
    main()
