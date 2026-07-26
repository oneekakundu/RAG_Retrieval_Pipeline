import streamlit as st
import sys
import re
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from database.sqlite import DatabaseManager
from extractor.normalizer import Normalizer

def clean_display_text(val):
    if not val or pd.isna(val) or str(val).strip().lower() in ["", "nan", "none", "null", "n/a", "none reported", "normal operations"]:
        return "None Reported"
    text = str(val).strip()
    text = re.sub(r"(?m)^\s*#+\s*", "", text)
    text = re.sub(r"\s*\|\s*", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

st.set_page_config(page_title="Evidence Explorer - Crop Calendar AI", page_icon="🔍", layout="wide")

st.title("🔍 Evidence Explorer")
st.subheader("Trace individual agricultural observations back to their source reports")

db = DatabaseManager()
# Use load_all_records instead of load_all_evidence to get all columns (district, events, chunks)
evidence_list = db.load_all_records()

if not evidence_list:
    st.warning("No evidence records found in the database. Please run the pipeline on the Dashboard first.")
else:
    df = pd.DataFrame(evidence_list)
    
    # Extract unique filter options
    crops = sorted(list(df["crop"].dropna().unique()))
    states = sorted(list(df["state"].dropna().unique()))
    
    # report_week might not exist in crop_records, but report_date does
    if "report_week" in df.columns:
        weeks = sorted(list(df["report_week"].dropna().unique()))
    else:
        weeks = sorted(list(df["report_date"].dropna().unique()))
        df["report_week"] = df["report_date"]

    diseases = sorted(list(df["disease"].dropna().unique()))
    pests = sorted(list(df["pest"].dropna().unique()))

    # Filters Section in Sidebar
    st.sidebar.header("🔍 Filter & Search")
    
    # Comprehensive search functionality
    global_search = st.sidebar.text_input("Global Search", value="", placeholder="Search crop, state, pest, disease, event...")
    
    selected_crop = st.sidebar.multiselect("Select Crops", options=crops, default=[])
    selected_state = st.sidebar.multiselect("Select States", options=states, default=[])
    selected_week = st.sidebar.multiselect("Select Dates/Weeks", options=weeks, default=[])
    
    # Apply Filters
    filtered_df = df
    if selected_crop:
        filtered_df = filtered_df[filtered_df["crop"].isin(selected_crop)]
    if selected_state:
        filtered_df = filtered_df[filtered_df["state"].isin(selected_state)]
    if selected_week:
        filtered_df = filtered_df[filtered_df["report_week"].isin(selected_week)]
    if global_search:
        search_lower = global_search.lower()
        # Search across relevant columns
        search_cols = ["crop", "state", "district", "report_week", "growth_stage", "pest", "disease", "evidence_sentence"]
        mask = pd.Series(False, index=filtered_df.index)
        for col in search_cols:
            if col in filtered_df.columns:
                mask = mask | filtered_df[col].astype(str).str.lower().str.contains(search_lower, na=False)
        filtered_df = filtered_df[mask]

    # Display count
    st.write(f"Showing **{len(filtered_df)}** matching evidence logs out of **{len(df)}** total records.")

    # Results Table
    # Ensure district and event information are visible
    display_cols = []
    preferred_cols = [
        "crop", "state", "district", "report_week", "growth_stage", 
        "pest", "disease", "confidence", "source_pdf"
    ]
    for col in preferred_cols:
        if col in filtered_df.columns:
            display_cols.append(col)
    
    # Clean up column values
    display_df = filtered_df[display_cols].copy()
    if "pest" in display_df.columns:
        display_df["pest"] = display_df["pest"].apply(lambda v: "None" if (pd.isna(v) or not v or "|" in str(v) or len(str(v)) > 60) else v)
    if "disease" in display_df.columns:
        display_df["disease"] = display_df["disease"].apply(lambda v: "None" if (pd.isna(v) or not v or "|" in str(v) or len(str(v)) > 60) else v)
    
    # Rename columns for clarity (Event Info / Cultivation Area)
    rename_mapping = {
        "district": "Specific Cultivation Area"
    }
    display_df = display_df.rename(columns=rename_mapping)
    display_df.columns = [col.replace("_", " ").title() for col in display_df.columns]
    
    st.dataframe(display_df, use_container_width=True)

    # Detailed Explorer View (View Source Chunks)
    st.markdown("### 📋 Detail & Source Chunk Inspector")
    st.write("Select a record index from the list to view its complete original text chunk, exact cultivation area, and event information.")
    
    selected_idx = st.selectbox(
        "Select record ID to inspect", 
        options=filtered_df.index, 
        format_func=lambda idx: f"ID {filtered_df.loc[idx, 'id']} | {filtered_df.loc[idx, 'crop']} in {filtered_df.loc[idx, 'state']} (Date {filtered_df.loc[idx, 'report_date']})"
    )

    if selected_idx is not None:
        rec = filtered_df.loc[selected_idx]
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Crop:** `{rec.get('crop', 'N/A')}`")
            st.markdown(f"**State / Region:** `{rec.get('state', 'N/A')}`")
            st.markdown(f"**Specific Cultivation Area (District):** `{rec.get('district', 'N/A')}`")
            st.markdown(f"**Growth Stage:** `{rec.get('growth_stage', 'N/A')}`")
            st.markdown(f"**Pest:** `{rec.get('pest', 'N/A')}`")
            st.markdown(f"**Disease:** `{rec.get('disease', 'N/A')}`")
        with col2:
            st.markdown(f"**Source Document:** `{rec.get('source_pdf', 'N/A')}` (Page `{rec.get('page_number', 'N/A')}`)")
            st.markdown(f"**Report Date:** `{rec.get('report_date', 'N/A')}`")
            st.markdown(f"**Model Confidence:** `{rec.get('confidence', 'N/A')}`")

        st.markdown("**Original Text Chunk (Source Evidence):**")
        chunk_text = rec.get("evidence_sentence") or rec.get("evidence") or rec.get("raw_text") or rec.get("original_text", "N/A")
        st.info(clean_display_text(chunk_text))