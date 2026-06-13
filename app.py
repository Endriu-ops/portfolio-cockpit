import os
import math
import json
import sqlite3
import requests
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(page_title="Portfolio Cockpit Definitive", layout="wide")

CORE_PORTFOLIO = {
    "SWDA.MI": {"name": "MSCI World", "target": 28.0, "bucket": "Core Equity"},
    "WSML.MI": {"name": "World Small Cap", "target": 7.0, "bucket": "Small Cap"},
    "SGLD.MI": {"name": "Physical Gold", "target": 13.0, "bucket": "Safe Haven Gold"},
    "AGGH.MI": {"name": "Global Aggregate Bond EUR Hedged", "target": 10.0, "bucket": "Bonds"},
    "XEON.MI": {"name": "EUR Overnight / Money Market", "target": 2.0, "bucket": "Cash"},
    "CMOD.MI": {"name": "Broad Commodities", "target": 7.0, "bucket": "Commodities"},
    "CBTC.MI": {"name": "Bitcoin ETP", "target": 5.0, "bucket": "Bitcoin"},
    "GDX.MI": {"name": "Gold Miners", "target": 8.0, "bucket": "Performance Gold"},
}

TACTICAL_PORTFOLIO = {
    "DFEN.MI": {"name": "Defense / NATO proxy", "target": 10.0, "bucket": "Tactical Defense"},
    "RBOT.MI": {"name": "AI & Automation proxy", "target": 10.0, "bucket": "Tactical AI"},
}

PORTFOLIO = {**CORE_PORTFOLIO, **TACTICAL_PORTFOLIO}
DEFAULT_BAND = 5.0

MARKET_TICKERS = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "Russell 2000": "^RUT",
    "VIX": "^VIX",
    "MOVE proxy / TLT": "TLT",
    "US Dollar Index": "DX-Y.NYB",
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Copper": "HG=F",
    "WTI Oil": "CL=F",
    "Brent Oil": "BZ=F",
    "Natural Gas": "NG=F",
    "US 10Y Yield": "^TNX",
    "Bitcoin": "BTC-USD",
    "EUR/USD": "EURUSD=X",
    "Baltic Dry proxy": "BDRY",
}

TACTICAL_WATCHLIST = {
    "Defense / NATO": ["DFEN.MI", "ITA", "XAR"],
    "AI / Automation": ["RBOT.MI", "BOTZ", "ROBO"],
    "Gold Miners": ["GDX.MI", "GDX"],
    "Energy": ["XLE", "IXC"],
    "Uranium": ["URA", "URNM"],
    "Healthcare": ["XLV", "IXJ"],
    "Financials": ["XLF", "IXG"],
    "Industrials": ["XLI", "EXI"],
    "Technology": ["XLK", "IYW"],
    "Semiconductors": ["SMH", "SOXX"],
    "Small Value": ["IJS", "VBR", "ZPRV.DE"],
    "Commodities": ["CMOD.MI", "DBC"],
}

FRED_SERIES = {
    "Fed Funds Rate": "FEDFUNDS",
    "US CPI": "CPIAUCSL",
    "US M2 Money Supply": "M2SL",
    "US 10Y Treasury": "DGS10",
    "US 2Y Treasury": "DGS2",
    "10Y-2Y Spread": "T10Y2Y",
    "High Yield Spread": "BAMLH0A0HYM2",
    "Investment Grade Spread": "BAMLC0A0CM",
    "CFNAI": "CFNAI",
    "Unemployment Rate": "UNRATE",
    "Industrial Production": "INDPRO",
    "Retail Sales": "RSAFS",
}

DB_PATH = "portfolio_cockpit.db"

# =========================================================
# SECRETS / UTILITIES
# =========================================================

def get_secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)

def fmt_pct(x):
    if x is None or pd.isna(x):
        return "n/a"
    return f"{x*100:.2f}%"

def fmt_num(x):
    if x is None or pd.isna(x):
        return "n/a"
    return f"{x:,.2f}"

# =========================================================
# DATA SOURCES
# =========================================================

@st.cache_data(ttl=3600)
def yf_history(ticker, period="5y", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def yf_last(ticker):
    df = yf_history(ticker, period="5d")
    if df.empty:
        return None
    return float(df["Close"].iloc[-1])

@st.cache_data(ttl=21600)
def fred_series(series_id):
    key = get_secret("FRED_API_KEY")
    if not key:
        return pd.DataFrame()
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": series_id, "api_key": key, "file_type": "json"}
    try:
        js = requests.get(url, params=params, timeout=20).json()
        df = pd.DataFrame(js.get("observations", []))
        if df.empty:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"].replace(".", pd.NA), errors="coerce")
        return df.set_index("date")[["value"]].dropna()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=21600)
