import os, math, json, sqlite3, requests
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.express as px
from datetime import datetime, date

st.set_page_config(page_title="Portfolio Cockpit Alpha Pro", layout="wide")

# ======================================================
# ALPHA PRO CONFIG
# ======================================================

CORE = {
    "IBGS.MI": ("Euro Gov Bond 1-3Y", 8.0, "Short Bonds"),
    "MTHP.MI": ("Euro Gov Bond 25+Y", 4.0, "Long Bonds"),
    "SGLD.MI": ("Physical Gold", 15.0, "Gold"),
    "VUSA.MI": ("S&P500 / Equity Core proxy", 22.0, "Equity Core"),
    "WSML.MI": ("World Small Cap", 19.0, "Small Cap"),
    "CBTC.MI": ("Bitcoin ETP", 5.0, "Bitcoin"),
    "CMOD.MI": ("Broad Commodities", 8.0, "Commodities"),
    "GDX.MI": ("Gold Miners", 6.0, "Performance Gold"),
}
SAT_TARGETS = {"SAT1": 5.0, "SAT2": 5.0, "SAT3": 3.0}

MARKET = {
    "S&P500": "^GSPC", "Nasdaq100": "^NDX", "Russell2000": "^RUT", "VIX": "^VIX",
    "DollarIndex": "DX-Y.NYB", "Gold": "GC=F", "Silver": "SI=F", "Copper": "HG=F",
    "WTI": "CL=F", "Brent": "BZ=F", "NatGas": "NG=F", "US10Y": "^TNX",
    "Bitcoin": "BTC-USD", "EURUSD": "EURUSD=X", "BalticDryProxy": "BDRY",
    "TLT": "TLT", "IEF": "IEF", "HYG": "HYG", "LQD": "LQD",
    "RSP": "RSP", "SPY": "SPY", "QQQ": "QQQ", "XLU": "XLU",
    "DBC": "DBC", "AGG": "AGG", "GDX": "GDX", "GLD": "GLD",
}

FRED = {
    "FedFunds": "FEDFUNDS",
    "CPI": "CPIAUCSL",
    "M2": "M2SL",
    "DGS10": "DGS10",
    "DGS2": "DGS2",
    "YieldCurve10Y2Y": "T10Y2Y",
    "HighYieldSpread": "BAMLH0A0HYM2",
    "IGSpread": "BAMLC0A0CM",
    "CFNAI": "CFNAI",
    "Unemployment": "UNRATE",
    "IndustrialProduction": "INDPRO",
    "RetailSales": "RSAFS",
    "FinancialConditions": "NFCI",
    "RealGDP": "GDPC1",
    "PCE": "PCE",
    "HousingStarts": "HOUST",
    "ConsumerSentiment": "UMCSENT",
}

TACTICAL = {
    "Defense": ["DFEN.MI", "ITA", "XAR"],
    "AI_Automation": ["RBOT.MI", "BOTZ", "ROBO"],
    "Energy": ["XLE", "IXC"],
    "Uranium": ["URA", "URNM"],
    "Healthcare": ["XLV", "IXJ"],
    "Financials": ["XLF", "IXG"],
    "Industrials": ["XLI", "EXI"],
    "Technology": ["XLK", "IYW"],
    "Semiconductors": ["SMH", "SOXX"],
    "SmallValue": ["IJS", "VBR"],
    "Commodities": ["CMOD.MI", "DBC"],
    "GoldMiners": ["GDX.MI", "GDX"],
    "Infrastructure": ["IGF", "PAVE"],
    "Water": ["PHO", "IH2O.L"],
    "CleanEnergy": ["ICLN", "QCLN"],
    "Cybersecurity": ["HACK", "CIBR"],
    "Aerospace": ["XAR", "ITA"],
}

