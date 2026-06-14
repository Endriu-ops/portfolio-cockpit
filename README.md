# Portfolio Cockpit Alpha Pro

Versione Alpha Pro con:
- Core 87% + satellite dinamico 13%
- Regime Score
- Alpha Score
- Tactical Allocation Score
- 78 indicatori/proxy potenziali
- FRED API
- Yahoo Finance
- relative strength
- liquidity score
- macro score
- breadth proxy
- sector ranking
- rebalance ±5
- paper trading
- Telegram alert

## Deploy

Carica tutti i file su GitHub.
Streamlit Cloud > main file: `app.py`

## Secrets consigliati

```toml
FRED_API_KEY = "..."
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
```

FRED è la chiave più importante.
