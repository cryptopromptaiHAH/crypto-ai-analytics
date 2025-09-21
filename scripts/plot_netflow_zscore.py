# -*- coding: utf-8 -*-
"""
plot_netflow_zscore.py
- Lit un CSV "netflow_daily_total_*.csv" (colonnes: date,inflow,outflow,netflow)
- Calcule moyenne/écart-type roulants et z-score sur 'netflow'
- Marque les anomalies (|z| >= seuil)
- Exporte un CSV des anomalies et 2 graphiques PNG

Usage:
  python scripts/plot_netflow_zscore.py \
    --csv_total data/netflow_daily_total_2025-05-01__2025-06-05.csv \
    --win 7 --z 2.5 \
    --out_img docs/img --out_csv data/top_netflow_anomalies.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def read_csv_robust(csv_path: str) -> pd.DataFrame:
    """Lit un CSV avec gestion d'encodage Windows/UTF-8."""
    try:
        return pd.read_csv(csv_path, parse_dates=["date"], encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(csv_path, parse_dates=["date"], encoding="latin1")


def compute_zscore(df: pd.DataFrame, col: str, win: int) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    # rolling moyenne / std (min_periods = moitié de la fenêtre, min 3)
    minp = max(3, win // 2)
    df["roll_mean"] = df[col].rolling(win, min_periods=minp).mean()
    df["roll_std"] = df[col].rolling(win, min_periods=minp).std(ddof=0)

    # éviter division par zéro
    safe_std = df["roll_std"].replace(0, np.nan)
    df["zscore"] = (df[col] - df["roll_mean"]) / safe_std
    df["zscore"] = df["zscore"].fillna(0.0)

    return df


def save_anomalies(df: pd.DataFrame, z: float, out_csv: Path) -> pd.DataFrame:
    mask = df["zscore"].abs() >= z
    anomalies = df.loc[mask, ["date", "inflow", "outflow", "netflow", "roll_mean", "roll_std", "zscore"]]
    anomalies = anomalies.sort_values("date")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    anomalies.to_csv(out_csv, index=False)
    return anomalies


def plot_netflow_with_bands(df: pd.DataFrame, out_dir: Path, title_suffix: str = ""):
    out_dir.mkdir(parents=True, exist_ok=True)

    # Figure 1: netflow + moyenne mobile ± 2*std
    plt.figure(figsize=(11, 4.5))
    plt.plot(df["date"], df["netflow"], label="Netflow total (LPT)")
    plt.plot(df["date"], df["roll_mean"], label=f"Moyenne mobile")
    # bandes ±2σ
    upper = df["roll_mean"] + 2 * df["roll_std"]
    lower = df["roll_mean"] - 2 * df["roll_std"]
    plt.plot(df["date"], upper, linestyle="--", label="+2σ")
    plt.plot(df["date"], lower, linestyle="--", label="-2σ")
    plt.title(f"Netflow total avec bandes ±2σ {title_suffix}".strip())
    plt.xlabel("Date")
    plt.ylabel("LPT")
    plt.legend()
    plt.tight_layout()
    outfile1 = out_dir / "netflow_with_bands.png"
    plt.savefig(outfile1, dpi=150)
    plt.close()

    return outfile1


def plot_zscore(df: pd.DataFrame, z: float, out_dir: Path, title_suffix: str = ""):
    out_dir.mkdir(parents=True, exist_ok=True)

    # Figure 2: z-score et seuils ±z
    plt.figure(figsize=(11, 4.0))
    plt.plot(df["date"], df["zscore"], label="z-score")
    plt.axhline(z, linestyle="--", label=f"+{z:g}")
    plt.axhline(-z, linestyle="--", label=f"-{z:g}")
    plt.title(f"z-score du netflow {title_suffix}".strip())
    plt.xlabel("Date")
    plt.ylabel("z")
    plt.legend()
    plt.tight_layout()
    outfile2 = out_dir / "netflow_zscore.png"
    plt.savefig(outfile2, dpi=150)
    plt.close()

    return outfile2


def main():
    ap = argparse.ArgumentParser(description="Calcule z-score du netflow et produit anomalies + graphiques.")
    ap.add_argument("--csv_total", required=True, help="Chemin du CSV netflow_daily_total_*.csv")
    ap.add_argument("--out_img", default="docs/img", help="Dossier de sortie pour les PNG")
    ap.add_argument("--out_csv", default=None, help="Chemin CSV de sortie des anomalies (par défaut: à côté du CSV source)")
    ap.add_argument("--win", type=int, default=7, help="Fenêtre rolling (jours). Défaut: 7")
    ap.add_argument("--z", type=float, default=2.5, help="Seuil z-score. Défaut: 2.5")
    args = ap.parse_args()

    csv_total = Path(args.csv_total)
    out_img = Path(args.out_img)
    out_csv = Path(args.out_csv) if args.out_csv else csv_total.with_name(csv_total.stem + "_ANOM.csv")

    df = read_csv_robust(str(csv_total))

    # Vérif colonnes minimales
    for c in ["date", "netflow"]:
        if c not in df.columns:
            raise SystemExit(f"[ERR] Colonne manquante dans {csv_total.name}: '{c}'")

    # Certaines exports n'ont pas inflow/outflow : on les crée vides pour la sortie anomalies
    if "inflow" not in df.columns:
        df["inflow"] = np.nan
    if "outflow" not in df.columns:
        df["outflow"] = np.nan

    df = compute_zscore(df, col="netflow", win=args.win)

    anomalies = save_anomalies(df, z=args.z, out_csv=out_csv)
    f1 = plot_netflow_with_bands(df, out_img, title_suffix=f"(win={args.win})")
    f2 = plot_zscore(df, args.z, out_img, title_suffix=f"(win={args.win}, z={args.z:g})")

    # Résumé console
    if anomalies.empty:
        print("Aucune anomalie au seuil choisi.")
    else:
        print("Anomalies détectées (aperçu) :")
        print(anomalies.head(10).to_string(index=False))

    print(f"\n[OK] CSV anomalies : {out_csv}")
    print(f"[OK] Graphiques   : {f1.name}, {f2.name}")


if __name__ == "__main__":
    main()