RS_PAIRS = {
    "Gold/SP500": ("GC=F", "^GSPC"),
    "Copper/Gold": ("HG=F", "GC=F"),
    "SmallCap/SP500": ("^RUT", "^GSPC"),
    "Commodities/Bonds": ("DBC", "AGG"),
    "Bitcoin/Gold": ("BTC-USD", "GC=F"),
    "Nasdaq/Utilities": ("QQQ", "XLU"),
    "EqualWeight/CapWeight": ("RSP", "SPY"),
    "GoldMiners/Gold": ("GDX", "GLD"),
    "HighYield/Treasury": ("HYG", "IEF"),
    "Tech/SP500": ("XLK", "SPY"),
    "Energy/SP500": ("XLE", "SPY"),
    "Healthcare/SP500": ("XLV", "SPY"),
}

INDICATOR_COUNT = 78
DB_PATH = "alpha_pro_cockpit.db"

# ======================================================
# DATA
# ======================================================

def secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)

@st.cache_data(ttl=3600)
def hist(ticker, period="5y"):
    try:
        df = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def last(ticker):
    df = hist(ticker, "5d")
    if df.empty:
        return None
    return float(df["Close"].iloc[-1])

@st.cache_data(ttl=21600)
def fred(sid):
    key = secret("FRED_API_KEY")
    if not key:
        return pd.DataFrame()
    try:
        js = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": sid, "api_key": key, "file_type": "json"},
            timeout=20
        ).json()
        df = pd.DataFrame(js.get("observations", []))
        if df.empty:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"].replace(".", pd.NA), errors="coerce")
        return df.set_index("date")[["value"]].dropna()
    except Exception:
        return pd.DataFrame()

# ======================================================
# MATH
# ======================================================

def pc(s, n):
    if len(s) <= n:
        return np.nan
    return float(s.iloc[-1] / s.iloc[-n-1] - 1)

def sma(s, n):
    if len(s) < n:
        return np.nan
    return float(s.rolling(n).mean().iloc[-1])

def vol(s, n=63):
    r = s.pct_change().dropna()
    if len(r) < n:
        return np.nan
    return float(r.tail(n).std() * math.sqrt(252))

def mdd(s):
    if len(s) < 2:
        return np.nan
    return float((s / s.cummax() - 1).min())

def zscore_last(s, n=252):
    if len(s) < n:
        return np.nan
    w = s.tail(n)
    sd = w.std()
    if sd == 0:
        return np.nan
    return float((w.iloc[-1] - w.mean()) / sd)

def bscore(x, scale=10):
    if pd.isna(x):
        return np.nan
    return float(100 / (1 + np.exp(-x * scale)))

def clean_mean(values, default=50):
    vals = [v for v in values if v is not None and not pd.isna(v)]
    if not vals:
        return default
    return float(np.nanmean(vals))

def trend_score(c):
    if len(c) < 200:
        return np.nan
    lastc = float(c.iloc[-1])
    ma50 = sma(c, 50)
    ma200 = sma(c, 200)
    score = 50
    if lastc > ma50:
        score += 20
    if lastc > ma200:
        score += 20
    if ma50 > ma200:
        score += 10
    return float(max(0, min(100, score)))

def momentum_score(c):
    if len(c) < 130:
        return np.nan
    raw = .20*pc(c,21) + .35*pc(c,63) + .45*pc(c,126)
    return bscore(raw, 12)

def vol_penalty(c):
    v = vol(c, 63)
    if pd.isna(v):
        return 0
    return max(0, min(30, (v - .25) * 70))

def rel_score(a, b="SPY", period="2y"):
    da, db = hist(a, period), hist(b, period)
    if da.empty or db.empty:
        return np.nan
    r = (da["Close"] / db["Close"]).dropna()
    if len(r) < 130:
        return np.nan
    return bscore(.35*pc(r,63) + .65*pc(r,126), 15)

# ======================================================
# SCORES
# ======================================================

