import argparse, os
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# charge .env (COINGECKO_API_KEY, etc.)
load_dotenv()

from src.common.utils import load_or_fetch_coin, rolling_apy
from src.lpt.lpt_netflow import mask_events

# ---------- helpers ----------
def load_csv_if_exists(path):
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=True, index_col=0)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        return df
    return None

def infer_zoom(index: pd.DatetimeIndex, prefer_may_june_2025=True, fallback_days=90):
    """
    Si possible, zoom sur mai–juin 2025 ; sinon, derniers `fallback_days`.
    """
    if len(index) == 0:
        return None, None

    idx_min, idx_max = index.min(), index.max()

    if prefer_may_june_2025:
        z0 = pd.Timestamp("2025-05-01")
        z1 = pd.Timestamp("2025-06-30 23:59:59")
        if (idx_min <= z1) and (idx_max >= z0):
            # chevauchement: on clip dans l'intervalle valide
            return max(idx_min, z0), min(idx_max, z1)

    # fallback: derniers N jours
    end = idx_max
    start = end - pd.Timedelta(days=fallback_days)
    return start, end

def save_plot(series_dict, title, out_path, xlim=None, ylabel=None):
    import matplotlib.pyplot as plt
    plt.figure()
    for label, s in series_dict.items():
        s.dropna().plot(label=label)
    if ylabel:
        plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    if xlim and all(xlim):
        try:
            import matplotlib.dates as mdates
            plt.xlim(xlim[0], xlim[1])
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        except Exception:
            pass
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()

# ---------- main ----------
def main(days: int):
    LPT = os.getenv("LPT_ID", "livepeer")
    BTC = os.getenv("BTC_ID", "bitcoin")
    ETH = os.getenv("ETH_ID", "ethereum")
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("docs/img", exist_ok=True)

    # === Market data via cache (quotidien, utils fait resample mean()+interpolate) ===
    lpt = load_or_fetch_coin(LPT, days=days)
    btc = load_or_fetch_coin(BTC, days=days)
    eth = load_or_fetch_coin(ETH, days=days)

    # === APY (rolling 30d) proxy prix ===
    lpt['apy_30'] = rolling_apy(lpt['price'], window=30)

    # === Netflow (détection + nettoyage) ===
    # Priorité au fichier clean si déjà généré
    nf = load_csv_if_exists("outputs/lpt_netflow_clean.csv")
    if nf is None:
        raw_nf = load_csv_if_exists("data/lpt_netflow.csv")
        events = None
        if os.path.exists("data/events.csv"):
            ev = pd.read_csv("data/events.csv")
            events = pd.to_datetime(ev['date']).dt.normalize()
        if raw_nf is not None:
            nf = mask_events(
                raw_nf,
                col='netflow',
                z_window=30,  # fenêtre plus courte si peu de données
                z_thresh=float(os.getenv("Z_THRESH", 2.5)),
                events=events
            )
            nf.to_csv("outputs/lpt_netflow_clean.csv")

    # === Corrélations roulantes (prix quotidiens alignés) ===
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
        dfu = prices[['lpt']].rename(columns={'lpt': 'price'}).join(minutes, how='left')
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

    # === PLOTS ===
    # APY
    save_plot(
        {"apy_30": lpt['apy_30']},
        title="LPT APY (Rolling 30d) — proxy from price",
        out_path="docs/img/lpt_apy_30d.png",
        xlim=infer_zoom(lpt.index)
    )

    # Netflow: niveau clean + tendance + variation journalière
    if nf is not None and len(nf) > 1:
        # daily change: bien plus lisible qu’un niveau cumulé
        nf['netflow_daily'] = nf['netflow_clean'].diff()

        z0, z1 = infer_zoom(nf.index, prefer_may_june_2025=True, fallback_days=90)

        # 1) graphique "clean + trend" (niveau)
        save_plot(
            {
                "netflow_clean": nf['netflow_clean'],
                "netflow_trend": nf['netflow_trend']
            },
            title="LPT Netflow — Cleaned & Trend (level)",
            out_path="docs/img/lpt_netflow_clean.png",
            xlim=(z0, z1),
            ylabel="LPT"
        )

        # 2) graphique "daily change" (variation)
        save_plot(
            {"netflow_daily": nf['netflow_daily']},
            title="LPT Netflow — Daily Change (diff)",
            out_path="docs/img/lpt_netflow_daily.png",
            xlim=(z0, z1),
            ylabel="Δ LPT"
        )

    # Corr 30d
    save_plot(
        {"corr_btc_30": lpt['corr_btc_30'], "corr_eth_30": lpt['corr_eth_30']},
        title="Rolling Corr (30d) — LPT vs BTC/ETH",
        out_path="docs/img/lpt_corr_30d.png",
        xlim=infer_zoom(lpt.index),
        ylabel="corr"
    )

    # Corr 60d
    save_plot(
        {"corr_btc_60": lpt['corr_btc_60'], "corr_eth_60": lpt['corr_eth_60']},
        title="Rolling Corr (60d) — LPT vs BTC/ETH",
        out_path="docs/img/lpt_corr_60d.png",
        xlim=infer_zoom(lpt.index),
        ylabel="corr"
    )

    print("Done. CSVs in outputs/, PNGs in docs/img/.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)  # 90j par défaut pour éviter le rate-limit
    args = ap.parse_args()
    main(args.days)
