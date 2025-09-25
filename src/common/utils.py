import os
import time
import json
import functools
import logging
from typing import Optional, Iterable
from datetime import datetime, UTC, date

import pandas as pd
import numpy as np
import requests

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Utils génériques (retry simple)
# -----------------------------------------------------------------------------
def retry(n: int = 3, wait: float = 1.0):
    """
    Décorateur retry avec backoff exponentiel simple (sans jitter).
    Réessaie n fois, avec un délai wait * 2^i entre les tentatives.
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*args, **kwargs):
            last = None
            for i in range(n):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last = e
                    sleep_s = wait * (2 ** i)
                    logger.warning("Retry %s/%s after error: %s; sleeping %.2fs", i + 1, n - 1, e, sleep_s)
                    time.sleep(sleep_s)
            raise last
        return wrap
    return deco


def _sleep_from_retry_after(resp: requests.Response) -> Optional[int]:
    """Parse l'en-tête Retry-After en secondes si présent et valide, sinon None."""
    ra = resp.headers.get("Retry-After")
    if ra:
        try:
            return max(1, int(float(ra)))
        except Exception:
            pass
    return None

# -----------------------------------------------------------------------------
# Helpers datetime (UTC, timezone-aware)
# -----------------------------------------------------------------------------
def utc_today() -> date:
    """Renvoie la date du jour (YYYY-MM-DD) en UTC."""
    return datetime.now(UTC).date()

def utc_now() -> datetime:
    """Renvoie un datetime timezone-aware (UTC)."""
    return datetime.now(UTC)

# -----------------------------------------------------------------------------
# HTTP helpers de base
# -----------------------------------------------------------------------------
def _http_get(url: str, headers: dict | None = None, timeout: float = 30) -> requests.Response:
    return requests.get(url, headers=headers or {}, timeout=timeout)

def _try_with_headers(url: str, key: str) -> requests.Response:
    """Essaie d'abord l'entête DEMO, puis PRO."""
    r = _http_get(url, headers={"x-cg-demo-api-key": key})
    if r.status_code == 200:
        return r
    if r.status_code not in (401, 403):
        return r
    return _http_get(url, headers={"x-cg-pro-api-key": key})

def _cg_get(url: str, max_attempts: int = 6) -> requests.Response:
    """
    Client CoinGecko tolérant aux rate-limits/erreurs.
    Essaie : api.coingecko.com puis pro-api.coingecko.com
    - Utilise COINGECKO_API_KEY si disponible
    - Gère Retry-After (429) + backoff gradué
    """
    key = os.getenv("COINGECKO_API_KEY", "").strip()
    bases = ["https://api.coingecko.com", "https://pro-api.coingecko.com"]
    path = url.split("coingecko.com", 1)[-1]
    last_exc: Optional[Exception] = None

    for attempt in range(max_attempts):
        for base in bases:
            full = f"{base}{path}"
            if not key:
                r = _http_get(full)
                if r.status_code == 200:
                    return r
            else:
                r = _try_with_headers(full, key)
                if r.status_code == 200:
                    return r
                if r.status_code in (401, 403) and "pro-api" in base:
                    sep = "&" if "?" in path else "?"
                    r = _http_get(f"{base}{path}{sep}x_cg_demo_api_key={key}")
                    if r.status_code == 200:
                        return r

            if r.status_code == 429:
                wait = _sleep_from_retry_after(r) or min(60, 3 * (2 ** attempt))
                logger.warning("Rate limited (429). Waiting %ss before retry...", wait)
                time.sleep(wait)
                last_exc = requests.HTTPError("429 Too Many Requests", response=r)
                break
            else:
                try:
                    r.raise_for_status()
                except requests.HTTPError as e:
                    last_exc = e
                    time.sleep(min(5, 1 + attempt))
        else:
            continue
        continue

    if last_exc:
        raise last_exc
    raise RuntimeError("CoinGecko request failed without explicit error")

# -----------------------------------------------------------------------------
# Mapping ticker -> CoinGecko coin_id
# -----------------------------------------------------------------------------
_COINGECKO_TICKER_MAP = {
    "LPT": "livepeer",
    "LIVEPEER": "livepeer",
    "AVAX": "avalanche-2",
    "BTC": "bitcoin",
    "ETH": "ethereum",
}

def resolve_coin_id(name: str) -> str:
    """
    Résout un ticker ou un id vers l'id CoinGecko.
    Ex: 'LPT'/'lpt'/'livepeer' -> 'livepeer'
    """
    if not name:
        raise ValueError("Empty coin name")
    n = name.strip()
    if n.lower() in (v.lower() for v in _COINGECKO_TICKER_MAP.values()):
        return n.lower()
    return _COINGECKO_TICKER_MAP.get(n.upper(), n.lower())

