#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_lpt_multi_cex.py
- Récupère les transferts LPT (ERC-20) pour plusieurs adresses (CEX) via Etherscan.
- Sort un CSV par adresse + un CSV combiné avec la colonne 'exchange'.

ENV requis: ETHERSCAN_API_KEY
Dépendances: requests, pandas

Exemples:
python scripts/get_lpt_multi_cex.py ^
  --config scripts/cex_addresses.json ^
  --startdate 2025-05-01 --enddate 2025-06-05 ^
  --outdir data

python scripts/get_lpt_multi_cex.py ^
  --addresses "binance20=0xF977...,kraken_cold1=0x22af..." ^
  --startblock 12600000 --endblock 12800000 ^
  --sort desc ^
  --outdir data
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import requests
import pandas as pd

LPT_CONTRACT = "0x58b6a8a3302369daec383334672404ee733ab239"  # Livepeer Token
ETHERSCAN_API = "https://api.etherscan.io/api"


# ---------- Utilitaires temps / blocs ----------

def to_utc_ts(date_str: str, end: bool = False) -> int:
    y, m, d = map(int, date_str.split("-"))
    hh, mm, ss = (23, 59, 59) if end else (0, 0, 0)
    return int(datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc).timestamp())

def block_by_time(ts: int, closest: str, api_key: str) -> int:
    """closest: 'before' ou 'after'"""
    r = requests.get(
        ETHERSCAN_API,
        params={
            "module": "block",
            "action": "getblocknobytime",
            "timestamp": ts,
            "closest": closest,
            "apikey": api_key,
        },
        timeout=30,
    )
    r.raise_for_status()
    js = r.json()
    if js.get("status") != "1":
        raise RuntimeError(f"getblocknobytime failed: {js}")
    return int(js["result"])


# ---------- Récupération paginée ----------

def fetch_pages_for_address(
    api_key: str,
    address: str,
    contract: str,
    startblock: int | None,
    endblock: int | None,
    startdate: str | None,
    enddate: str | None,
    maxpages: int,
    pagesize: int,
    sort: str = "desc",
    sleep_sec: float = 0.2,
) -> List[dict]:
    """
    Boucle paginée sur Etherscan pour une adresse.
    Retourne une liste de dict (brut Etherscan).
    """
    params_base = {
        "module": "account",
        "action": "tokentx",
        "contractaddress": contract,
        "address": address,
        "sort": sort,              # 'desc' par défaut pour aller du plus récent au plus ancien
        "apikey": api_key,
    }
    if startblock is not None:
        params_base["startblock"] = startblock
    if endblock is not None:
        params_base["endblock"] = endblock

    results: List[dict] = []
    for page in range(1, maxpages + 1):
        params = dict(params_base)
        params["page"] = page
        params["offset"] = pagesize

        r = requests.get(ETHERSCAN_API, params=params, timeout=45)
        r.raise_for_status()
        js = r.json()
        if js.get("status") != "1":
            # fin des données pour cette plage / token
            break

        batch = js.get("result", [])
        if not batch:
            break

        results.extend(batch)

        # Si moins qu'une page complète, on stoppe (fin de liste)
        if len(batch) < pagesize:
            break

        time.sleep(sleep_sec)

    # Filtrage par dates côté client (sécurité supplémentaire)
    if startdate or enddate:
        ts_min = to_utc_ts(startdate, end=False) if startdate else None
        ts_max = to_utc_ts(enddate, end=True) if enddate else None
        filtered = []
        for tx in results:
            try:
                ts = int(tx.get("timeStamp", 0))
            except Exception:
                continue
            if ts_min is not None and ts < ts_min:
                continue
            if ts_max is not None and ts > ts_max:
                continue
            filtered.append(tx)
        results = filtered

    return results


# ---------- Normalisation ----------

def normalize_rows(rows: List[dict]) -> pd.DataFrame:
    """
    Transforme le JSON Etherscan en DataFrame standardisé:
    [hash, blockNumber, timeStamp, from, to, value_LPT]
    """
    cols = ["hash", "blockNumber", "timeStamp", "from", "to", "value", "tokenDecimal"]
    if not rows:
        return pd.DataFrame(columns=["hash", "blockNumber", "timeStamp", "from", "to", "value_LPT"])

    df = pd.DataFrame(rows)
    for c in cols:
        if c not in df.columns:
            df[c] = None

    df["blockNumber"] = pd.to_numeric(df["blockNumber"], errors="coerce").astype("Int64")
    df["timeStamp"] = pd.to_numeric(df["timeStamp"], errors="coerce").astype("Int64")
    # value -> LPT humain (tokenDecimal=18 pour LPT)
    decimals = pd.to_numeric(df["tokenDecimal"], errors="coerce").fillna(18).astype(int)
    scale = (10 ** decimals).astype(object)
    df["value_LPT"] = (pd.to_numeric(df["value"], errors="coerce").fillna(0) / scale).astype(float)

    return df[["hash", "blockNumber", "timeStamp", "from", "to", "value_LPT"]].copy()


