import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# --- CAN SLIM criteria
criteria = {
    "min_eps_growth_qtr": 0.25,
    "min_eps_growth_annual": 0.25,
    "min_inst_ownership": 0.7,
    "near_high_pct": 0.85,
}

# --- Get stock score
@st.cache_data(show_spinner=False)
def get_canslim_score(ticker, market_up=True):
    stock = yf.Ticker(ticker)
    info = stock.info
    hist = stock.history(period="1y")

    current_price = info.get("currentPrice")
    earnings_growth_qtr = info.get("earningsQuarterlyGrowth")
    earnings_growth_annual = info.get("earningsGrowth")
    inst_own = info.get("heldPercentInstitutions")
    company_name = info.get("longName") or info.get("shortName")
    sector = info.get("sector", "Unknown")
    industry = info.get("industry", "Unknown")
    high_52w = hist["Close"].max() if not hist.empty else 1
    near_52wh = current_price >= criteria["near_high_pct"] * high_52w if current_price else False

    if earnings_growth_qtr is None or earnings_growth_annual is None:
        return {
            "Ticker": ticker,
            "Company": company_name,
            "Sector": sector,
            "Industry": industry,
            "Price": current_price,
            "EPS Growth (Q)": np.nan,
            "EPS Growth (Yr)": np.nan,
            "Institutional %": inst_own,
            "52W High %": f"{(current_price / high_52w * 100):.1f}%" if current_price else "N/A",
            "CAN SLIM Score": np.nan,
            "Pass CAN SLIM": "⚠️ Missing EPS Data"
        }

    score = 0
    passed = {}

    passed["C"] = earnings_growth_qtr >= criteria["min_eps_growth_qtr"]
    score += int(passed["C"])

    passed["A"] = earnings_growth_annual >= criteria["min_eps_growth_annual"]
    score += int(passed["A"])

    passed["N"] = near_52wh
    score += int(passed["N"])

    passed["S"] = True  # Placeholder
    score += int(passed["S"])

    passed["L"] = passed["C"] and passed["A"]
    score += int(passed["L"])

    passed["I"] = inst_own is not None and inst_own >= criteria["min_inst_ownership"]
    score += int(passed["I"])

    passed["M"] = market_up
    score += int(passed["M"])

    meets_all = all(passed.values())

    return {
        "Ticker": ticker,
        "Company": company_name,
        "Sector": sector,
        "Industry": industry,
        "Price": current_price,
        "EPS Growth (Q)": earnings_growth_qtr,
        "EPS Growth (Yr)": earnings_growth_annual,
        "Institutional %": inst_own,
        "52W High %": f"{(current_price / high_52w * 100):.1f}%" if current_price else "N/A",
        "CAN SLIM Score": f"{score}/7",
        "Pass CAN SLIM": "✅" if meets_all else "❌"
    }

# --- UI Setup
st.set_page_config(page_title="CAN SLIM Screener", layout="wide")
st.title("📈 CAN SLIM Screener Dashboard")

# --- Stock List
default_tickers = ["NVDA", "AAPL", "MSFT", "GOOGL", "META", "LLY", "TSLA", "PEP", "MKC", "LYFT", "JNJ", "ADM", "PLTR"]
tickers = st.multiselect("Choose tickers to analyze:", default_tickers, default=default_tickers)

# --- Fetch Data
with st.spinner("Fetching CAN SLIM scores..."):
    results = [get_canslim_score(t) for t in tickers]
    df = pd.DataFrame(results)

# --- Convert to numeric types
for col in ["EPS Growth (Q)", "EPS Growth (Yr)"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# --- Sector Filter
sectors = ["All"] + sorted(df["Sector"].dropna().unique().tolist())
selected_sector = st.selectbox("Filter by Sector:", sectors)
if selected_sector != "All":
    df = df[df["Sector"] == selected_sector]

# --- Style Function
def highlight_score(val):
    if isinstance(val, str) and "/7" in val:
        score = int(val.split("/")[0])
        if score >= 6:
            return "background-color: lightgreen"
        elif score >= 4:
            return "background-color: khaki"
        else:
            return "background-color: lightcoral"
    return ""

# --- Display Data
st.dataframe(
    df.style.map(highlight_score, subset=["CAN SLIM Score"]),
    use_container_width=True
)

# --- Timestamp
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- CSV Export
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Download CSV", csv, "canslim_results.csv", "text/csv")

# --- Refresh Button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()
