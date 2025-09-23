import os, time, functools, logging
from typing import Optional
import pandas as pd
import numpy as np
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# -------------------- utils génériques --------------------
def retry(n=3, wait=1.0):
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*args, **kwargs):
            last = None
            for i in range(n):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last = e
                    time.sleep(wait * (2**i))
            raise last
        return wrap
    return deco

def _sleep_from_retry_after(resp):
    ra = resp.headers.get("Retry-After")
    if ra:
        try:
            return max(1, int(float(ra)))
        except Exception:
            pass
    return None

def _http_get(url: str, headers: dict | None = None, timeout=30) -> requests.Response:
    return requests.get(url, headers=headers or {}, timeout=timeout)

def _try_with_headers(url: str, key: str) -> requests.Response | None:
    # 1) header DEMO
    r = _http_get(url, headers={"x-cg-demo-api-key": key})
    if r.status_code == 200:
        return r
    if r.status_code not in (401, 403):
        return r
    # 2) header PRO
    r = _http_get(url, headers={"x-cg-pro-api-key": key})
    return r

def _cg_get(url: str, max_attempts=6) -> requests.Response:
    """
    Essaie : api.coingecko.com puis pro-api.coingecko.com
    Clé : header demo -> header pro -> query demo
    Gère 429 (Retry-After) avec backoff.
    """
    key = os.getenv("COINGECKO_API_KEY", "").strip()
    bases = [
        "https://api.coingecko.com",
        "https://pro-api.coingecko.com",
    ]
    path = url.split("coingecko.com", 1)[-1]  # '/api/v3/...'
    last_exc = None

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
                wait = _sleep_from_retry_after(r) or min(60, 2 ** attempt * 3)
                logging.warning("Rate limited (429). Waiting %ss before retry...", wait)
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

# -------------------- fetch marché (quotidien) --------------------
@retry(n=3, wait=1.0)
def cg_market_chart_range(coin_id: str, vs: str="usd", days: int=400) -> pd.DataFrame:
    """
    Récupère market_chart pour `days` et renvoie un DataFrame QUOTIDIEN:
    colonnes = price, market_cap, volume
    index = dates (journalières)
    """
    base = os.getenv("COINGECKO_API_BASE", "https://api.coingecko.com")
    url = f"{base}/api/v3/coins/{coin_id}/market_chart?vs_currency={vs}&days={days}"
    r = _cg_get(url)
    data = r.json()

    df_price = pd.DataFrame(data['prices'], columns=['ts_ms','price'])
    df_mcap  = pd.DataFrame(data['market_caps'], columns=['ts_ms','market_cap'])
    df_vol   = pd.DataFrame(data['total_volumes'], columns=['ts_ms','volume'])
    df = df_price.merge(df_mcap, on='ts_ms').merge(df_vol, on='ts_ms')
    df['ts'] = pd.to_datetime(df['ts_ms'], unit='ms', utc=True).dt.tz_convert(None)
    df = df.drop(columns=['ts_ms']).set_index('ts').sort_index()

    # 🔧 important: éviter séries plates -> moyenne quotidienne + interpolation
    df = df.resample("1D").mean().interpolate()

    return df

# -------------------- petites métriques --------------------
def rolling_apy(price: pd.Series, window=30) -> pd.Series:
    return price.pct_change().add(1).rolling(window).apply(lambda x: np.prod(x)-1, raw=False)

def zscore(s: pd.Series, window=60) -> pd.Series:
    m = s.rolling(window).mean()
    sd = s.rolling(window).std(ddof=0)
    return (s - m) / sd

def ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()

def shift_corr(a: pd.Series, b: pd.Series, lag: int=0, window: int=60) -> pd.Series:
    if lag != 0:
        b = b.shift(lag)
    return a.rolling(window).corr(b)

# -------------------- cache local --------------------
def load_or_fetch_coin(coin_id: str, vs: str="usd", days: int=400, force_refresh=False) -> pd.DataFrame:
    """
    Charge depuis cache local si dispo, sinon fetch depuis CoinGecko et sauvegarde.
    Fichiers: data/cache_{coin}_{vs}_{days}d.csv
    """
    cache_dir = "data"
    os.makedirs(cache_dir, exist_ok=True)
    fname = os.path.join(cache_dir, f"cache_{coin_id}_{vs}_{days}d.csv")

    if not force_refresh and os.path.exists(fname):
        try:
            df = pd.read_csv(fname, parse_dates=True, index_col=0)
            df.index = pd.to_datetime(df.index)
            return df
        except Exception:
            logging.warning("Cache corrompu pour %s, refetch...", coin_id)

    df = cg_market_chart_range(coin_id, vs=vs, days=days)
    df.to_csv(fname)
    return df

