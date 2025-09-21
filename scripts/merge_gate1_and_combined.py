# -*- coding: utf-8 -*-
import argparse, glob
from pathlib import Path
import pandas as pd

def merge_gate1_slices(out_path: Path):
    patterns = [
        "data/lpt_transfers_gate1_2025-05-01__2025-05-10__blk*.csv",
        "data/lpt_transfers_gate1_2025-05-11__2025-05-20__blk*.csv",
        "data/lpt_transfers_gate1_2025-05-21__2025-06-05__blk*.csv",
        "data/lpt_transfers_gate1_2025-05-01__2025-05-02__blk*.csv",
        "data/lpt_transfers_gate1_2025-05-02__2025-05-03__blk*.csv",
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))

    if not files:
        raise SystemExit("No Gate1 slices found.")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df["exchange"] = "gate1"
        dfs.append(df)

    g1 = pd.concat(dfs, ignore_index=True)

    keys = [c for c in ["hash","timeStamp","from","to","value_LPT"] if c in g1.columns]
    g1 = g1.sort_values("timeStamp")
    if keys:
        g1 = g1.drop_duplicates(subset=keys)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    g1.to_csv(out_path, index=False)
    print(f"[OK] Gate1 merged -> {out_path} rows={len(g1):,}")
    return out_path

def rebuild_combined_fixed(g1_merged: Path, out_path: Path):
    base = Path("data")
    # take all CEX files for the full window EXCEPT gate1 (we replace it with merged)
    others = [p for p in base.glob("lpt_transfers_*_2025-05-01__2025-06-05__blk22385294_22641841.csv")
              if "_gate1_" not in p.name]

    dfs = []
    for f in others:
        df = pd.read_csv(f)
        if "exchange" not in df.columns:
            try:
                ex = f.name.split("_")[2]  # e.g., lpt_transfers_binance14_...
            except Exception:
                ex = "unknown"
            df["exchange"] = ex
        dfs.append(df)

    dg1 = pd.read_csv(g1_merged)
    if "exchange" not in dg1.columns:
        dg1["exchange"] = "gate1"
    dfs.append(dg1)

    allx = pd.concat(dfs, ignore_index=True).sort_values(["timeStamp", "exchange"])
    keys = [c for c in ["hash","timeStamp","from","to","value_LPT","exchange"] if c in allx.columns]
    if keys:
        allx = allx.drop_duplicates(subset=keys)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    allx.to_csv(out_path, index=False)
    print(f"[OK] Combined fixed -> {out_path} rows={len(allx):,}")
    return out_path

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--g1_out", default="data/lpt_transfers_gate1_2025-05-01__2025-06-05_MERGED.csv")
    ap.add_argument("--combined_out", default="data/lpt_transfers_all_2025-05-01__2025-06-05_FIXED.csv")
    args = ap.parse_args()

    g1_out = merge_gate1_slices(Path(args.g1_out))
    rebuild_combined_fixed(g1_out, Path(args.combined_out))