def alpha_vantage_daily(symbol):
    key = get_secret("ALPHA_VANTAGE_API_KEY")
    if not key:
        return pd.DataFrame()
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": symbol,
        "outputsize": "compact",
        "apikey": key,
    }
    try:
        js = requests.get(url, params=params, timeout=20).json()
        k = "Time Series (Daily)"
        if k not in js:
            return pd.DataFrame()
        df = pd.DataFrame(js[k]).T
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df.rename(columns={
            "1. open": "Open",
            "2. high": "High",
            "3. low": "Low",
            "4. close": "Close",
            "5. adjusted close": "Adj Close",
            "6. volume": "Volume",
        })
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=21600)
def fear_greed_proxy():
    """
    Proxy gratuito interno:
    - VIX basso = greed
    - S&P sopra 200dma = greed
    - Nasdaq momentum = greed
    - breadth non disponibile gratuitamente in modo stabile
    """
    vix = yf_last("^VIX")
    sp = yf_history("^GSPC", period="1y")
    ndx = yf_history("^NDX", period="1y")
    score = 50
    components = []
    if vix is not None:
        if vix < 15:
            score += 20; components.append("VIX very low")
        elif vix < 20:
            score += 10; components.append("VIX low")
        elif vix > 30:
            score -= 25; components.append("VIX high")
        elif vix > 25:
            score -= 15; components.append("VIX elevated")
    if not sp.empty and len(sp) > 200:
        close = sp["Close"]
        ma200 = close.rolling(200).mean().iloc[-1]
        if close.iloc[-1] > ma200:
            score += 15; components.append("S&P above 200dma")
        else:
            score -= 15; components.append("S&P below 200dma")
    if not ndx.empty and len(ndx) > 63:
        mom = ndx["Close"].iloc[-1] / ndx["Close"].iloc[-64] - 1
        if mom > 0.08:
            score += 15; components.append("Nasdaq strong 3m")
        elif mom < -0.08:
            score -= 15; components.append("Nasdaq weak 3m")
    score = max(0, min(100, score))
    return score, components

@st.cache_data(ttl=86400)
def cftc_cot_disclaimer_table():
    """
    Placeholder operativo: il COT è gratuito ma richiede mapping contratti/mercati.
    Qui si segnala la disponibilità e si lascia struttura pronta.
    """
    rows = [
        {"Market": "Gold", "Status": "COT parsing non ancora automatizzato", "Use": "Commercials / Managed Money positioning"},
        {"Market": "Copper", "Status": "COT parsing non ancora automatizzato", "Use": "Industrial cycle / China proxy"},
        {"Market": "Oil", "Status": "COT parsing non ancora automatizzato", "Use": "Energy positioning"},
        {"Market": "S&P 500", "Status": "COT parsing non ancora automatizzato", "Use": "Equity futures positioning"},
    ]
    return pd.DataFrame(rows)

# =========================================================
# SIGNALS
# =========================================================

def pct_change(series, n):
    if len(series) <= n:
        return np.nan
    return float(series.iloc[-1] / series.iloc[-n-1] - 1)

def sma(series, n):
    if len(series) < n:
        return np.nan
    return float(series.rolling(n).mean().iloc[-1])

def volatility(series, n=63):
    r = series.pct_change().dropna()
    if len(r) < n:
        return np.nan
    return float(r.tail(n).std() * math.sqrt(252))

def max_drawdown(series):
    if len(series) < 2:
        return np.nan
    dd = series / series.cummax() - 1
    return float(dd.min())

def momentum_score(close):
    close = close.dropna()
    if len(close) < 130:
        return np.nan
    raw = 0.20*pct_change(close,21) + 0.35*pct_change(close,63) + 0.45*pct_change(close,126)
    return float(100 / (1 + np.exp(-raw * 12)))

def trend_score(close):
    close = close.dropna()
    if len(close) < 200:
        return np.nan
    last, ma50, ma200 = float(close.iloc[-1]), sma(close,50), sma(close,200)
    score = 50
    if last > ma50:
        score += 20
    if last > ma200:
        score += 20
    if ma50 > ma200:
        score += 10
    return float(max(0, min(100, score)))