def liquidity_score():
    parts = []
    m2 = fred("M2SL")
    cpi = fred("CPIAUCSL")
    fedf = fred("FEDFUNDS")
    nfci = fred("NFCI")

    if not m2.empty and len(m2) > 13:
        m2_yoy = m2["value"].iloc[-1]/m2["value"].iloc[-13]-1
        parts.append(bscore(m2_yoy, 20))

    if not cpi.empty and len(cpi) > 13 and not fedf.empty:
        cpi_yoy = cpi["value"].iloc[-1]/cpi["value"].iloc[-13]-1
        real_rate = fedf["value"].iloc[-1] - cpi_yoy*100
        parts.append(max(0, min(100, 70 - real_rate*8)))

    if not nfci.empty:
        val = nfci["value"].iloc[-1]
        parts.append(max(0, min(100, 60 - val*40)))

    return clean_mean(parts)

def macro_score():
    parts = []
    yc = fred("T10Y2Y")
    hy = fred("BAMLH0A0HYM2")
    ig = fred("BAMLC0A0CM")
    cfnai = fred("CFNAI")
    un = fred("UNRATE")
    ip = fred("INDPRO")
    retail = fred("RSAFS")

    if not yc.empty:
        parts.append(max(0, min(100, 50 + yc["value"].iloc[-1]*10)))
    if not hy.empty:
        parts.append(max(0, min(100, 80 - hy["value"].iloc[-1]*8)))
    if not ig.empty:
        parts.append(max(0, min(100, 85 - ig["value"].iloc[-1]*12)))
    if not cfnai.empty:
        parts.append(max(0, min(100, 50 + cfnai["value"].iloc[-1]*25)))
    if not un.empty and len(un) > 6:
        delta = un["value"].iloc[-1] - un["value"].iloc[-7]
        parts.append(max(0, min(100, 55 - delta*35)))
    if not ip.empty and len(ip) > 13:
        yoy = ip["value"].iloc[-1]/ip["value"].iloc[-13]-1
        parts.append(bscore(yoy, 30))
    if not retail.empty and len(retail) > 13:
        yoy = retail["value"].iloc[-1]/retail["value"].iloc[-13]-1
        parts.append(bscore(yoy, 15))

    return clean_mean(parts)

def market_risk_score():
    parts = []
    v = last("^VIX")
    if v is not None:
        if v < 15: parts.append(90)
        elif v < 20: parts.append(75)
        elif v < 25: parts.append(55)
        elif v < 30: parts.append(35)
        else: parts.append(20)

    for t in ["^GSPC", "^NDX", "^RUT"]:
        df = hist(t, "2y")
        if not df.empty:
            parts.append(trend_score(df["Close"]))

    # credit proxy HYG/IEF
    hyg, ief = hist("HYG", "2y"), hist("IEF", "2y")
    if not hyg.empty and not ief.empty:
        r = (hyg["Close"]/ief["Close"]).dropna()
        if len(r) > 126:
            parts.append(bscore(pc(r,126),15))

    return clean_mean(parts)

def breadth_score():
    parts = []
    for a,b in [("RSP","SPY"),("^RUT","^GSPC"),("QQQ","XLU"),("IWM","SPY")]:
        da, db = hist(a, "2y"), hist(b, "2y")
        if da.empty or db.empty:
            continue
        r = (da["Close"]/db["Close"]).dropna()
        if len(r) > 126:
            parts.append(bscore(pc(r,126), 15))
    return clean_mean(parts)

def inflation_real_assets_score():
    parts = []
    for a,b in [("DBC","AGG"),("GC=F","^GSPC"),("HG=F","GC=F"),("GDX","GLD")]:
        da, db = hist(a, "2y"), hist(b, "2y")
        if da.empty or db.empty:
            continue
        r = (da["Close"]/db["Close"]).dropna()
        if len(r) > 126:
            parts.append(bscore(pc(r,126), 12))
    return clean_mean(parts)

def composite_scores():
    liq = liquidity_score()
    mac = macro_score()
    risk = market_risk_score()
    br = breadth_score()
    real = inflation_real_assets_score()

    regime = .25*liq + .25*mac + .25*risk + .25*br
    alpha = .20*liq + .20*mac + .25*risk + .20*br + .15*real
    defensive = 100 - (.35*risk + .25*br + .20*liq + .20*mac)
    return {
        "Liquidity": liq,
        "Macro": mac,
        "MarketRisk": risk,
        "Breadth": br,
        "RealAssets": real,
        "RegimeScore": regime,
        "AlphaScore": alpha,
        "DefensivePressure": max(0, min(100, defensive)),
    }

