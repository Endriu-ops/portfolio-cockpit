import streamlit as st, pandas as pd, numpy as np, plotly.express as px
from config import PORTFOLIO, CORE_PORTFOLIO, TACTICAL_PORTFOLIO, MARKET_TICKERS, TACTICAL_WATCHLIST, FRED_SERIES, REBALANCE_BAND_POINTS
from utils import yf_history, yf_last, fred_series, pct_change, sma, macro_score, tactical_score, signal, rebalance_table, send_telegram

st.set_page_config(page_title="Portfolio Cockpit Pro", layout="wide")
st.title("Portfolio Cockpit Pro")
st.caption("Core/Satellite + macro dashboard + segnali tattici + ribilanciamento ±5%. Strumento educativo, non consulenza finanziaria.")

with st.sidebar:
    period = st.selectbox("Periodo storico", ["1y","2y","5y","10y"], index=2)
    band = st.number_input("Banda rebalance ± punti percentuali", 1.0, 20.0, float(REBALANCE_BAND_POINTS), .5)

tabs=st.tabs(["Home","Portfolio","Macro","Tactical","FRED","Paper Trading","Alert"])

with tabs[0]:
    target=pd.DataFrame([{"ticker":k, **v} for k,v in PORTFOLIO.items()])
    c1,c2,c3=st.columns(3)
    c1.metric("Target totale", f"{target['target'].sum():.1f}%")
    c2.metric("Core", f"{sum(v['target'] for v in CORE_PORTFOLIO.values()):.0f}%")
    c3.metric("Satellite", f"{sum(v['target'] for v in TACTICAL_PORTFOLIO.values()):.0f}%")
    st.plotly_chart(px.pie(target, values="target", names="ticker", title="Target allocation"), use_container_width=True)
    st.dataframe(target, use_container_width=True)

with tabs[1]:
    st.subheader("Ribilanciamento ±5")
    positions=st.data_editor(pd.DataFrame([{"ticker":t,"shares":0.0} for t in PORTFOLIO]), use_container_width=True, num_rows="fixed")
    if st.button("Calcola rebalance"):
        prices={t:yf_last(t) for t in positions["ticker"]}
        positions["price"]=positions["ticker"].map(prices).fillna(0)
        targets={k:v["target"] for k,v in PORTFOLIO.items()}
        rb=rebalance_table(positions, targets, band)
        st.dataframe(rb, use_container_width=True)
        if rb["value"].sum()>0:
            st.plotly_chart(px.pie(rb, values="current_weight", names="ticker", title="Pesi attuali"), use_container_width=True)
            act=rb[rb["action"]!="HOLD"]
            if act.empty: st.success("Nessuna azione: dentro banda.")
            else: st.warning("Azioni suggerite"); st.dataframe(act, use_container_width=True)

with tabs[2]:
    st.subheader("Macro dashboard")
    rows=[]
    for name,ticker in MARKET_TICKERS.items():
        df=yf_history(ticker, period)
        if df.empty:
            rows.append({"Indicatore":name,"Ticker":ticker,"Last":None,"1M %":None,"3M %":None,"6M %":None,"Trend":"NO DATA"})
            continue
        c=df["Close"]; last=float(c.iloc[-1]); ma200=sma(c,200)
        trend="above 200dma" if not np.isnan(ma200) and last>ma200 else ("below 200dma" if not np.isnan(ma200) else "n/a")
        rows.append({"Indicatore":name,"Ticker":ticker,"Last":round(last,4),
            "1M %":round(pct_change(c,21)*100,2) if len(c)>22 else None,
            "3M %":round(pct_change(c,63)*100,2) if len(c)>64 else None,
            "6M %":round(pct_change(c,126)*100,2) if len(c)>127 else None,
            "Trend":trend})
    mdf=pd.DataFrame(rows)
    v=mdf.loc[mdf["Indicatore"]=="VIX","Last"]
    sp=mdf.loc[mdf["Indicatore"]=="S&P 500","Trend"]
    risk=macro_score(None if v.empty or pd.isna(v.iloc[0]) else float(v.iloc[0]), True if sp.empty else sp.iloc[0]=="above 200dma")
    c1,c2=st.columns(2); c1.metric("Macro Risk Score", f"{risk:.0f}/100"); c2.metric("Regime", "Risk-on" if risk>=60 else ("Neutral" if risk>=45 else "Risk-off"))
    st.dataframe(mdf, use_container_width=True)

with tabs[3]:
    st.subheader("Segnali tattici")
    vix=yf_last("^VIX")
    sp=yf_history("^GSPC", period)
    sp_above=True
    if not sp.empty and len(sp)>200: sp_above=sp["Close"].iloc[-1]>sma(sp["Close"],200)
    macro=macro_score(vix, sp_above)
    rows=[]
    for theme,tickers in TACTICAL_WATCHLIST.items():
        best=None
        for t in tickers:
            df=yf_history(t, period)
            if df.empty or len(df)<130: continue
            c=df["Close"]; sc=tactical_score(c, macro)
            row={"Tema":theme,"Ticker":t,"Score":None if pd.isna(sc) else round(sc,1),"Segnale":signal(sc),
                 "1M %":round(pct_change(c,21)*100,2) if len(c)>22 else None,
                 "3M %":round(pct_change(c,63)*100,2) if len(c)>64 else None,
                 "6M %":round(pct_change(c,126)*100,2) if len(c)>127 else None}
            if best is None or (row["Score"] is not None and row["Score"]>best["Score"]): best=row
        rows.append(best or {"Tema":theme,"Ticker":"NO DATA","Score":None,"Segnale":"NO DATA"})
    tdf=pd.DataFrame(rows).sort_values("Score", ascending=False, na_position="last")
    st.dataframe(tdf, use_container_width=True)
    top=tdf.dropna(subset=["Score"]).head(8)
    if not top.empty: st.plotly_chart(px.bar(top,x="Tema",y="Score",color="Segnale"), use_container_width=True)
    st.info("Regola: satellite ruota solo se Score >75. Se nessun tema supera 60, satellite in cash/bond breve.")

with tabs[4]:
    st.subheader("FRED macro")
    rows=[]
    for name,sid in FRED_SERIES.items():
        df=fred_series(sid)
        rows.append({"Indicatore":name,"Serie":sid,"Ultimo":None if df.empty else round(float(df["value"].iloc[-1]),4),
                     "Data":None if df.empty else str(df.index[-1].date())})
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.caption("Se vuoto, inserisci FRED_API_KEY nei Secrets di Streamlit Cloud.")

with tabs[5]:
    st.subheader("Paper trading log")
    log=st.data_editor(pd.DataFrame(columns=["Data","Segnale","Ticker","Azione","Peso target","Motivo","Esito"]), num_rows="dynamic", use_container_width=True)
    st.download_button("Scarica CSV", log.to_csv(index=False).encode("utf-8"), "paper_trading_log.csv", "text/csv")

with tabs[6]:
    st.subheader("Alert Telegram")
    msg=st.text_area("Messaggio", "Portfolio Cockpit: test alert operativo.")
    if st.button("Invia alert"):
        ok, resp=send_telegram(msg)
        st.success("Inviato") if ok else st.error(resp)
