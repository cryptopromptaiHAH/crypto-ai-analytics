#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
netflow_multi_cex.py

Calcule les inflows/outflows et le netflow quotidien par exchange à partir
du CSV combiné issu de get_lpt_multi_cex.py, en utilisant un fichier JSON
qui mappe chaque 'exchange' à son adresse (pour déterminer le sens).

Entrées:
  --combined  data/lpt_transfers_all_....csv
  --config    scripts/cex_addresses.json (ex: {"binance20":"0xF977...","kraken_cold1":"0x22af..."})
Sorties:
  data/netflow_daily_by_exchange_<period>.csv
  data/netflow_daily_total_<period>.csv
  docs/img/netflow_total_daily.png
  docs/img/inflow_outflow_total_daily.png
  docs/img/netflow_by_exchange.png

Dépendances: pandas, matplotlib
"""

import argparse
from pathlib import Path
import json
from datetime import datetime, timezone

import pandas as pd
import matplotlib.pyplot as plt


def load_mapping(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # normaliser en minuscule
    return {k: str(v).lower() for k, v in data.items()}


def add_direction_flags(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """
    Ajoute les colonnes:
      - exchange_addr: adresse (lower) de l'exchange
      - direction: 'inflow' si to == exchange_addr, 'outflow' si from == exchange_addr, sinon 'other'
      - signed_flow: +value_LPT pour inflow, -value_LPT pour outflow, 0 sinon
    """
    df = df.copy()
    df["from_l"] = df["from"].str.lower()
    df["to_l"] = df["to"].str.lower()

    # map label -> addr
    df["exchange_addr"] = df["exchange"].map(mapping)

    # direction
    df["direction"] = "other"
    df.loc[df["to_l"] == df["exchange_addr"], "direction"] = "inflow"
    df.loc[df["from_l"] == df["exchange_addr"], "direction"] = "outflow"

    # signed flow
    df["signed_flow"] = 0.0
    df.loc[df["direction"] == "inflow", "signed_flow"] = df.loc[df["direction"] == "inflow", "value_LPT"].astype(float)
    df.loc[df["direction"] == "outflow", "signed_flow"] = -df.loc[df["direction"] == "outflow", "value_LPT"].astype(float)

    return df


def ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convertit timeStamp (UNIX sec) en datetime UTC + colonne date (YYYY-MM-DD)
    """
    df = df.copy()
    df["timeStamp"] = pd.to_numeric(df["timeStamp"], errors="coerce")
    df = df.dropna(subset=["timeStamp"])
    df["dt"] = pd.to_datetime(df["timeStamp"], unit="s", utc=True)
    df["date"] = df["dt"].dt.date
    return df


