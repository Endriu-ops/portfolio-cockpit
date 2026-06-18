
import os, math, requests, io
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Portfolio Cockpit Alpha Pro v7.1", layout="wide")

CORE = {
    "IBGS.MI": ("Euro Gov Bond 1-3Y", 8.0, "Short Bonds", "Bonds"),
    "MTHP.MI": ("Euro Gov Bond 25+Y", 4.0, "Long Bonds", "Bonds"),
    "SGLD.MI": ("Physical Gold", 15.0, "Gold", "Gold"),
    "SXR8": ("S&P500 / User ETF", 22.0, "Equity Core", "Equity"),
    "ZPRV": ("Small Cap Value / User ETF", 19.0, "Small Cap", "Equity"),
    "BTC": ("Bitcoin Spot", 5.0, "Bitcoin", "Crypto"),
    "CMOD.MI": ("Broad Commodities", 8.0, "Commodities", "Commodities"),
    "GDX.MI": ("Gold Miners", 6.0, "Performance Gold", "Gold"),
}
SAT_WEIGHTS = [5.0, 5.0, 3.0]
INDICATOR_COUNT = 120
PORTFOLIO_CSV = "portfolio_positions.csv"
TRANSACTIONS_CSV = "portfolio_transactions.csv"

PRELOADED_PORTFOLIO = [{'ticker': 'IBGS.MI', 'shares': 98.0, 'avg_price': 139.9, 'manual_price': 0, 'broker': '', 'note': ''}, {'ticker': 'MTHP.MI', 'shares': 193.0, 'avg_price': 73.1012, 'manual_price': 0, 'broker': '', 'note': ''}, {'ticker': 'SGLD.MI', 'shares': 70.974, 'avg_price': 208.48, 'manual_price': 0, 'broker': '', 'note': ''}, {'ticker': 'SXR8', 'shares': 10.419, 'avg_price': 588.85, 'manual_price': 0, 'broker': '', 'note': ''}, {'ticker': 'ZPRV', 'shares': 407.0, 'avg_price': 66.241, 'manual_price': 0, 'broker': '', 'note': ''}, {'ticker': 'BTC', 'shares': 0.126, 'avg_price': 70381.31, 'manual_price': 0, 'broker': '', 'note': 'BTC spot'}, {'ticker': 'CMOD.MI', 'shares': 460.0, 'avg_price': 27.195, 'manual_price': 0, 'broker': '', 'note': ''}, {'ticker': 'GDX.MI', 'shares': 110.0, 'avg_price': 85.01, 'manual_price': 0, 'broker': '', 'note': ''}, {'ticker': 'RBOT.MI', 'shares': 0.0, 'avg_price': 0.0, 'manual_price': 0, 'broker': '', 'note': 'AI'}, {'ticker': 'DFEN.MI', 'shares': 0.0, 'avg_price': 0.0, 'manual_price': 0, 'broker': '', 'note': 'Defense'}, {'ticker': 'SMH', 'shares': 46.0, 'avg_price': 101.18, 'manual_price': 0, 'broker': '', 'note': 'tattico 3%'}, {'ticker': 'VWCE', 'shares': 4.0, 'avg_price': 161.97, 'manual_price': 0, 'broker': '', 'note': 'PAC globale'}, {'ticker': 'VUAA', 'shares': 203.0, 'avg_price': 108.4737, 'manual_price': 0, 'broker': '', 'note': 'S&P500 equivalente'}]

PORTFOLIO_BACKUP_PREFIX = "portfolio_positions_backup"

def clean_portfolio_df(df):
    required_cols = ["ticker","shares","avg_price","manual_price","broker","note"]
    if df is None or df.empty:
        df = pd.DataFrame(columns=required_cols)
    df = df.copy()
    for col in required_cols:
        if col not in df.columns:
            df[col] = "" if col in ["ticker","broker","note"] else 0.0

    df["ticker"] = df["ticker"].astype(str).str.strip()
    df["ticker"] = df["ticker"].replace({"CBTC.MI":"BTC", "BTC-USD":"BTC", "XZPRV":"ZPRV"})
    df = df[~df["ticker"].astype(str).isin(["VUSA.MI","WSML.MI","", "nan", "None"])]

    df["shares"] = pd.to_numeric(df["shares"], errors="coerce").fillna(0.0)
    df["avg_price"] = pd.to_numeric(df["avg_price"], errors="coerce").fillna(0.0)
    df["manual_price"] = pd.to_numeric(df["manual_price"], errors="coerce").fillna(0.0)
    df["broker"] = df["broker"].fillna("").astype(str)
    df["note"] = df["note"].fillna("").astype(str)

    # Collapse duplicates by ticker, weighted avg_price.
    rows = []
    for ticker, g in df.groupby("ticker", sort=False):
        shares = float(g["shares"].sum())
        if shares > 0:
            avg_price = float((g["shares"] * g["avg_price"]).sum() / shares)
        else:
            avg_price = float(g["avg_price"].iloc[-1]) if len(g) else 0.0
        manual_price = float(g["manual_price"].replace(0, pd.NA).dropna().iloc[-1]) if not g["manual_price"].replace(0, pd.NA).dropna().empty else 0.0
        rows.append({
            "ticker": ticker,
            "shares": shares,
            "avg_price": avg_price,
            "manual_price": manual_price,
            "broker": g["broker"].iloc[-1],
            "note": g["note"].iloc[-1],
        })
    return pd.DataFrame(rows, columns=required_cols)

def portfolio_to_csv_bytes(df):
    return clean_portfolio_df(df).to_csv(index=False).encode("utf-8")

def save_portfolio_with_backup(df):
    clean = clean_portfolio_df(df)
    clean.to_csv(PORTFOLIO_CSV, index=False)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    clean.to_csv(f"{PORTFOLIO_BACKUP_PREFIX}_{ts}.csv", index=False)
    return clean


PRICE_ALIASES = {
    # User-friendly tickers -> Yahoo candidates
    "SXR8": ["SXR8.MI", "SXR8.DE", "SXR8.SW"],
    "SXR8.MI": ["SXR8.MI", "SXR8.DE", "SXR8.SW"],
    "VUAA": ["VUAA.MI", "VUAA.DE", "VUAA.L"],
    "VUAA.MI": ["VUAA.MI", "VUAA.DE", "VUAA.L"],
    "VWCE": ["VWCE.MI", "VWCE.DE", "VWCE.SW"],
    "VWCE.MI": ["VWCE.MI", "VWCE.DE", "VWCE.SW"],
    "ZPRV": ["ZPRV.MI", "ZPRV.DE"],
    "ZPRV.MI": ["ZPRV.MI", "ZPRV.DE"],
    "MTHP.MI": ["MTH.PA", "MTH.FR", "MTHP.MI", "MTHP.PA"],
    "MTH.PA": ["MTH.PA"],
    "MTH.FR": ["MTH.PA", "MTH.FR"],
    "BTC": ["BTC-USD"],
    "BTC-USD": ["BTC-USD"],
    "BTC": ["BTC-USD"],
    "SMH": ["SMH.MI"],
    "XLK": ["XLK"],
    "RBOT.MI": ["RBOT.MI", "RBOT.L"],
    "DFEN.MI": ["DFEN.MI"],
}


GOLDEN_BUTTERFLY = {"IBGS.MI":20, "MTHP.MI":20, "SGLD.MI":20, "SXR8":20, "ZPRV":20}
ALPHA_STATIC = {"IBGS.MI":8, "MTHP.MI":4, "SGLD.MI":15, "SXR8":22, "ZPRV":19, "BTC":5, "CMOD.MI":8, "GDX.MI":6, "DFEN.MI":5, "RBOT.MI":5, "SMH":3}

# V7.1: proxy storici per estendere il backtest a 10 anni.
BACKTEST_PROXY = {
    "IBGS.MI": "SHY",
    "MTHP.MI": "TLT",
    "SGLD.MI": "GLD",
    "SXR8": "SPY",
    "SXR8.MI": "SPY",
    "VUAA": "SPY",
    "VUAA.MI": "SPY",
    "VWCE": "VT",
    "VWCE.MI": "VT",
    "ZPRV": "VBR",
    "ZPRV.MI": "VBR",
    "BTC": "BTC-USD",
    "BTC-USD": "BTC-USD",
    "CMOD.MI": "DBC",
    "GDX.MI": "GDX",
    "DFEN.MI": "ITA",
    "RBOT.MI": "XLK",
    "SMH": "SMH",
    "SMH.MI": "SMH",
    "XEON.MI": "SHY",
}

def map_backtest_ticker(ticker, mode="Real ETF History"):
    if mode == "Extended 10Y Proxy History":
        return BACKTEST_PROXY.get(ticker, ticker)
    return ticker

def backtest_proxy_map(weights, mode="Real ETF History"):
    mapped = {}
    for t, w in weights.items():
        proxy = map_backtest_ticker(t, mode)
        mapped[proxy] = mapped.get(proxy, 0) + w
    return mapped


