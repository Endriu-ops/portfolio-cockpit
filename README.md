# Portfolio Cockpit Alpha Pro v6.4

Fix principale:
- MTHP.MI ora usa come fonte primaria MTH.PA su Yahoo Finance.
- MTHP.MI non dovrebbe più finire in AVG_FALLBACK.
- BTC spot mantenuto.
- Data Quality mantenuta.
- manual_price fallback mantenuto.

## Nota MTHP

MTHP.MI nel portafoglio viene risolto così:

1. MTH.PA
2. MTH.FR
3. MTHP.MI
4. MTHP.PA

Il prezzo corrente dovrebbe essere letto in area 74-75 EUR, invece del vecchio fallback PMC 73.1012.

## Deploy

Caricare su GitHub:

- app.py
- requirements.txt
- README.md

Poi:
1. Streamlit → Clear cache
2. Rerun/Reboot
3. Data Quality → verifica MTHP.MI source = MTH.PA e status = YAHOO
