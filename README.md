# Portfolio Cockpit Alpha Pro v6.8

## Fix principale

Correzione ticker portfolio reale:

- `DFEN.MI` non usa più fallback verso `DFEN` USA.
- `SMH` non usa più fallback verso `SMH` USA.
- Il resolver prova:
  - DFEN.MI -> solo DFEN.MI
  - SMH -> solo SMH.MI
- Se Yahoo non trova il prezzo europeo corretto:
  - usa `manual_price` se presente
  - altrimenti usa `avg_price` come fallback
- Questo evita errori abnormi tipo:
  - DFEN = 80.9 da ticker USA
  - SMH = 627.5 da ETF USA

## Cosa fare dopo il deploy

1. Apri My Portfolio.
2. Per DFEN.MI e SMH verifica Data Quality.
3. Se uno dei due va in `AVG_FALLBACK`, inserisci il prezzo reale in `manual_price`.
4. Premi Salva e aggiorna portafoglio.

## File da caricare

- app.py
- requirements.txt
- README.md
- portfolio_positions.csv