MARKET = {
    "S&P500":"^GSPC", "Nasdaq100":"^NDX", "Russell2000":"^RUT", "VIX":"^VIX",
    "DollarIndex":"DX-Y.NYB", "Gold":"GC=F", "Copper":"HG=F", "WTI":"CL=F",
    "Bitcoin":"BTC-USD", "US10Y":"^TNX", "RSP":"RSP", "SPY":"SPY", "QQQ":"QQQ",
    "XLU":"XLU", "DBC":"DBC", "AGG":"AGG", "GDX":"GDX", "GLD":"GLD",
    "HYG":"HYG", "IEF":"IEF", "TLT":"TLT", "LQD":"LQD", "IWM":"IWM"
}
FRED = {
    "FedFunds":"FEDFUNDS", "CPI":"CPIAUCSL", "M2":"M2SL",
    "DGS10":"DGS10", "DGS2":"DGS2", "YieldCurve10Y2Y":"T10Y2Y",
    "HighYieldSpread":"BAMLH0A0HYM2", "IGSpread":"BAMLC0A0CM",
    "CFNAI":"CFNAI", "Unemployment":"UNRATE", "IndustrialProduction":"INDPRO",
    "RetailSales":"RSAFS", "FinancialConditions":"NFCI", "ConsumerSentiment":"UMCSENT"
}
TACTICAL = {
    "Defense": {"tickers":["DFEN.MI","ITA","XAR"], "macro":"Defense"},
    "AI_Automation": {"tickers":["RBOT.MI","BOTZ","ROBO"], "macro":"Technology"},
    "Semiconductors": {"tickers":["SMH","SOXX"], "macro":"Technology"},
    "Technology": {"tickers":["XLK","IYW"], "macro":"Technology"},
    "Cybersecurity": {"tickers":["HACK","CIBR"], "macro":"Technology"},
    "Energy": {"tickers":["XLE","IXC"], "macro":"Energy"},
    "Uranium": {"tickers":["URA","URNM"], "macro":"Energy"},
    "Healthcare": {"tickers":["XLV","IXJ"], "macro":"Defensive Equity"},
    "Biotech": {"tickers":["IBB","XBI"], "macro":"Healthcare"},
    "Financials": {"tickers":["XLF","IXG"], "macro":"Cyclicals"},
    "Industrials": {"tickers":["XLI","EXI"], "macro":"Cyclicals"},
    "SmallValue": {"tickers":["IJS","VBR"], "macro":"Cyclicals"},
    "Commodities": {"tickers":["CMOD.MI","DBC"], "macro":"Real Assets"},
    "GoldMiners": {"tickers":["GDX.MI","GDX"], "macro":"Gold"},
    "Infrastructure": {"tickers":["IGF","PAVE"], "macro":"Infrastructure"},
    "Water": {"tickers":["PHO","IH2O.L"], "macro":"Infrastructure"},
    "CleanEnergy": {"tickers":["ICLN","QCLN"], "macro":"Energy"},
    "India": {"tickers":["INDA","INDY"], "macro":"Emerging Markets"},
    "EmergingMarkets": {"tickers":["EEM","IEMG"], "macro":"Emerging Markets"},
}
RS_PAIRS = {
    "Gold/SP500":("GC=F","^GSPC"), "Copper/Gold":("HG=F","GC=F"),
    "SmallCap/SP500":("^RUT","^GSPC"), "Commodities/Bonds":("DBC","AGG"),
    "Bitcoin/Gold":("BTC-USD","GC=F"), "Nasdaq/Utilities":("QQQ","XLU"),
    "EqualWeight/CapWeight":("RSP","SPY"), "GoldMiners/Gold":("GDX","GLD"),
    "HighYield/Treasury":("HYG","IEF"), "Tech/SP500":("XLK","SPY"),
    "Energy/SP500":("XLE","SPY"), "Healthcare/SP500":("XLV","SPY"),
}

def secret(name, default=""):
    try: return st.secrets.get(name, default)
    except Exception: return os.getenv(name, default)

@st.cache_data(ttl=3600)
def hist(ticker, period="10y"):
    try:
        df = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns=[c[0] for c in df.columns]
        df.index = pd.to_datetime(df.index, errors="coerce")
        df = df[~df.index.isna()].sort_index()
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def yahoo_candidates(ticker):
    t = str(ticker).strip()
    if not t:
        return []
    if t in PRICE_ALIASES:
        return PRICE_ALIASES[t]
    candidates = [t]
    if "." not in t:
        candidates += [t + ".MI", t + ".DE", t + ".SW", t + ".L"]
    return list(dict.fromkeys(candidates))

def last_yahoo(ticker):
    for cand in yahoo_candidates(ticker):
        df = hist(cand, "10d")
        if not df.empty and "Close" in df.columns:
            val = float(df["Close"].dropna().iloc[-1])
            if val > 0:
                return val, cand
    return None, None

def last(ticker):
    val, _ = last_yahoo(ticker)
    return val

def resolved_price(ticker, manual_price=0, avg_price=0):
    val, source = last_yahoo(ticker)
    if val is not None and val > 0:
        return val, source, "YAHOO"
    try:
        mp = float(manual_price)
    except Exception:
        mp = 0
    if mp > 0:
        return mp, "manual_price", "MANUAL"
    try:
        ap = float(avg_price)
    except Exception:
        ap = 0
    if ap > 0:
        return ap, "avg_price_fallback", "AVG_FALLBACK"
    return 0.0, None, "MISSING"

@st.cache_data(ttl=21600)
def fred(sid):
    key=secret("FRED_API_KEY")
    if not key: return pd.DataFrame()
    try:
        js=requests.get("https://api.stlouisfed.org/fred/series/observations",
            params={"series_id":sid,"api_key":key,"file_type":"json"},timeout=20).json()
        df=pd.DataFrame(js.get("observations",[]))
        if df.empty: return pd.DataFrame()
        df["date"]=pd.to_datetime(df["date"])
        df["value"]=pd.to_numeric(df["value"].replace(".",pd.NA),errors="coerce")
        return df.set_index("date")[["value"]].dropna()
    except Exception:
        return pd.DataFrame()

def pc(s,n):
    if len(s)<=n: return np.nan
    return float(s.iloc[-1]/s.iloc[-n-1]-1)
def sma(s,n):
    if len(s)<n: return np.nan
    return float(s.rolling(n).mean().iloc[-1])
def vol(s,n=63):
    r=s.pct_change().dropna()
    if len(r)<n: return np.nan
    return float(r.tail(n).std()*math.sqrt(252))
def mdd(s):
    if len(s)<2: return np.nan
    return float((s/s.cummax()-1).min())
def current_drawdown(s):
    if len(s)<2: return np.nan
    return float(s.iloc[-1]/s.cummax().iloc[-1]-1)
def bscore(x,scale=10):
    if pd.isna(x): return np.nan
    return float(100/(1+np.exp(-x*scale)))
def mean(vals, default=50):
    vals=[v for v in vals if v is not None and not pd.isna(v)]
    return default if not vals else float(np.nanmean(vals))
def trend(c):
    if len(c)<200: return np.nan
    lc=float(c.iloc[-1]); ma50=sma(c,50); ma200=sma(c,200)
    return float(max(0,min(100,50+(20 if lc>ma50 else 0)+(20 if lc>ma200 else 0)+(10 if ma50>ma200 else 0))))
def mom(c):
    if len(c)<130: return np.nan
    return bscore(.2*pc(c,21)+.35*pc(c,63)+.45*pc(c,126),12)
def rel(a,b="SPY"):
    da,db=hist(a,"2y"),hist(b,"2y")
    if da.empty or db.empty: return np.nan
    r=(da["Close"]/db["Close"]).dropna()
    if len(r)<130: return np.nan
    return bscore(.35*pc(r,63)+.65*pc(r,126),15)

def inflation_score():
    cpi=fred("CPIAUCSL")
    if cpi.empty or len(cpi)<14: return 50
    yoy=cpi["value"].iloc[-1]/cpi["value"].iloc[-13]-1
    return max(0,min(100,75-yoy*500))
def liquidity_score():
    parts=[]; m2=fred("M2SL"); cpi=fred("CPIAUCSL"); fedf=fred("FEDFUNDS"); nfci=fred("NFCI")
    if not m2.empty and len(m2)>13: parts.append(bscore(m2["value"].iloc[-1]/m2["value"].iloc[-13]-1,20))
    if not cpi.empty and len(cpi)>13 and not fedf.empty:
        cpi_yoy=cpi["value"].iloc[-1]/cpi["value"].iloc[-13]-1
        parts.append(max(0,min(100,70-(fedf["value"].iloc[-1]-cpi_yoy*100)*8)))
    if not nfci.empty: parts.append(max(0,min(100,60-nfci["value"].iloc[-1]*40)))
    return mean(parts)
def macro_score():
    parts=[]; yc=fred("T10Y2Y"); cf=fred("CFNAI"); un=fred("UNRATE"); ip=fred("INDPRO"); retail=fred("RSAFS")
    if not yc.empty: parts.append(max(0,min(100,50+yc["value"].iloc[-1]*10)))
    if not cf.empty: parts.append(max(0,min(100,50+cf["value"].iloc[-1]*25)))
    if not un.empty and len(un)>6: parts.append(max(0,min(100,55-(un["value"].iloc[-1]-un["value"].iloc[-7])*35)))
    if not ip.empty and len(ip)>13: parts.append(bscore(ip["value"].iloc[-1]/ip["value"].iloc[-13]-1,30))
    if not retail.empty and len(retail)>13: parts.append(bscore(retail["value"].iloc[-1]/retail["value"].iloc[-13]-1,15))
    return mean(parts)
def credit_score():
    parts=[]; hy=fred("BAMLH0A0HYM2"); ig=fred("BAMLC0A0CM")
    if not hy.empty: parts.append(max(0,min(100,80-hy["value"].iloc[-1]*8)))
    if not ig.empty: parts.append(max(0,min(100,85-ig["value"].iloc[-1]*12)))
    hyg,ief=hist("HYG","2y"),hist("IEF","2y")
    if not hyg.empty and not ief.empty:
        r=(hyg["Close"]/ief["Close"]).dropna()
        if len(r)>126: parts.append(bscore(pc(r,126),15))
    return mean(parts)
def trend_market_score():
    return mean([trend(hist(t,"2y")["Close"]) for t in ["^GSPC","^NDX","^RUT"] if not hist(t,"2y").empty])
def breadth_score():
    parts=[]
    for a,b in [("RSP","SPY"),("^RUT","^GSPC"),("QQQ","XLU"),("HYG","IEF")]:
        da,db=hist(a,"2y"),hist(b,"2y")
        if not da.empty and not db.empty:
            r=(da["Close"]/db["Close"]).dropna()
            if len(r)>126: parts.append(bscore(pc(r,126),15))
    return mean(parts)
def fear_greed_score(vix_override=None):
    v=vix_override if vix_override is not None else last("^VIX")
    parts=[]
    if v is not None: parts.append(90 if v<10 else 75 if v<15 else 60 if v<25 else 40 if v<35 else 20 if v<60 else 5)
    parts += [breadth_score(), credit_score()]
    sp=hist("SPY","1y")
    if not sp.empty and len(sp)>126: parts.append(bscore(pc(sp["Close"],126),8))
    return mean(parts)
def real_assets_score():
    parts=[]
    for a,b in [("DBC","AGG"),("GC=F","^GSPC"),("HG=F","GC=F"),("GDX","GLD")]:
        da,db=hist(a,"2y"),hist(b,"2y")
        if not da.empty and not db.empty:
            r=(da["Close"]/db["Close"]).dropna()
            if len(r)>126: parts.append(bscore(pc(r,126),12))
    return mean(parts)
def relative_strength_score():
    return mean([rel(a,b) for a,b in RS_PAIRS.values()])
def market_risk_score(vix_override=None):
    parts=[]; v=vix_override if vix_override is not None else last("^VIX")
    if v is not None: parts.append(90 if v<15 else 75 if v<20 else 55 if v<25 else 35 if v<30 else 10 if v<60 else 0)
    parts += [trend_market_score(), credit_score()]
    return mean(parts)

