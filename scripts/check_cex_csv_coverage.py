#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_cex_csv_coverage.py

Vérifie qu’un CSV (export get_lpt_multi_cex.py pour une adresse CEX) couvre
bien la période demandée et s’il risque d’être tronqué par la limite de pages.

Entrées:
  --csv PATH           Fichier CSV à contrôler
  --start YYYY-MM-DD   Début de fenêtre demandée
  --end   YYYY-MM-DD   Fin de fenêtre demandée
  --hard_max INT       Seuil "pile" lignes (ex: 10000) pour suspecter un cut (défaut 10000)
  --tolerance_days INT Tolérance de décalage aux bords (défaut 1 jour)

Sortie: résumé lisible + code retour 0 (OK) / 2 (suspicion de troncature).
"""

import argparse
from pathlib import Path
import sys
import pandas as pd
from datetime import datetime, timezone

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end",   required=True, help="YYYY-MM-DD")
    ap.add_argument("--hard_max", type=int, default=10000)
    ap.add_argument("--tolerance_days", type=int, default=1)
    args = ap.parse_args()

    p = Path(args.csv)
    if not p.exists():
        print(f"[ERR] CSV introuvable: {p}")
        sys.exit(1)

    df = pd.read_csv(p)
    if df.empty:
        print("[INFO] CSV vide.")
        sys.exit(0)

    # Convertir timeStamp UNIX -> datetime UTC
    if "timeStamp" not in df.columns:
        print("[ERR] Colonne 'timeStamp' absente.")
        sys.exit(1)

    # to_numeric pour éviter les strings
    df["timeStamp"] = pd.to_numeric(df["timeStamp"], errors="coerce")
    df = df.dropna(subset=["timeStamp"])
    df["dt"] = pd.to_datetime(df["timeStamp"], unit="s", utc=True)

    # borne demandée
    s = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    e = datetime.strptime(args.end,   "%Y-%m-%d").replace(tzinfo=timezone.utc)

    n = len(df)
    dmin = df["dt"].min()
    dmax = df["dt"].max()

    # gaps aux bords
    gap_start_days = (dmin - s).total_seconds() / 86400.0
    gap_end_days   = (e - dmax).total_seconds() / 86400.0

    print("=== COVERAGE REPORT ===")
    print(f"File        : {p.name}")
    print(f"Rows        : {n:,}")
    print(f"Asked range : {s.date()} → {e.date()}")
    print(f"Data range  : {dmin.date()} → {dmax.date()}")
    print(f"Start gap   : {gap_start_days:+.2f} day(s) (positive = data starts AFTER requested start)")
    print(f"End gap     : {gap_end_days:+.2f} day(s)   (positive = data ends   BEFORE requested end)")

    # Heuristiques de troncature
    truncated = False
    reasons = []

    # 1) pile la "taille max"
    if n >= args.hard_max:
        truncated = True
        reasons.append(f"rows ==/>= hard_max ({args.hard_max}) ⇒ possible page limit")

    # 2) data ne touche pas les bords (au-delà tolérance)
    if gap_start_days > args.tolerance_days:
        truncated = True
        reasons.append(f"data starts {gap_start_days:.2f}d AFTER requested start (> tol {args.tolerance_days}d)")
    if gap_end_days > args.tolerance_days:
        truncated = True
        reasons.append(f"data ends {gap_end_days:.2f}d BEFORE requested end (> tol {args.tolerance_days}d)")

    if truncated:
        print("\n⚠️  SUSPICION: DATA MAY BE TRUNCATED")
        for r in reasons:
            print(f" - {r}")
        print("\nNext steps:")
        print(" - Réduire la fenêtre (ex: scinder en 2025-05-01→2025-05-20 puis 2025-05-21→2025-06-05)")
        print(" - Ou rejouer avec --sort asc/desc et vérifier les bords (min/max)")
        sys.exit(2)
    else:
        print("\n✅ Coverage OK (aucun signe clair de troncature)")
        sys.exit(0)

if __name__ == "__main__":
    main()
