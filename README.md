
# Crypto AI Analytics – Livepeer (LPT) On-Chain Data

## 📌 Description
This project aims to analyze on-chain flows related to the **Livepeer (LPT)** token in order to detect early signals of **buying/selling pressure** and their potential impact on price.

## 📂 Included Dataset
### `lpt_transfers_binance_hotwallet20.csv`
Extract of **LPT ERC-20 transfers** for the address **Binance Hot Wallet 20**  
`0xF977814e90dA44bFA03b6295A0616a897441aceC`

#### Columns:
- `hash` → unique transaction identifier  
- `blockNumber` → Ethereum block number  
- `timeStamp` → UNIX timestamp (in seconds)  
- `from` → sender address  
- `to` → recipient address  
- `value_LPT` → transferred amount in LPT (normalized to human-readable units)

#### Example:
| hash | blockNumber | timeStamp | from | to | value_LPT |
|------|-------------|-----------|------|----|-----------|
| 0x0056...c676 | 12650622 | 1623915020 | 0x28c6...21d60 | 0xf977...1acec | 476,851.50 |

---

## 🔎 Quick Analysis
- The observed volumes (250k to 476k LPT) correspond to **internal CEX movements**, typical of **liquidity rebalancing**.  
- Large inflows of LPT into Binance can be interpreted as a **sell pressure signal** (tokens being prepared for sale).  
- Conversely, large outflows from CEX to private wallets/orchestrators often indicate an **accumulation phase**.  
- Monitoring these flows acts as an **early volatility indicator**, complementing market metrics (open interest, funding rate, spot price).

---

## 🚀 Next Steps
- Extend analysis to other **CEXs (Kraken, Coinbase, Gate, etc.)**.  
- Track **top 20 Livepeer orchestrators** to correlate staking/unbonding events with selling pressure.  
- Automate a **real-time dashboard** combining on-chain flows + market metrics (Coinglass).

---

## 🎓 Educational Note
This project is developed as part of an **intensive training program in blockchain & AI engineering applied to crypto trading**.  
It documents my progress step by step:  
- **Week 1:** environment setup + first on-chain script + Binance LPT dataset.  
- Next steps will aim to enrich the analysis and automate signal detection.  

---

✍️ **Author:** cryptopromptaiHAH  
📅 **First dataset:** September 2025