def all_scores(vix_override=None, tax_efficiency=80, portfolio_health=80):
    macro=macro_score(); inflation=inflation_score(); liquidity=liquidity_score(); credit=credit_score()
    trend_s=trend_market_score(); breadth=breadth_score(); feargreed=fear_greed_score(vix_override)
    rs=relative_strength_score(); real=real_assets_score(); marketrisk=market_risk_score(vix_override)
    regime=.20*macro+.15*liquidity+.15*credit+.15*trend_s+.15*breadth+.10*inflation+.10*marketrisk
    alpha=.15*macro+.15*liquidity+.15*credit+.15*trend_s+.15*breadth+.10*rs+.10*real+.05*feargreed
    defensive=max(0,min(100,100-(.30*marketrisk+.20*breadth+.20*liquidity+.20*credit+.10*macro)))
    confidence=mean([macro,liquidity,credit,trend_s,breadth,rs,portfolio_health,tax_efficiency])
    return {"Macro":macro,"Inflation":inflation,"Liquidity":liquidity,"Credit":credit,"Trend":trend_s,"Breadth":breadth,"FearGreed":feargreed,"RelativeStrength":rs,"TaxEfficiency":tax_efficiency,"PortfolioHealth":portfolio_health,"RealAssets":real,"MarketRisk":marketrisk,"RegimeScore":regime,"AlphaScore":alpha,"DefensivePressure":defensive,"Confidence":confidence}

def regime_label(reg):
    if reg>=80: return "Expansion / Strong Risk-On"
    if reg>=65: return "Growth / Risk-On"
    if reg>=50: return "Neutral"
    if reg>=35: return "Slowdown"
    return "Recession / Risk-Off"
def traffic_light(score, high=65, low=45):
    return "🟢" if score>=high else "🟡" if score>=low else "🔴"
def vix_ladder(vix):
    if vix is None: return ("Unknown","No VIX data","Standard")
    if vix < 5: return ("Impossible/Anomaly","Check data quality; no aggressive buys","Reduce risk-on")
    if vix < 10: return ("Extreme complacency","Build tactical cash; avoid chasing","Caution")
    if vix < 15: return ("Complacency","Normal PAC; rebalance prudently","Normal")
    if vix < 30: return ("Normal","Standard system active","Normal")
    if vix < 50: return ("Stress","Slow rotations; require double confirmation","Caution")
    if vix < 70: return ("Panic","Use tranche #1: 25% tactical cash; core only","Defensive")
    if vix < 80: return ("Capitulation","Use tranche #2: another 25%; avoid speculative satellite","Defensive")
    return ("Extreme crash","Satellite defensive; tranche buying; no emotional sells","Crash Protocol")

def tact_score(ticker, scs):
    df=hist(ticker,"5y")
    if df.empty or len(df)<200: return np.nan
    c=df["Close"]; mo=mom(c); tr=trend(c); rs=rel(ticker,"SPY")
    if pd.isna(mo) or pd.isna(tr): return np.nan
    if pd.isna(rs): rs=50
    vv=vol(c,63); penalty=max(0,min(30,(vv-.25)*70)) if not pd.isna(vv) else 0
    return float(max(0,min(100,.30*mo+.20*rs+.20*tr+.15*scs["Breadth"]+.15*scs["AlphaScore"]-.25*penalty)))
def sig(sc):
    if pd.isna(sc): return "NO DATA"
    return "OVERWEIGHT / BUY" if sc>=75 else "HOLD" if sc>=60 else "NEUTRAL" if sc>=45 else "REDUCE / EXIT"
def ranking(period="5y", vix_override=None):
    scs=all_scores(vix_override); rows=[]
    for theme,meta in TACTICAL.items():
        best=None
        for t in meta["tickers"]:
            df=hist(t,period)
            if df.empty: continue
            sc=tact_score(t,scs); c=df["Close"]
            row={"Theme":theme,"MacroSector":meta["macro"],"Ticker":t,"Score":None if pd.isna(sc) else round(sc,1),"Signal":sig(sc),"1M%":round(pc(c,21)*100,2) if len(c)>22 else None,"3M%":round(pc(c,63)*100,2) if len(c)>64 else None,"6M%":round(pc(c,126)*100,2) if len(c)>127 else None}
            if best is None or (row["Score"] is not None and row["Score"]>best["Score"]): best=row
        rows.append(best or {"Theme":theme,"MacroSector":meta["macro"],"Ticker":"NO DATA","Score":None,"Signal":"NO DATA"})
    return pd.DataFrame(rows).sort_values("Score",ascending=False,na_position="last")
def satellite_plan(max_per_macro=1, vix_override=None):
    """
    v6.1 satellite:
    - AI fixed 5%
    - Defense fixed 5%
    - tactical dynamic 3%
    In risk-off, only the 3% tactical goes to XEON; AI and Defense remain strategic.
    """
    scs = all_scores(vix_override)
    v = vix_override if vix_override is not None else last("^VIX")

    rows = [
        {"Slot":"SAT1","Theme":"AI_Automation strategic","MacroSector":"Technology","Ticker":"RBOT.MI","Score":None,"TargetWeight":5.0},
        {"Slot":"SAT2","Theme":"Defense strategic","MacroSector":"Defense","Ticker":"DFEN.MI","Score":None,"TargetWeight":5.0},
    ]

    # Risk-off: tactical 3% to cash/bond short
    if scs["RegimeScore"] < 45 or scs["DefensivePressure"] >= 80 or (v is not None and v >= 60):
        rows.append({"Slot":"SAT3","Theme":"Cash/Bond breve tactical","MacroSector":"Cash","Ticker":"XEON.MI","Score":None,"TargetWeight":3.0})
        return pd.DataFrame(rows)

    # Risk-on / neutral: choose one tactical theme, excluding AI and Defense duplicates.
    df = ranking("5y", vix_override).dropna(subset=["Score"])
    df = df[df["Score"] >= 75]
    excluded = {"AI_Automation", "Defense", "Technology"}  # avoid AI/Tech duplication in the 3% tactical
    chosen = None
    for _, r in df.iterrows():
        if r["Theme"] in excluded:
            continue
        chosen = r
        break

    if chosen is None:
        rows.append({"Slot":"SAT3","Theme":"Cash/Bond breve tactical","MacroSector":"Cash","Ticker":"XEON.MI","Score":None,"TargetWeight":3.0})
    else:
        rows.append({
            "Slot":"SAT3",
            "Theme":chosen["Theme"] + " tactical",
            "MacroSector":chosen["MacroSector"],
            "Ticker":chosen["Ticker"],
            "Score":chosen["Score"],
            "TargetWeight":3.0
        })

    return pd.DataFrame(rows)

def normalize(d):
    s=sum(d.values()); return {k:v/s for k,v in d.items() if v>0}
def price_matrix(weights, period):
    frames=[]
    for t in weights:
        df=hist(t,period)
        if not df.empty and "Close" in df.columns:
            s=df["Close"].copy(); s.index=pd.to_datetime(s.index, errors="coerce"); s=s[~s.index.isna()].sort_index()
            frames.append(s.rename(t))
    if not frames: return pd.DataFrame()
    pm=pd.concat(frames,axis=1); pm.index=pd.to_datetime(pm.index, errors="coerce"); pm=pm[~pm.index.isna()].sort_index()
    return pm.apply(pd.to_numeric, errors="coerce").dropna(how="all").ffill().dropna()
def backtest(weights, period="10y", rebalance_months=12):
    pm=price_matrix(weights,period)
    if pm.empty or not isinstance(pm.index,pd.DatetimeIndex): return pd.Series(dtype=float)
    rets=pm.resample("ME").last().pct_change().dropna()
    if rets.empty: return pd.Series(dtype=float)
    w=pd.Series(weights).reindex(rets.columns).fillna(0)
    if w.sum()==0: return pd.Series(dtype=float)
    w=w/w.sum(); cur=w.copy(); val=1.0; out=[]
    for i,(dt,r) in enumerate(rets.iterrows(),1):
        val*=1+float((cur*r).sum()); out.append((dt,val)); cur=cur*(1+r); cur=cur/cur.sum()
        if i%rebalance_months==0: cur=w.copy()
    return pd.Series([v for d,v in out],index=[d for d,v in out])
def dynamic_alpha_weights(vix_override=None):
    plan=satellite_plan(vix_override=vix_override); weights={k:v[1] for k,v in CORE.items()}
    for _,r in plan.iterrows(): weights[r["Ticker"]]=weights.get(r["Ticker"],0)+float(r["TargetWeight"])
    return weights
def perf_stats(eq):
    if eq.empty or len(eq)<3: return {}
    r=eq.pct_change().dropna(); years=len(r)/12
    cagr=(eq.iloc[-1]/eq.iloc[0])**(1/years)-1 if years>0 else np.nan
    vv=r.std()*math.sqrt(12); downside=r[r<0]; sortino=cagr/(downside.std()*math.sqrt(12)) if len(downside)>1 and downside.std()>0 else np.nan
    draw=eq/eq.cummax()-1; maxdd=draw.min(); ulcer=math.sqrt(np.mean((draw[draw<0]*100)**2)) if len(draw)>0 else np.nan
    return {"CAGR":cagr,"Volatility":vv,"Max Drawdown":maxdd,"Sharpe":cagr/vv if vv>0 else np.nan,"Sortino":sortino,"Calmar":cagr/abs(maxdd) if maxdd<0 else np.nan,"Ulcer Index":ulcer,"Final Multiple":eq.iloc[-1]/eq.iloc[0]}


def apply_equivalent_targets(df, targets):
    """
    v6.9: SXR8, VUAA and VWCE are treated as Equity Core equivalents.
    The 22% Equity Core target is split across the held equivalent tickers
    by current market value, avoiding false SELL signals on VUAA/VWCE.
    """
    if df is None or df.empty:
        return targets

    out = dict(targets)

    equity_equiv = ["SXR8", "SXR8.MI", "VUAA", "VUAA.MI", "VWCE", "VWCE.MI"]
    held = []
    values = []

    for _, r in df.iterrows():
        t = str(r.get("ticker", "")).strip()
        if t in equity_equiv:
            price, _, _ = resolved_price(t, r.get("manual_price", 0), r.get("avg_price", 0))
            mv = float(r.get("shares", 0)) * float(price)
            if mv > 0:
                held.append(t)
                values.append(mv)

    if held:
        core_target = 22.0
        total_mv = sum(values)
        # remove direct 22% from only SXR8, then distribute
        for t in equity_equiv:
            out[t] = 0.0
        for t, mv in zip(held, values):
            out[t] = core_target * mv / total_mv

    return out

