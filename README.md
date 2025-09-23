# ðŸ“Š Crypto AI Analytics  

Pipeline dâ€™analyses quantitatives (LPT, AVAX, GMX) : netflows, APY, corrÃ©lations, usage, productivitÃ©.  
Objectif : fournir des visuels et des notes type analyste **prÃªtes pour un recruteur ou un investisseur**.  

---

## ðŸš€ Quickstart

```bash
# 1. Cloner le repo
git clone https://github.com/cryptopromptaiHAH/crypto-ai-analytics.git
cd crypto-ai-analytics

# 2. CrÃ©er un environnement Python
python -m venv .venv
.venv\Scripts\activate   # (Windows PowerShell)

# 3. Installer les dÃ©pendances
pip install -r requirements.txt

# 4. Lancer le pipeline LPT (90 jours par dÃ©faut)
$env:PYTHONPATH = "$PWD"
python src/lpt/lpt_pipeline.py --days 90
```

ðŸ‘‰ Les rÃ©sultats apparaissent dans :  
- `outputs/` (CSVs analysables)  
- `docs/img/` (graphes PNG exportÃ©s)  

---

## ðŸ“‘ Reports
- `docs/top_netflow_zscore.md` â†’ Top Netflow Z-Score Days  
- `docs/summary_2025-05_focus.md` â†’ Mayâ€“June 2025 Focus Summary  
- `docs/ANALYSE_LPT_MAI-JUIN-2025.md` â†’ Detailed Analysis (Mayâ€“June 2025)  

---

## Data Caching & Attribution

- **Caching**  
  Les prix / market cap / volumes sont mis en cache local dans `data/cache_<coin>_<vs>_<days>d.csv`.  
  - Premier run â†’ fetch API + Ã©criture cache  
  - Runs suivants (mÃªmes paramÃ¨tres) â†’ lecture cache (runs beaucoup plus rapides âš¡)  
  - Forcer un refresh â†’ supprimer le fichier de cache correspondant ou relancer avec un autre `--days`.

- **API Key**  
  CrÃ©ez un fichier `.env` Ã  la racine avec :  
  ```bash
  COINGECKO_API_KEY=YOUR_API_KEY_HERE
  ```
> âš ï¸ Ne partagez jamais votre clÃ© API publique dans un dÃ©pÃ´t GitHub.  
> Vous pouvez obtenir une clÃ© gratuite sur [CoinGecko API](https://www.coingecko.com/en/api).

- **Attribution**  
  Data provided by [CoinGecko](https://www.coingecko.com/en/api).

---

âœï¸ **Author:** cryptopromptaiHAH  
ðŸ“… **Period analyzed:** Mayâ€“June 2025  
## ?? Core charts (90d)

![LPT ï¿½ APY 30j](docs/img/previews/lpt_apy_30d.jpg)

![LPT ? BTC/ETH ï¿½ Corr 30j](docs/img/previews/lpt_corr_30d.jpg)

![LPT ? BTC/ETH ï¿½ Corr 60j](docs/img/previews/lpt_corr_60d.jpg)

