import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from database.sqlite import DatabaseManager

st.set_page_config(page_title="Analytics - Crop Calendar AI", page_icon="📈", layout="wide")

st.title("📈 Agricultural Analytics Dashboard")
st.subheader("Statistical summaries and distribution metrics of extracted observations")

db = DatabaseManager()
evidence_list = db.load_all_evidence()

if not evidence_list:
    st.warning("No evidence records found. Run the extraction pipeline on the Dashboard first.")
else:
    df = pd.DataFrame(evidence_list)
    
    # Grid of charts
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)
    
    with row1_col1:
        st.write("### 🌾 Crop Distribution in Observations")
        crop_counts = df["crop"].value_counts()
        st.bar_chart(crop_counts)
        st.caption("Total count of extracted evidence records per crop.")

    with row1_col2:
        st.write("### 🗺️ State Distribution in Observations")
        state_counts = df["state"].value_counts()
        st.bar_chart(state_counts)
        st.caption("Total count of extracted evidence records per state.")

    with row2_col1:
        st.write("### 🔄 Growth Stage Distribution")
        stage_counts = df["growth_stage"].value_counts()
        st.bar_chart(stage_counts)
        st.caption("Distribution of crop growth stages across all reports.")

    with row2_col2:
        st.write("### 📅 Reporting Density over Weeks")
        week_counts = df["report_week"].value_counts().sort_index()
        st.line_chart(week_counts)
        st.caption("Number of observations extracted per calendar week of the year.")

    st.divider()

    col_pest, col_disease = st.columns(2)
    
    with col_pest:
        st.write("### 🐞 Top Reported Pests")
        # Filter out 'None' or empty values
        pest_df = df[~df["pest"].str.lower().isin(["none", "none reported", "below etl", ""])]
        if not pest_df.empty:
            top_pests = pest_df["pest"].value_counts().head(10)
            st.dataframe(pd.DataFrame({"Report Count": top_pests}), use_container_width=True)
        else:
            st.write("No specific pests reported yet.")

    with col_disease:
        st.write("### 🍄 Top Reported Diseases")
        disease_df = df[~df["disease"].str.lower().isin(["none", "none reported", "below etl", ""])]
        if not disease_df.empty:
            top_diseases = disease_df["disease"].value_counts().head(10)
            st.dataframe(pd.DataFrame({"Report Count": top_diseases}), use_container_width=True)
        else:
            st.write("No specific diseases reported yet.")