def real_table(df, targets, band):
    x = df.copy()
    if "manual_price" not in x.columns:
        x["manual_price"] = 0.0

    prices = x.apply(
        lambda r: resolved_price(
            r.get("ticker", ""),
            r.get("manual_price", 0),
            r.get("avg_price", 0)
        ),
        axis=1
    )

    x["last_price"] = [p[0] for p in prices]
    x["price_source"] = [p[1] for p in prices]
    x["price_status"] = [p[2] for p in prices]

    x["market_value"] = x["shares"] * x["last_price"]
    x["cost_value"] = x["shares"] * x["avg_price"]
    x["pnl"] = x["market_value"] - x["cost_value"]

    # Avoid fake -100% when price is missing.
    x["pnl_pct"] = np.where(
        (x["cost_value"] > 0) & (x["price_status"] != "MISSING"),
        x["pnl"] / x["cost_value"] * 100,
        np.nan
    )

    total = x["market_value"].sum()
    x["current_weight"] = 0 if total <= 0 else x["market_value"] / total * 100

    x["target_weight"] = x["ticker"].map(targets).fillna(0)
    x["deviation_pp"] = x["current_weight"] - x["target_weight"]
    x["target_value"] = total * x["target_weight"] / 100
    x["trade_value"] = x["target_value"] - x["market_value"]

    x["action"] = np.where(
        x["price_status"] == "MISSING",
        "FIX PRICE",
        np.where(
            x["deviation_pp"] > band,
            "SELL/TRIM",
            np.where(x["deviation_pp"] < -band, "BUY/ADD", "HOLD")
        )
    )

    return x

def portfolio_health(df):
    if df.empty or df["market_value"].sum()<=0: return 80
    weights=df["market_value"]/df["market_value"].sum(); concentration=weights.max()*100; n_eff=1/(weights**2).sum()
    score=100
    if concentration>25: score-=15
    if concentration>35: score-=25
    if n_eff<5: score-=25
    elif n_eff<8: score-=10
    return max(0,min(100,score))
def tax_engine(df, tax_rate, tax_budget, simulate_rebalance=False):
    """
    v6.7:
    Default = monitor only.
    It does NOT assume that every SELL/TRIM recommendation will be executed.
    Rebalance taxes are calculated only if simulate_rebalance=True.
    """
    if df is None or df.empty:
        return 100, pd.DataFrame(), 0, pd.DataFrame(), 0

    x = df.copy()
    x["latent_gain"] = x["pnl"].clip(lower=0)
    x["latent_tax_est"] = x["latent_gain"] * (tax_rate / 100)
    latent_tax_total = float(x["latent_tax_est"].sum())

    latent = x[[
        "ticker", "market_value", "cost_value", "pnl", "pnl_pct",
        "latent_gain", "latent_tax_est", "current_weight", "target_weight",
        "deviation_pp", "action"
    ]].copy()

    if not simulate_rebalance:
        # Monitor mode: do not penalize the portfolio for hypothetical sales.
        return 100, pd.DataFrame(), 0, latent, latent_tax_total

    sells = x[(x["trade_value"] < 0) & (x["action"] == "SELL/TRIM")].copy()
    if sells.empty:
        return 100, sells, 0, latent, latent_tax_total

    sells["sell_amount"] = sells["trade_value"].abs()
    sells["gain_ratio"] = np.where(sells["market_value"] > 0, sells["pnl"] / sells["market_value"], 0)
    sells["taxable_gain_est"] = np.where(sells["gain_ratio"] > 0, sells["sell_amount"] * sells["gain_ratio"], 0)
    sells["tax_est"] = sells["taxable_gain_est"] * (tax_rate / 100)
    sells["net_after_tax"] = sells["sell_amount"] - sells["tax_est"]

    tax_total = float(sells["tax_est"].sum())

    if tax_total == 0:
        score = 100
    elif tax_total <= tax_budget * 0.25:
        score = 85
    elif tax_total <= tax_budget * 0.5:
        score = 70
    elif tax_total <= tax_budget:
        score = 50
    else:
        score = 25

    return score, sells, tax_total, latent, latent_tax_total

def decision_center(scores, vix, rebalance_needed, tax_score, portfolio_score):
    macro_light=traffic_light(scores["RegimeScore"]); market_light=traffic_light(scores["MarketRisk"])
    portfolio_light="🟢" if portfolio_score>=80 and not rebalance_needed else "🟡" if portfolio_score>=60 else "🔴"
    vix_regime, vix_action, mode=vix_ladder(vix)
    action="HOLD"; reasons=[]
    if vix is not None and vix>=80: action="CRASH PROTOCOL"; reasons.append("VIX extreme crash")
    elif scores["DefensivePressure"]>=80: action="DEFENSIVE HOLD"; reasons.append("High defensive pressure")
    elif rebalance_needed and tax_score>=50: action="REBALANCE"; reasons.append("Portfolio outside ±5% and tax impact acceptable")
    elif rebalance_needed and tax_score<50: action="DEFER / TAX REVIEW"; reasons.append("Rebalance needed but tax impact high")
    elif scores["AlphaScore"]>=70 and scores["RegimeScore"]>=60 and mode in ["Normal","Caution"]: action="HOLD / SATELLITE ACTIVE"; reasons.append("Risk regime supports satellite")
    else: reasons.append("No strong action signal")
    return {"MacroLight":macro_light,"MarketLight":market_light,"PortfolioLight":portfolio_light,"VIXRegime":vix_regime,"VIXAction":vix_action,"Mode":mode,"Action":action,"Reasons":reasons}

def data_quality_table(portfolio_df):
    if portfolio_df is None or portfolio_df.empty:
        return pd.DataFrame()
    rows = []
    for _, r in portfolio_df.iterrows():
        ticker = r.get("ticker", "")
        manual = r.get("manual_price", 0)
        avg = r.get("avg_price", 0)
        price, source, status = resolved_price(ticker, manual, avg)
        rows.append({
            "ticker": ticker,
            "resolved_price": price,
            "source": source,
            "status": status,
            "manual_price": manual,
            "avg_price": avg,
            "candidates": ", ".join(yahoo_candidates(ticker))
        })
    return pd.DataFrame(rows)

def scenario_protocol(name):
    if name=="VIX 80 / panic": return ["Satellite: 10% XEON/bond breve + 3% oro.","Nessuna vendita forzata del core.","Acquisti solo a tranche.","Controllo credit spread + HYG/IEF.","Ribilanciamento solo se deviazione > ±5 pp e impatto fiscale accettabile."]
    if name=="Inflazione alta": return ["Favoriti: commodities, gold, miners, bitcoin moderato.","Penalizzati: bond lunghi.","Riduci duration se credit stress basso."]
    if name=="Recessione": return ["Favoriti: bond breve, bond lungo moderato, oro.","Penalizzati: small cap, cyclicals, crypto.","Satellite verso cash/bond breve."]
    if name=="Risk-on forte": return ["Satellite pieno sui top sector.","Mantieni stop concentrazione macro-settore.","Non inseguire se score sotto 75."]
    return []


def regime_engine_details(vix_override=None):
    v = vix_override if vix_override is not None else last("^VIX")
    if v is None:
        vix_score = 50
    elif v < 12:
        vix_score = 95
    elif v < 18:
        vix_score = 80
    elif v < 25:
        vix_score = 65
    elif v < 35:
        vix_score = 45
    elif v < 50:
        vix_score = 25
    else:
        vix_score = 5

    yc = fred("T10Y2Y")
    curve = 50 if yc.empty else max(0, min(100, 50 + yc["value"].iloc[-1] * 12))
    nfci = fred("NFCI")
    fincond = 50 if nfci.empty else max(0, min(100, 60 - nfci["value"].iloc[-1] * 40))

    sp = hist("^GSPC","2y")
    sptrend = trend(sp["Close"]) if not sp.empty else 50
    rut = hist("^RUT","2y")
    smalltrend = trend(rut["Close"]) if not rut.empty else 50

    dxy = hist("DX-Y.NYB","1y")
    dollar = 50
    if not dxy.empty and len(dxy)>63:
        dollar = max(0, min(100, 55 - pc(dxy["Close"],63)*250))

    copper = hist("HG=F","1y")
    copper_score = 50
    if not copper.empty and len(copper)>63:
        copper_score = bscore(pc(copper["Close"],63),10)

    m2 = fred("M2SL")
    m2_score = 50
    if not m2.empty and len(m2)>13:
        m2_score = bscore(m2["value"].iloc[-1]/m2["value"].iloc[-13]-1,20)

    rows = [
        {"Component":"VIX", "Score":vix_score, "Weight":15},
        {"Component":"Credit HY/IG", "Score":credit_score(), "Weight":15},
        {"Component":"Yield Curve", "Score":curve, "Weight":10},
        {"Component":"Financial Conditions", "Score":fincond, "Weight":10},
        {"Component":"S&P500 Trend", "Score":sptrend, "Weight":15},
        {"Component":"Small Cap Trend", "Score":smalltrend, "Weight":10},
        {"Component":"Dollar Index", "Score":dollar, "Weight":5},
        {"Component":"Copper", "Score":copper_score, "Weight":5},
        {"Component":"M2 Liquidity", "Score":m2_score, "Weight":5},
        {"Component":"Breadth", "Score":breadth_score(), "Weight":10},
    ]
    df = pd.DataFrame(rows)
    score = float((df["Score"]*df["Weight"]).sum()/df["Weight"].sum())
    mode = "RISK ON" if score >= 65 else "NEUTRAL" if score >= 45 else "RISK OFF"
    return score, mode, df

def explain_satellite_row(row, vix_override=None):
    ticker = row.get("Ticker", "")
    if ticker in ["XEON.MI","SGLD.MI"]:
        return ["Defensive allocation selected by VIX/regime protocol"]
    reasons = []
    df = hist(ticker, "2y")
    if df.empty:
        return ["No sufficient price data"]
    c = df["Close"]
    if len(c)>200 and c.iloc[-1] > c.rolling(200).mean().iloc[-1]:
        reasons.append("Price above 200-day moving average")
    if len(c)>63 and pc(c,63)>0:
        reasons.append("Positive 3M momentum")
    if len(c)>126 and pc(c,126)>0:
        reasons.append("Positive 6M momentum")
    rs = rel(ticker, "SPY")
    if not pd.isna(rs) and rs > 60:
        reasons.append("Relative strength above market")
    if all_scores(vix_override)["RegimeScore"] >= 60:
        reasons.append("Macro regime supportive")
    return reasons or ["Selected by ranking score, but weak explainability"]

def drift_monitor_table(real_df):
    if real_df is None or real_df.empty:
        return pd.DataFrame()
    cols = ["ticker","current_weight","target_weight","deviation_pp","action","trade_value"]
    out = real_df[cols].copy()
    out["severity"] = np.where(out["deviation_pp"].abs() >= 7, "HIGH",
                        np.where(out["deviation_pp"].abs() >= 5, "MEDIUM", "LOW"))
    return out.sort_values("deviation_pp", key=lambda s: s.abs(), ascending=False)

