# Portfolio Cockpit Alpha Pro v6.7

## Fix principale

Il Tax Engine non tassa più automaticamente ogni scostamento dal target.

Prima:
- se una posizione era sopra target, la app simulava automaticamente una vendita;
- questo generava tasse stimate elevate;
- il Tax Efficiency Score poteva scendere a 25/100 anche senza una reale decisione di vendita.

Ora:
- modalità default = Monitor Only;
- mostra plusvalenze latenti;
- non penalizza il Decision Center;
- le tasse da ribilanciamento si calcolano solo se attivi `Simula tasse da rebalance` nella sidebar.

## Perché vedevi tasse alte

SMH era molto sopra il target tattico del 3%.
La vecchia logica assumeva:
SMH sopra target -> vendi -> tassa immediata.

La v6.7 separa:
- monitoraggio fiscale
- simulazione ribilanciamento
- decisione operativa reale

## Deploy

Caricare su GitHub:
- app.py
- requirements.txt
- README.md
- portfolio_positions.csv
