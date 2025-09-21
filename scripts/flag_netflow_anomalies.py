import argparse
import pandas as pd
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv_total", required=True, help="CSV netflow_daily_total_*.csv")
    ap.add_argument("--out", default=None, help="CSV de sortie (avec flags)")
    ap.add_argument("--win", type=int, default=7, help="fenêtre rolling (jours)")
    ap.add_argument("--z", type=float, default=2.5, help="seuil z-score")
    args = ap.parse_args()

    df = pd.read_csv(args.csv_total, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # z-score sur netflow total
    df["roll_mean"] = df["netflow"].rolling(args.win, min_periods=max(3, args.win//2)).mean()
    df["roll_std"]  = df["netflow"].rolling(args.win, min_periods=max(3, args.win//2)).std(ddof=0)
    df["zscore"]    = (df["netflow"] - df["roll_mean"]) / df["roll_std"]
    df["anomaly_hi"] = (df["zscore"] >= args.z)    # spikes d’inflow (potentielle pression de vente)
    df["anomaly_lo"] = (df["zscore"] <= -args.z)   # gros outflows (accumulation potentielle)

    out = args.out or (Path(args.csv_total).with_name(Path(args.csv_total).stem + "_ANOM.csv"))
    df.to_csv(out, index=False)

    top = df.loc[df["anomaly_hi"] | df["anomaly_lo"], ["date","netflow","zscore","anomaly_hi","anomaly_lo"]]
    if not top.empty:
        print(top.to_string(index=False))
    else:
        print("Aucune anomalie au seuil choisi.")

    print(f"\n[OK] Écrit : {out}")

if __name__ == "__main__":
    main()
