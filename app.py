
import os, math, requests
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Portfolio Cockpit Alpha Pro v5", layout="wide")

# ======================================================
# CONFIG
# ======================================================

CORE = {
    "IBGS.MI": ("Euro Gov Bond 1-3Y", 8.0, "Short Bonds", "Bonds"),
    "MTHP.MI": ("Euro Gov Bond 25+Y", 4.0, "Long Bonds", "Bonds"),
    "SGLD.MI": ("Physical Gold", 15.0, "Gold", "Gold"),
    "VUSA.MI": ("S&P500 / Equity Core proxy", 22.0, "Equity Core", "Equity"),
    "WSML.MI": ("World Small Cap", 19.0, "Small Cap", "Equity"),
    "CBTC.MI": ("Bitcoin ETP", 5.0, "Bitcoin", "Crypto"),
    "CMOD.MI": ("Broad Commodities", 8.0, "Commodities", "Commodities"),
    "GDX.MI": ("Gold Miners", 6.0, "Performance Gold", "Gold"),
}

SAT_WEIGHTS = [5.0, 5.0, 3.0]
INDICATOR_COUNT = 120

GOLDEN_BUTTERFLY = {"IBGS.MI":20, "MTHP.MI":20, "SGLD.MI":20, "VUSA.MI":20, "WSML.MI":20}
ALPHA_STATIC = {"IBGS.MI":8, "MTHP.MI":4, "SGLD.MI":15, "VUSA.MI":22, "WSML.MI":19, "CBTC.MI":5, "CMOD.MI":8, "GDX.MI":6, "DFEN.MI":5, "RBOT.MI":5, "XEON.MI":3}

