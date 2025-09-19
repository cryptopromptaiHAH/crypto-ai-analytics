\# Crypto AI Analytics – Livepeer (LPT) On-Chain Data



\## 📌 Description

Ce projet vise à analyser les flux on-chain liés au token \*\*Livepeer (LPT)\*\* afin de détecter les signaux précoces de \*\*pression acheteuse/vendeuse\*\* et leur impact potentiel sur le prix.



\## 📂 Dataset inclus

\### `lpt\_transfers\_binance\_hotwallet20.csv`

Extrait des transferts ERC-20 du token \*\*LPT\*\* pour l’adresse \*\*Binance Hot Wallet 20\*\*  

`0xF977814e90dA44bFA03b6295A0616a897441aceC`



\#### Colonnes :

\- `hash` → identifiant unique de la transaction  

\- `blockNumber` → numéro du bloc Ethereum  

\- `timeStamp` → horodatage UNIX (en secondes)  

\- `from` → adresse expéditeur  

\- `to` → adresse destinataire  

\- `value\_LPT` → montant transféré en LPT (normalisé en unités humaines)



\#### Exemple :

| hash | blockNumber | timeStamp | from | to | value\_LPT |

|------|-------------|-----------|------|----|-----------|

| 0x0056...c676 | 12650622 | 1623915020 | 0x28c6...21d60 | 0xf977...1acec | 476,851.50 |



---



\## 🔎 Analyse rapide

\- Les volumes observés (250k à 476k LPT) correspondent à des \*\*mouvements internes entre CEX\*\*, typiques de \*\*rééquilibrages de liquidité\*\*.  

\- Les entrées massives de LPT sur Binance peuvent être interprétées comme un \*\*signal de pression vendeuse\*\* (préparation à la vente).  

\- À l’inverse, des sorties massives de CEX vers des wallets privés/orchestrateurs indiquent souvent une \*\*phase d’accumulation\*\*.  

\- Le suivi de ces flux est un \*\*indicateur avancé\*\* de volatilité et complète utilement les métriques de marché (open interest, funding rate, prix spot).



---



\## 🚀 Prochaines étapes

\- Étendre l’analyse à d’autres \*\*CEX (Kraken, Coinbase, Gate, etc.)\*\*.  

\- Suivre également les \*\*orchestrateurs top 20 Livepeer\*\* pour corréler staking/unbonding avec la pression de vente.  

\- Automatiser un \*\*dashboard temps réel\*\* combinant flux on-chain + métriques de marché (Coinglass).



---



\## 🎓 Note pédagogique

Ce projet est développé dans le cadre d’une \*\*formation intensive en ingénierie blockchain \& IA appliquée au trading crypto\*\*.  

Il illustre mes progrès étape par étape :  

\- \*\*Semaine 1 :\*\* environnement + premier script on-chain + dataset LPT/ Binance.  

\- Les étapes suivantes viseront à enrichir l’analyse et automatiser la détection de signaux de marché.  



---



✍️ \*\*Auteur :\*\* cryptopromptaiHAH  

📅 \*\*Premier dataset :\*\* Septembre 2025



