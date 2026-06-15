
import os, math, requests
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Portfolio Cockpit Alpha Pro v4", layout="wide")

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
INDICATOR_COUNT = 110

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
    parts=[]; yc=fred("T10Y2Y"); hy=fred("BAMLH0A0HYM2"); ig=fred("BAMLC0A0CM")
    cf=fred("CFNAI"); un=fred("UNRATE"); ip=fred("INDPRO"); retail=fred("RSAFS")
    if not yc.empty: parts.append(max(0,min(100,50+yc["value"].iloc[-1]*10)))
    if not hy.empty: parts.append(max(0,min(100,80-hy["value"].iloc[-1]*8)))
    if not ig.empty: parts.append(max(0,min(100,85-ig["value"].iloc[-1]*12)))
    if not cf.empty: parts.append(max(0,min(100,50+cf["value"].iloc[-1]*25)))
    if not un.empty and len(un)>6: parts.append(max(0,min(100,55-(un["value"].iloc[-1]-un["value"].iloc[-7])*35)))
    if not ip.empty and len(ip)>13: parts.append(bscore(ip["value"].iloc[-1]/ip["value"].iloc[-13]-1,30))
    if not retail.empty and len(retail)>13: parts.append(bscore(retail["value"].iloc[-1]/retail["value"].iloc[-13]-1,15))
    return mean(parts)

def market_score(vix_override=None):
    parts=[]; v=vix_override if vix_override is not None else last("^VIX")
    if v is not None:
        parts.append(90 if v<15 else 75 if v<20 else 55 if v<25 else 35 if v<30 else 10 if v<60 else 0)
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

def real_assets_score():
    parts=[]
    for a,b in [("DBC","AGG"),("GC=F","^GSPC"),("HG=F","GC=F"),("GDX","GLD")]:
        da,db=hist(a,"2y"),hist(b,"2y")
        if not da.empty and not db.empty:
            r=(da["Close"]/db["Close"]).dropna()
            if len(r)>126: parts.append(bscore(pc(r,126),12))
    return mean(parts)

def scores(vix_override=None):
    liq=liquidity_score(); mac=macro_score(); risk=market_score(vix_override); br=breadth_score(); real=real_assets_score()
    regime=.25*(liq+mac+risk+br)
    alpha=.2*liq+.2*mac+.25*risk+.2*br+.15*real
    defensive=max(0,min(100,100-(.35*risk+.25*br+.2*liq+.2*mac)))
    return {"Liquidity":liq,"Macro":mac,"MarketRisk":risk,"Breadth":br,"RealAssets":real,"RegimeScore":regime,"AlphaScore":alpha,"DefensivePressure":defensive}

def regime_label(reg):
    if reg>=80: return "Expansion / Strong Risk-On"
    if reg>=65: return "Growth / Risk-On"
    if reg>=50: return "Neutral"
    if reg>=35: return "Slowdown"
    return "Recession / Risk-Off"

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
    scs=scores(vix_override); rows=[]
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
    scs=scores(vix_override)
    if scs["DefensivePressure"]>=80 or (vix_override is not None and vix_override>=60):
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
    if df.empty or df["market_value"].sum()<=0: return 0
    weights=df["market_value"]/df["market_value"].sum()
    concentration=weights.max()*100
    n_eff=1/(weights**2).sum()
    score=100
    if concentration>25: score-=20
    if concentration>35: score-=20
    if n_eff<5: score-=25
    if n_eff<8: score-=10
    return max(0,min(100,score))

def scenario_protocol(name):
    if name=="VIX 80 / panic":
        return [
            "Blocca nuovi acquisti rischiosi per 24-72h salvo piano predefinito.",
            "Satellite: 10% XEON/bond breve + 3% oro.",
            "Nessuna vendita forzata del core se dentro piano strategico.",
            "Usa cash solo a tranche: 25% subito, 25% se -10%, 25% se -20%, 25% a segnale di stabilizzazione.",
            "Controlla credit spread e HYG/IEF: se peggiorano, resta difensivo.",
            "Ribilancia solo se deviazione > ±5 pp e impatto fiscale accettabile.",
        ]
    if name=="Inflazione alta":
        return ["Favoriti: commodities, gold, miners, bitcoin moderato.", "Penalizzati: bond lunghi.", "Riduci duration se credit stress basso."]
    if name=="Recessione":
        return ["Favoriti: bond breve, bond lungo moderato, oro.", "Penalizzati: small cap, cyclicals, crypto.", "Satellite verso cash/bond breve."]
    if name=="Risk-on forte":
        return ["Satellite pieno sui top sector.", "Mantieni stop di concentrazione macro-settore.", "Non inseguire se score sotto 75."]
    return []

def send_telegram(msg):
    token=secret("TELEGRAM_BOT_TOKEN"); chat=secret("TELEGRAM_CHAT_ID")
    if not token or not chat: return False,"Telegram secrets missing"
    try:
        r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",json={"chat_id":chat,"text":msg},timeout=15)
        return r.ok,r.text
    except Exception as e: return False,str(e)