# ---------- Parsing adresses ----------

def parse_addresses(addresses_str: str | None, config_path: str | None) -> List[Tuple[str, str]]:
    """
    Retourne une liste [(label, address), ...]
    - addresses_str: "binance20=0x...,kraken=0x..."
    - config_path: JSON {"binance20":"0x...","kraken":"0x..."}
    """
    pairs: List[Tuple[str, str]] = []
    if addresses_str:
        for item in addresses_str.split(","):
            item = item.strip()
            if not item:
                continue
            if "=" not in item:
                raise SystemExit(f"Adresse mal formée (attendu label=address): {item}")
            label, addr = item.split("=", 1)
            pairs.append((label.strip(), addr.strip()))
    if config_path:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for label, addr in data.items():
            pairs.append((label.strip(), str(addr).strip()))

    # dédoublonner en gardant l'ordre
    seen = set()
    uniq = []
    for label, addr in pairs:
        key = (label.lower(), addr.lower())
        if key not in seen:
            seen.add(key)
            uniq.append((label, addr))

    if not uniq:
        raise SystemExit("Aucune adresse fournie. Utilise --addresses ou --config.")
    return uniq


# ---------- Main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--addresses", help='Liste "label=addr,label2=addr2"')
    ap.add_argument("--config", help="Fichier JSON {label: address, ...}")
    ap.add_argument("--contract", default=LPT_CONTRACT, help="Adresse contrat ERC-20 (défaut: LPT)")
    ap.add_argument("--startdate", help="YYYY-MM-DD (UTC)")
    ap.add_argument("--enddate", help="YYYY-MM-DD (UTC)")
    ap.add_argument("--startblock", type=int, help="N° bloc de début")
    ap.add_argument("--endblock", type=int, help="N° bloc de fin")
    ap.add_argument("--maxpages", type=int, default=50, help="Nb max pages Etherscan (défaut 50)")
    ap.add_argument("--pagesize", type=int, default=1000, help="Taille page (défaut 1000)")
    ap.add_argument("--sort", choices=["asc", "desc"], default="desc", help="Ordre de tri Etherscan (défaut: desc)")
    ap.add_argument("--outdir", default="data", help="Dossier de sortie CSV")
    args = ap.parse_args()

    api_key = os.getenv("ETHERSCAN_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("ETHERSCAN_API_KEY non défini (setx / $env:ETHERSCAN_API_KEY)")

    pairs = parse_addresses(args.addresses, args.config)
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    # Si dates fournies mais pas de blocs, on convertit en plage de blocs
    if args.startdate and args.enddate and args.startblock is None and args.endblock is None:
        ts_start = to_utc_ts(args.startdate, end=False)
        ts_end = to_utc_ts(args.enddate, end=True)
        try:
            sblk = block_by_time(ts_start, "after", api_key)
            eblk = block_by_time(ts_end, "before", api_key)
            print(f"[info] block range: {sblk} → {eblk}")
            args.startblock, args.endblock = sblk, eblk
        except Exception as e:
            print(f"[warn] getblocknobytime a échoué, fallback filtre côté client: {e}")

    # période lisible pour noms de fichiers
    period = []
    if args.startdate: period.append(args.startdate)
    if args.enddate: period.append(args.enddate)
    if args.startblock is not None or args.endblock is not None:
        period.append(f"blk{args.startblock or 'min'}_{args.endblock or 'max'}")
    period_str = "__".join(period) if period else "all"

    combined = []
    for label, addr in pairs:
        print(f"→ Fetch {label} ({addr}) ...")
        rows = fetch_pages_for_address(
            api_key=api_key,
            address=addr,
            contract=args.contract,
            startblock=args.startblock,
            endblock=args.endblock,
            startdate=args.startdate,
            enddate=args.enddate,
            maxpages=args.maxpages,
            pagesize=args.pagesize,
            sort=args.sort,
        )
        df = normalize_rows(rows)
        df["exchange"] = label

        # sauvegarde par adresse
        out_file = outdir / f"lpt_transfers_{label}_{period_str}.csv"
        df.to_csv(out_file, index=False)
        print(f"   ✓ {label}: {len(df)} lignes → {out_file.name}")

        combined.append(df)

    # CSV combiné
    if combined:
        df_all = pd.concat(combined, ignore_index=True).sort_values(["timeStamp", "exchange"])
        out_all = outdir / f"lpt_transfers_all_{period_str}.csv"
        df_all.to_csv(out_all, index=False)
        print(f"✓ COMBINED: {len(df_all)} lignes → {out_all.name}")
    else:
        print("⚠️ Aucun résultat combiné.")

if __name__ == "__main__":
    main()