def vol_penalty(close):
    vol = volatility(close, 63)
    if pd.isna(vol):
        return 0
    return max(0, min(25, (vol - 0.25) * 60))

def macro_regime_score():
    score = 50
    notes = []
    vix = yf_last("^VIX")
    sp = yf_history("^GSPC", "1y")
    copper = yf_history("HG=F", "1y")
    gold = yf_history("GC=F", "1y")

    if vix is not None:
        if vix < 15:
            score += 15; notes.append("VIX basso: risk-on")
        elif vix < 20:
            score += 5; notes.append("VIX moderato")
        elif vix > 30:
            score -= 20; notes.append("VIX alto: risk-off")
        elif vix > 25:
            score -= 10; notes.append("VIX elevato")

    if not sp.empty and len(sp) > 200:
        ma200 = sp["Close"].rolling(200).mean().iloc[-1]
        if sp["Close"].iloc[-1] > ma200:
            score += 10; notes.append("S&P sopra 200dma")
        else:
            score -= 10; notes.append("S&P sotto 200dma")

    if not copper.empty and not gold.empty:
        ratio = (copper["Close"] / gold["Close"]).dropna()
        if len(ratio) > 63:
            mom = ratio.iloc[-1] / ratio.iloc[-64] - 1
            if mom > 0:
                score += 5; notes.append("Copper/Gold positivo")
            else:
                score -= 5; notes.append("Copper/Gold negativo")

    return max(0, min(100, score)), notes

def tactical_score(close, macro_score=50):
    ms, ts = momentum_score(close), trend_score(close)
    if pd.isna(ms) or pd.isna(ts):
        return np.nan
    score = 0.40*ms + 0.35*ts + 0.15*macro_score + 0.10*(100-vol_penalty(close))
    return float(max(0, min(100, score)))

def signal_from_score(score):
    if pd.isna(score):
        return "NO DATA"
    if score >= 75:
        return "OVERWEIGHT / BUY"
    if score >= 60:
        return "HOLD"
    if score >= 45:
        return "NEUTRAL"
    return "REDUCE / EXIT"

def rebalance_table(positions, targets, band):
    df = positions.copy()
    df["value"] = df["shares"] * df["price"]
    total = df["value"].sum()
    df["current_weight"] = 0 if total <= 0 else df["value"] / total * 100
    df["target_weight"] = df["ticker"].map(targets).fillna(0)
    df["deviation_pp"] = df["current_weight"] - df["target_weight"]
    df["target_value"] = total * df["target_weight"] / 100
    df["trade_value"] = df["target_value"] - df["value"]
    df["action"] = np.where(
        df["deviation_pp"] > band, "SELL/TRIM",
        np.where(df["deviation_pp"] < -band, "BUY/ADD", "HOLD")
    )
    return df

# =========================================================
# DATABASE
# =========================================================

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        signal_date TEXT,
        ticker TEXT,
        action TEXT,
        target_weight REAL,
        reason TEXT,
        result TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        total_value REAL,
        data_json TEXT
    )
    """)
    con.commit()
    con.close()

def add_paper_trade(signal_date, ticker, action, target_weight, reason, result):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
    INSERT INTO paper_trades(created_at, signal_date, ticker, action, target_weight, reason, result)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.utcnow().isoformat(), str(signal_date), ticker, action, float(target_weight), reason, result))
    con.commit()
    con.close()

def load_paper_trades():
    con = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM paper_trades ORDER BY id DESC", con)
    finally:
        con.close()
    return df

def save_snapshot(total_value, data):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
    INSERT INTO portfolio_snapshots(created_at, total_value, data_json)
    VALUES (?, ?, ?)
    """, (datetime.utcnow().isoformat(), float(total_value), json.dumps(data)))
    con.commit()
    con.close()

init_db()

# =========================================================
# BACKTEST
# =========================================================

def make_price_matrix(tickers, period="10y"):
    frames = []
    for t in tickers:
        df = yf_history(t, period=period)
        if not df.empty and "Close" in df.columns:
            frames.append(df["Close"].rename(t))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1).dropna(how="all").ffill().dropna()

