#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_lpt_transfers.py
--------------------
Récupère tous les transferts ERC-20 LPT (Livepeer) pour une adresse ETH donnée,
avec pagination automatique Etherscan jusqu'à épuisement ou limites choisies.

Usage (PowerShell, depuis la racine du projet) :
  $env:ETHERSCAN_API_KEY="TA_CLE"
  # a) Fenêtre par dates (recommandé, UTC)
  python scripts/get_lpt_transfers.py 0xF977814e90dA44bFA03b6295A0616a897441aceC `
    --startdate 2021-06-01 --enddate 2021-07-31 `
    --out data/lpt_transfers_binance_hotwallet20.csv
  # b) Fenêtre par blocs
  python scripts/get_lpt_transfers.py 0xAdresse --startblock 12000000 --endblock 13000000 --out data/out.csv
"""

import os
import sys
import time
import csv
import argparse
from datetime import datetime, timezone
import requests

ETHERSCAN_API = "https://api.etherscan.io/api"
LPT_CONTRACT  = "0x58b6a8a3302369daec383334672404ee733ab239"

def api_key() -> str:
    k = os.getenv("ETHERSCAN_API_KEY", "").strip()
    if not k:
        sys.exit("Erreur: variable d'environnement ETHERSCAN_API_KEY manquante.")
    return k

def get_block_by_time(ts_utc: int, closest: str = "before") -> int:
    """Mappe un timestamp (UTC) -> numéro de bloc via Etherscan."""
    params = {
        "module": "block",
        "action": "getblocknobytime",
        "timestamp": ts_utc,
        "closest": closest,
        "apikey": api_key(),
    }
    r = requests.get(ETHERSCAN_API, params=params, timeout=40)
    r.raise_for_status()
    js = r.json()
    res = js.get("result")
    try:
        return int(res)
    except Exception:
        raise SystemExit(f"Etherscan getblocknobytime error: {res}")

def parse_date_iso(d: str, end=False) -> int:
    """'YYYY-MM-DD' -> timestamp UTC (seconde)."""
    try:
        y, m, dd = map(int, d.split("-"))
        if end:
            dt = datetime(y, m, dd, 23, 59, 59, tzinfo=timezone.utc)
        else:
            dt = datetime(y, m, dd, 0, 0, 0, tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        raise SystemExit(f"Date invalide: {d} (attendu YYYY-MM-DD)")

def fetch_transfers(address: str,
                    startblock: int,
                    endblock:   int,
                    pagesize:   int = 10000,
                    pause_s:    float = 0.21,
                    max_pages:  int | None = None):
    """
    Récupère les transferts LPT paginés.
    - pagesize: jusqu'à 10000 (limite Etherscan)
    - pause_s : petite pause pour limiter le rate limit
    - max_pages: pour borner (None = pas de borne)
    """
    page = 1
    total = 0
    session = requests.Session()

    while True:
        if max_pages is not None and page > max_pages:
            break

        params = {
            "module": "account",
            "action": "tokentx",
            "contractaddress": LPT_CONTRACT,
            "address": address,
            "startblock": startblock,
            "endblock": endblock,
            "page": page,
            "offset": pagesize,
            "sort": "asc",
            "apikey": api_key(),
        }
        r = session.get(ETHERSCAN_API, params=params, timeout=40)
        r.raise_for_status()
        js = r.json()

        # Cas "No transactions found"
        if js.get("status") == "0" and js.get("message") == "No transactions found":
            break

        result = js.get("result", [])
        if not isinstance(result, list) or len(result) == 0:
            break

        for it in result:
            yield {
                "hash": it.get("hash"),
                "blockNumber": it.get("blockNumber"),
                "timeStamp": it.get("timeStamp"),
                "from": it.get("from"),
                "to": it.get("to"),
                "value_LPT": float(it.get("value", "0"))/1e18,
            }
        total += len(result)
        # Si la page n'est pas pleine, on a fini
        if len(result) < pagesize:
            break

        page += 1
        time.sleep(pause_s)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("address", help="Adresse Ethereum (ex: 0x...)")
    ap.add_argument("--out", required=True, help="CSV de sortie")
    # Fenêtre par blocs
    ap.add_argument("--startblock", type=int, default=None)
    ap.add_argument("--endblock",   type=int, default=None)
    # Fenêtre par dates (UTC)
    ap.add_argument("--startdate", type=str, default=None, help="YYYY-MM-DD")
    ap.add_argument("--enddate",   type=str, default=None, help="YYYY-MM-DD")
    # Contrôle pagination
    ap.add_argument("--pagesize", type=int, default=10000)
    ap.add_argument("--maxpages", type=int, default=None)  # sécurité si tu veux borner
    args = ap.parse_args()

    # Résoudre bloc range depuis dates si fourni
    sb = args.startblock
    eb = args.endblock
    if args.startdate or args.enddate:
        if not (args.startdate and args.enddate):
            sys.exit("Si vous utilisez les dates, fournissez --startdate ET --enddate.")
        ts_start = parse_date_iso(args.startdate, end=False)
        ts_end   = parse_date_iso(args.enddate,   end=True)
        if ts_start > ts_end:
            sys.exit("startdate > enddate.")
        sb = get_block_by_time(ts_start, closest="after")
        eb = get_block_by_time(ts_end,   closest="before")

    if sb is None: sb = 0
    if eb is None: eb = 99999999

    rows = []
    for row in fetch_transfers(
        address=args.address,
        startblock=sb,
        endblock=eb,
        pagesize=args.pagesize,
        pause_s=0.21,
        max_pages=args.maxpages,
    ):
        rows.append(row)

    # Écriture CSV
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["hash","blockNumber","timeStamp","from","to","value_LPT"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"✅ Exported {len(rows)} transfers to {args.out}")

if __name__ == "__main__":
    main()
