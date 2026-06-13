CORE_PORTFOLIO = {
    "SWDA.MI": {"name": "MSCI World", "target": 28.0, "bucket": "Core Equity"},
    "WSML.MI": {"name": "World Small Cap", "target": 7.0, "bucket": "Small Cap"},
    "SGLD.MI": {"name": "Physical Gold", "target": 13.0, "bucket": "Gold"},
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
REBALANCE_BAND_POINTS = 5.0
MARKET_TICKERS = {
    "S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "Russell 2000": "^RUT", "VIX": "^VIX",
    "Dollar Index": "DX-Y.NYB", "Gold": "GC=F", "Silver": "SI=F", "Copper": "HG=F",
    "WTI Oil": "CL=F", "Brent Oil": "BZ=F", "Natural Gas": "NG=F",
    "US 10Y Yield": "^TNX", "Bitcoin": "BTC-USD", "EUR/USD": "EURUSD=X",
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
    "Small Value": ["IJS", "VBR"],
    "Commodities": ["CMOD.MI", "DBC"],
}
FRED_SERIES = {
    "Fed Funds Rate": "FEDFUNDS", "US CPI": "CPIAUCSL", "US M2 Money Supply": "M2SL",
    "US 10Y Treasury": "DGS10", "US 2Y Treasury": "DGS2", "10Y-2Y Spread": "T10Y2Y",
    "High Yield Spread": "BAMLH0A0HYM2", "Investment Grade Spread": "BAMLC0A0CM",
    "CFNAI": "CFNAI", "Unemployment Rate": "UNRATE", "Industrial Production": "INDPRO",
}