def aggregate_daily(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Renvoie:
      daily_by_ex: index (date, exchange) -> inflow, outflow, netflow
      daily_total: index date -> inflow, outflow, netflow
    """
    # agrégation par (date, exchange, direction)
    grp = df.groupby(["date", "exchange", "direction"], dropna=False)["value_LPT"].sum().unstack(fill_value=0)

    # garantir colonnes
    if "inflow" not in grp.columns: grp["inflow"] = 0.0
    if "outflow" not in grp.columns: grp["outflow"] = 0.0

    grp = grp[["inflow", "outflow"]].copy()
    grp["netflow"] = grp["inflow"] - grp["outflow"]

    # total par jour (somme des exchanges)
    daily_total = grp.groupby(level="date")[["inflow", "outflow", "netflow"]].sum()

    # remettre en DataFrame standard
    daily_by_ex = grp.reset_index()
    daily_total = daily_total.reset_index()

    return daily_by_ex, daily_total


def period_from_df(df: pd.DataFrame) -> str:
    if df.empty:
        return "empty"
    dmin = df["date"].min()
    dmax = df["date"].max()
    return f"{dmin}__{dmax}"


def save_csvs(daily_by_ex: pd.DataFrame, daily_total: pd.DataFrame, out_data: Path, period: str):
    out_data.mkdir(parents=True, exist_ok=True)
    f1 = out_data / f"netflow_daily_by_exchange_{period}.csv"
    f2 = out_data / f"netflow_daily_total_{period}.csv"
    daily_by_ex.to_csv(f1, index=False)
    daily_total.to_csv(f2, index=False)
    print(f"✓ CSV: {f1.name}, {f2.name}")


def plot_total_series(daily_total: pd.DataFrame, out_img: Path):
    out_img.mkdir(parents=True, exist_ok=True)

    # 1) Netflow total par jour (ligne)
    plt.figure(figsize=(10,4))
    plt.plot(daily_total["date"], daily_total["netflow"])
    plt.title("Total Netflow (LPT) — Daily")
    plt.xlabel("Date")
    plt.ylabel("LPT")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(out_img / "netflow_total_daily.png", dpi=150)
    plt.close()

    # 2) Inflow vs Outflow total (barres)
    plt.figure(figsize=(10,4))
    # barres côte-à-côte pour lisibilité
    x = pd.to_datetime(daily_total["date"])
    plt.bar(x, daily_total["inflow"], label="Inflow")
    plt.bar(x, -daily_total["outflow"], label="Outflow")  # outflow en négatif pour visuel
    plt.title("Total Inflow / Outflow (LPT) — Daily")
    plt.xlabel("Date")
    plt.ylabel("LPT (+in / -out)")
    plt.xticks(rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_img / "inflow_outflow_total_daily.png", dpi=150)
    plt.close()


def plot_by_exchange(daily_by_ex: pd.DataFrame, out_img: Path, top_n: int = 6):
    """
    Ligne nette (netflow) par exchange pour les top_n (par |netflow| cumulé sur la période).
    """
    out_img.mkdir(parents=True, exist_ok=True)

    # sélectionner top exchanges en fonction du volume absolu cumulé
    agg_ex = daily_by_ex.groupby("exchange")["netflow"].apply(lambda s: s.abs().sum()).sort_values(ascending=False)
    top = list(agg_ex.head(top_n).index)

    df_top = daily_by_ex[daily_by_ex["exchange"].isin(top)].copy()
    pivot = df_top.pivot(index="date", columns="exchange", values="netflow").fillna(0.0).sort_index()

    plt.figure(figsize=(11,5))
    for col in pivot.columns:
        plt.plot(pivot.index, pivot[col], label=col)
    plt.title(f"Netflow by Exchange — Top {top_n}")
    plt.xlabel("Date")
    plt.ylabel("LPT")
    plt.xticks(rotation=45, ha="right")
    plt.legend(ncols=2)
    plt.tight_layout()
    plt.savefig(out_img / "netflow_by_exchange.png", dpi=150)
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--combined", required=True, help="CSV combiné (get_lpt_multi_cex.py)")
    ap.add_argument("--config", required=True, help="JSON mapping {exchange: address}")
    ap.add_argument("--out_data", default="data", help="Dossier sortie CSV (défaut: data)")
    ap.add_argument("--out_img", default="docs/img", help="Dossier sortie images (défaut: docs/img)")
    args = ap.parse_args()

    out_data = Path(args.out_data)
    out_img = Path(args.out_img)

    # 1) Charger données & mapping
    df = pd.read_csv(args.combined)
    if df.empty:
        raise SystemExit("Le CSV combiné est vide — lance d’abord get_lpt_multi_cex.py avec une période qui contient des transferts.")
    for col in ["hash","blockNumber","timeStamp","from","to","value_LPT","exchange"]:
        if col not in df.columns:
            raise SystemExit(f"Colonne manquante dans le CSV combiné: {col}")

    mapping = load_mapping(args.config)

    # 2) Préparer date & direction
    df = ensure_date_column(df)
    df = add_direction_flags(df, mapping)

    # 3) Agrégations
    daily_by_ex, daily_total = aggregate_daily(df)
    period = period_from_df(daily_by_ex)

    # 4) Sauvegardes CSV
    save_csvs(daily_by_ex, daily_total, out_data, period)

    # 5) Graphiques
    plot_total_series(daily_total, out_img)
    plot_by_exchange(daily_by_ex, out_img, top_n=6)

    print("✓ Graphs: netflow_total_daily.png, inflow_outflow_total_daily.png, netflow_by_exchange.png")
    print("Done.")


if __name__ == "__main__":
    main()
