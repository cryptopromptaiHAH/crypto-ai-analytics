#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_lpt_transfers.py
--------------------
Télécharge l'historique des transferts LPT (ERC-20 Livepeer) pour une adresse ETH donnée,
via l'API Etherscan, et sauvegarde un CSV.

Prérequis:
  - Python 3.10+
  - pip install -r requirements.txt
  - Variable d'environnement ETHERSCAN_API_KEY définie

Utilisation (PowerShell):
  $env:ETHERSCAN_API_KEY="N8ZEVM9UVIYS1ZZQF93IJXINEDT56B3GJQN"
  python get_lpt_transfers.py 0xAdresseEth --out lpt_transfers.csv
"""
import os
import sys
import csv
import time
import argparse
import requests

ETHERSCAN_API = "https://api.etherscan.io/api"
LPT_CONTRACT  = "0x58b6a8a3302369daec383334672404ee733ab239"

def fetch_lpt_transfers(address: str, startblock=0, endblock=99999999, pagesize=10000, sort="asc"):
    api_key = os.getenv("ETHERSCAN_API_KEY", "").strip()
    if not api_key:
        sys.exit("Erreur: variable d'environnement ETHERSCAN_API_KEY manquante.")
    page = 1
    all_rows = []
    while True:
        params = {
            "module": "account",
            "action": "tokentx",
            "contractaddress": LPT_CONTRACT,
            "address": address,
            "page": page,
            "offset": pagesize,
            "startblock": startblock,
            "endblock": endblock,
            "sort": sort,
            "apikey": api_key,
        }
        r = requests.get(ETHERSCAN_API, params=params, timeout=40)
        r.raise_for_status()
        js = r.json()
        status = js.get("status")
        result = js.get("result", [])
        if status == "0" and js.get("message") == "No transactions found":
            break
        if not isinstance(result, list) or not result:
            break
        for it in result:
            all_rows.append({
                "hash": it.get("hash"),
                "blockNumber": it.get("blockNumber"),
                "timeStamp": it.get("timeStamp"),
                "from": it.get("from"),
                "to": it.get("to"),
                "value_LPT": float(it.get("value", "0"))/1e18,
            })
        if len(result) < pagesize:
            break
        page += 1
        time.sleep(0.2)  # limiter le rate
    return all_rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("address", help="Adresse Ethereum à analyser (ex: 0x...)")
    ap.add_argument("--out", default="lpt_transfers.csv", help="Nom du fichier CSV de sortie")
    ap.add_argument("--startblock", type=int, default=0)
    ap.add_argument("--endblock", type=int, default=99999999)
    ap.add_argument("--pagesize", type=int, default=10000)
    ap.add_argument("--sort", choices=["asc","desc"], default="asc")
    args = ap.parse_args()

    rows = fetch_lpt_transfers(args.address, args.startblock, args.endblock, args.pagesize, args.sort)
    if not rows:
        print("Aucune transaction trouvée.")
        open(args.out, "w", newline="", encoding="utf-8").close()
        return

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["hash","blockNumber","timeStamp","from","to","value_LPT"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"OK: {len(rows)} lignes écrites dans {args.out}")

if __name__ == "__main__":
    main()
