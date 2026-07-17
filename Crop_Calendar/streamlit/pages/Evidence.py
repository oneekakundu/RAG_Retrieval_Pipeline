import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from database.sqlite import DatabaseManager

st.set_page_config(page_title="Evidence Explorer - Crop Calendar AI", page_icon="🔍", layout="wide")

st.title("🔍 Evidence Explorer")
st.subheader("Trace individual agricultural observations back to their source reports")

db = DatabaseManager()
evidence_list = db.load_all_evidence()

if not evidence_list:
    st.warning("No evidence records found in the database. Please run the pipeline on the Dashboard first.")
else:
    df = pd.DataFrame(evidence_list)
    
    # Extract unique filter options
    crops = sorted(list(df["crop"].dropna().unique()))
    states = sorted(list(df["state"].dropna().unique()))
    weeks = sorted(list(df["report_week"].dropna().unique()))
    diseases = sorted(list(df["disease"].dropna().unique()))
    pests = sorted(list(df["pest"].dropna().unique()))

    # Filters Section in Sidebar
    st.sidebar.header("🔍 Filter Evidence Logs")
    
    selected_crop = st.sidebar.multiselect("Select Crops", options=crops, default=[])
    selected_state = st.sidebar.multiselect("Select States", options=states, default=[])
    selected_week = st.sidebar.multiselect("Select Weeks", options=weeks, default=[])
    
    pest_disease_search = st.sidebar.text_input("Search Pest / Disease", value="")

    # Apply Filters
    filtered_df = df
    if selected_crop:
        filtered_df = filtered_df[filtered_df["crop"].isin(selected_crop)]
    if selected_state:
        filtered_df = filtered_df[filtered_df["state"].isin(selected_state)]
    if selected_week:
        filtered_df = filtered_df[filtered_df["report_week"].isin(selected_week)]
    if pest_disease_search:
        search_lower = pest_disease_search.lower()
        filtered_df = filtered_df[
            filtered_df["pest"].str.lower().str.contains(search_lower, na=False) |
            filtered_df["disease"].str.lower().str.contains(search_lower, na=False)
        ]

    # Display count
    st.write(f"Showing **{len(filtered_df)}** matching evidence logs out of **{len(df)}** total records.")

    # Results Table
    display_cols = [
        "crop", "state", "district", "report_week", "growth_stage", 
        "pest", "disease", "confidence", "source_pdf", "page_number"
    ]
    
    # Capitalize headers for display
    display_df = filtered_df[display_cols].copy()
    display_df.columns = [col.replace("_", " ").title() for col in display_cols]
    
    st.dataframe(display_df, use_container_width=True)

    # Detailed Explorer View
    st.markdown("### 📋 Detail Inspector")
    st.write("Select a record index from the list to view its complete original text context and provenance.")
    
    selected_idx = st.selectbox(
        "Select record ID to inspect", 
        options=filtered_df.index, 
        format_func=lambda idx: f"ID {filtered_df.loc[idx, 'id']} | {filtered_df.loc[idx, 'crop']} in {filtered_df.loc[idx, 'state']} (Week {filtered_df.loc[idx, 'report_week']})"
    )

    if selected_idx is not None:
        rec = filtered_df.loc[selected_idx]
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Crop:** `{rec['crop']}`")
            st.markdown(f"**State / Region:** `{rec['state']}`")
            st.markdown(f"**District:** `{rec['district']}`")
            st.markdown(f"**Growth Stage:** `{rec['growth_stage']}`")
            st.markdown(f"**Pest:** `{rec['pest']}`")
            st.markdown(f"**Disease:** `{rec['disease']}`")
        with col2:
            st.markdown(f"**Source Document:** `{rec['source_pdf']}`")
            st.markdown(f"**Page Number:** `{rec['page_number']}`")
            st.markdown(f"**Report Date:** `{rec['report_date']}` (Week `{rec['report_week']}`)")
            st.markdown(f"**Model Confidence:** `{rec['confidence']}`")
            st.markdown(f"**Weather Condition:** `{rec['weather_condition']}`")

        st.markdown("**Original Sentence Context:**")
        st.info(rec["original_text"])
        
        st.markdown("**Advisory Details:**")
        st.warning(rec["advisory"])