MARKET = {
    "S&P500":"^GSPC", "Nasdaq100":"^NDX", "Russell2000":"^RUT", "VIX":"^VIX",
    "DollarIndex":"DX-Y.NYB", "Gold":"GC=F", "Copper":"HG=F", "WTI":"CL=F",
    "Bitcoin":"BTC-USD", "US10Y":"^TNX", "RSP":"RSP", "SPY":"SPY", "QQQ":"QQQ",
    "XLU":"XLU", "DBC":"DBC", "AGG":"AGG", "GDX":"GDX", "GLD":"GLD",
    "HYG":"HYG", "IEF":"IEF", "TLT":"TLT", "LQD":"LQD", "IWM":"IWM",
    "GoldMiners":"GDX", "LongTreasury":"TLT", "ShortTreasury":"SHY"
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

# ======================================================
# DATA
# ======================================================

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

def last(ticker):
    df=hist(ticker,"5d")
    return None if df.empty else float(df["Close"].iloc[-1])

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

# ======================================================
# MATH
# ======================================================

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
    sc=50+(20 if lc>ma50 else 0)+(20 if lc>ma200 else 0)+(10 if ma50>ma200 else 0)
    return float(max(0,min(100,sc)))

def mom(c):
    if len(c)<130: return np.nan
    return bscore(.2*pc(c,21)+.35*pc(c,63)+.45*pc(c,126),12)

def rel(a,b="SPY"):
    da,db=hist(a,"2y"),hist(b,"2y")
    if da.empty or db.empty: return np.nan
    r=(da["Close"]/db["Close"]).dropna()
    if len(r)<130: return np.nan
    return bscore(.35*pc(r,63)+.65*pc(r,126),15)

# ======================================================
# SCORES
# ======================================================

def inflation_score():
    cpi=fred("CPIAUCSL")
    if cpi.empty or len(cpi)<14: return 50
    yoy=cpi["value"].iloc[-1]/cpi["value"].iloc[-13]-1
    # Higher inflation pressure = lower risk-asset score
    return max(0,min(100,75-yoy*500))

def liquidity_score():
    parts=[]; m2=fred("M2SL"); cpi=fred("CPIAUCSL"); fedf=fred("FEDFUNDS"); nfci=fred("NFCI")
    if not m2.empty and len(m2)>13: parts.append(bscore(m2["value"].iloc[-1]/m2["value"].iloc[-13]-1,20))
    if not cpi.empty and len(cpi)>13 and not fedf.empty:
        cpi_yoy=cpi["value"].iloc[-1]/cpi["value"].iloc[-13]-1
        real_rate=fedf["value"].iloc[-1]-cpi_yoy*100
        parts.append(max(0,min(100,70-real_rate*8)))
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
    parts=[]
    for t in ["^GSPC","^NDX","^RUT"]:
        df=hist(t,"2y")
        if not df.empty: parts.append(trend(df["Close"]))
    return mean(parts)

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
    if v is not None:
        parts.append(90 if v<10 else 75 if v<15 else 60 if v<25 else 40 if v<35 else 20 if v<60 else 5)
    parts.append(breadth_score())
    parts.append(credit_score())
    sp=hist("SPY","1y")
    if not sp.empty and len(sp)>126:
        parts.append(bscore(pc(sp["Close"],126),8))
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
    vals=[]
    for a,b in RS_PAIRS.values():
        vals.append(rel(a,b))
    return mean(vals)

def market_risk_score(vix_override=None):
    parts=[]; v=vix_override if vix_override is not None else last("^VIX")
    if v is not None:
        parts.append(90 if v<15 else 75 if v<20 else 55 if v<25 else 35 if v<30 else 10 if v<60 else 0)
    parts.append(trend_market_score())
    parts.append(credit_score())
    return mean(parts)

def all_scores(vix_override=None, tax_efficiency=80, portfolio_health=80):
    macro=macro_score()
    inflation=inflation_score()
    liquidity=liquidity_score()
    credit=credit_score()
    trend_s=trend_market_score()
    breadth=breadth_score()
    feargreed=fear_greed_score(vix_override)
    rs=relative_strength_score()
    real=real_assets_score()
    marketrisk=market_risk_score(vix_override)
    regime=.20*macro+.15*liquidity+.15*credit+.15*trend_s+.15*breadth+.10*inflation+.10*marketrisk
    alpha=.15*macro+.15*liquidity+.15*credit+.15*trend_s+.15*breadth+.10*rs+.10*real+.05*feargreed
    defensive=max(0,min(100,100-(.30*marketrisk+.20*breadth+.20*liquidity+.20*credit+.10*macro)))
    confidence=mean([macro,liquidity,credit,trend_s,breadth,rs,portfolio_health,tax_efficiency])
    return {
        "Macro":macro,"Inflation":inflation,"Liquidity":liquidity,"Credit":credit,
        "Trend":trend_s,"Breadth":breadth,"FearGreed":feargreed,"RelativeStrength":rs,
        "TaxEfficiency":tax_efficiency,"PortfolioHealth":portfolio_health,
        "RealAssets":real,"MarketRisk":marketrisk,
        "RegimeScore":regime,"AlphaScore":alpha,"DefensivePressure":defensive,"Confidence":confidence
    }

def regime_label(reg):
    if reg>=80: return "Expansion / Strong Risk-On"
    if reg>=65: return "Growth / Risk-On"
    if reg>=50: return "Neutral"
    if reg>=35: return "Slowdown"
    return "Recession / Risk-Off"

def traffic_light(score, high=65, low=45):
    if score>=high: return "🟢"
    if score>=low: return "🟡"
    return "🔴"

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
    scs=all_scores(vix_override)
    rows=[]
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
    scs=all_scores(vix_override)
    v=vix_override if vix_override is not None else last("^VIX")
    if scs["DefensivePressure"]>=80 or (v is not None and v>=60):
        return pd.DataFrame([
            {"Slot":"SAT1","Theme":"Cash/Bond breve","MacroSector":"Cash","Ticker":"XEON.MI","Score":None,"TargetWeight":5.0},
            {"Slot":"SAT2","Theme":"Cash/Bond breve","MacroSector":"Cash","Ticker":"XEON.MI","Score":None,"TargetWeight":5.0},
            {"Slot":"SAT3","Theme":"Gold / safe haven","MacroSector":"Gold","Ticker":"SGLD.MI","Score":None,"TargetWeight":3.0},
        ])
    df=ranking("5y", vix_override).dropna(subset=["Score"])
    df=df[df["Score"]>=75]
    selected=[]; used_macro={}
    for _,r in df.iterrows():
        macro=r["MacroSector"]
        if used_macro.get(macro,0)>=max_per_macro: continue
        selected.append(r); used_macro[macro]=used_macro.get(macro,0)+1
        if len(selected)==3: break
    out=[]
    for i,r in enumerate(selected):
        out.append({"Slot":f"SAT{i+1}","Theme":r["Theme"],"MacroSector":r["MacroSector"],"Ticker":r["Ticker"],"Score":r["Score"],"TargetWeight":SAT_WEIGHTS[i]})
    for j in range(len(out),3):
        out.append({"Slot":f"SAT{j+1}","Theme":"Cash/Bond breve","MacroSector":"Cash","Ticker":"XEON.MI","Score":None,"TargetWeight":SAT_WEIGHTS[j]})
    return pd.DataFrame(out)

def normalize(d):
    s=sum(d.values())
    return {k:v/s for k,v in d.items() if v>0}

def price_matrix(weights, period):
    frames=[]
    for t in weights:
        df=hist(t,period)
        if not df.empty and "Close" in df.columns:
            s=df["Close"].copy()
            s.index=pd.to_datetime(s.index, errors="coerce")
            s=s[~s.index.isna()].sort_index()
            frames.append(s.rename(t))
    if not frames: return pd.DataFrame()
    pm=pd.concat(frames,axis=1)
    pm.index=pd.to_datetime(pm.index, errors="coerce")
    pm=pm[~pm.index.isna()].sort_index()
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
        val*=1+float((cur*r).sum()); out.append((dt,val))
        cur=cur*(1+r); cur=cur/cur.sum()
        if i%rebalance_months==0: cur=w.copy()
    return pd.Series([v for d,v in out],index=[d for d,v in out])

def dynamic_alpha_weights(vix_override=None):
    plan=satellite_plan(vix_override=vix_override)
    weights={k:v[1] for k,v in CORE.items()}
    for _,r in plan.iterrows():
        weights[r["Ticker"]]=weights.get(r["Ticker"],0)+float(r["TargetWeight"])
    return weights

def perf_stats(eq):
    if eq.empty or len(eq)<3: return {}
    r=eq.pct_change().dropna(); years=len(r)/12
    cagr=(eq.iloc[-1]/eq.iloc[0])**(1/years)-1 if years>0 else np.nan
    vv=r.std()*math.sqrt(12); downside=r[r<0]
    sortino=cagr/(downside.std()*math.sqrt(12)) if len(downside)>1 and downside.std()>0 else np.nan
    draw=eq/eq.cummax()-1; maxdd=draw.min()
    ulcer=math.sqrt(np.mean((draw[draw<0]*100)**2)) if len(draw)>0 else np.nan
    calmar=cagr/abs(maxdd) if maxdd<0 else np.nan
    sharpe=cagr/vv if vv>0 else np.nan
    return {"CAGR":cagr,"Volatility":vv,"Max Drawdown":maxdd,"Sharpe":sharpe,"Sortino":sortino,"Calmar":calmar,"Ulcer Index":ulcer,"Final Multiple":eq.iloc[-1]/eq.iloc[0]}

def real_table(df, targets, band):
    x=df.copy(); x["last_price"]=x["ticker"].apply(lambda t: last(t) or 0)
    x["market_value"]=x["shares"]*x["last_price"]; x["cost_value"]=x["shares"]*x["avg_price"]
    x["pnl"]=x["market_value"]-x["cost_value"]
    x["pnl_pct"]=np.where(x["cost_value"]>0,x["pnl"]/x["cost_value"]*100,np.nan)
    total=x["market_value"].sum()
    x["current_weight"]=0 if total<=0 else x["market_value"]/total*100
    x["target_weight"]=x["ticker"].map(targets).fillna(0)
    x["deviation_pp"]=x["current_weight"]-x["target_weight"]
    x["target_value"]=total*x["target_weight"]/100
    x["trade_value"]=x["target_value"]-x["market_value"]
    x["action"]=np.where(x["deviation_pp"]>band,"SELL/TRIM",np.where(x["deviation_pp"]<-band,"BUY/ADD","HOLD"))
    return x

def portfolio_health(df):
    if df.empty or df["market_value"].sum()<=0: return 80
    weights=df["market_value"]/df["market_value"].sum()
    concentration=weights.max()*100
    n_eff=1/(weights**2).sum()
    score=100
    if concentration>25: score-=15
    if concentration>35: score-=25
    if n_eff<5: score-=25
    elif n_eff<8: score-=10
    return max(0,min(100,score))

def tax_engine(df, tax_rate, tax_budget):
    if df is None or df.empty:
        return 80, pd.DataFrame(), 0
    sells=df[df["trade_value"]<0].copy()
    if sells.empty:
        return 100, sells, 0
    sells["sell_amount"]=sells["trade_value"].abs()
    sells["gain_ratio"]=np.where(sells["market_value"]>0,sells["pnl"]/sells["market_value"],0)
    sells["taxable_gain_est"]=np.where(sells["gain_ratio"]>0,sells["sell_amount"]*sells["gain_ratio"],0)
    sells["tax_est"]=sells["taxable_gain_est"]*(tax_rate/100)
    sells["net_after_tax"]=sells["sell_amount"]-sells["tax_est"]
    tax_total=float(sells["tax_est"].sum())
    if tax_total==0: score=100
    elif tax_total<=tax_budget*0.25: score=85
    elif tax_total<=tax_budget*0.5: score=70
    elif tax_total<=tax_budget: score=50
    else: score=25
    return score, sells, tax_total

def decision_center(scores, vix, rebalance_needed, tax_score, portfolio_score):
    macro_light=traffic_light(scores["RegimeScore"])
    market_light=traffic_light(scores["MarketRisk"])
    portfolio_light="🟢" if portfolio_score>=80 and not rebalance_needed else "🟡" if portfolio_score>=60 else "🔴"
    vix_regime, vix_action, mode=vix_ladder(vix)
    action="HOLD"
    reasons=[]
    if vix is not None and vix>=80:
        action="CRASH PROTOCOL"
        reasons.append("VIX extreme crash")
    elif scores["DefensivePressure"]>=80:
        action="DEFENSIVE HOLD"
        reasons.append("High defensive pressure")
    elif rebalance_needed and tax_score>=50:
        action="REBALANCE"
        reasons.append("Portfolio outside ±5% and tax impact acceptable")
    elif rebalance_needed and tax_score<50:
        action="DEFER / TAX REVIEW"
        reasons.append("Rebalance needed but tax impact high")
    elif scores["AlphaScore"]>=70 and scores["RegimeScore"]>=60 and mode in ["Normal","Caution"]:
        action="HOLD / SATELLITE ACTIVE"
        reasons.append("Risk regime supports satellite")
    else:
        reasons.append("No strong action signal")
    return {"MacroLight":macro_light,"MarketLight":market_light,"PortfolioLight":portfolio_light,"VIXRegime":vix_regime,"VIXAction":vix_action,"Mode":mode,"Action":action,"Reasons":reasons}

def scenario_protocol(name):
    if name=="VIX 80 / panic":
        return ["Satellite: 10% XEON/bond breve + 3% oro.","Nessuna vendita forzata del core.","Acquisti solo a tranche.","Controllo credit spread + HYG/IEF.","Ribilanciamento solo se deviazione > ±5 pp e impatto fiscale accettabile."]
    if name=="Inflazione alta":
        return ["Favoriti: commodities, gold, miners, bitcoin moderato.","Penalizzati: bond lunghi.","Riduci duration se credit stress basso."]
    if name=="Recessione":
        return ["Favoriti: bond breve, bond lungo moderato, oro.","Penalizzati: small cap, cyclicals, crypto.","Satellite verso cash/bond breve."]
    if name=="Risk-on forte":
        return ["Satellite pieno sui top sector.","Mantieni stop concentrazione macro-settore.","Non inseguire se score sotto 75."]
    return []

def send_telegram(msg):
    token=secret("TELEGRAM_BOT_TOKEN"); chat=secret("TELEGRAM_CHAT_ID")
    if not token or not chat: return False,"Telegram secrets missing"
    try:
        r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",json={"chat_id":chat,"text":msg},timeout=15)
        return r.ok,r.text
    except Exception as e: return False,str(e)

# ======================================================
# SESSION
# ======================================================

if "snapshots" not in st.session_state: st.session_state["snapshots"]=[]
if "trades" not in st.session_state: st.session_state["trades"]=[]

# ======================================================
# UI
# ======================================================

st.title("Portfolio Cockpit Alpha Pro v5")
st.caption("Decision Center Edition: 110+ indicatori → 10 score → 3 semafori → 1 decisione.")

with st.sidebar:
    period=st.selectbox("Periodo dashboard",["1y","2y","5y","10y"],index=2)
    btperiod=st.selectbox("Periodo backtest",["5y","10y","max"],index=1)
    band=st.number_input("Banda rebalance ± punti percentuali",1.0,20.0,5.0,.5)
    tax_rate=st.number_input("Aliquota fiscale indicativa plusvalenze %",0.0,40.0,26.0,.5)
    tax_budget=st.number_input("Tax budget annuale",0.0,100000.0,2000.0,100.0)
    vix_stress=st.number_input("Scenario VIX manuale",0.0,100.0,0.0,1.0)
    vix_override = vix_stress if vix_stress>0 else None
    st.metric("Indicatori/proxy potenziali",INDICATOR_COUNT)

tabs=st.tabs(["Decision Center","Allocation","My Portfolio","Scores","Market","FRED","Relative Strength","Tactical Ranking","Satellite Auto","Backtest","Tax Engine","Scenario Simulator","Paper Trading","Alerts"])

# Compute global decision context
current_vix = vix_override if vix_override is not None else last("^VIX")
portfolio_score = portfolio_health(st.session_state.get("real_table", pd.DataFrame()))
tax_score, tax_sells, tax_total = tax_engine(st.session_state.get("real_table", pd.DataFrame()), tax_rate, tax_budget)
sc = all_scores(vix_override, tax_efficiency=tax_score, portfolio_health=portfolio_score)
rebalance_needed = False
if "real_table" in st.session_state:
    rebalance_needed = bool((st.session_state["real_table"]["action"]!="HOLD").any())
dc = decision_center(sc, current_vix, rebalance_needed, tax_score, portfolio_score)

with tabs[0]:
    st.subheader("Alpha Pro Decision Center")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Portfolio Health", f"{portfolio_score:.0f}/100")
    c2.metric("Regime Score", f"{sc['RegimeScore']:.0f}/100")
    c3.metric("Alpha Score", f"{sc['AlphaScore']:.0f}/100")
    c4.metric("Confidence", f"{sc['Confidence']:.0f}/100")
    c5.metric("VIX", "n/a" if current_vix is None else f"{current_vix:.1f}")

    s1,s2,s3 = st.columns(3)
    s1.metric("Macro", dc["MacroLight"])
    s2.metric("Market", dc["MarketLight"])
    s3.metric("Portfolio", dc["PortfolioLight"])

    st.markdown(f"### Azione consigliata oggi: **{dc['Action']}**")
    st.write(f"**VIX Regime:** {dc['VIXRegime']}")
    st.write(f"**VIX Action:** {dc['VIXAction']}")
    st.write(f"**Regime macro:** {regime_label(sc['RegimeScore'])}")
    st.write("**Motivi:** " + "; ".join(dc["Reasons"]))

    plan=satellite_plan(vix_override=vix_override)
    st.write("### Satellite attuale")
    st.dataframe(plan,use_container_width=True)

    message = f"""ALPHA PRO DECISION CENTER
Action: {dc['Action']}
Portfolio Health: {portfolio_score:.0f}/100
Regime: {sc['RegimeScore']:.0f}/100
Alpha: {sc['AlphaScore']:.0f}/100
Confidence: {sc['Confidence']:.0f}/100
VIX: {'n/a' if current_vix is None else round(current_vix,1)}
VIX Regime: {dc['VIXRegime']}
Reasons: {'; '.join(dc['Reasons'])}
"""
    st.code(message)
    if st.button("Invia Decision Center via Telegram"):
        ok,resp=send_telegram(message)
        st.success("Inviato") if ok else st.error(resp)

with tabs[1]:
    core=pd.DataFrame([{"ticker":k,"name":v[0],"target":v[1],"bucket":v[2],"macro":v[3]} for k,v in CORE.items()])
    c1,c2,c3=st.columns(3); c1.metric("Core","87%"); c2.metric("Satellite dinamico","13%"); c3.metric("Total","100%")
    st.dataframe(core,use_container_width=True)
    st.plotly_chart(px.pie(pd.concat([core.rename(columns={"target":"weight"})[["ticker","weight"]],pd.DataFrame([{"ticker":"Satellite Dynamic","weight":13}])]),names="ticker",values="weight"),use_container_width=True)

with tabs[2]:
    plan=satellite_plan(vix_override=vix_override)
    rows=[{"ticker":t,"shares":0.0,"avg_price":0.0} for t in CORE]
    for _,r in plan.iterrows(): rows.append({"ticker":r["Ticker"],"shares":0.0,"avg_price":0.0})
    pos=st.data_editor(pd.DataFrame(rows),use_container_width=True,num_rows="dynamic",key="real")
    if st.button("Aggiorna portafoglio reale"):
        targets={k:v[1] for k,v in CORE.items()}
        for _,r in plan.iterrows(): targets[r["Ticker"]]=targets.get(r["Ticker"],0)+float(r["TargetWeight"])
        tab=real_table(pos,targets,band)
        st.session_state["real_table"]=tab
        st.session_state["snapshots"].append({"time":datetime.utcnow(),"total":tab["market_value"].sum()})
        st.rerun()
    if "real_table" in st.session_state:
        tab=st.session_state["real_table"]; total=tab["market_value"].sum(); pnl=tab["pnl"].sum(); cost=tab["cost_value"].sum()
        a,b,c,d=st.columns(4); a.metric("Valore totale",f"{total:,.2f}"); b.metric("P/L",f"{pnl:,.2f}"); c.metric("P/L %",f"{(pnl/cost*100 if cost>0 else 0):.2f}%"); d.metric("Portfolio Health",f"{portfolio_health(tab):.0f}/100")
        st.dataframe(tab,use_container_width=True)
        if total>0: st.plotly_chart(px.pie(tab,names="ticker",values="current_weight"),use_container_width=True)
    if st.session_state["snapshots"]:
        st.line_chart(pd.DataFrame(st.session_state["snapshots"]).set_index("time")["total"])

with tabs[3]:
    cols=st.columns(10)
    keys=["Macro","Inflation","Liquidity","Credit","Trend","Breadth","FearGreed","RelativeStrength","TaxEfficiency","PortfolioHealth"]
    for i,k in enumerate(keys): cols[i].metric(k,f"{sc[k]:.0f}")
    st.divider()
    cols2=st.columns(4)
    for i,k in enumerate(["RegimeScore","AlphaScore","DefensivePressure","Confidence"]): cols2[i].metric(k,f"{sc[k]:.0f}/100")

with tabs[4]:
    out=[]
    for name,t in MARKET.items():
        df=hist(t,period)
        if df.empty: out.append({"Indicator":name,"Ticker":t,"Last":None}); continue
        c=df["Close"]; lc=float(c.iloc[-1]); ma200=sma(c,200)
        out.append({"Indicator":name,"Ticker":t,"Last":round(lc,4),"1M%":round(pc(c,21)*100,2) if len(c)>22 else None,"3M%":round(pc(c,63)*100,2) if len(c)>64 else None,"6M%":round(pc(c,126)*100,2) if len(c)>127 else None,"Trend":"above 200dma" if not pd.isna(ma200) and lc>ma200 else ("below 200dma" if not pd.isna(ma200) else "n/a"),"Vol3M":round(vol(c,63)*100,2) if not pd.isna(vol(c,63)) else None,"CurrentDD":round(current_drawdown(c)*100,2) if not pd.isna(current_drawdown(c)) else None})
    st.dataframe(pd.DataFrame(out),use_container_width=True)

with tabs[5]:
    out=[]
    for name,sid in FRED.items():
        df=fred(sid)
        if df.empty: out.append({"Indicator":name,"Series":sid,"Last":None,"Date":None})
        else:
            v=df["value"]
            out.append({"Indicator":name,"Series":sid,"Last":round(float(v.iloc[-1]),4),"Date":str(df.index[-1].date()),"3M chg":round(float(v.iloc[-1]-v.iloc[-4]),4) if len(v)>4 else None,"12M chg":round(float(v.iloc[-1]-v.iloc[-13]),4) if len(v)>13 else None})
    st.dataframe(pd.DataFrame(out),use_container_width=True)

with tabs[6]:
    out=[]
    for name,(a,b) in RS_PAIRS.items():
        da,db=hist(a,"2y"),hist(b,"2y")
        if da.empty or db.empty: out.append({"Pair":name,"A":a,"B":b,"Score":None}); continue
        r=(da["Close"]/db["Close"]).dropna()
        out.append({"Pair":name,"A":a,"B":b,"3M%":round(pc(r,63)*100,2) if len(r)>64 else None,"6M%":round(pc(r,126)*100,2) if len(r)>127 else None,"Score":round(bscore(pc(r,126),15),1) if len(r)>127 else None})
    st.dataframe(pd.DataFrame(out),use_container_width=True)

with tabs[7]:
    df=ranking(period,vix_override)
    st.dataframe(df,use_container_width=True)
    top=df.dropna(subset=["Score"]).head(10)
    if not top.empty: st.plotly_chart(px.bar(top,x="Theme",y="Score",color="MacroSector"),use_container_width=True)

with tabs[8]:
    plan=satellite_plan(vix_override=vix_override)
    st.dataframe(plan,use_container_width=True)
    msg="Satellite automatico v5:\n"+"\n".join([f"{r['Slot']}: {r['Ticker']} {r['TargetWeight']}% ({r['Theme']})" for _,r in plan.iterrows()])
    st.code(msg)

with tabs[9]:
    reb_freq=st.selectbox("Frequenza ribilanciamento",["Annuale","Semestrale","Trimestrale"],index=0)
    months={"Annuale":12,"Semestrale":6,"Trimestrale":3}[reb_freq]
    if st.button("Esegui backtest comparativo"):
        dyn=dynamic_alpha_weights(vix_override)
        series={}
        for name,w in [("Golden Butterfly proxy",normalize(GOLDEN_BUTTERFLY)),("Alpha Pro static",normalize(ALPHA_STATIC)),("Alpha Pro dynamic current",normalize(dyn)),("S&P500 benchmark",{"SPY":1.0})]:
            eq=backtest(w,btperiod,months)
            if not eq.empty: series[name]=eq
        if not series: st.error("Dati insufficienti.")
        else:
            df=pd.concat(series,axis=1).dropna(); st.line_chart(df)
            rows=[]
            for n in df.columns:
                ps=perf_stats(df[n])
                rows.append({"Portfolio":n,**{k:(round(v*100,2) if k not in ["Final Multiple","Ulcer Index"] else round(v,2)) for k,v in ps.items()}})
            st.dataframe(pd.DataFrame(rows),use_container_width=True)

with tabs[10]:
    st.subheader("Tax Engine")
    st.metric("Tax Efficiency Score", f"{tax_score:.0f}/100")
    st.metric("Tasse stimate", f"{tax_total:,.2f}")
    if tax_sells is not None and not tax_sells.empty:
        st.dataframe(tax_sells[["ticker","market_value","pnl","pnl_pct","sell_amount","taxable_gain_est","tax_est","net_after_tax"]],use_container_width=True)
    else:
        st.success("Nessuna vendita fiscalmente rilevante rilevata.")

with tabs[11]:
    scenario=st.selectbox("Scenario",["VIX 80 / panic","Inflazione alta","Recessione","Risk-on forte"])
    for item in scenario_protocol(scenario): st.write("• " + item)
    if scenario=="VIX 80 / panic":
        st.dataframe(satellite_plan(vix_override=80),use_container_width=True)

with tabs[12]:
    with st.form("paper"):
        ticker=st.text_input("Ticker"); action=st.selectbox("Azione",["BUY","SELL","HOLD","REDUCE","OVERWEIGHT"]); weight=st.number_input("Peso target",0.0,100.0,0.0,.5); reason=st.text_area("Motivo"); notes=st.text_area("Note")
        if st.form_submit_button("Salva"):
            st.session_state["trades"].append({"time":datetime.utcnow(),"ticker":ticker,"action":action,"weight":weight,"reason":reason,"notes":notes})
            st.success("Paper trade salvato.")
    st.dataframe(pd.DataFrame(st.session_state["trades"]),use_container_width=True)

with tabs[13]:
    msg=st.text_area("Messaggio","Portfolio Cockpit Alpha Pro v5: test alert.")
    if st.button("Invia Telegram"):
        ok,resp=send_telegram(msg); st.success("Inviato") if ok else st.error(resp)
