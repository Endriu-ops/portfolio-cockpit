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
