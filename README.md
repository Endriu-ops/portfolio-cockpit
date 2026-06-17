# Portfolio Cockpit Alpha Pro v6.9

## Novità

- VUAA e VWCE inseriti stabilmente nel My Portfolio.
- `portfolio_positions.csv` aggiornato con:
  - VUAA 203 @ 108.4737
  - VWCE 4 @ 161.97
- VUAA/VWCE/SXR8 gestiti come equivalenti dell'Equity Core.
- Il target Equity Core 22% viene distribuito tra SXR8, VUAA e VWCE in base al valore reale detenuto.
- Evita falsi segnali SELL su VUAA/VWCE solo perché non erano nel CORE principale.
- Mantiene:
  - BTC spot
  - MTHP via MTH.PA
  - resolver sicuro DFEN/SMH
  - Tax Engine monitor-only
  - Persistence Engine

## File da caricare su GitHub

- app.py
- requirements.txt
- README.md
- portfolio_positions.csv

## Dopo il deploy

1. Apri My Portfolio.
2. Premi Carica CSV salvato oppure Reset valori precompilati.
3. Premi Salva e aggiorna portafoglio.
4. Controlla Data Quality.
