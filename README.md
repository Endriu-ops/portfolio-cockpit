# Portfolio Cockpit Alpha Pro V7.3 Hotfix

## Fix

Risolto errore:

```text
AttributeError su r["deviation_pp"].abs()
```

Causa:
`.abs()` era applicato a un valore scalare dentro `pac_advisor()`.

Fix:
`abs(float(r["deviation_pp"]))`

## Deploy

Caricare su GitHub:

- app.py
- requirements.txt
- README.md
- portfolio_positions.csv

Poi fare Rerun/Clear cache su Streamlit.
