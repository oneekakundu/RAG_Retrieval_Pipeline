import streamlit as st
import sys
import pandas as pd
from pathlib import Path
import json

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))
import importlib
if "search_engine" in sys.modules:
    importlib.reload(sys.modules["search_engine"])
from search_engine import SearchEngine
import config

st.set_page_config(page_title="Crop Explorer - Knowledge Repository", page_icon="🌾", layout="wide")

st.title("🌾 Crop Knowledge Explorer")
st.subheader("Permanent Evidence Repository & Analytics")

engine = SearchEngine()
crop_index = engine.get_crop_index()

if not crop_index:
    st.warning("Crop Knowledge Repository is empty. Please run the processing pipeline first.")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("🔍 Search Engine")

selected_crop = st.sidebar.selectbox("Select Crop", options=sorted(crop_index.keys()))

st.sidebar.markdown("### Advanced Filters")
selected_state = st.sidebar.text_input("State (Optional)", placeholder="e.g. Maharashtra")
keyword = st.sidebar.text_input("Keyword", placeholder="e.g. Flood, Sowing")
selected_stage = st.sidebar.text_input("Growth Stage", placeholder="e.g. Vegetative")
selected_pest = st.sidebar.text_input("Pest", placeholder="e.g. Bollworm")
selected_disease = st.sidebar.text_input("Disease", placeholder="e.g. Rust")

# Search Trigger
search_clicked = st.sidebar.button("Search Observations")

# --- Overview Section ---
st.markdown("---")
st.header(f"📊 {selected_crop} Repository Overview")

crop_meta = crop_index.get(selected_crop, {})
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Extracted Chunks", crop_meta.get("total_chunks", 0))
col2.metric("Verified Observations", crop_meta.get("total_observations", 0))
col3.metric("States Monitored", crop_meta.get("states", 0))
col4.metric("First Report", crop_meta.get("first_report", "N/A"))

st.caption(f"Last updated: {crop_meta.get('last_updated', 'N/A')}")
st.markdown("---")

# Load derived CSVs for the selected crop
crop_dir = config.CROP_KNOWLEDGE_DIR / selected_crop

@st.cache_data
def load_csv(path):
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()

df_obs = load_csv(crop_dir / "observations" / "observations.csv")
df_time = load_csv(crop_dir / "timeline" / "timeline.csv")
df_stat = load_csv(crop_dir / "statistics" / "statistics.csv")

tab1, tab2, tab3, tab4 = st.tabs(["📋 Observations Search", "📅 Timeline", "📈 Statistics", "🔎 Evidence Explorer"])

with tab1:
    st.subheader("Search Results")
    if search_clicked:
        results = engine.search_observations(
            crop=selected_crop,
            state=selected_state if selected_state else None,
            keyword=keyword if keyword else None,
            growth_stage=selected_stage if selected_stage else None,
            pest=selected_pest if selected_pest else None,
            disease=selected_disease if selected_disease else None
        )
        if results:
            st.success(f"Found {len(results)} matching verified observations.")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("No observations matched your search criteria.")
    else:
        st.write("Displaying all observations from CSV.")
        st.dataframe(df_obs)

    if not df_obs.empty:
        csv_data = df_obs.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Observations CSV",
            data=csv_data,
            file_name=f"{selected_crop}_observations.csv",
            mime="text/csv"
        )

with tab2:
    st.subheader("Chronological Activity Timeline")
    st.dataframe(df_time)
    if not df_time.empty:
        csv_data = df_time.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Timeline CSV",
            data=csv_data,
            file_name=f"{selected_crop}_timeline.csv",
            mime="text/csv"
        )

with tab3:
    st.subheader("Quantitative Statistics")
    st.dataframe(df_stat)
    if not df_stat.empty:
        csv_data = df_stat.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Statistics CSV",
            data=csv_data,
            file_name=f"{selected_crop}_statistics.csv",
            mime="text/csv"
        )

with tab4:
    st.subheader("Original Evidence Viewer")
    st.write("Browse and verify the exact original text chunk for any observation. These chunks are permanent and unmodified.")
    
    if not df_obs.empty:
        # Select an observation to view evidence
        chunk_ids = df_obs["Chunk ID"].dropna().unique()
        selected_chunk_id = st.selectbox("Select Chunk ID to View Original Evidence", options=chunk_ids)
        
        if selected_chunk_id:
            chunk_data = engine.get_chunk(selected_crop, selected_chunk_id)
            if chunk_data:
                st.markdown("### Provenance Metadata")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**PDF Name:** `{chunk_data.get('pdf_name')}`")
                    st.write(f"**Page Number:** `{chunk_data.get('page')}`")
                    st.write(f"**Report Date:** `{chunk_data.get('report_date')}`")
                with col_b:
                    st.write(f"**Chunk Type:** `{chunk_data.get('chunk_type')}`")
                    st.write(f"**Section:** `{chunk_data.get('section')}`")
                    st.write(f"**Processed At:** `{chunk_data.get('processed_timestamp')}`")
                
                st.markdown("### Original Permanent Chunk Text")
                st.info(chunk_data.get("chunk_text", "No text available"))
            else:
                st.error("Original chunk file not found in the repository.")
    else:
        st.info("No observations available to explore.")
