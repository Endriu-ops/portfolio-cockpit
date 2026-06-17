# Portfolio Cockpit Alpha Pro v6.1

Versione deployabile completa.

## Modifiche principali

- Rimossi VUSA.MI e WSML.MI da Allocation e My Portfolio template.
- Filtrati VUSA.MI e WSML.MI anche dal CSV salvato.
- Inseriti ETF reali/analoghi:
  - SXR8 = S&P500 / ETF reale utente
  - XZPRV = Small Cap Value / ETF reale utente
- Satellite v6.1:
  - AI 5% fisso
  - Defense 5% fisso
  - Tattico dinamico 3%
- Se Regime Score <45 o VIX >=60:
  - il 3% tattico va in XEON/bond breve
  - AI e Defense restano strategici
- Decision Engine, Regime Engine, Drift Monitor e Stress Test mantenuti.
- Inserimento manuale stabile mantenuto.
- CSV persistenti mantenuti.

## Deploy

Caricare su GitHub:

- app.py
- requirements.txt
- README.md

Dopo il deploy:
1. Aprire My Portfolio.
2. Premere Reset Template.
3. Reinserire o caricare i dati corretti.
4. Premere Salva e aggiorna portafoglio.
