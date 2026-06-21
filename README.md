# Portfolio Cockpit Alpha Pro V7.2

## Novità

### Defense fix definitivo
- Sostituito `DFEN.MI` con `DFNS.MI`.
- `DFNS.MI` = VanEck Defense UCITS ETF su Borsa Italiana.
- Alias Yahoo:
  - DFNS.MI
  - DFNS
  - DFEN.DE
  - DFNS.PA
  - DFNS.L

### My Portfolio permanente aggiornato
- DFNS.MI: 146 quote @ 53.46
- RBOT.MI: 428 quote @ 18.26

### Portfolio baseline
- IBGS.MI 98 @ 139.90
- MTHP.MI 193 @ 73.1012
- SGLD.MI 70.974 @ 208.48
- SXR8 10.419 @ 588.85
- ZPRV 407 @ 66.241
- BTC 0.126 @ 70381.31
- CMOD.MI 460 @ 27.195
- GDX.MI 110 @ 85.01
- VWCE 4 @ 161.97
- VUAA 203 @ 108.4737
- DFNS.MI 146 @ 53.46
- RBOT.MI 428 @ 18.26
- SMH 46 @ 101.18

### Data Quality
- Fallback PMC ora segnalato come warning.
- Health Score penalizzato se esistono AVG_FALLBACK o MISSING.

### Moduli mantenuti
- Extended 10Y Proxy Backtest
- Crisis Dashboard
- VIX Adaptive Engine
- Attribution
- Stress Test Pro
- Fiscal Optimizer
- Portfolio Persistence Engine

## Deploy

Caricare su GitHub:
- app.py
- requirements.txt
- README.md
- portfolio_positions.csv

Dopo il deploy:
1. My Portfolio
2. Reset valori precompilati oppure Carica CSV salvato
3. Salva e aggiorna portafoglio
4. Data Quality: verificare DFNS.MI
