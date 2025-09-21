#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot daily volume + inflow/outflow + netflow pour un CSV de transferts LPT.

Entrée CSV attendue (colonnes):
hash, blockNumber, timeStamp, from, to, value_LPT

Exemples d'usage:
python scripts/plot_inout_netflow.py --csv data/lpt_transfers_binance_hotwallet20_2025-05.csv \
  --address 0xF977814e90dA44bFA03b6295A0616a897441aceC \
  --startdate 2025-05-20 --enddate 2025-06-05 \
  --outprefix lpt_may2025

Sorties:
- docs/img/<prefix>_volume_daily.png
- docs/img/<prefix>_in_vs_out.png
- docs/img/<prefix>_netflow.png
- data/<prefix>_daily_inout.csv
"""
import argparse
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import matplotlib.pyplot as plt

def to_utc_ts(date_str: str, end=False) -> int:
    y, m, d = map(int, date_str.split("-"))
    hh, mm, ss = (23, 59, 59) if end else (0, 0, 0)
    dt = datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)
    return int(dt.timestamp())

def load_filtered(csv_path: str, start: str|None, end: str|None) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "timeStamp" not in df.columns:
        raise SystemExit("timeStamp column missing in CSV")
    # datetime + day
    df["dt"] = pd.to_datetime(df["timeStamp"], unit="s", utc=True)
    df["date"] = df["dt"].dt.date
    # filtre
    if start:
        ts_start = to_utc_ts(start, end=False)
        df = df[df["timeStamp"] >= ts_start]
    if end:
        ts_end = to_utc_ts(end, end=True)
        df = df[df["timeStamp"] <= ts_end]
    # tri
    df = df.sort_values("timeStamp").reset_index(drop=True)
    return df

def plot_daily_volume(df: pd.DataFrame, outpath: Path):
    outpath.parent.mkdir(parents=True, exist_ok=True)
    daily = df.groupby("date")["value_LPT"].sum().sort_index()
    plt.figure(figsize=(10,4))
    daily.plot()  # pas de couleurs forcées
    plt.title("Daily LPT Volume (sum)")
    plt.xlabel("Date"); plt.ylabel("LPT")
    plt.tight_layout()
    plt.savefig(outpath, dpi=150); plt.close()
    return outpath

def plot_inout_netflow(df: pd.DataFrame, address: str, out_inout: Path, out_net: Path, out_csv: Path):
    addr = address.lower()
    inflow  = df.loc[df["to"].str.lower()==addr].groupby("date")["value_LPT"].sum()
    outflow = df.loc[df["from"].str.lower()==addr].groupby("date")["value_LPT"].sum()
    daily = pd.concat([inflow.rename("inflow"), outflow.rename("outflow")], axis=1).fillna(0.0)
    daily["netflow"] = daily["inflow"] - daily["outflow"]

    # In vs Out
    out_inout.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10,4))
    daily[["inflow","outflow"]].plot(ax=plt.gca())
    plt.title("Inflow vs Outflow")
    plt.xlabel("Date"); plt.ylabel("LPT")
    plt.tight_layout()
    plt.savefig(out_inout, dpi=150); plt.close()

    # Netflow
    plt.figure(figsize=(10,4))
    daily["netflow"].plot(ax=plt.gca())
    plt.title("Netflow (inflow - outflow)")
    plt.xlabel("Date"); plt.ylabel("LPT")
    plt.tight_layout()
    plt.savefig(out_net, dpi=150); plt.close()

    # export CSV
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(out_csv)
    return out_inout, out_net, out_csv

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="CSV d'entrée (ex: data/lpt_transfers_binance_hotwallet20_2025-05.csv)")
    ap.add_argument("--address", help="Adresse focus (CEX) pour inflow/outflow/netflow")
    ap.add_argument("--startdate", help="YYYY-MM-DD (UTC)")
    ap.add_argument("--enddate", help="YYYY-MM-DD (UTC)")
    ap.add_argument("--outprefix", default="lpt_focus", help="Préfixe de sortie pour fichiers")
    ap.add_argument("--imgdir", default="docs/img", help="Dossier images (par défaut docs/img)")
    ap.add_argument("--datadir", default="data", help="Dossier data (par défaut data)")
    args = ap.parse_args()

    df = load_filtered(args.csv, args.startdate, args.enddate)
    if df.empty:
        print("⚠️ Aucune donnée après filtrage. Rien à tracer.")
        return

    imgdir = Path(args.imgdir)
    datadir = Path(args.datadir)

    vol_png = imgdir / f"{args.outprefix}_volume_daily.png"
    plot_daily_volume(df, vol_png)

    if args.address:
        inout_png = imgdir / f"{args.outprefix}_in_vs_out.png"
        net_png   = imgdir / f"{args.outprefix}_netflow.png"
        out_csv   = datadir / f"{args.outprefix}_daily_inout.csv"
        plot_inout_netflow(df, args.address, inout_png, net_png, out_csv)

    print("✅ Terminé.")

if __name__ == "__main__":
    main()