if "snapshots" not in st.session_state: st.session_state["snapshots"]=[]
if "trades" not in st.session_state: st.session_state["trades"]=[]

st.title("Portfolio Cockpit Alpha Pro v4")
st.caption("Wealth & Tax Edition: tax-aware rebalance, scenario engine, VIX stress protocol.")

with st.sidebar:
    period=st.selectbox("Periodo dashboard",["1y","2y","5y","10y"],index=2)
    btperiod=st.selectbox("Periodo backtest",["5y","10y","max"],index=1)
    band=st.number_input("Banda rebalance ± punti percentuali",1.0,20.0,5.0,.5)
    tax_rate=st.number_input("Aliquota fiscale indicativa plusvalenze %",0.0,40.0,26.0,.5)
    vix_stress=st.number_input("Scenario VIX manuale",0.0,100.0,0.0,1.0)
    vix_override = vix_stress if vix_stress>0 else None
    st.metric("Indicatori/proxy potenziali",INDICATOR_COUNT)

tabs=st.tabs(["Allocation","My Portfolio","Scores","Market","FRED","Relative Strength","Tactical Ranking","Satellite Auto","Backtest","Tax Engine","Scenario Simulator","Paper Trading","Alerts"])

with tabs[0]:
    core=pd.DataFrame([{"ticker":k,"name":v[0],"target":v[1],"bucket":v[2],"macro":v[3]} for k,v in CORE.items()])
    c1,c2,c3=st.columns(3); c1.metric("Core","87%"); c2.metric("Satellite dinamico","13%"); c3.metric("Total","100%")
    st.dataframe(core,use_container_width=True)
    st.plotly_chart(px.pie(pd.concat([core.rename(columns={"target":"weight"})[["ticker","weight"]],pd.DataFrame([{"ticker":"Satellite Dynamic","weight":13}])]),names="ticker",values="weight"),use_container_width=True)

with tabs[1]:
    plan=satellite_plan(vix_override=vix_override)
    rows=[{"ticker":t,"shares":0.0,"avg_price":0.0} for t in CORE]
    for _,r in plan.iterrows(): rows.append({"ticker":r["Ticker"],"shares":0.0,"avg_price":0.0})
    pos=st.data_editor(pd.DataFrame(rows),use_container_width=True,num_rows="dynamic",key="real")
    if st.button("Aggiorna portafoglio reale"):
        targets={k:v[1] for k,v in CORE.items()}
        for _,r in plan.iterrows(): targets[r["Ticker"]]=targets.get(r["Ticker"],0)+float(r["TargetWeight"])
        tab=real_table(pos,targets,band); st.session_state["real_table"]=tab
        st.session_state["snapshots"].append({"time":datetime.utcnow(),"total":tab["market_value"].sum()})
    if "real_table" in st.session_state:
        tab=st.session_state["real_table"]; total=tab["market_value"].sum(); pnl=tab["pnl"].sum(); cost=tab["cost_value"].sum()
        a,b,c,d=st.columns(4); a.metric("Valore totale",f"{total:,.2f}"); b.metric("P/L",f"{pnl:,.2f}"); c.metric("P/L %",f"{(pnl/cost*100 if cost>0 else 0):.2f}%"); d.metric("Portfolio Health",f"{portfolio_health(tab):.0f}/100")
        st.dataframe(tab,use_container_width=True)
        if total>0: st.plotly_chart(px.pie(tab,names="ticker",values="current_weight"),use_container_width=True)
    if st.session_state["snapshots"]:
        st.line_chart(pd.DataFrame(st.session_state["snapshots"]).set_index("time")["total"])

with tabs[2]:
    sc=scores(vix_override)
    cols=st.columns(8)
    for i,k in enumerate(["Liquidity","Macro","MarketRisk","Breadth","RealAssets","RegimeScore","AlphaScore","DefensivePressure"]): cols[i].metric(k,f"{sc[k]:.0f}/100")
    st.info(f"Regime attuale: {regime_label(sc['RegimeScore'])}")

with tabs[3]:
    out=[]
    for name,t in MARKET.items():
        df=hist(t,period)
        if df.empty: out.append({"Indicator":name,"Ticker":t,"Last":None}); continue
        c=df["Close"]; lc=float(c.iloc[-1]); ma200=sma(c,200)
        out.append({"Indicator":name,"Ticker":t,"Last":round(lc,4),"1M%":round(pc(c,21)*100,2) if len(c)>22 else None,"3M%":round(pc(c,63)*100,2) if len(c)>64 else None,"6M%":round(pc(c,126)*100,2) if len(c)>127 else None,"Trend":"above 200dma" if not pd.isna(ma200) and lc>ma200 else ("below 200dma" if not pd.isna(ma200) else "n/a"),"Vol3M":round(vol(c,63)*100,2) if not pd.isna(vol(c,63)) else None,"CurrentDD":round(mdd(c)*100,2) if not pd.isna(mdd(c)) else None})
    st.dataframe(pd.DataFrame(out),use_container_width=True)