def stress_test_estimate(real_df, scenario):
    if real_df is None or real_df.empty or real_df["market_value"].sum() <= 0:
        return pd.DataFrame()
    shocks = {
        "VIX 80 / panic": {"Equity":-0.28,"Gold":0.08,"Bonds":0.04,"Commodities":-0.10,"Crypto":-0.45},
        "Inflazione alta": {"Equity":-0.08,"Gold":0.08,"Bonds":-0.12,"Commodities":0.18,"Crypto":0.02},
        "Recessione": {"Equity":-0.22,"Gold":0.06,"Bonds":0.08,"Commodities":-0.15,"Crypto":-0.35},
        "Risk-on forte": {"Equity":0.18,"Gold":-0.04,"Bonds":-0.03,"Commodities":0.08,"Crypto":0.30},
    }
    mapping = {
        "IBGS.MI":"Bonds","MTHP.MI":"Bonds","SGLD.MI":"Gold","GDX.MI":"Gold",
        "CMOD.MI":"Commodities","BTC":"Crypto","BTC":"Crypto","BTC-USD":"Crypto","SXR8":"Equity","ZPRV":"Equity",
        "VWCE":"Equity","XVUAA":"Equity","SXR8.MI":"Equity","VUAA.MI":"Equity"
    }
    shock = shocks.get(scenario, shocks["VIX 80 / panic"])
    df = real_df.copy()
    df["asset_class"] = df["ticker"].map(mapping).fillna("Equity")
    df["shock"] = df["asset_class"].map(shock).fillna(-0.10)
    df["estimated_pnl"] = df["market_value"] * df["shock"]
    total = df["market_value"].sum()
    df["portfolio_impact_pct"] = df["estimated_pnl"] / total * 100
    return df[["ticker","asset_class","market_value","shock","estimated_pnl","portfolio_impact_pct"]]


def vix_adaptive_engine(vix, regime_score, cash_available_pct=0.0):
    if vix is None:
        return {"VIX": None, "Zone": "Unknown", "RiskMode": "STANDARD", "Action": "No VIX data", "TacticalWeight": 3.0, "CashDeployPct": 0.0}
    if vix < 10:
        return {"VIX": vix, "Zone": "Extreme complacency", "RiskMode": "RISK-ON CAUTION", "Action": "Avoid chasing; keep satellite but do not add aggressively", "TacticalWeight": 3.0, "CashDeployPct": 0.0}
    if vix < 15:
        return {"VIX": vix, "Zone": "Complacency", "RiskMode": "RISK ON", "Action": "Satellite active; PAC standard", "TacticalWeight": 3.0, "CashDeployPct": 0.0}
    if vix < 25:
        return {"VIX": vix, "Zone": "Normal", "RiskMode": "NORMAL", "Action": "Standard allocation", "TacticalWeight": 3.0, "CashDeployPct": 0.0}
    if vix < 35:
        return {"VIX": vix, "Zone": "Stress light", "RiskMode": "CAUTION", "Action": "Reduce tactical turnover; require confirmation", "TacticalWeight": 2.0, "CashDeployPct": 0.0}
    if vix < 50:
        return {"VIX": vix, "Zone": "Stress", "RiskMode": "DEFENSIVE", "Action": "Prepare staged buying; no emotional sales", "TacticalWeight": 1.0, "CashDeployPct": 0.0}
    if vix < 70:
        return {"VIX": vix, "Zone": "Panic", "RiskMode": "PANIC BUY LADDER", "Action": "Deploy first 25% of tactical cash into core", "TacticalWeight": 0.0, "CashDeployPct": 25.0}
    if vix < 80:
        return {"VIX": vix, "Zone": "Capitulation", "RiskMode": "CRISIS", "Action": "Deploy second 25% of tactical cash; core only", "TacticalWeight": 0.0, "CashDeployPct": 50.0}
    return {"VIX": vix, "Zone": "Extreme crash", "RiskMode": "EXTREME CRASH", "Action": "Crash protocol: freeze satellite, staged buying, no forced sales", "TacticalWeight": 0.0, "CashDeployPct": 75.0}

def perf_stats_professional(eq, benchmark=None, turnover=0.0):
    if eq is None or eq.empty or len(eq) < 3:
        return {}
    eq = eq.dropna()
    r = eq.pct_change().dropna()
    if len(r) < 2:
        return {}
    start, end = eq.index[0], eq.index[-1]
    years = max((end - start).days / 365.25, len(r)/12)
    total_return = eq.iloc[-1] / eq.iloc[0] - 1
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    vol_ann = r.std() * math.sqrt(12)
    draw = eq / eq.cummax() - 1
    maxdd = draw.min()
    hit_ratio = (r > 0).mean()
    sharpe = cagr / vol_ann if vol_ann and vol_ann > 0 else np.nan
    sortino = cagr / (r[r < 0].std() * math.sqrt(12)) if len(r[r < 0]) > 1 and r[r < 0].std() > 0 else np.nan
    out = {
        "Start": str(start.date()),
        "End": str(end.date()),
        "Years": years,
        "Total Return": total_return,
        "CAGR": cagr,
        "Volatility": vol_ann,
        "Max Drawdown": maxdd,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Hit Ratio": hit_ratio,
        "Turnover Ann.": turnover,
        "Final Multiple": eq.iloc[-1] / eq.iloc[0],
    }
    if benchmark is not None and not benchmark.empty:
        joined = pd.concat([eq.rename("p"), benchmark.rename("b")], axis=1).dropna()
        if len(joined) > 3:
            rp = joined["p"].pct_change().dropna()
            rb = joined["b"].pct_change().dropna()
            common = pd.concat([rp, rb], axis=1).dropna()
            if not common.empty:
                active = common.iloc[:,0] - common.iloc[:,1]
                b_years = max((joined.index[-1] - joined.index[0]).days / 365.25, len(common)/12)
                b_cagr = (joined["b"].iloc[-1]/joined["b"].iloc[0])**(1/b_years)-1 if b_years > 0 else np.nan
                out["Benchmark CAGR"] = b_cagr
                out["Excess CAGR"] = cagr - b_cagr
                out["Information Ratio"] = (active.mean()*12)/(active.std()*math.sqrt(12)) if active.std() > 0 else np.nan
    return out

def backtest_diagnostics(series_dict):
    rows = []
    if not series_dict:
        return pd.DataFrame()
    bench = series_dict.get("S&P500 benchmark")
    for name, eq in series_dict.items():
        stats = perf_stats_professional(eq, benchmark=bench if name != "S&P500 benchmark" else None)
        if stats:
            rows.append({"Portfolio": name, **stats})
    return pd.DataFrame(rows)

def attribution_engine(real_df):
    if real_df is None or real_df.empty or "market_value" not in real_df.columns or real_df["market_value"].sum() <= 0:
        return pd.DataFrame()
    mapping = {
        "IBGS.MI":"Core Bonds", "MTHP.MI":"Core Bonds",
        "SGLD.MI":"Core Gold", "GDX.MI":"Gold Miners",
        "SXR8":"Equity Core", "VUAA":"Equity Core", "VWCE":"Equity Core",
        "ZPRV":"Small Cap Value", "BTC":"Crypto",
        "CMOD.MI":"Commodities", "RBOT.MI":"AI", "DFEN.MI":"Defense",
        "SMH":"Tactical"
    }
    df = real_df.copy()
    df["Block"] = df["ticker"].map(mapping).fillna("Other")
    total = df["market_value"].sum()
    out = df.groupby("Block").agg(
        MarketValue=("market_value","sum"),
        PnL=("pnl","sum")
    ).reset_index()
    out["Weight"] = out["MarketValue"]/total*100
    out["ContributionToPortfolioPnL"] = out["PnL"]/total*100
    out["RiskProxy"] = out["Weight"] * out["Block"].map({
        "Core Bonds":0.3, "Core Gold":0.6, "Equity Core":1.0, "Small Cap Value":1.25,
        "Crypto":2.0, "Commodities":0.9, "Gold Miners":1.4, "AI":1.4,
        "Defense":1.0, "Tactical":1.5, "Other":1.0
    }).fillna(1.0)
    return out.sort_values("MarketValue", ascending=False)

def historical_stress_engine(real_df):
    if real_df is None or real_df.empty or "market_value" not in real_df.columns or real_df["market_value"].sum() <= 0:
        return pd.DataFrame()
    scenarios = {
        "2008 GFC": {"Equity":-0.50, "Bonds":0.10, "Gold":0.05, "Commodities":-0.35, "Crypto":-0.65, "Gold Miners":-0.35},
        "Covid 2020": {"Equity":-0.34, "Bonds":0.06, "Gold":0.03, "Commodities":-0.25, "Crypto":-0.45, "Gold Miners":-0.25},
        "2022 Inflation": {"Equity":-0.25, "Bonds":-0.18, "Gold":0.00, "Commodities":0.18, "Crypto":-0.65, "Gold Miners":-0.15},
        "VIX 50": {"Equity":-0.22, "Bonds":0.03, "Gold":0.06, "Commodities":-0.10, "Crypto":-0.35, "Gold Miners":-0.20},
        "VIX 80": {"Equity":-0.35, "Bonds":0.06, "Gold":0.10, "Commodities":-0.15, "Crypto":-0.50, "Gold Miners":-0.25},
        "Bond + Equity Crash": {"Equity":-0.25, "Bonds":-0.15, "Gold":0.05, "Commodities":0.05, "Crypto":-0.45, "Gold Miners":-0.10},
    }
    asset_map = {
        "IBGS.MI":"Bonds","MTHP.MI":"Bonds","SGLD.MI":"Gold","GDX.MI":"Gold Miners",
        "CMOD.MI":"Commodities","BTC":"Crypto","SXR8":"Equity","ZPRV":"Equity",
        "VWCE":"Equity","VUAA":"Equity","RBOT.MI":"Equity","DFEN.MI":"Equity","SMH":"Equity"
    }
    rows = []
    for scenario, shocks in scenarios.items():
        impact = 0
        for _, r in real_df.iterrows():
            cls = asset_map.get(str(r["ticker"]), "Equity")
            impact += float(r["market_value"]) * shocks.get(cls, -0.10)
        total = real_df["market_value"].sum()
        rows.append({"Scenario":scenario, "EstimatedPnL":impact, "PortfolioImpactPct":impact/total*100})
    return pd.DataFrame(rows).sort_values("PortfolioImpactPct")

def fiscal_optimizer(real_df, tax_rate=26.0):
    if real_df is None or real_df.empty:
        return pd.DataFrame()
    df = real_df.copy()
    candidates = df[df["action"].isin(["SELL/TRIM"])].copy()
    if candidates.empty:
        return pd.DataFrame()
    candidates["sell_amount"] = candidates["trade_value"].abs()
    candidates["gain_ratio"] = np.where(candidates["market_value"]>0, candidates["pnl"]/candidates["market_value"], 0)
    candidates["tax_est"] = np.where(candidates["gain_ratio"]>0, candidates["sell_amount"]*candidates["gain_ratio"]*(tax_rate/100), 0)
    candidates["tax_drag_pct"] = np.where(candidates["sell_amount"]>0, candidates["tax_est"]/candidates["sell_amount"]*100, 0)
    candidates["priority"] = np.where(candidates["tax_drag_pct"]<5, "HIGH",
                              np.where(candidates["tax_drag_pct"]<15, "MEDIUM", "LOW/TAX REVIEW"))
    return candidates[["ticker","current_weight","target_weight","deviation_pp","sell_amount","pnl_pct","tax_est","tax_drag_pct","priority"]].sort_values(["priority","tax_drag_pct"])

