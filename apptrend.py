
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(page_title="FOCUS-Trend", layout="wide")
st.title("📈 FOCUS-Trend – Trend Insights + Burn Forecast")

FOCUS_DIVISIONS = ['HCS', 'SIS', 'MIS', 'PEQ', 'NCS', 'SEM', 'EMS', 'MCS', 'BBS', 'TES', 'WPS', 'ENS']

def extract_date(filename):
    match = re.search(r"(\d{2})-(\d{2})-(\d{4})", filename)
    if match:
        return datetime.strptime(match.group(0), "%m-%d-%Y").date()
    return None

uploaded_files = st.file_uploader("📂 Upload multiple SOF Excel files", type=["xlsx"], accept_multiple_files=True)

if uploaded_files:
    dfs = []
    for f in uploaded_files:
        try:
            df = pd.read_excel(f, sheet_name="Status of Funds", skiprows=10)
            df.columns = df.columns.str.strip()
            df["Date"] = extract_date(f.name)
            df["Division"] = df["Division"].astype(str).str.strip().str.upper()
            df["Commitments"] = pd.to_numeric(df["Commitments"], errors="coerce")
            df["Available"] = pd.to_numeric(df["Available"], errors="coerce")
            df = df[df["Division"].isin(FOCUS_DIVISIONS)]
            dfs.append(df)
        except Exception as e:
            st.warning(f"Error reading {f.name}: {e}")

    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        st.success("SOF data loaded.")

        selected_divs = st.multiselect("Select Divisions", sorted(combined["Division"].unique()), default=sorted(combined["Division"].unique()))
        combined = combined[combined["Division"].isin(selected_divs)]

        latest_dates = sorted(combined["Date"].dropna().unique())
        if len(latest_dates) >= 2:
            d1, d2 = latest_dates[-2], latest_dates[-1]
            df1 = combined[combined["Date"] == d1].set_index("Division")
            df2 = combined[combined["Date"] == d2].set_index("Division")

            # Delta Table (Feature 5)
            st.subheader("📋 Division-Level Delta Table (Last 2 Days)")
            delta = pd.DataFrame(index=FOCUS_DIVISIONS)
            delta["Commitments Δ"] = df2["Commitments"] - df1["Commitments"]
            delta["Available Δ"] = df2["Available"] - df1["Available"]
            delta["Commitments % Change"] = ((df2["Commitments"] - df1["Commitments"]) / df1["Commitments"]) * 100
            delta["Available % Change"] = ((df2["Available"] - df1["Available"]) / df1["Available"]) * 100
            delta = delta.loc[delta.index.intersection(selected_divs)].round(2)
            st.dataframe(delta)

        # Burn Rate Forecast (Feature 8)
        st.subheader("🔥 Burn Rate Forecast")
        days_tracked = len(combined["Date"].unique())
        days_remaining = (datetime(datetime.now().year, 9, 30) - datetime.now()).days
        burn_rate = combined.groupby("Division")["Commitments"].sum() / days_tracked
        forecasted_commitments = burn_rate * days_remaining
        forecast_df = pd.DataFrame()
        forecast_df["Avg Daily Burn"] = burn_rate
        forecast_df["Forecasted Commitments"] = forecasted_commitments
        forecast_df = forecast_df.loc[selected_divs].round(2)
        st.dataframe(forecast_df)

        # Funding Risk Score (Feature 9)
        st.subheader("⚠️ Funding Risk Score")
        latest_df = combined[combined["Date"] == combined["Date"].max()]
        risk_df = latest_df.groupby("Division")[["Commitments", "Available"]].sum()
        risk_df["Risk Score"] = (risk_df["Commitments"] / (risk_df["Available"] + 1))
        risk_df = risk_df.loc[selected_divs].sort_values("Risk Score", ascending=False)
        st.dataframe(risk_df.style.background_gradient(cmap="Reds", subset=["Risk Score"]))

        # Trend Charts
        st.subheader("📈 Trend Charts")
        tab1, tab2 = st.tabs(["Commitments", "Available"])
        with tab1:
            data = combined.groupby(["Date", "Division"])["Commitments"].sum().reset_index()
            st.plotly_chart(px.line(data, x="Date", y="Commitments", color="Division"))
        with tab2:
            data = combined.groupby(["Date", "Division"])["Available"].sum().reset_index()
            st.plotly_chart(px.line(data, x="Date", y="Available", color="Division"))
    else:
        st.warning("No valid SOF data found.")
else:
    st.info("Upload multiple daily SOF reports to begin trend analysis.")
