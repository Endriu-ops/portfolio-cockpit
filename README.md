# Portfolio Cockpit Alpha Pro V7.1

## Novità

### Professional Backtest V7.1

Aggiunta doppia modalità:

1. Real ETF History
   - usa solo lo storico reale degli ETF;
   - se un ETF è giovane, il periodo comune può fermarsi a circa 2 anni.

2. Extended 10Y Proxy History
   - usa proxy storici per ETF giovani;
   - permette un backtest più vicino a 10 anni.

## Proxy principali

- IBGS.MI → SHY
- MTHP.MI → TLT
- SGLD.MI → GLD
- SXR8 / VUAA → SPY
- VWCE → VT
- ZPRV → VBR
- BTC → BTC-USD
- CMOD.MI → DBC
- GDX.MI → GDX
- DFEN.MI → ITA
- RBOT.MI → XLK
- SMH → SMH
- XEON.MI → SHY

## Deploy

Caricare su GitHub:

- app.py
- requirements.txt
- README.md
- portfolio_positions.csv

Dopo il deploy:
1. Professional Backtest.
2. Seleziona Extended 10Y Proxy History.
3. Esegui.
4. Controlla Start, End e Years effettivi.
