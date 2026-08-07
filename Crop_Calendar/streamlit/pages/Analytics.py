import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add project root and local Streamlit module path to sys.path
sys.path.append(str(Path(__file__).resolve().parents[2]))
sys.path.append(str(Path(__file__).resolve().parents[1]))
from database.sqlite import DatabaseManager
from extractor.normalizer import Normalizer
from display import get_display_table

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
        # Normalize and filter only biologically verified pests
        norm_pests = df["pest"].apply(Normalizer.normalize_pest_disease).dropna()
        norm_pests = norm_pests[norm_pests.str.strip() != ""]
        
        if not norm_pests.empty:
            top_pests = norm_pests.value_counts().head(10)
            st.dataframe(get_display_table(pd.DataFrame({"Report Count": top_pests})), use_container_width=True)
        else:
            st.info("No biologically verified pests reported in dataset.")

    with col_disease:
        st.write("### 🍄 Top Reported Diseases")
        # Normalize and filter only biologically verified diseases
        norm_diseases = df["disease"].apply(Normalizer.normalize_pest_disease).dropna()
        norm_diseases = norm_diseases[norm_diseases.str.strip() != ""]
        
        if not norm_diseases.empty:
            top_diseases = norm_diseases.value_counts().head(10)
            st.dataframe(get_display_table(pd.DataFrame({"Report Count": top_diseases})), use_container_width=True)
        else:
            st.info("No biologically verified diseases reported in dataset.")
