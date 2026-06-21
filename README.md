# Portfolio Cockpit Alpha Pro — v8.0

## Novità rispetto a v7.2

### 1. Price Sanity Check
- Ogni prezzo Yahoo viene verificato: se devia >50% dalla chiusura precedente o è fuori dal range 52w → warning globale prominente
- Impedisce che split non aggiustati o dati errati entrino silenziosamente nel calcolo

### 2. AVG_FALLBACK bloccato con errore prominente
- Se un ticker usa avg_price come fallback prezzo, banner rosso in cima all'app
- Il campo `price_status` (YAHOO/MANUAL/AVG_FALLBACK/MISSING) è visibile in Data Quality
- I segnali per ETF con AVG_FALLBACK/MISSING sono evidenziati come inaffidabili

### 3. Lista Ordini Prioritizzati (tab "Segnali & Ordini")
- Nuova tab dedicata con ordini concreti: ticker, azione, quote, valore in €, imposta stimata, timing
- Priorità 1=PAC/FIX urgente · 2=BUY sottopeso · 3=SELL overweight · 4=DEFER fiscale
- Include analisi fiscale per ogni vendita: rinvia se tax drag >10%

### 4. PAC Advisor (tab dedicata)
- Distribuisce rata mensile proporzionalmente agli ETF più sottopesati
- Nessuna vendita → zero imposta
- Numero tranche DCA adattivo al VIX (più volatile = più rate)
- Grafico distribuzione rata

### 5. Nuovi indicatori macro
- **LEI (USSLIND)**: Conference Board Leading Economic Index
- **PCE Core (PCEPILFE)**: inflazione target Fed (più preciso di CPI)
- **Jobless Claims (ICSA)**: segnale lavoro settimanale
- **Put/Call Ratio**: sentiment contrarian
- Regime engine ora su 14 componenti (era 10)
- Scores tab mostra tutti i nuovi indicatori

### 6. Stress Test Beta-Adjusted
- Ogni ETF ora usa il proprio **beta storico** calcolato via yfinance (3 anni)
- Shock = beta × shock benchmark (non più shock fisso per classe)
- ZPRV, RBOT, SMH hanno beta >1 → shock correttamente amplificati
- SGLD, IBGS, MTHP usano direttamente lo shock del loro benchmark (gold/TLT)
- Mostra: ticker, beta, benchmark usato, shock benchmark, shock ETF, P&L stimato

### 7. UX Semplificata
- Nuova tab **Home Operativa**: vista rapida con azione consigliata, metriche chiave, donut allocazione, 6 score macro
- Tab operative in prima posizione (Home, My Portfolio, Segnali & Ordini, PAC Advisor, Transazioni)
- Tab analitiche dopo (Scores, Decision Engine, Mercati, FRED, ecc.)
- 23 tab totali (vs 22) ma struttura più logica

## Deploy

1. Carica su GitHub:
   - `app_v8.py` (rinomina in `app.py`)
   - `requirements_v8.txt` (rinomina in `requirements.txt`)
   - `portfolio_positions.csv`

2. Streamlit Cloud → gestisci i secrets:
   - `FRED_API_KEY` = tua key FRED (gratuita su fred.stlouisfed.org)
   - `TELEGRAM_BOT_TOKEN` (opzionale)
   - `TELEGRAM_CHAT_ID` (opzionale)

3. Flusso primo avvio:
   - Tab "My Portfolio" → compila o importa CSV
   - Premi "Salva e aggiorna portafoglio"
   - Vai a "Home Operativa" per la vista generale
   - Vai a "Segnali & Ordini" per gli ordini prioritizzati
   - Vai a "PAC Advisor" per la rata mensile

## Note importanti
- senza FRED_API_KEY i dati macro (yield curve, credit spread, ecc.) non si caricano
- I beta vengono calcolati via yfinance (cache 24h) — primo caricamento più lento
- AVG_FALLBACK viene mostrato come errore prominente: correggere il ticker prima di operare
