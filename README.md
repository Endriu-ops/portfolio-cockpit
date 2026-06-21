# Portfolio Cockpit Alpha Pro V8.2 Operativa

## Nuove funzioni

### 1. PAC Mode Selector
- Rebalance: distribuisce il PAC sui sottopesi.
- Alpha: 70% sui migliori Alpha Score + 30% riequilibrio.
- Tactical: 100% sul miglior Alpha Score.

### 2. Alpha Score Engine
Formula:
- 50% Tactical Ranking
- 30% Relative Strength
- 20% Drift Opportunity

### 3. Dynamic Drift Bands
- Core: ±20% relativo al target, minimo 2 pp.
- Satellite: ±50% relativo al target, minimo 2 pp.

### 4. Dynamic Satellite Mode
- Static: satellite attuale.
- Dynamic: top 3 dal Tactical Ranking.

### 5. Tax-Aware Rebalance Lite
Prima di vendere, il sistema verifica se PAC/nuova liquidità può correggere il drift.

### 6. Alpha Readiness Score
Score sintetico 0-100 su regime, alpha score, market risk e data quality.

## File da caricare su GitHub
- app.py
- requirements.txt
- README.md
- portfolio_positions.csv

## Dopo il deploy
1. Clear cache / Reboot.
2. My Portfolio → Salva e aggiorna.
3. Alpha Score → verifica ranking.
4. PAC Alpha → verifica suggerimenti.
5. Satellite Auto → prova Static/Dynamic.