def static_rebalance_backtest(price_matrix, target_weights, freq_months=12):
    monthly = price_matrix.resample("M").last().pct_change().dropna()
    if monthly.empty:
        return pd.Series(dtype=float)
    weights = pd.Series(target_weights, dtype=float).reindex(monthly.columns).fillna(0)
    weights = weights / weights.sum()
    current = weights.copy()
    equity = []
    value = 1.0
    for i, (dt, ret) in enumerate(monthly.iterrows(), start=1):
        value *= (1 + float((current * ret).sum()))
        equity.append((dt, value))
        current = current * (1 + ret)
        current = current / current.sum()
        if i % freq_months == 0:
            current = weights.copy()
    return pd.Series([v for _, v in equity], index=[d for d, _ in equity])

def perf_stats(eq):
    if eq.empty or len(eq) < 3:
        return {}
    rets = eq.pct_change().dropna()
    years = len(rets) / 12
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1/years) - 1 if years > 0 else np.nan
    vol = rets.std() * math.sqrt(12)
    dd = eq / eq.cummax() - 1
    return {
        "CAGR": cagr,
        "Volatility": vol,
        "Max Drawdown": dd.min(),
        "Final multiple": eq.iloc[-1] / eq.iloc[0],
    }

# =========================================================
# ALERTS
# =========================================================

def send_telegram(msg):
    token = get_secret("TELEGRAM_BOT_TOKEN")
    chat_id = get_secret("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False, "TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID mancanti"
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg},
            timeout=15
        )
        return r.ok, r.text
    except Exception as e:
        return False, str(e)

# =========================================================
# UI
# =========================================================

st.title("Portfolio Cockpit Definitive")
st.caption("Core/Satellite + macro dashboard + segnali tattici + ribilanciamento ±5 + backtest + paper trading. Strumento educativo, non consulenza finanziaria.")

with st.sidebar:
    st.header("Impostazioni")
    period = st.selectbox("Periodo storico dashboard", ["1y", "2y", "5y", "10y"], index=2)
    band = st.number_input("Banda rebalance ± punti percentuali", min_value=1.0, max_value=20.0, value=DEFAULT_BAND, step=0.5)
    st.divider()
    st.metric("Core target", f"{sum(v['target'] for v in CORE_PORTFOLIO.values()):.0f}%")
    st.metric("Satellite target", f"{sum(v['target'] for v in TACTICAL_PORTFOLIO.values()):.0f}%")

tabs = st.tabs([
    "Home",
    "Portfolio",
    "Macro",
    "Tactical Signals",
    "FRED Macro",
    "COT / Alternative Data",
    "Backtest",
    "Paper Trading",
    "Alerts",
    "Operational Rules"
])

# HOME
with tabs[0]:
    st.subheader("Architettura")
    target_df = pd.DataFrame([{"ticker": k, **v} for k, v in PORTFOLIO.items()])
    c1, c2, c3 = st.columns(3)
    c1.metric("Target totale", f"{target_df['target'].sum():.1f}%")
    c2.metric("Numero strumenti", len(target_df))
    fg_score, fg_notes = fear_greed_proxy()
    c3.metric("Fear/Greed proxy", f"{fg_score:.0f}/100")
    st.plotly_chart(px.pie(target_df, values="target", names="ticker", title="Target allocation"), use_container_width=True)
    st.dataframe(target_df, use_container_width=True)

# PORTFOLIO
with tabs[1]:
    st.subheader("Monitor portafoglio e ribilanciamento ±5")
    positions = st.data_editor(
        pd.DataFrame([{"ticker": t, "shares": 0.0} for t in PORTFOLIO.keys()]),
        use_container_width=True,
        num_rows="fixed",
        key="positions_editor"
    )
    if st.button("Aggiorna prezzi e calcola rebalance"):
        prices = {t: yf_last(t) for t in positions["ticker"].tolist()}
        positions["price"] = positions["ticker"].map(prices).fillna(0)
        targets = {k: v["target"] for k, v in PORTFOLIO.items()}
        rb = rebalance_table(positions, targets, band)
        st.session_state["rb"] = rb
        save_snapshot(rb["value"].sum(), rb.to_dict(orient="records"))

    if "rb" in st.session_state:
        rb = st.session_state["rb"]
        st.dataframe(rb, use_container_width=True)
        total = rb["value"].sum()
        st.metric("Valore totale", f"{total:,.2f}")
        if total > 0:
            st.plotly_chart(px.pie(rb, values="current_weight", names="ticker", title="Pesi attuali"), use_container_width=True)
            actions = rb[rb["action"] != "HOLD"]
            if actions.empty:
                st.success("Nessuna azione: tutti gli strumenti sono dentro la banda.")
            else:
                st.warning("Azioni richieste dal ribilanciamento:")
                st.dataframe(actions[["ticker", "current_weight", "target_weight", "deviation_pp", "action", "trade_value"]], use_container_width=True)