with tabs[4]:
    out=[]
    for name,sid in FRED.items():
        df=fred(sid)
        if df.empty: out.append({"Indicator":name,"Series":sid,"Last":None,"Date":None})
        else:
            v=df["value"]
            out.append({"Indicator":name,"Series":sid,"Last":round(float(v.iloc[-1]),4),"Date":str(df.index[-1].date()),"3M chg":round(float(v.iloc[-1]-v.iloc[-4]),4) if len(v)>4 else None,"12M chg":round(float(v.iloc[-1]-v.iloc[-13]),4) if len(v)>13 else None})
    st.dataframe(pd.DataFrame(out),use_container_width=True)

with tabs[5]:
    out=[]
    for name,(a,b) in RS_PAIRS.items():
        da,db=hist(a,"2y"),hist(b,"2y")
        if da.empty or db.empty: out.append({"Pair":name,"A":a,"B":b,"Score":None}); continue
        r=(da["Close"]/db["Close"]).dropna()
        out.append({"Pair":name,"A":a,"B":b,"3M%":round(pc(r,63)*100,2) if len(r)>64 else None,"6M%":round(pc(r,126)*100,2) if len(r)>127 else None,"Score":round(bscore(pc(r,126),15),1) if len(r)>127 else None})
    st.dataframe(pd.DataFrame(out),use_container_width=True)

with tabs[6]:
    df=ranking(period,vix_override)
    st.dataframe(df,use_container_width=True)
    top=df.dropna(subset=["Score"]).head(10)
    if not top.empty: st.plotly_chart(px.bar(top,x="Theme",y="Score",color="MacroSector"),use_container_width=True)

with tabs[7]:
    plan=satellite_plan(max_per_macro=1,vix_override=vix_override)
    st.dataframe(plan,use_container_width=True)
    msg="Satellite automatico v4:\n"+"\n".join([f"{r['Slot']}: {r['Ticker']} {r['TargetWeight']}% ({r['Theme']})" for _,r in plan.iterrows()])
    st.code(msg)
    if st.button("Invia piano via Telegram"):
        ok,resp=send_telegram(msg); st.success("Inviato") if ok else st.error(resp)

with tabs[8]:
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

with tabs[9]:
    st.subheader("Tax Engine")
    if "real_table" not in st.session_state:
        st.warning("Prima aggiorna My Portfolio.")
    else:
        tab=st.session_state["real_table"].copy()
        sells=tab[tab["trade_value"]<0].copy()
        if sells.empty:
            st.success("Nessuna vendita richiesta.")
        else:
            sells["sell_amount"]=sells["trade_value"].abs()
            sells["gain_ratio"]=np.where(sells["market_value"]>0,sells["pnl"]/sells["market_value"],0)
            sells["taxable_gain_est"]=np.where(sells["gain_ratio"]>0,sells["sell_amount"]*sells["gain_ratio"],0)
            sells["tax_est"]=sells["taxable_gain_est"]*(tax_rate/100)
            sells["net_after_tax"]=sells["sell_amount"]-sells["tax_est"]
            st.dataframe(sells[["ticker","market_value","pnl","pnl_pct","sell_amount","taxable_gain_est","tax_est","net_after_tax"]],use_container_width=True)
            st.metric("Tasse stimate",f"{sells['tax_est'].sum():,.2f}")
            st.info("Stima indicativa: non sostituisce calcolo fiscale del broker/commercialista.")

with tabs[10]:
    st.subheader("Scenario Simulator")
    scenario=st.selectbox("Scenario",["VIX 80 / panic","Inflazione alta","Recessione","Risk-on forte"])
    for item in scenario_protocol(scenario):
        st.write("• " + item)
    if scenario=="VIX 80 / panic":
        stress_plan=satellite_plan(vix_override=80)
        st.write("Piano satellite in scenario VIX 80:")
        st.dataframe(stress_plan,use_container_width=True)

with tabs[11]:
    with st.form("paper"):
        ticker=st.text_input("Ticker"); action=st.selectbox("Azione",["BUY","SELL","HOLD","REDUCE","OVERWEIGHT"]); weight=st.number_input("Peso target",0.0,100.0,0.0,.5); reason=st.text_area("Motivo"); notes=st.text_area("Note")
        if st.form_submit_button("Salva"):
            st.session_state["trades"].append({"time":datetime.utcnow(),"ticker":ticker,"action":action,"weight":weight,"reason":reason,"notes":notes})
            st.success("Paper trade salvato.")
    st.dataframe(pd.DataFrame(st.session_state["trades"]),use_container_width=True)

with tabs[12]:
    msg=st.text_area("Messaggio","Portfolio Cockpit Alpha Pro v4: test alert.")
    if st.button("Invia Telegram"):
        ok,resp=send_telegram(msg); st.success("Inviato") if ok else st.error(resp)
