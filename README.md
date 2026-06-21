# Portfolio Cockpit Alpha Pro V8.1 Candidate

## Correzioni implementate

1. PAC Advisor hardening
- Corretto `.abs()` su scalare.
- Usa `abs(float(r["deviation_pp"]))` dentro `iterrows()`.

2. DFNS / VanEck Defense UCITS ETF
- Normalizzato `DFEN.MI → DFNS.MI`.
- Alias:
  - DFNS.MI
  - DFNS
  - DFEN.DE
  - DFNS.PA
  - DFNS.L

3. Persistence policy
- `portfolio_positions.csv` = fonte primaria.
- GitHub Gist = backup opzionale.

4. Backtest 10Y
- Aggiunta verifica periodo effettivo.
- Warning se backtest 10Y produce meno di 9 anni.
- Tabella ticker/proxy limitanti.

5. Price sanity
- ETF: 20%
- BTC: 40%

## File da caricare su GitHub

- app.py
- requirements.txt
- README.md
- portfolio_positions.csv

## Dopo il deploy

1. Clear cache / Reboot Streamlit.
2. My Portfolio → Salva e aggiorna.
3. Data Quality → verificare DFNS.MI.
4. Professional Backtest → Extended 10Y Proxy History → controllare Years effettivi.
