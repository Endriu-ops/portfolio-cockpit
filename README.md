# Portfolio Cockpit Alpha Pro V8.3 – Tax Optimization Engine

## Novità

### 1. Tax Budget annuale operativo
Monitora:
- tax budget annuale
- imposte già pagate
- budget residuo
- capacità residua di realizzo plusvalenze

### 2. Tax-aware Order Plan
Ogni operazione viene classificata:
- BUY_WITH_PAC
- SELL_ALLOWED
- DEFER_SELL_USE_PAC
- TAX_BLOCK
- HOLD

### 3. Deferred Sell Queue
Le vendite fiscalmente inefficienti vengono spostate in coda:
- differire
- usare PAC
- attendere gennaio
- compensare con minusvalenze

### 4. Tax-adjusted Alpha Score
Alpha Score corretto per fiscal drag potenziale.

### 5. PAC-first rebalancing
Gerarchia:
1. PAC / nuova liquidità
2. acquisti per ridurre sottopesi
3. vendite solo se fiscalmente accettabili
4. differimento se fiscalmente inefficiente

## File da caricare su GitHub
- app.py
- requirements.txt
- README.md
- portfolio_positions.csv

## Dopo il deploy
1. Clear cache / Reboot.
2. My Portfolio → Salva e aggiorna.
3. Apri Tax Optimizer Pro.
4. Controlla Budget residuo e Deferred Sell Queue.
