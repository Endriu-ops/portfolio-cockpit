# Portfolio Cockpit Alpha Pro V9.0 — Regime & Crisis Engine

## Nuove funzioni

### Regime Engine V9
Classifica il mercato in:
- RISK ON
- NEUTRAL
- RISK OFF
- CRISIS

### Componenti
- VIX
- Trend 200DMA SPY / QQQ / IWM
- Breadth
- Credit
- Macro
- Liquidity
- Rates
- Dollar

### Dynamic Risk Budget
- Risk On: satellite fino a 15%, tactical 5%, PAC Alpha
- Neutral: satellite 13%, tactical 3%
- Risk Off: satellite 7%, tactical 0%, PAC Rebalance
- Crisis: satellite 0%, cash/core defensive

### Crisis Protocol
Regole operative per:
- VIX alto
- SPY/QQQ sotto 200DMA
- credit stress
- crash protocol

### Regime-aware PAC
Il PAC cambia destinazione in base al regime:
- Risk On/Neutral: Alpha
- Risk Off/Crisis: core difensivo, oro, bond, cash proxy

### Trade Guard
In Risk Off/Crisis blocca nuovi acquisti satellite.

## File da caricare su GitHub
- app.py
- requirements.txt
- README.md
- portfolio_positions.csv

## Dopo il deploy
1. Clear cache / Reboot.
2. Apri 🛡️ Regime & Crisis V9.
3. Controlla Regime, Risk Budget e Crisis Protocol.
4. Controlla Home Operativa e PAC Advisor.
