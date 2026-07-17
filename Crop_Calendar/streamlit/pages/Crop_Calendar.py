import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from database.sqlite import DatabaseManager

st.set_page_config(page_title="Crop Calendar Matrix - Crop Calendar AI", page_icon="📅", layout="wide")

st.title("📅 Weekly Crop Calendar Matrix")
st.subheader("Week-by-week aggregated timelines of crop stages, pests, and advisories")

db = DatabaseManager()
calendar_data = db.load_all_calendar()

if not calendar_data:
    st.warning("No crop calendar entries found. Please execute the pipeline on the Dashboard first.")
else:
    df = pd.DataFrame(calendar_data)
    
    # Sidebar Filters
    st.sidebar.header("📅 Calendar Selection")
    
    crops = sorted(list(df["crop"].unique()))
    states = sorted(list(df["state"].unique()))
    
    selected_crop = st.sidebar.selectbox("Select Crop", options=crops)
    selected_state = st.sidebar.selectbox("Select State", options=states)

    # Filter data
    filtered_df = df[(df["crop"] == selected_crop) & (df["state"] == selected_state)]
    
    if filtered_df.empty:
        st.info(f"No calendar entries found for {selected_crop} in {selected_state}. Verify if any evidence was extracted for this combination.")
    else:
        # Sort by week
        filtered_df = filtered_df.sort_values("report_week")
        
        st.markdown(f"### 🌾 Calendar for **{selected_crop}** in **{selected_state}**")
        st.write("Aggregated weekly status of growth stages and health observations:")

        # Create structured matrix
        matrix_data = []
        weeks_labels = []
        
        stages = []
        pests = []
        diseases = []
        advisories = []
        
        for idx, row in filtered_df.iterrows():
            week_num = int(row["report_week"])
            weeks_labels.append(f"Week {week_num}")
            stages.append(row["growth_stage"])
            pests.append(row["pests"])
            diseases.append(row["diseases"])
            advisories.append(row["advisories"])
            
        matrix_df = pd.DataFrame({
            "Growth Stage": stages,
            "Pests": pests,
            "Diseases": diseases,
            "Advisory Summary": advisories
        }, index=weeks_labels).T
        
        st.dataframe(matrix_df, use_container_width=True)

        st.divider()

        # Detailed week-by-week timeline view
        st.header("🕒 Timeline View")
        for idx, row in filtered_df.iterrows():
            week_num = int(row["report_week"])
            with st.expander(f"📅 Week {week_num} - {row['growth_stage']} (Based on {row['evidence_count']} reports)", expanded=True):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown("**🛡️ Plant Protection Status**")
                    st.write(f"🐞 **Pests:** {row['pests']}")
                    st.write(f"🍄 **Diseases:** {row['diseases']}")
                    st.write(f"🎯 **Model Confidence:** `{row['confidence']}`")
                with col2:
                    st.markdown("**📝 Advisories & Sowing Guidance**")
                    adv_list = row["advisories"].split("; ")
                    for adv in adv_list:
                        if adv.strip():
                            st.write(f"- {adv}")