def crisis_dashboard_payload(sc, current_vix, regime_score_v6, regime_mode_v6, dc):
    vixinfo = vix_adaptive_engine(current_vix, regime_score_v6)
    return {
        "Market Regime": regime_mode_v6,
        "Regime Score": regime_score_v6,
        "VIX": current_vix,
        "VIX Zone": vixinfo["Zone"],
        "VIX Action": vixinfo["Action"],
        "Decision": dc["Action"],
        "Confidence": sc.get("Confidence", np.nan),
        "Macro": traffic_light(sc.get("RegimeScore", 50)),
        "Market": traffic_light(sc.get("MarketRisk", 50)),
    }

def send_telegram(msg):
    token=secret("TELEGRAM_BOT_TOKEN"); chat=secret("TELEGRAM_CHAT_ID")
    if not token or not chat: return False,"Telegram secrets missing"
    try:
        r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",json={"chat_id":chat,"text":msg},timeout=15)
        return r.ok,r.text
    except Exception as e: return False,str(e)

# persistence
def default_portfolio_rows(vix_override=None):
    # v6.5: portfolio reale precompilato come base iniziale
    base = pd.DataFrame(PRELOADED_PORTFOLIO)

    required_cols = ["ticker","shares","avg_price","manual_price","broker","note"]
    for col in required_cols:
        if col not in base.columns:
            base[col] = "" if col in ["ticker","broker","note"] else 0.0

    base["ticker"] = base["ticker"].astype(str).replace({"CBTC.MI":"BTC", "BTC-USD":"BTC"})
    base = base[~base["ticker"].astype(str).isin(["VUSA.MI","WSML.MI"])]

    # Aggiunge eventuali righe satellite mancanti
    plan = satellite_plan(vix_override=vix_override)
    existing = set(base["ticker"].astype(str))
    extra = []
    for _, r in plan.iterrows():
        if str(r["Ticker"]) not in existing:
            extra.append({"ticker": r["Ticker"], "shares": 0.0, "avg_price": 0.0, "manual_price": 0.0, "broker": "", "note": ""})

    if extra:
        base = pd.concat([base, pd.DataFrame(extra)], ignore_index=True)

    base["shares"] = pd.to_numeric(base["shares"], errors="coerce").fillna(0.0)
    base["avg_price"] = pd.to_numeric(base["avg_price"], errors="coerce").fillna(0.0)
    base["manual_price"] = pd.to_numeric(base["manual_price"], errors="coerce").fillna(0.0)
    return clean_portfolio_df(base[required_cols])

def load_portfolio_csv(vix_override=None):
    try:
        df = pd.read_csv(PORTFOLIO_CSV)
        df = clean_portfolio_df(df)
        if df.empty:
            st.session_state["portfolio_source"] = "PRELOADED_EMPTY_CSV"
            return default_portfolio_rows(vix_override)
        st.session_state["portfolio_source"] = f"CSV: {PORTFOLIO_CSV}"
        return merge_template_with_saved(df, vix_override)
    except Exception:
        st.session_state["portfolio_source"] = "PRELOADED_DEFAULT"
        return default_portfolio_rows(vix_override)

def save_portfolio_csv(df):
    save_portfolio_with_backup(df)

def load_transactions_csv():
    try:
        df=pd.read_csv(TRANSACTIONS_CSV)
        for col in ["date","ticker","side","qty","price","fees","broker","note"]:
            if col not in df.columns: df[col]=""
        df["qty"]=pd.to_numeric(df["qty"],errors="coerce").fillna(0.0)
        df["price"]=pd.to_numeric(df["price"],errors="coerce").fillna(0.0)
        df["fees"]=pd.to_numeric(df["fees"],errors="coerce").fillna(0.0)
        return df[["date","ticker","side","qty","price","fees","broker","note"]]
    except Exception:
        return pd.DataFrame(columns=["date","ticker","side","qty","price","fees","broker","note"])
def save_transactions_csv(df):
    out=df.copy()
    for col in ["date","ticker","side","qty","price","fees","broker","note"]:
        if col not in out.columns: out[col]=""
    out["qty"]=pd.to_numeric(out["qty"],errors="coerce").fillna(0.0)
    out["price"]=pd.to_numeric(out["price"],errors="coerce").fillna(0.0)
    out["fees"]=pd.to_numeric(out["fees"],errors="coerce").fillna(0.0)
    out[["date","ticker","side","qty","price","fees","broker","note"]].to_csv(TRANSACTIONS_CSV,index=False)
def portfolio_from_transactions(tx):
    if tx is None or tx.empty: return pd.DataFrame(columns=["ticker","shares","avg_price","manual_price","broker","note"])
    rows=[]
    for ticker,g in tx.groupby("ticker"):
        qty_total=0.0; cost_total=0.0; broker=""
        for _,r in g.sort_values("date").iterrows():
            side=str(r["side"]).upper(); qty=float(r["qty"]); price=float(r["price"]); fees=float(r.get("fees",0.0))
            if side=="BUY":
                qty_total+=qty; cost_total+=qty*price+fees
            elif side=="SELL" and qty_total>0:
                avg=cost_total/qty_total; q=min(qty,qty_total); qty_total-=q; cost_total-=avg*q
            broker=r.get("broker","")
        avg_price=cost_total/qty_total if qty_total>0 else 0.0
        rows.append({"ticker":ticker,"shares":qty_total,"avg_price":avg_price,"manual_price":0.0,"broker":broker,"note":"auto PMC da transazioni"})
    return pd.DataFrame(rows)
def merge_template_with_saved(saved, vix_override=None):
    template=default_portfolio_rows(vix_override)
    if saved is None or saved.empty: return template
    out=saved.copy(); out = out[~out["ticker"].astype(str).isin(["VUSA.MI","WSML.MI"])] ; existing=set(out["ticker"].astype(str))
    missing=template[~template["ticker"].astype(str).isin(existing)]
    return pd.concat([out,missing],ignore_index=True)[["ticker","shares","avg_price","manual_price","broker","note"]]

if "snapshots" not in st.session_state: st.session_state["snapshots"]=[]
if "trades" not in st.session_state: st.session_state["trades"]=[]
if "transactions_df" not in st.session_state: st.session_state["transactions_df"]=load_transactions_csv()
if "portfolio_df" not in st.session_state: st.session_state["portfolio_df"]=merge_template_with_saved(load_portfolio_csv())

st.title("Portfolio Cockpit Alpha Pro v7.1")
st.caption("V7.1: Extended 10Y Proxy Backtest, VIX Adaptive Engine, Attribution, Fiscal Optimizer, Crisis Dashboard.")

with st.sidebar:
    period=st.selectbox("Periodo dashboard",["1y","2y","5y","10y"],index=2)
    btperiod=st.selectbox("Periodo backtest",["5y","10y","max"],index=1)
    band=st.number_input("Banda rebalance ± punti percentuali",1.0,20.0,5.0,.5)
    tax_rate=st.number_input("Aliquota fiscale indicativa plusvalenze %",0.0,40.0,26.0,.5)
    tax_budget=st.number_input("Tax budget annuale",0.0,100000.0,2000.0,100.0)
    simulate_rebalance_tax = st.checkbox("Simula tasse da rebalance", value=False, help="Se disattivato, il Tax Engine mostra solo plusvalenze latenti e non penalizza il Decision Center.")
    vix_stress=st.number_input("Scenario VIX manuale",0.0,100.0,0.0,1.0)
    vix_override=vix_stress if vix_stress>0 else None
    st.metric("Indicatori/proxy potenziali",INDICATOR_COUNT)

tabs=st.tabs(["Decision Center","Crisis Dashboard","Allocation","My Portfolio","Transactions","Scores","Decision Engine","Market","FRED","Relative Strength","Tactical Ranking","Satellite Auto","Professional Backtest","Attribution","Drift Monitor","Stress Test Pro","Fiscal Optimizer","Tax Engine","Data Quality","Scenario Simulator","Paper Trading","Alerts"])

current_vix = vix_override if vix_override is not None else last("^VIX")
portfolio_score=portfolio_health(st.session_state.get("real_table",pd.DataFrame()))
tax_score,tax_sells,tax_total,latent_tax_table,latent_tax_total=tax_engine(st.session_state.get("real_table",pd.DataFrame()),tax_rate,tax_budget,simulate_rebalance_tax)
sc=all_scores(vix_override,tax_efficiency=tax_score,portfolio_health=portfolio_score)
rebalance_needed=False
if "real_table" in st.session_state: rebalance_needed=bool((st.session_state["real_table"]["action"]!="HOLD").any())
dc=decision_center(sc,current_vix,rebalance_needed,tax_score,portfolio_score)

with tabs[0]:
    st.subheader("Alpha Pro Decision Center")
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Portfolio Health",f"{portfolio_score:.0f}/100"); c2.metric("Regime Score",f"{sc['RegimeScore']:.0f}/100"); c3.metric("Alpha Score",f"{sc['AlphaScore']:.0f}/100"); c4.metric("Confidence",f"{sc['Confidence']:.0f}/100"); c5.metric("VIX","n/a" if current_vix is None else f"{current_vix:.1f}")
    s1,s2,s3=st.columns(3); s1.metric("Macro",dc["MacroLight"]); s2.metric("Market",dc["MarketLight"]); s3.metric("Portfolio",dc["PortfolioLight"])
    st.markdown(f"### Azione consigliata oggi: **{dc['Action']}**")
    st.write(f"**VIX Regime:** {dc['VIXRegime']}"); st.write(f"**VIX Action:** {dc['VIXAction']}"); st.write(f"**Regime macro:** {regime_label(sc['RegimeScore'])}"); st.write("**Motivi:** "+"; ".join(dc["Reasons"]))
    st.write("### Satellite attuale"); st.dataframe(satellite_plan(vix_override=vix_override),use_container_width=True)

with tabs[1]:
    st.subheader("Crisis Dashboard")
    regime_score_v7, regime_mode_v7, regime_df_v7 = regime_engine_details(vix_override)
    payload = crisis_dashboard_payload(sc, current_vix, regime_score_v7, regime_mode_v7, dc)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Regime", payload["Market Regime"])
    c2.metric("Regime Score", f"{payload['Regime Score']:.0f}/100")
    c3.metric("VIX", "n/a" if payload["VIX"] is None else f"{payload['VIX']:.1f}")
    c4.metric("Decisione", payload["Decision"])
    st.info(f"VIX Zone: {payload['VIX Zone']} — {payload['VIX Action']}")
    st.dataframe(pd.DataFrame([payload]), use_container_width=True)
    st.write("### Regime components")
    st.dataframe(regime_df_v7, use_container_width=True)