def tactical_score(ticker, scores):
    df = hist(ticker, "5y")
    if df.empty or len(df) < 200:
        return np.nan
    c = df["Close"]
    mom = momentum_score(c)
    tr = trend_score(c)
    rs = rel_score(ticker, "SPY")
    if pd.isna(rs):
        rs = 50
    if pd.isna(mom) or pd.isna(tr):
        return np.nan
    score = .30*mom + .20*rs + .20*tr + .15*scores["Breadth"] + .15*scores["AlphaScore"]
    score -= vol_penalty(c) * .25
    return float(max(0, min(100, score)))

def signal(sc):
    if pd.isna(sc):
        return "NO DATA"
    if sc >= 75:
        return "OVERWEIGHT / BUY"
    if sc >= 60:
        return "HOLD"
    if sc >= 45:
        return "NEUTRAL"
    return "REDUCE / EXIT"

def allocation_rule(score):
    if score >= 75:
        return "Eligible for satellite"
    if score >= 60:
        return "Hold only"
    if score >= 45:
        return "Neutral / watch"
    return "Avoid / reduce"

# ======================================================
# DB
# ======================================================

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS paper_trades(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        ticker TEXT,
        action TEXT,
        weight REAL,
        reason TEXT,
        notes TEXT
    )""")
    con.commit()
    con.close()

def add_trade(ticker, action, weight, reason, notes):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT INTO paper_trades(created_at,ticker,action,weight,reason,notes) VALUES (?,?,?,?,?,?)",
                (datetime.utcnow().isoformat(), ticker, action, float(weight), reason, notes))
    con.commit()
    con.close()

def load_trades():
    con = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM paper_trades ORDER BY id DESC", con)
    finally:
        con.close()
    return df

init_db()

# ======================================================
# REBALANCE
# ======================================================

def rebalance_table(df, targets, band):
    x = df.copy()
    x["value"] = x["shares"] * x["price"]
    total = x["value"].sum()
    x["current_weight"] = 0 if total <= 0 else x["value"]/total*100
    x["target_weight"] = x["ticker"].map(targets).fillna(0)
    x["deviation_pp"] = x["current_weight"] - x["target_weight"]
    x["target_value"] = total*x["target_weight"]/100
    x["trade_value"] = x["target_value"] - x["value"]
    x["action"] = np.where(x["deviation_pp"] > band, "SELL/TRIM",
                  np.where(x["deviation_pp"] < -band, "BUY/ADD", "HOLD"))
    return x

def send_telegram(msg):
    token = secret("TELEGRAM_BOT_TOKEN")
    chat = secret("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False, "Telegram secrets missing"
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat, "text": msg}, timeout=15)
        return r.ok, r.text
    except Exception as e:
        return False, str(e)

# ======================================================
# UI
# ======================================================

st.title("Portfolio Cockpit Alpha Pro")
st.caption("Core 87% + Satellite dinamico 13%. Regime, Alpha e Tactical Allocation Score.")

with st.sidebar:
    period = st.selectbox("Periodo dashboard", ["1y","2y","5y","10y"], index=2)
    band = st.number_input("Banda rebalance ± punti percentuali", 1.0, 20.0, 5.0, .5)
    st.metric("Indicatori/proxy potenziali", INDICATOR_COUNT)

tabs = st.tabs([
    "Allocation",
    "Scores",
    "Market",
    "FRED",
    "Relative Strength",
    "Tactical Ranking",
    "Satellite Plan",
    "Rebalance",
    "Paper Trading",
    "Alerts",
])

with tabs[0]:
    st.subheader("Alpha Pro Allocation")
    core = pd.DataFrame([{"ticker":k, "name":v[0], "target":v[1], "bucket":v[2]} for k,v in CORE.items()])
    sat = pd.DataFrame([
        {"slot":"Satellite #1", "target":5.0, "rule":"Best theme if score >75"},
        {"slot":"Satellite #2", "target":5.0, "rule":"Second theme if score >75"},
        {"slot":"Satellite #3", "target":3.0, "rule":"Third theme if score >75"},
    ])
    c1,c2,c3=st.columns(3)
    c1.metric("Core", "87%")
    c2.metric("Satellite", "13%")
    c3.metric("Total", "100%")
    st.dataframe(core, use_container_width=True)
    st.dataframe(sat, use_container_width=True)
    pie = pd.concat([
        core.rename(columns={"target":"weight"})[["ticker","weight"]],
        pd.DataFrame([{"ticker":"Satellite Dynamic","weight":13.0}])
    ])
    st.plotly_chart(px.pie(pie, names="ticker", values="weight", title="Alpha Pro allocation"), use_container_width=True)

with tabs[1]:
    st.subheader("Regime / Alpha / Defensive Scores")
    scores = composite_scores()
    cols = st.columns(8)
    for i,k in enumerate(["Liquidity","Macro","MarketRisk","Breadth","RealAssets","RegimeScore","AlphaScore","DefensivePressure"]):
        cols[i].metric(k, f"{scores[k]:.0f}/100")
    st.info("AlphaScore integra liquidità, macro, rischio mercato, breadth proxy e forza degli asset reali.")

with tabs[2]:
    rows=[]
    for name,t in MARKET.items():
        df=hist(t,period)
        if df.empty:
            rows.append({"Indicator":name,"Ticker":t,"Last":None,"1M%":None,"3M%":None,"6M%":None,"Trend":"NO DATA","Vol3M":None,"MaxDD":None})
            continue
        c=df["Close"]; lc=float(c.iloc[-1]); ma200=sma(c,200)
        rows.append({
            "Indicator":name, "Ticker":t, "Last":round(lc,4),
            "1M%":round(pc(c,21)*100,2) if len(c)>22 else None,
            "3M%":round(pc(c,63)*100,2) if len(c)>64 else None,
            "6M%":round(pc(c,126)*100,2) if len(c)>127 else None,
            "Trend":"above 200dma" if not pd.isna(ma200) and lc>ma200 else ("below 200dma" if not pd.isna(ma200) else "n/a"),
            "Vol3M":round(vol(c,63)*100,2) if not pd.isna(vol(c,63)) else None,
            "MaxDD":round(mdd(c)*100,2) if not pd.isna(mdd(c)) else None,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

with tabs[3]:
    rows=[]
    for name,sid in FRED.items():
        df=fred(sid)
        if df.empty:
            rows.append({"Indicator":name,"Series":sid,"Last":None,"Date":None,"3M chg":None,"12M chg":None})
        else:
            v=df["value"]
            rows.append({
                "Indicator":name, "Series":sid, "Last":round(float(v.iloc[-1]),4), "Date":str(df.index[-1].date()),
                "3M chg":round(float(v.iloc[-1]-v.iloc[-4]),4) if len(v)>4 else None,
                "12M chg":round(float(v.iloc[-1]-v.iloc[-13]),4) if len(v)>13 else None,
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.caption("Serve FRED_API_KEY nei Secrets per popolare questa sezione.")

with tabs[4]:
    rows=[]
    for name,(a,b) in RS_PAIRS.items():
        da,db = hist(a,"2y"), hist(b,"2y")
        if da.empty or db.empty:
            rows.append({"Pair":name,"A":a,"B":b,"3M%":None,"6M%":None,"Score":None})
            continue
        r=(da["Close"]/db["Close"]).dropna()
        rows.append({
            "Pair":name, "A":a, "B":b,
            "3M%":round(pc(r,63)*100,2) if len(r)>64 else None,
            "6M%":round(pc(r,126)*100,2) if len(r)>127 else None,
            "Score":round(bscore(pc(r,126),15),1) if len(r)>127 else None,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

with tabs[5]:
    scores = composite_scores()
    rows=[]
    for theme,tickers in TACTICAL.items():
        best=None
        for t in tickers:
            df=hist(t,period)
            if df.empty:
                continue
            sc=tactical_score(t,scores)
            c=df["Close"]
            row={
                "Theme":theme, "Ticker":t,
                "Score":None if pd.isna(sc) else round(sc,1),
                "Signal":signal(sc),
                "Rule":allocation_rule(sc) if not pd.isna(sc) else "NO DATA",
                "1M%":round(pc(c,21)*100,2) if len(c)>22 else None,
                "3M%":round(pc(c,63)*100,2) if len(c)>64 else None,
                "6M%":round(pc(c,126)*100,2) if len(c)>127 else None,
            }
            if best is None or (row["Score"] is not None and row["Score"] > best["Score"]):
                best=row
        rows.append(best or {"Theme":theme,"Ticker":"NO DATA","Score":None,"Signal":"NO DATA","Rule":"NO DATA"})
    tdf=pd.DataFrame(rows).sort_values("Score",ascending=False,na_position="last")
    st.dataframe(tdf,use_container_width=True)
    top=tdf.dropna(subset=["Score"]).head(8)
    if not top.empty:
        st.plotly_chart(px.bar(top,x="Theme",y="Score",color="Signal",title="Tactical Ranking"),use_container_width=True)

with tabs[6]:
    st.subheader("Satellite Allocation Plan")
    scores=composite_scores()
    rows=[]
    for theme,tickers in TACTICAL.items():
        best=None
        for t in tickers:
            sc=tactical_score(t,scores)
            if pd.isna(sc): continue
            if best is None or sc>best["Score"]:
                best={"Theme":theme,"Ticker":t,"Score":sc}
        if best: rows.append(best)
    df=pd.DataFrame(rows).sort_values("Score",ascending=False) if rows else pd.DataFrame()
    if df.empty:
        st.warning("No tactical data.")
    else:
        eligible=df[df["Score"]>=75].head(3).copy()
        plan=[]
        weights=[5,5,3]
        for i,(_,r) in enumerate(eligible.iterrows()):
            plan.append({"Slot":f"SAT{i+1}","Theme":r["Theme"],"Ticker":r["Ticker"],"Score":round(r["Score"],1),"TargetWeight":weights[i]})
        if len(plan)<3:
            for j in range(len(plan),3):
                plan.append({"Slot":f"SAT{j+1}","Theme":"Cash/Bond breve","Ticker":"XEON.MI","Score":None,"TargetWeight":weights[j]})
        st.dataframe(pd.DataFrame(plan),use_container_width=True)

with tabs[7]:
    template=[{"ticker":t,"shares":0.0} for t in CORE.keys()]+[{"ticker":"SAT1","shares":0.0},{"ticker":"SAT2","shares":0.0},{"ticker":"SAT3","shares":0.0}]
    pos=st.data_editor(pd.DataFrame(template),use_container_width=True,num_rows="dynamic")
    if st.button("Calcola rebalance"):
        prices={t:(1.0 if str(t).startswith("SAT") else (last(t) or 0)) for t in pos["ticker"]}
        pos["price"]=pos["ticker"].map(prices).fillna(0)
        targets={k:v[1] for k,v in CORE.items()}
        targets.update(SAT_TARGETS)
        st.dataframe(rebalance_table(pos,targets,band),use_container_width=True)

with tabs[8]:
    with st.form("paper"):
        ticker=st.text_input("Ticker")
        action=st.selectbox("Azione",["BUY","SELL","HOLD","REDUCE","OVERWEIGHT"])
        weight=st.number_input("Peso target",0.0,100.0,0.0,.5)
        reason=st.text_area("Motivo")
        notes=st.text_area("Note")
        if st.form_submit_button("Salva"):
            add_trade(ticker,action,weight,reason,notes)
            st.success("Paper trade salvato.")
    st.dataframe(load_trades(),use_container_width=True)

with tabs[9]:
    msg=st.text_area("Messaggio", "Portfolio Cockpit Alpha Pro: test alert.")
    if st.button("Invia Telegram"):
        ok,resp=send_telegram(msg)
        st.success("Inviato") if ok else st.error(resp)