# MACRO
with tabs[2]:
    st.subheader("Macro / Market dashboard")
    rows = []
    for name, ticker in MARKET_TICKERS.items():
        df = yf_history(ticker, period=period)
        if df.empty:
            rows.append({"Indicatore": name, "Ticker": ticker, "Last": None, "1M %": None, "3M %": None, "6M %": None, "Trend": "NO DATA", "Vol 3M": None, "Max DD": None})
            continue
        c = df["Close"]
        last = float(c.iloc[-1])
        ma200 = sma(c, 200)
        trend = "above 200dma" if not pd.isna(ma200) and last > ma200 else ("below 200dma" if not pd.isna(ma200) else "n/a")
        rows.append({
            "Indicatore": name,
            "Ticker": ticker,
            "Last": round(last, 4),
            "1M %": round(pct_change(c,21)*100,2) if len(c)>22 else None,
            "3M %": round(pct_change(c,63)*100,2) if len(c)>64 else None,
            "6M %": round(pct_change(c,126)*100,2) if len(c)>127 else None,
            "Trend": trend,
            "Vol 3M": round(volatility(c,63)*100,2) if not pd.isna(volatility(c,63)) else None,
            "Max DD": round(max_drawdown(c)*100,2) if not pd.isna(max_drawdown(c)) else None,
        })
    mdf = pd.DataFrame(rows)
    macro_score, macro_notes = macro_regime_score()
    fg_score, fg_notes = fear_greed_proxy()
    c1, c2, c3 = st.columns(3)
    c1.metric("Macro Risk Score", f"{macro_score:.0f}/100")
    c2.metric("Regime", "Risk-on" if macro_score >= 60 else ("Neutral" if macro_score >= 45 else "Risk-off"))
    c3.metric("Fear/Greed proxy", f"{fg_score:.0f}/100")
    st.write("Macro notes:", ", ".join(macro_notes) if macro_notes else "n/a")
    st.write("Fear/Greed proxy notes:", ", ".join(fg_notes) if fg_notes else "n/a")
    st.dataframe(mdf, use_container_width=True)

# TACTICAL
with tabs[3]:
    st.subheader("Segnali tattici settoriali")
    macro_score, _ = macro_regime_score()
    out = []
    for theme, tickers in TACTICAL_WATCHLIST.items():
        best = None
        for t in tickers:
            df = yf_history(t, period=period)
            if df.empty or len(df) < 130:
                continue
            c = df["Close"]
            score = tactical_score(c, macro_score)
            row = {
                "Tema": theme,
                "Ticker": t,
                "Score": None if pd.isna(score) else round(score, 1),
                "Segnale": signal_from_score(score),
                "1M %": round(pct_change(c,21)*100,2) if len(c)>22 else None,
                "3M %": round(pct_change(c,63)*100,2) if len(c)>64 else None,
                "6M %": round(pct_change(c,126)*100,2) if len(c)>127 else None,
                "Vol 3M": round(volatility(c,63)*100,2) if not pd.isna(volatility(c,63)) else None,
            }
            if best is None or (row["Score"] is not None and row["Score"] > best["Score"]):
                best = row
        out.append(best or {"Tema": theme, "Ticker": "NO DATA", "Score": None, "Segnale": "NO DATA"})
    tdf = pd.DataFrame(out).sort_values("Score", ascending=False, na_position="last")
    st.dataframe(tdf, use_container_width=True)
    top = tdf.dropna(subset=["Score"]).head(8)
    if not top.empty:
        st.plotly_chart(px.bar(top, x="Tema", y="Score", color="Segnale", title="Ranking tattico"), use_container_width=True)
    st.info("Regola satellite: entra/sovrappesa solo con score >75. Se nessun tema supera 60, satellite in cash/bond breve.")

# FRED
with tabs[4]:
    st.subheader("FRED Macro")
    rows = []
    for name, sid in FRED_SERIES.items():
        df = fred_series(sid)
        if df.empty:
            rows.append({"Indicatore": name, "Serie": sid, "Ultimo": None, "Data": None, "3M chg": None, "12M chg": None})
        else:
            val = df["value"]
            last = float(val.iloc[-1])
            chg3 = float(val.iloc[-1] - val.iloc[-4]) if len(val) > 4 else None
            chg12 = float(val.iloc[-1] - val.iloc[-13]) if len(val) > 13 else None
            rows.append({"Indicatore": name, "Serie": sid, "Ultimo": round(last, 4), "Data": str(df.index[-1].date()), "3M chg": None if chg3 is None else round(chg3, 4), "12M chg": None if chg12 is None else round(chg12, 4)})
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.caption("Se vuoto, inserisci FRED_API_KEY nei Secrets di Streamlit Cloud.")