with tabs[2]:
    core=pd.DataFrame([{"ticker":k,"name":v[0],"target":v[1],"bucket":v[2],"macro":v[3]} for k,v in CORE.items()])
    c1,c2,c3=st.columns(3); c1.metric("Core","87%"); c2.metric("Satellite dinamico","13%"); c3.metric("Total","100%")
    st.info("Satellite v6.1: AI 5% + Defense 5% + Tattico dinamico 3%. VUSA.MI e WSML.MI rimossi dal template.")
    st.dataframe(core,use_container_width=True)
    st.plotly_chart(px.pie(pd.concat([core.rename(columns={"target":"weight"})[["ticker","weight"]],pd.DataFrame([{"ticker":"Satellite Dynamic","weight":13}])]),names="ticker",values="weight"),use_container_width=True)

with tabs[3]:
    st.subheader("My Portfolio — Portfolio Persistence Engine")
    st.caption("CSV automatico + uploader reale + export + backup. Compila e premi 'Salva e aggiorna portafoglio'.")

    source = st.session_state.get("portfolio_source", "SESSION")
    st.info(f"Fonte portafoglio attuale: {source}")

    csave1, csave2, csave3, csave4 = st.columns(4)

    uploaded_portfolio = csave1.file_uploader(
        "Importa CSV",
        type=["csv"],
        key="portfolio_csv_uploader",
        help="Carica un file con colonne: ticker, shares, avg_price, manual_price, broker, note"
    )

    if uploaded_portfolio is not None:
        try:
            imported = pd.read_csv(uploaded_portfolio)
            st.session_state["portfolio_df"] = merge_template_with_saved(clean_portfolio_df(imported), vix_override)
            st.session_state["portfolio_source"] = "UPLOADED_CSV"
            save_portfolio_csv(st.session_state["portfolio_df"])
            st.success("CSV importato e salvato.")
            st.rerun()
        except Exception as e:
            st.error(f"Errore import CSV: {e}")

    if csave2.button("Carica CSV salvato"):
        st.session_state["portfolio_df"] = load_portfolio_csv(vix_override)
        st.success("Portafoglio caricato dal CSV salvato.")
        st.rerun()

    if csave3.button("Reset valori precompilati"):
        st.session_state["portfolio_df"] = default_portfolio_rows(vix_override)
        st.session_state["portfolio_source"] = "PRELOADED_DEFAULT_RESET"
        save_portfolio_csv(st.session_state["portfolio_df"])
        st.warning("Valori precompilati ripristinati e salvati.")
        st.rerun()

    if csave4.button("Usa PMC da transazioni"):
        st.session_state["portfolio_df"] = merge_template_with_saved(
            portfolio_from_transactions(st.session_state["transactions_df"]),
            vix_override
        )
        st.session_state["portfolio_source"] = "TRANSACTIONS_PMC"
        save_portfolio_csv(st.session_state["portfolio_df"])
        st.success("PMC calcolato da transazioni e salvato.")
        st.rerun()

    with st.form("portfolio_manual_form", clear_on_submit=False):
        edited_portfolio = st.data_editor(
            st.session_state["portfolio_df"],
            use_container_width=True,
            num_rows="dynamic",
            key="portfolio_editor_form",
            column_config={
                "ticker": st.column_config.TextColumn("ticker"),
                "shares": st.column_config.NumberColumn("shares", format="%.6f"),
                "avg_price": st.column_config.NumberColumn("avg_price", format="%.6f"),
                "manual_price": st.column_config.NumberColumn("manual_price", format="%.6f", help="Usato se Yahoo non trova il prezzo"),
                "broker": st.column_config.TextColumn("broker"),
                "note": st.column_config.TextColumn("note"),
            }
        )
        submitted = st.form_submit_button("Salva e aggiorna portafoglio")

    if submitted:
        st.session_state["portfolio_df"] = clean_portfolio_df(edited_portfolio)
        save_portfolio_csv(st.session_state["portfolio_df"])
        st.session_state["portfolio_source"] = "MANUAL_EDIT_SAVED"

        plan = satellite_plan(vix_override=vix_override)
        targets = {k: v[1] for k, v in CORE.items()}
        for _, r in plan.iterrows():
            targets[r["Ticker"]] = targets.get(r["Ticker"], 0) + float(r["TargetWeight"])

        targets = apply_equivalent_targets(st.session_state["portfolio_df"], targets)
        tab = real_table(st.session_state["portfolio_df"], targets, band)
        st.session_state["real_table"] = tab
        st.session_state["snapshots"].append({"time": datetime.utcnow(), "total": tab["market_value"].sum()})
        st.success("Portafoglio salvato, backup creato e metriche aggiornate.")
        st.rerun()

    st.download_button(
        "Scarica portfolio_positions.csv aggiornato",
        data=portfolio_to_csv_bytes(st.session_state["portfolio_df"]),
        file_name="portfolio_positions.csv",
        mime="text/csv"
    )

    if "real_table" in st.session_state:
        tab = st.session_state["real_table"]
        total = tab["market_value"].sum()
        pnl = tab["pnl"].sum()
        cost = tab["cost_value"].sum()

        a, b, c, d = st.columns(4)
        a.metric("Valore totale", f"{total:,.2f}")
        b.metric("P/L", f"{pnl:,.2f}")
        c.metric("P/L %", f"{(pnl/cost*100 if cost>0 else 0):.2f}%")
        d.metric("Portfolio Health", f"{portfolio_health(tab):.0f}/100")

        st.dataframe(tab, use_container_width=True)
        if total > 0:
            st.plotly_chart(px.pie(tab, names="ticker", values="current_weight"), use_container_width=True)

with tabs[4]:
    st.subheader("Transactions — storico e PMC automatico")
    st.caption("Inserimento manuale stabile: compila e premi 'Salva transazioni'.")

    tload1, tload2 = st.columns(2)

    if tload1.button("Carica transazioni da CSV"):
        st.session_state["transactions_df"] = load_transactions_csv()
        st.success("Transazioni caricate.")
        st.rerun()

    if tload2.button("Reset transazioni"):
        st.session_state["transactions_df"] = pd.DataFrame(
            columns=["date","ticker","side","qty","price","fees","broker","note"]
        )
        st.warning("Tabella transazioni resettata. Premi Salva per sovrascrivere il CSV.")

    with st.form("transactions_manual_form", clear_on_submit=False):
        edited_tx = st.data_editor(
            st.session_state["transactions_df"],
            use_container_width=True,
            num_rows="dynamic",
            key="transactions_editor_form",
            column_config={
                "date": st.column_config.TextColumn("date", help="Formato consigliato YYYY-MM-DD"),
                "side": st.column_config.SelectboxColumn("side", options=["BUY","SELL"]),
                "qty": st.column_config.NumberColumn("qty", format="%.6f"),
                "price": st.column_config.NumberColumn("price", format="%.6f"),
                "fees": st.column_config.NumberColumn("fees", format="%.4f"),
            }
        )
        tx_submitted = st.form_submit_button("Salva transazioni")

    if tx_submitted:
        st.session_state["transactions_df"] = edited_tx.copy()
        save_transactions_csv(st.session_state["transactions_df"])
        st.success("Transazioni salvate.")

    if st.button("Calcola portafoglio da transazioni"):
        st.dataframe(portfolio_from_transactions(st.session_state["transactions_df"]), use_container_width=True)

with tabs[5]:
    cols=st.columns(10); keys=["Macro","Inflation","Liquidity","Credit","Trend","Breadth","FearGreed","RelativeStrength","TaxEfficiency","PortfolioHealth"]
    for i,k in enumerate(keys): cols[i].metric(k,f"{sc[k]:.0f}")
    cols2=st.columns(4)
    for i,k in enumerate(["RegimeScore","AlphaScore","DefensivePressure","Confidence"]): cols2[i].metric(k,f"{sc[k]:.0f}/100")
with tabs[6]:
    st.subheader("V6 Decision Engine — Regime esplicito")
    regime_score_v6, regime_mode_v6, regime_df = regime_engine_details(vix_override)
    c1,c2,c3 = st.columns(3)
    c1.metric("Regime Engine Score", f"{regime_score_v6:.0f}/100")
    c2.metric("Risk Mode", regime_mode_v6)
    c3.metric("VIX Protocol", dc["VIXRegime"])
    st.dataframe(regime_df, use_container_width=True)
    st.info(f"Decisione sintetica: {dc['Action']} — Motivi: {'; '.join(dc['Reasons'])}")
    st.subheader("VIX Adaptive Engine")
    vix_info = vix_adaptive_engine(current_vix, regime_score_v6)
    st.dataframe(pd.DataFrame([vix_info]), use_container_width=True)

    st.subheader("Explainability satellite")
    plan_exp = satellite_plan(vix_override=vix_override)
    for _, r in plan_exp.iterrows():
        st.write(f"**{r['Slot']} — {r['Ticker']} — {r['Theme']}**")
        for reason in explain_satellite_row(r, vix_override):
            st.write("• " + reason)

with tabs[7]:
    out=[]
    for name,t in MARKET.items():
        df=hist(t,period)
        if df.empty: out.append({"Indicator":name,"Ticker":t,"Last":None}); continue
        c=df["Close"]; lc=float(c.iloc[-1]); ma200=sma(c,200)
        out.append({"Indicator":name,"Ticker":t,"Last":round(lc,4),"1M%":round(pc(c,21)*100,2) if len(c)>22 else None,"3M%":round(pc(c,63)*100,2) if len(c)>64 else None,"6M%":round(pc(c,126)*100,2) if len(c)>127 else None,"Trend":"above 200dma" if not pd.isna(ma200) and lc>ma200 else ("below 200dma" if not pd.isna(ma200) else "n/a"),"Vol3M":round(vol(c,63)*100,2) if not pd.isna(vol(c,63)) else None,"CurrentDD":round(current_drawdown(c)*100,2) if not pd.isna(current_drawdown(c)) else None})
    st.dataframe(pd.DataFrame(out),use_container_width=True)
with tabs[8]:
    out=[]
    for name,sid in FRED.items():
        df=fred(sid)
        if df.empty: out.append({"Indicator":name,"Series":sid,"Last":None,"Date":None})
        else:
            v=df["value"]; out.append({"Indicator":name,"Series":sid,"Last":round(float(v.iloc[-1]),4),"Date":str(df.index[-1].date()),"3M chg":round(float(v.iloc[-1]-v.iloc[-4]),4) if len(v)>4 else None,"12M chg":round(float(v.iloc[-1]-v.iloc[-13]),4) if len(v)>13 else None})
    st.dataframe(pd.DataFrame(out),use_container_width=True)
