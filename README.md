# Portfolio Cockpit Alpha Pro v11.0 Stable

Build stabile derivata dal repository completo.

## Correzioni
- Rimosso definitivamente `DFEN.MI`; resta solo `DFNS.MI`.
- Normalizzato `portfolio_positions.csv`.
- Disattivati blocchi sperimentali instabili:
  - Geographic PAC automatico
  - EEM policy automatica
  - VWCE path simulation
- Aggiunti fallback stabili per evitare NameError runtime.
- Riallineata lista tabs con i blocchi UI.
- Verificata compilazione Python di `app.py`.

## File da caricare su GitHub
- app.py
- requirements.txt
- README.md
- portfolio_positions.csv

Dopo il deploy:
- Streamlit → Clear cache
- Streamlit → Reboot app


## v11.1 SAT3 Cooldown Update

Questa versione aggiunge una memoria persistente per il satellite tattico SAT3.

- `MIN_SAT3_HOLDING_DAYS = 90`
- stato salvato in `satellite_state.csv`
- rotazione bloccata prima di 90 giorni
- eccezioni: risk-off/VIX panic oppure score dell'attuale SAT3 sotto 45
- nuova sezione nella tab `Satellite Auto` con stato, giorni detenuti e reset manuale

Il file `satellite_state.csv` viene creato automaticamente alla prima esecuzione.