# -----------------------------------------------------------------------------
# Fetch marché (quotidien)
# -----------------------------------------------------------------------------
@retry(n=3, wait=1.0)
def cg_market_chart_range(coin_id_or_ticker: str, vs: str = "usd", days: int = 400) -> pd.DataFrame:
    """
    Renvoie un DataFrame quotidien: colonnes = price, market_cap, volume ; index = dates.
    Accepte 'LPT', 'livepeer', etc. (résolution automatique).
    """
    resolved_id = resolve_coin_id(coin_id_or_ticker)
    base = os.getenv("COINGECKO_API_BASE", "https://api.coingecko.com")
    url = f"{base}/api/v3/coins/{resolved_id}/market_chart?vs_currency={vs}&days={days}"
    r = _cg_get(url)
    data = r.json()
    if not isinstance(data, dict) or "prices" not in data:
        try:
            data = json.loads(r.text)
        except Exception:
            pass

    df_price = pd.DataFrame(data.get("prices", []), columns=["ts_ms", "price"])
    df_mcap = pd.DataFrame(data.get("market_caps", []), columns=["ts_ms", "market_cap"])
    df_vol = pd.DataFrame(data.get("total_volumes", []), columns=["ts_ms", "volume"])

    if df_price.empty and df_mcap.empty and df_vol.empty:
        logger.warning("Réponse CoinGecko vide pour %s (vs=%s, days=%s).", resolved_id, vs, days)
        return pd.DataFrame(columns=["price", "market_cap", "volume"])

    df = df_price.merge(df_mcap, on="ts_ms", how="outer").merge(df_vol, on="ts_ms", how="outer")
    df["ts"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True).dt.tz_convert(None)
    df = df.drop(columns=["ts_ms"]).set_index("ts").sort_index()
    df = df.resample("1D").mean().interpolate()
    return df

# -----------------------------------------------------------------------------
# Petites métriques
# -----------------------------------------------------------------------------
def rolling_apy(price: pd.Series, window: int = 30) -> pd.Series:
    return price.pct_change().add(1).rolling(window).apply(lambda x: np.prod(x) - 1, raw=False)

def zscore(s: pd.Series, window: int = 60) -> pd.Series:
    m = s.rolling(window).mean()
    sd = s.rolling(window).std(ddof=0)
    return (s - m) / sd

def ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()

def shift_corr(a: pd.Series, b: pd.Series, lag: int = 0, window: int = 60) -> pd.Series:
    if lag != 0:
        b = b.shift(lag)
    return a.rolling(window).corr(b)

# -----------------------------------------------------------------------------
# Cache local
# -----------------------------------------------------------------------------
def load_or_fetch_coin(coin_id_or_ticker: str, vs: str = "usd", days: int = 400, force_refresh: bool = False) -> pd.DataFrame:
    """
    Charge depuis cache local si dispo, sinon fetch depuis CoinGecko et sauvegarde.
    Fichiers: data/cache_{coinIdResolu}_{vs}_{days}d.csv
    """
    resolved_id = resolve_coin_id(coin_id_or_ticker)
    os.makedirs("data", exist_ok=True)
    fname = os.path.join("data", f"cache_{resolved_id}_{vs}_{days}d.csv")

    if not force_refresh and os.path.exists(fname):
        try:
            df = pd.read_csv(fname, parse_dates=True, index_col=0)
            df.index = pd.to_datetime(df.index)
            return df
        except Exception:
            logger.warning("Cache corrompu pour %s, refetch...", resolved_id)

    df = cg_market_chart_range(resolved_id, vs=vs, days=days)
    df.to_csv(fname)
    return df

# -----------------------------------------------------------------------------
# Helpers graphiques
# -----------------------------------------------------------------------------
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

def _ensure_series_for_rolling(s, window: int, min_extra: int = 5) -> bool:
    try:
        series = getattr(s, "dropna", lambda: s)()
        return len(series) >= (window + min_extra)
    except Exception:
        return False

def savefig_stable(path: str, width: int = 1200, height: int = 700, dpi: int = 150):
    plt.gcf().set_size_inches(width / 100, height / 100)
    plt.tight_layout()
    plt.savefig(path, dpi=dpi, transparent=False, bbox_inches="tight")
    plt.close()

# -----------------------------------------------------------------------------
# Export public
# -----------------------------------------------------------------------------
__all__ = [
    "retry",
    "utc_today", "utc_now",
    "resolve_coin_id",
    "cg_market_chart_range",
    "load_or_fetch_coin",
    "rolling_apy", "zscore", "ema", "shift_corr",
    "savefig_stable",
]
