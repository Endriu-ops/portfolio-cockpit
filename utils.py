import os, requests, streamlit as st, yfinance as yf, pandas as pd, numpy as np

def secret(name):
    try: return st.secrets.get(name, "")
    except Exception: return os.getenv(name, "")

@st.cache_data(ttl=3600)
def yf_history(ticker, period="1y"):
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True, threads=False)
        if df is None or df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = [c[0] for c in df.columns]
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def yf_last(ticker):
    df = yf_history(ticker, "5d")
    return None if df.empty else float(df["Close"].iloc[-1])

@st.cache_data(ttl=21600)
def fred_series(sid):
    key = secret("FRED_API_KEY")
    if not key: return pd.DataFrame()
    try:
        r = requests.get("https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": sid, "api_key": key, "file_type":"json"}, timeout=20)
        df = pd.DataFrame(r.json().get("observations", []))
        if df.empty: return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"].replace(".", pd.NA), errors="coerce")
        return df.set_index("date")[["value"]].dropna()
    except Exception:
        return pd.DataFrame()

def pct_change(s, n):
    if len(s) <= n: return np.nan
    return float(s.iloc[-1]/s.iloc[-n-1]-1)

def sma(s,n):
    if len(s)<n: return np.nan
    return float(s.rolling(n).mean().iloc[-1])

def momentum_score(close):
    if len(close)<130: return np.nan
    raw=.2*pct_change(close,21)+.35*pct_change(close,63)+.45*pct_change(close,126)
    return float(100/(1+np.exp(-raw*12)))

def trend_score(close):
    if len(close)<200: return np.nan
    last, ma50, ma200 = float(close.iloc[-1]), sma(close,50), sma(close,200)
    score=50
    if last>ma50: score+=20
    if last>ma200: score+=20
    if ma50>ma200: score+=10
    return max(0,min(100,score))

def vol_penalty(close):
    r=close.pct_change().dropna()
    if len(r)<63: return 0
    vol=float(r.tail(63).std()*np.sqrt(252))
    return max(0,min(25,(vol-.25)*60))

def macro_score(vix=None, sp_above=True):
    score=50
    if vix is not None:
        if vix<15: score+=15
        elif vix<20: score+=5
        elif vix>30: score-=20
        elif vix>25: score-=10
    score += 10 if sp_above else -10
    return max(0,min(100,score))

def tactical_score(close, macro=50):
    ms, ts = momentum_score(close), trend_score(close)
    if np.isnan(ms) or np.isnan(ts): return np.nan
    return max(0,min(100,.40*ms+.35*ts+.15*macro+.10*(100-vol_penalty(close))))

def signal(score):
    if pd.isna(score): return "NO DATA"
    if score>=75: return "OVERWEIGHT / BUY"
    if score>=60: return "HOLD"
    if score>=45: return "NEUTRAL"
    return "REDUCE / EXIT"

def rebalance_table(df, targets, band):
    x=df.copy()
    x["value"]=x["shares"]*x["price"]
    total=x["value"].sum()
    x["current_weight"]=0 if total<=0 else x["value"]/total*100
    x["target_weight"]=x["ticker"].map(targets).fillna(0)
    x["deviation_pp"]=x["current_weight"]-x["target_weight"]
    x["target_value"]=total*x["target_weight"]/100
    x["trade_value"]=x["target_value"]-x["value"]
    x["action"]=np.where(x["deviation_pp"]>band,"SELL/TRIM",np.where(x["deviation_pp"]<-band,"BUY/ADD","HOLD"))
    return x

def send_telegram(msg):
    token, chat = secret("TELEGRAM_BOT_TOKEN"), secret("TELEGRAM_CHAT_ID")
    if not token or not chat: return False, "Telegram secrets missing"
    try:
        r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id":chat,"text":msg}, timeout=15)
        return r.ok, r.text
    except Exception as e:
        return False, str(e)