with tabs[9]:
    out=[]
    for name,(a,b) in RS_PAIRS.items():
        da,db=hist(a,"2y"),hist(b,"2y")
        if da.empty or db.empty: out.append({"Pair":name,"A":a,"B":b,"Score":None}); continue
        r=(da["Close"]/db["Close"]).dropna()
        out.append({"Pair":name,"A":a,"B":b,"3M%":round(pc(r,63)*100,2) if len(r)>64 else None,"6M%":round(pc(r,126)*100,2) if len(r)>127 else None,"Score":round(bscore(pc(r,126),15),1) if len(r)>127 else None})
    st.dataframe(pd.DataFrame(out),use_container_width=True)
with tabs[10]:
    df=ranking(period,vix_override); st.dataframe(df,use_container_width=True)
    top=df.dropna(subset=["Score"]).head(10)
    if not top.empty: st.plotly_chart(px.bar(top,x="Theme",y="Score",color="MacroSector"),use_container_width=True)
with tabs[11]:
    plan=satellite_plan(vix_override=vix_override); st.dataframe(plan,use_container_width=True)
with tabs[12]:
    st.subheader("Professional Backtest V7.1")
    st.caption("Modalità reale oppure proxy esteso 10Y. Il periodo effettivo viene mostrato sempre.")

    bt_mode = st.radio(
        "Backtest mode",
        ["Real ETF History", "Extended 10Y Proxy History"],
        index=1,
        horizontal=True,
        help="Real ETF History usa solo gli ETF reali. Extended 10Y Proxy usa proxy storici per ETF giovani."
    )

    reb_freq=st.selectbox("Frequenza ribilanciamento",["Annuale","Semestrale","Trimestrale"],index=0, key="prof_reb_freq")
    months={"Annuale":12,"Semestrale":6,"Trimestrale":3}[reb_freq]

    with st.expander("Mostra mappa proxy usata per backtest esteso"):
        proxy_table = pd.DataFrame([{"Ticker operativo":k, "Proxy backtest":v} for k,v in BACKTEST_PROXY.items()])
        st.dataframe(proxy_table, use_container_width=True)

    if st.button("Esegui Professional Backtest"):
        dyn=dynamic_alpha_weights(vix_override)
        raw_portfolios = [
            ("Golden Butterfly proxy", normalize(GOLDEN_BUTTERFLY)),
            ("Alpha Pro static", normalize(ALPHA_STATIC)),
            ("Alpha Pro dynamic current", normalize(dyn)),
            ("S&P500 benchmark", {"SPY":1.0})
        ]

        series={}
        effective_weights_rows=[]
        for name,w in raw_portfolios:
            mapped_w = backtest_proxy_map(w, bt_mode)
            mapped_w = normalize(mapped_w)
            for tk, wt in mapped_w.items():
                effective_weights_rows.append({"Portfolio":name, "BacktestTicker":tk, "Weight":wt})
            eq=backtest(mapped_w, btperiod, months)
            if not eq.empty:
                series[name]=eq

        if not series:
            st.error("Dati insufficienti.")
        else:
            df_bt=pd.concat(series,axis=1).dropna()
            st.line_chart(df_bt)

            years_eff = (df_bt.index[-1]-df_bt.index[0]).days/365.25
            p1,p2,p3,p4=st.columns(4)
            p1.metric("Start", str(df_bt.index[0].date()))
            p2.metric("End", str(df_bt.index[-1].date()))
            p3.metric("Years effettivi", f"{years_eff:.2f}")
            p4.metric("Mode", bt_mode)

            if bt_mode == "Real ETF History" and years_eff < 9 and btperiod == "10y":
                st.warning("Stai usando storico ETF reale: alcuni ETF sono giovani, quindi il periodo comune è inferiore a 10 anni.")
            if bt_mode == "Extended 10Y Proxy History" and years_eff >= 9:
                st.success("Backtest esteso attivo: il periodo effettivo è vicino ai 10 anni richiesti.")
            elif bt_mode == "Extended 10Y Proxy History":
                st.warning("Anche con proxy esteso il periodo resta inferiore a 9 anni: almeno un proxy non ha abbastanza dati.")

            st.write("### Metriche professionali")
            stats = backtest_diagnostics({c:df_bt[c] for c in df_bt.columns})
            pct_cols = ["Total Return","CAGR","Volatility","Max Drawdown","Hit Ratio","Benchmark CAGR","Excess CAGR"]
            for col in pct_cols:
                if col in stats.columns:
                    stats[col] = stats[col]*100
            st.dataframe(stats, use_container_width=True)

            st.write("### Ticker effettivamente usati nel backtest")
            st.dataframe(pd.DataFrame(effective_weights_rows), use_container_width=True)

            st.info("La modalità proxy non è un backtest perfettamente investibile: serve a stimare il comportamento di lungo periodo prima del lancio degli ETF reali.")

with tabs[13]:
    st.subheader("Attribution Engine")
    if "real_table" not in st.session_state:
        st.warning("Prima aggiorna My Portfolio.")
    else:
        attr = attribution_engine(st.session_state["real_table"])
        st.dataframe(attr, use_container_width=True)
        if not attr.empty:
            st.plotly_chart(px.pie(attr, names="Block", values="Weight"), use_container_width=True)

with tabs[14]:
    st.subheader("Drift Monitor — regola ±5%")
    if "real_table" not in st.session_state:
        st.warning("Prima aggiorna My Portfolio.")
    else:
        drift = drift_monitor_table(st.session_state["real_table"])
        st.dataframe(drift, use_container_width=True)
        high = drift[drift["severity"].isin(["HIGH","MEDIUM"])]
        if high.empty:
            st.success("Nessun drift rilevante oltre soglia.")
        else:
            st.warning("Drift rilevante rilevato. Verificare Tax Engine prima di operare.")

with tabs[15]:
    st.subheader("Stress Test Pro")
    if "real_table" not in st.session_state:
        st.warning("Prima aggiorna My Portfolio.")
    else:
        st.write("### Historical / synthetic stress scenarios")
        hstress = historical_stress_engine(st.session_state["real_table"])
        st.dataframe(hstress, use_container_width=True)
        if not hstress.empty:
            st.plotly_chart(px.bar(hstress, x="Scenario", y="PortfolioImpactPct"), use_container_width=True)
        st.write("### Custom scenario")
        scenario_stress = st.selectbox("Scenario stress", ["VIX 80 / panic","Inflazione alta","Recessione","Risk-on forte"], key="stress_scenario")
        stress_df = stress_test_estimate(st.session_state["real_table"], scenario_stress)
        st.dataframe(stress_df, use_container_width=True)
        if not stress_df.empty:
            impact = stress_df["estimated_pnl"].sum()
            total = st.session_state["real_table"]["market_value"].sum()
            st.metric("Impatto stimato", f"{impact:,.2f}", f"{impact/total*100:.2f}%")

with tabs[16]:
    st.subheader("Fiscal Optimizer")
    if "real_table" not in st.session_state:
        st.warning("Prima aggiorna My Portfolio.")
    else:
        opt = fiscal_optimizer(st.session_state["real_table"], tax_rate)
        if opt.empty:
            st.success("Nessuna vendita suggerita dal drift monitor.")
        else:
            st.dataframe(opt, use_container_width=True)
            st.info("Priorità HIGH = minore attrito fiscale stimato. Prima di operare verificare sempre broker/commercialista.")

with tabs[17]:
    st.subheader("Tax Engine v6.7")
    mode = "REBALANCE TAX SIMULATION" if simulate_rebalance_tax else "MONITOR ONLY"
    st.info(f"Modalità fiscale attiva: {mode}")

    ctax1, ctax2, ctax3 = st.columns(3)
    ctax1.metric("Tax Efficiency Score", f"{tax_score:.0f}/100")
    ctax2.metric("Tasse stimate da rebalance", f"{tax_total:,.2f}")
    ctax3.metric("Tasse latenti teoriche", f"{latent_tax_total:,.2f}")

    st.caption("Monitor Only: le tasse da vendita NON vengono considerate finché non attivi 'Simula tasse da rebalance' nella sidebar.")

    st.subheader("Plusvalenze / minusvalenze latenti")
    if latent_tax_table is not None and not latent_tax_table.empty:
        st.dataframe(latent_tax_table, use_container_width=True)
    else:
        st.success("Nessun dato fiscale disponibile.")

    st.subheader("Simulazione tasse da ribilanciamento")
    if not simulate_rebalance_tax:
        st.warning("Simulazione disattivata. Attiva 'Simula tasse da rebalance' nella sidebar per vedere le tasse sulle vendite suggerite.")
    else:
        if tax_sells is not None and not tax_sells.empty:
            st.dataframe(tax_sells, use_container_width=True)
        else:
            st.success("Nessuna vendita fiscalmente rilevante rilevata.")

with tabs[18]:
    st.subheader("Data Quality — controllo prezzi e ticker")
    qdf = data_quality_table(st.session_state.get("portfolio_df", pd.DataFrame()))
    st.dataframe(qdf, use_container_width=True)
    bad = qdf[qdf["status"] == "MISSING"] if not qdf.empty else pd.DataFrame()
    if bad.empty:
        st.success("Tutti i ticker hanno un prezzo risolto tramite Yahoo, manual_price o fallback PMC.")
    else:
        st.error("Alcuni ticker non hanno prezzo. Inserisci manual_price o correggi il ticker.")
        st.dataframe(bad, use_container_width=True)

with tabs[19]:
    scenario=st.selectbox("Scenario",["VIX 80 / panic","Inflazione alta","Recessione","Risk-on forte"])
    for item in scenario_protocol(scenario): st.write("• "+item)
with tabs[20]:
    with st.form("paper"):
        ticker=st.text_input("Ticker"); action=st.selectbox("Azione",["BUY","SELL","HOLD","REDUCE","OVERWEIGHT"]); weight=st.number_input("Peso target",0.0,100.0,0.0,.5); reason=st.text_area("Motivo"); notes=st.text_area("Note")
        if st.form_submit_button("Salva"):
            st.session_state["trades"].append({"time":datetime.utcnow(),"ticker":ticker,"action":action,"weight":weight,"reason":reason,"notes":notes}); st.success("Paper trade salvato.")
    st.dataframe(pd.DataFrame(st.session_state["trades"]),use_container_width=True)
with tabs[21]:
    msg=st.text_area("Messaggio","Portfolio Cockpit Alpha Pro v7.1: test alert.")
    if st.button("Invia Telegram"):
        ok,resp=send_telegram(msg); st.success("Inviato") if ok else st.error(resp)