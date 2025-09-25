# scripts/generate_lpt_assets.py
# Génère CSV + graphes pour LPT (Livepeer) :
# - CSV: data/lpt_market_<days>d.csv
# - PNG stables (overwrite): outputs/lpt_price_ema.png, outputs/lpt_zscore.png, outputs/lpt_apy.png
# Options:
#   --days 180   --vs usd   --offline   --force-refresh   --param-names
#
# Exemples:
#   python scripts/generate_lpt_assets.py --days 180 --vs usd
#   python scripts/generate_lpt_assets.py --days 90 --vs eur --force-refresh
#   python scripts/generate_lpt_assets.py --days 180 --vs usd --param-names

from __future__ import annotations

import sys
import argparse
from pathlib import Path

def _ensure_src_on_path():
    here = Path(__file__).resolve()
    repo_root = here.parent.parent          # .../crypto-ai-analytics
    src_dir = repo_root / "src"             # .../crypto-ai-analytics/src
    if src_dir.exists():
        p = str(src_dir)
        if p not in sys.path:
            sys.path.insert(0, p)

_ensure_src_on_path()

from common import utils   # noqa: E402


def ensure_dirs():
    (Path("data")).mkdir(parents=True, exist_ok=True)
    (Path("outputs")).mkdir(parents=True, exist_ok=True)
    (Path("outputs/variants")).mkdir(parents=True, exist_ok=True)


def compute_metrics(df):
    df["ema_7"]  = utils.ema(df["price"], span=7)
    df["ema_21"] = utils.ema(df["price"], span=21)
    df["z_60"]   = utils.zscore(df["price"], window=60)
    df["apy_30"] = utils.rolling_apy(df["price"], window=30)
    return df


def plot_price_ema(df, out_path: Path):
    series = {"Price": df["price"]}
    if "ema_7" in df:
        series["EMA 7"] = df["ema_7"]
    if "ema_21" in df:
        series["EMA 21"] = df["ema_21"]
    utils.safe_plot_lines(df.index, series, str(out_path), title="LPT — Price & EMAs", ylabel="Price")


def plot_zscore(df, out_path: Path):
    utils.safe_plot_series(df.index, df["z_60"], str(out_path), title="LPT — Z-Score (60j)", ylabel="Z")


def plot_apy(df, out_path: Path):
    utils.safe_plot_series(df.index, df["apy_30"], str(out_path), title="LPT — Rolling APY (30j)", ylabel="APY", label="APY(30)")


def main():
    ap = argparse.ArgumentParser(description="Génère les assets LPT (CSV + PNG).")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--vs", type=str, default="usd")
    ap.add_argument("--offline", action="store_true", help="N'utilise que le cache local (si présent).")
    ap.add_argument("--force-refresh", action="store_true", help="Ignore le cache et refait les fetchs.")
    ap.add_argument("--param-names", dest="param_names", action="store_true",
                    help="Sauvegarde aussi des variantes nommées avec days/vs.")
    args = ap.parse_args()

    ensure_dirs()

    coin_id = utils.resolve_coin_id("LPT")  # 'LPT' -> 'livepeer'

    cache_csv = Path(f"data/cache_{coin_id}_{args.vs}_{args.days}d.csv")
    if args.offline and not cache_csv.exists():
        print(f"[ERROR] Mode offline: cache absent {cache_csv}. Relance sans --offline.")
        return 2

    df = utils.load_or_fetch_coin(coin_id, vs=args.vs, days=args.days, force_refresh=args.force_refresh)
    if df.empty:
        print("[WARN] Série vide renvoyée par CoinGecko.")
        return 1

    df = compute_metrics(df)

    csv_path = Path(f"data/lpt_market_{args.days}d.csv")
    df.to_csv(csv_path)

    out_price_ema = Path("outputs/lpt_price_ema.png")
    out_zscore    = Path("outputs/lpt_zscore.png")
    out_apy       = Path("outputs/lpt_apy.png")

    plot_price_ema(df, out_price_ema)
    plot_zscore(df, out_zscore)
    plot_apy(df, out_apy)

    # Variantes paramétrées si demandé (copie simple des stables)
    if args.param_names:
        outv_price = Path(f"outputs/variants/lpt_price_ema_{args.days}d_{args.vs.lower()}.png")
        outv_z     = Path(f"outputs/variants/lpt_zscore_{args.days}d_{args.vs.lower()}.png")
        outv_apy   = Path(f"outputs/variants/lpt_apy_{args.days}d_{args.vs.lower()}.png")
        outv_price.write_bytes(out_price_ema.read_bytes())
        outv_z.write_bytes(out_zscore.read_bytes())
        outv_apy.write_bytes(out_apy.read_bytes())

    print("=== LPT assets generated ===")
    print(f"CSV : {csv_path}")
    print(f"PNG : {out_price_ema}")
    print(f"PNG : {out_zscore}")
    print(f"PNG : {out_apy}")
    print(f"Range: last {args.days} days — vs={args.vs.lower()} — generated {utils.utc_today().isoformat()} UTC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
