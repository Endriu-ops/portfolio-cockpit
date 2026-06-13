# Portfolio Cockpit Definitive

Dashboard Streamlit per portafoglio core/satellite con:
- monitor portafoglio
- ribilanciamento ±5 punti percentuali
- dashboard macro
- segnali tattici settoriali
- backtest 10 anni semplificato
- tracking performance
- paper trading
- FRED API
- Alpha Vantage opzionale
- CFTC COT opzionale
- Fear & Greed proxy
- Baltic Dry proxy
- Put/Call placeholder
- Telegram alert opzionale

## Deploy su Streamlit Cloud

1. Estrai lo ZIP.
2. Carica TUTTI i file su GitHub nel repository `portfolio-cockpit`.
3. Vai su https://share.streamlit.io
4. New App
5. Repository: `Endriu-ops/portfolio-cockpit`
6. Branch: `main`
7. Main file: `app.py`
8. Deploy

## Secrets Streamlit Cloud

In Streamlit Cloud > App > Settings > Secrets, inserisci:

```toml
FRED_API_KEY = "LA_TUA_KEY"
ALPHA_VANTAGE_API_KEY = "LA_TUA_KEY"
NASDAQ_DATA_LINK_API_KEY = ""
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
```

Solo FRED è fortemente consigliata. Le altre sono opzionali.

## Uso operativo

- Core 80%: ribilanciamento ±5 pp.
- Satellite 20%: rotazione solo con score >75.
- Se nessun tema >60: satellite in cash/bond breve.
- Frequenza decisionale consigliata: settimanale/mensile, non intraday.
- Prima di capitale reale: paper trading 3-6 mesi.

## Nota

Strumento educativo e decisionale. Non è consulenza finanziaria personalizzata.
