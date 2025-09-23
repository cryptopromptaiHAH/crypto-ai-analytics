import pandas as pd
from src.common.utils import zscore, ema

# ✅ fenêtre réduite à 30 pour séries courtes/factices
def mask_events(df: pd.DataFrame, col='netflow', z_window=30, z_thresh=2.5, events=None):
    df = df.copy()
    # s'assure que l'index est bien Date/Datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df['z'] = zscore(df[col], window=z_window)
    mask = df['z'].abs() > z_thresh
    if events is not None and len(events) > 0:
        mask = mask | df.index.normalize().isin(pd.to_datetime(events).normalize())

    df['netflow_clean'] = df[col].where(~mask)
    df['netflow_trend'] = ema(df['netflow_clean'], span=30)
    return df[['netflow','netflow_clean','netflow_trend','z']]


