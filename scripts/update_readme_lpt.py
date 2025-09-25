# scripts/update_readme_lpt.py
# Met à jour README.md avec les graphes LPT générés.
# - Insère/rafraîchit le bloc délimité par:
#   <!-- LPT-ASSETS:START --> ... <!-- LPT-ASSETS:END -->
# - Supprime automatiquement l'ancienne section "Core charts (...)"
#
# Usage:
#   python scripts/update_readme_lpt.py [days] [vs]
#   ex: python scripts/update_readme_lpt.py 180 usd

from __future__ import annotations
from pathlib import Path
import re
import sys

MARK_START = "<!-- LPT-ASSETS:START -->"
MARK_END = "<!-- LPT-ASSETS:END -->"


def _ensure_src_on_path():
    here = Path(__file__).resolve()
    repo_root = here.parent.parent          # .../crypto-ai-analytics
    src_dir = repo_root / "src"
    if src_dir.exists():
        p = str(src_dir)
        if p not in sys.path:
            sys.path.insert(0, p)

_ensure_src_on_path()

from common import utils  # noqa: E402


def remove_legacy_core_charts(text: str) -> str:
    """
    Supprime tout bloc dont le titre commence par '## Core charts'.
    On enlève jusqu'au prochain '## ' ou la fin de fichier.
    """
    pattern = re.compile(r"^##\s+Core charts.*?(?=^##\s+|\Z)", re.DOTALL | re.MULTILINE)
    return re.sub(pattern, "", text).strip() + "\n"


def build_block(days: int, vs: str) -> str:
    """Construit le bloc markdown à insérer dans le README."""
    required = [
        Path("outputs/lpt_price_ema.png"),
        Path("outputs/lpt_zscore.png"),
        Path("outputs/lpt_apy.png"),
        Path("outputs/lpt_corr.png"),   # NEW
    ]
    missing = [p for p in required if not p.exists()]
    if missing:
        miss_list = ", ".join(str(m) for m in missing)
        raise FileNotFoundError(
            f"Fichier(s) manquant(s): {miss_list}. Lance d'abord 'python scripts/generate_lpt_assets.py'."
        )

    today = utils.utc_today().isoformat()
    return f"""
{MARK_START}
## LPT — Graphes (auto-générés)

*Dernière mise à jour (UTC): **{today}** — Fenêtre: **{days} jours** — Devise: **{vs.upper()}***

**Price & EMAs**
![LPT Price & EMAs](outputs/lpt_price_ema.png)

**Z-Score (60j)**
![LPT Z-Score](outputs/lpt_zscore.png)

**Rolling APY (30j)**
![LPT APY](outputs/lpt_apy.png)

**Corrélation (60j) — vs BTC & ETH**
![LPT Corr](outputs/lpt_corr.png)
{MARK_END}
""".strip()


def upsert_block(readme_path: Path, days: int, vs: str) -> bool:
    """Insère/remplace le bloc LPT-ASSETS dans README.md et retire 'Core charts' legacy."""
    text = readme_path.read_text(encoding="utf-8")
    text = remove_legacy_core_charts(text)

    block = build_block(days=days, vs=vs)

    if MARK_START in text and MARK_END in text:
        # Remplacement in-place
        pre, _, tail = text.partition(MARK_START)
        _, _, post = tail.partition(MARK_END)
        new_text = pre + block + post
    else:
        # Ajout en fin de fichier
        sep = "\n\n---\n\n" if text and not text.endswith("\n") else "\n\n---\n\n"
        new_text = text + sep + block + "\n"

    if new_text != text:
        readme_path.write_text(new_text, encoding="utf-8", newline="\n")
        return True
    return False


def main():
    repo_root = Path(__file__).resolve().parent.parent
    readme_path = repo_root / "README.md"

    if not readme_path.exists():
        print("[-] README.md non trouvé.")
        return 1

    days = int(sys.argv[1]) if len(sys.argv) >= 2 else 180
    vs = sys.argv[2] if len(sys.argv) >= 3 else "usd"

    if upsert_block(readme_path, days=days, vs=vs):
        print(f"[OK] Mise à jour: {readme_path}")
    else:
        print(f"[=] Aucun changement: {readme_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
