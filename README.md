# Portfolio Cockpit Alpha Pro V8.2.1 Hotfix

## Fix principale

Risolto errore:

```text
NameError: dynamic_satellite_plan_v82 is not defined
```

La funzione è stata aggiunta con fallback sicuro:

- Static → `satellite_plan()`
- Dynamic → Top 3 Tactical Ranking
- Se ranking non disponibile → fallback a Static

## File da caricare su GitHub

- app.py
- requirements.txt
- README.md
- portfolio_positions.csv

## Dopo il deploy

1. Clear cache / Reboot.
2. Apri Home Operativa.
3. Verifica Satellite attuale.
4. Prova Satellite Mode Static/Dynamic.
