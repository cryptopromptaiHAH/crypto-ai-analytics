
import argparse, os
import pandas as pd
from dotenv import load_dotenv

# charge .env (COINGECKO_API_KEY)
load_dotenv()

from src.common.utils import load_or_fetch_coin, rolling_apy
from src.lpt.lpt_netflow import mask_events

def load_csv_if_exists(path):
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=True, index_col=0)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        return df
    return None

def main(days: int):
    LPT = os.getenv("LPT_ID", "livepeer")
    BTC = os.getenv("BTC_ID", "bitcoin")
    ETH = os.getenv("ETH_ID", "ethereum")
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("docs/img", exist_ok=True)

    # === Market data via cache local ===
    lpt = load_or_fetch_coin(LPT, days=days)
    btc = load_or_fetch_coin(BTC, days=days)
    eth = load_or_fetch_coin(ETH, days=days)

    # === APY (rolling 30d) sur prix (proxy) ===
    lpt['apy_30'] = rolling_apy(lpt['price'], window=30)

    # === Netflow (facultatif) ===
    nf = load_csv_if_exists("data/lpt_netflow.csv")
    events = None
    if os.path.exists("data/events.csv"):
        ev = pd.read_csv("data/events.csv")
        events = pd.to_datetime(ev['date']).dt.normalize()
    if nf is not None:
        nf = mask_events(nf, col='netflow', z_window=30, z_thresh=float(os.getenv("Z_THRESH", 2.5)), events=events)
        nf.to_csv("outputs/lpt_netflow_clean.csv")

    # === Rolling corr LPT vs BTC/ETH (prix quotidiens alignés) ===
    prices = pd.concat(
        [lpt['price'].rename('lpt'),
         btc['price'].rename('btc'),
         eth['price'].rename('eth')],
        axis=1
    ).dropna()
    rets = prices.pct_change()
    for w in (30, 60):
        lpt[f"corr_btc_{w}"] = rets['lpt'].rolling(w).corr(rets['btc'])
        lpt[f"corr_eth_{w}"] = rets['lpt'].rolling(w).corr(rets['eth'])

    # === Usage protocole (facultatif) : minutes vs prix ===
    minutes = load_csv_if_exists("data/lpt_minutes.csv")
    if minutes is not None:
        dfu = prices[['lpt']].rename(columns={'lpt':'price'}).join(minutes, how='left')
        for lag in (0, 7, 30):
            dfu[f"corr_min_price_lag{lag}"] = dfu['minutes'].rolling(60).corr(dfu['price'].shift(lag))
        dfu.to_csv("outputs/lpt_usage_vs_price.csv")

    # === Productivité Minutes / Market Cap ===
    if minutes is not None:
        prod = lpt[['market_cap']].join(minutes, how='left')
        prod['minutes_per_mcap_bps'] = (prod['minutes'] / prod['market_cap']) * 1e4
        prod.to_csv("outputs/lpt_productivity_ratio.csv")

    # === Save core ===
    lpt.to_csv("outputs/lpt_core.csv")

    # === Plots ===
    import matplotlib.pyplot as plt

    plt.figure()
    lpt['apy_30'].plot(title="LPT APY (Rolling 30d) — proxy from price")
    plt.tight_layout()
    plt.savefig("docs/img/lpt_apy_30d.png", dpi=160)
    plt.close()

    if nf is not None:
        plt.figure()
        nf[['netflow','netflow_clean','netflow_trend']].plot(title="LPT Netflow — Cleaned & Trend")
        plt.tight_layout()
        plt.savefig("docs/img/lpt_netflow_clean.png", dpi=160)
        plt.close()

    plt.figure()
    lpt[['corr_btc_30','corr_eth_30']].plot(title="Rolling Corr (30d) — LPT vs BTC/ETH")
    plt.tight_layout()
    plt.savefig("docs/img/lpt_corr_30d.png", dpi=160)
    plt.close()

    plt.figure()
    lpt[['corr_btc_60','corr_eth_60']].plot(title="Rolling Corr (60d) — LPT vs BTC/ETH")
    plt.tight_layout()
    plt.savefig("docs/img/lpt_corr_60d.png", dpi=160)
    plt.close()

    print("Done. CSVs in outputs/, PNGs in docs/img/.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)  # par défaut 90j pour éviter rate-limit
    args = ap.parse_args()
    main(args.days)