# COT / ALTERNATIVE
with tabs[5]:
    st.subheader("COT / Alternative Data")
    st.write("Questa sezione è predisposta. Alcuni dati gratuiti non hanno API stabili o richiedono parsing specifico.")
    st.dataframe(cftc_cot_disclaimer_table(), use_container_width=True)
    st.markdown("""
    **Incluso ora:**
    - Baltic Dry proxy tramite ETF/ETN BDRY da Yahoo Finance
    - Fear & Greed proxy interno
    - Copper/Gold ratio tramite futures Yahoo
    - M2, CFNAI, spread, tassi tramite FRED

    **Da integrare manualmente in una fase successiva se desideri precisione istituzionale:**
    - COT ufficiale CFTC con mapping contratti
    - Put/Call Ratio CBOE
    - flussi istituzionali ETF/fondi
    - PMI ufficiali da provider dedicati
    """)

# BACKTEST
with tabs[6]:
    st.subheader("Backtest 10 anni semplificato")
    st.write("Ribilanciamento annuale del portafoglio target. Non include tasse, spread, cambio e strumenti con storico breve.")
    if st.button("Esegui backtest"):
        tickers = list(PORTFOLIO.keys())
        pm = make_price_matrix(tickers, period="10y")
        if pm.empty:
            st.error("Dati insufficienti.")
        else:
            targets = {k: v["target"]/100 for k, v in PORTFOLIO.items()}
            eq = static_rebalance_backtest(pm, targets)
            if eq.empty:
                st.error("Backtest non calcolabile.")
            else:
                stats = perf_stats(eq)
                st.line_chart(eq)
                st.json({k: (round(v*100,2) if k != "Final multiple" else round(v,2)) for k, v in stats.items()})

# PAPER TRADING
with tabs[7]:
    st.subheader("Paper trading")
    with st.form("paper_form"):
        signal_date = st.date_input("Data segnale", date.today())
        ticker = st.text_input("Ticker")
        action = st.selectbox("Azione", ["BUY", "SELL", "HOLD", "REDUCE", "OVERWEIGHT"])
        target_weight = st.number_input("Peso target", 0.0, 100.0, 0.0, 0.5)
        reason = st.text_area("Motivo")
        result = st.text_area("Esito / note")
        submitted = st.form_submit_button("Salva paper trade")
        if submitted:
            add_paper_trade(signal_date, ticker, action, target_weight, reason, result)
            st.success("Paper trade salvato.")
    trades = load_paper_trades()
    st.dataframe(trades, use_container_width=True)
    if not trades.empty:
        st.download_button("Scarica CSV", trades.to_csv(index=False).encode("utf-8"), "paper_trades.csv", "text/csv")

# ALERTS
with tabs[8]:
    st.subheader("Alert Telegram")
    msg = st.text_area("Messaggio", "Portfolio Cockpit: alert operativo.")
    if st.button("Invia alert Telegram"):
        ok, resp = send_telegram(msg)
        if ok:
            st.success("Alert inviato.")
        else:
            st.error(resp)

# RULES
with tabs[9]:
    st.subheader("Regole operative")
    st.markdown("""
    ### Core 80%
    - Ribilanciamento se deviazione > ±5 punti percentuali.
    - In assenza di deviazione: nessuna azione.
    - Evitare market timing sul core.

    ### Satellite 20%
    - Rotazione solo se score >75.
    - Tra 60 e 75: hold.
    - Tra 45 e 60: neutrale.
    - Sotto 45: riduzione/uscita.
    - Se nessun settore >60: satellite in XEON / cash / bond breve.

    ### Macro
    - Risk-on: è possibile mantenere satellite pienamente allocato.
    - Neutral: riduci rotazioni aggressive.
    - Risk-off: privilegia cash, oro, bond breve.

    ### Validazione
    - Backtest prima.
    - Paper trading 3-6 mesi.
    - Poi eventuale capitale reale ridotto.
    - Nessuna automazione diretta broker finché il sistema non ha dimostrato stabilità operativa.
    """)
