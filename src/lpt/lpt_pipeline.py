import os
import argparse
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common.utils import cg_market_chart_range
# helpers ajoutés dans common.utils (vois Option B si tu ne les as pas encore)
from common.utils import savefig_stable, _ensure_series_for_rolling

LPT = "livepeer"
BTC = "bitcoin"
ETH = "ethereum"

def ensure_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Quotidien, aligné, trous comblés."""
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        df.index = pd.to_datetime(df.index)
    # moyenne journalière + interpolation pour éviter graphes plats/vides
    return df.resample("1D").mean().interpolate()

def plot_apy_30d(lpt_df, out="docs/img/lpt_apy_30d.png"):
    s = lpt_df["price"].pct_change().add(1)
    if not _ensure_series_for_rolling(s, 30):
        print("[skip] APY 30d: not enough data")
        return
    apy30 = s.rolling(30).apply(lambda x: x.prod()-1)
    apy30 = apy30.dropna()
    if apy30.empty:
        print("[skip] APY 30d: empty after dropna")
        return
    plt.figure()
    apy30.plot()
    plt.title("LPT APY (Rolling 30d) — proxy from price")
    plt.xlabel("date"); plt.ylabel("apy_30")
    savefig_stable(out)

def plot_corr(lpt, btc, eth, window=30, out="docs/img/lpt_corr_30d.png"):
    prices = pd.concat(
        [lpt["price"].rename("lpt"),
         btc["price"].rename("btc"),
         eth["price"].rename("eth")],
        axis=1
    ).dropna()
    if not _ensure_series_for_rolling(prices["lpt"].pct_change(), window):
        print(f"[skip] Corr {window}d: not enough data")
        return
    rets = prices.pct_change().dropna()
    corr_btc = rets["lpt"].rolling(window).corr(rets["btc"])
    corr_eth = rets["lpt"].rolling(window).corr(rets["eth"])
    corr = pd.DataFrame({
        f"corr_btc_{window}": corr_btc,
        f"corr_eth_{window}": corr_eth
    }).dropna()
    if corr.empty:
        print(f"[skip] Corr {window}d: empty after dropna")
        return
    plt.figure()
    corr.plot(ax=plt.gca())
    plt.title(f"Rolling Corr ({window}d) — LPT vs BTC/ETH")
    plt.xlabel("ts"); plt.ylabel("corr")
    savefig_stable(out)

def main(days:int=90):
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("docs/img", exist_ok=True)

    lpt = ensure_daily(cg_market_chart_range(LPT, days=days))
    btc = ensure_daily(cg_market_chart_range(BTC, days=days))
    eth = ensure_daily(cg_market_chart_range(ETH, days=days))

    # sauvegarde core CSV pour debug/analyses
    core = pd.concat([lpt["price"].rename("lpt_price"),
                      btc["price"].rename("btc_price"),
                      eth["price"].rename("eth_price")], axis=1)
    core.to_csv("outputs/lpt_core.csv", index=True)

    # plots essentiels
    plot_apy_30d(lpt, out="docs/img/lpt_apy_30d.png")
    plot_corr(lpt, btc, eth, 30, out="docs/img/lpt_corr_30d.png")
    plot_corr(lpt, btc, eth, 60, out="docs/img/lpt_corr_60d.png")

    print("Done. CSVs in outputs/, PNGs in docs/img/ (core only).")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()
    main(args.days)
