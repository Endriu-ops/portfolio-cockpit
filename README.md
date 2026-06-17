# Portfolio Cockpit Alpha Pro v6.2

Fix principale:
- risoluzione ticker robusta con alias Yahoo
- ZPRV al posto di XZPRV
- colonna manual_price nel My Portfolio
- se Yahoo non trova il prezzo, usa manual_price
- se manca anche manual_price, usa avg_price come fallback prudenziale
- niente più P/L fittizi -100% per prezzo mancante
- tab Data Quality per identificare ticker non letti

Ticker alias principali:
- SXR8 -> SXR8.MI / SXR8.DE / SXR8.SW
- VUAA -> VUAA.MI / VUAA.DE / VUAA.L
- VWCE -> VWCE.MI / VWCE.DE / VWCE.SW
- ZPRV -> ZPRV.MI / ZPRV.DE
- MTHP.MI -> MTHP.MI / MTHP.PA
- CBTC.MI -> CBTC.MI / CBTC.SW / BTC-USD

Main file: app.py
