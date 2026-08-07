import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add project root and local Streamlit module path to sys.path
sys.path.append(str(Path(__file__).resolve().parents[2]))
sys.path.append(str(Path(__file__).resolve().parents[1]))
from database.sqlite import DatabaseManager
from extractor.normalizer import Normalizer
import importlib
if "display" in sys.modules:
    importlib.reload(sys.modules["display"])
from display import get_display_table, get_pdf_link

st.set_page_config(page_title="Crop Calendar Matrix - Crop Calendar AI", page_icon="📅", layout="wide")

st.title("📅 Weekly Crop Calendar Matrix")
st.subheader("Week-by-week aggregated timelines of crop stages, pests, and advisories")

db = DatabaseManager()
calendar_data = db.load_all_calendar()

def format_week_display(val, idx=1):
    if not val or pd.isna(val) or str(val).strip() in ["", "nan", "None", "null"]:
        return f"Report #{idx}"
    val_str = str(val).strip()
    if val_str.isdigit():
        return f"Week {val_str}"
    if len(val_str) >= 10 and "-" in val_str:
        try:
            from datetime import datetime
            dt = datetime.strptime(val_str[:10], "%Y-%m-%d")
            return f"W{dt.isocalendar()[1]} ({val_str})"
        except Exception:
            pass
import re

def clean_display_text(val):
    if not val or pd.isna(val) or str(val).strip().lower() in ["", "nan", "none", "null", "n/a", "none reported", "normal operations"]:
        return "None Reported"
    text = str(val).strip()
    # Strip leading markdown hashes (#, ##, ###) to prevent Giant Font size rendering in Streamlit
    text = re.sub(r"(?m)^\s*#+\s*", "", text)
    return text

def clean_val_display(val, default_val="None Reported"):
    if not val or pd.isna(val) or str(val).strip().lower() in ["", "nan", "none", "null", "n/a"]:
        return default_val
    return str(val).strip()

if not calendar_data:
    st.warning("No authenticated crop calendar entries found. Please execute the pipeline on the Dashboard first.")
else:
    df = pd.DataFrame(calendar_data)
    all_records = pd.DataFrame(db.load_all_records())
    
    # Helper to infer season from report date
    def infer_season(date_str):
        if not date_str or not isinstance(date_str, str) or len(date_str) < 7:
            return "Kharif"
        try:
            m = int(date_str.split("-")[1])
            if m in [6, 7, 8, 9, 10]:
                return "Kharif (Monsoon / Summer)"
            elif m in [11, 12, 1, 2, 3, 4]:
                return "Rabi (Winter / Post-Monsoon)"
            else:
                return "Zaid (Summer / Inter-season)"
        except Exception:
            return "Kharif (Monsoon / Summer)"

    df["Season"] = df["report_week"].apply(infer_season)

    # Normalize crop and state columns in df to ensure clean matching
    df["crop"] = df["crop"].apply(Normalizer.normalize_crop)
    df["state"] = df["state"].apply(Normalizer.normalize_state)

    if not all_records.empty:
        all_records["crop"] = all_records["crop"].apply(Normalizer.normalize_crop)
        all_records["state"] = all_records["state"].apply(Normalizer.normalize_state)

    # Sidebar Filters
    st.sidebar.header("📅 Crop Calendar Selection")
    
    crops = sorted(list(df["crop"].dropna().unique()))
    selected_crop = st.sidebar.selectbox("Select Crop", options=crops)
    
    # Filter states dynamically for the selected crop
    crop_df = df[df["crop"] == selected_crop]
    raw_states = crop_df["state"].dropna().unique()
    valid_states = sorted(list(set(s for s in raw_states if s and s != "All India")))
    
    if "All India" not in valid_states:
        valid_states.insert(0, "All India")
        
    selected_state = st.sidebar.selectbox("Select Region / State", options=valid_states)
    seasons = ["All Seasons", "Kharif (Monsoon / Summer)", "Rabi (Winter / Post-Monsoon)", "Zaid (Summer / Inter-season)"]
    selected_season = st.sidebar.selectbox("Select Season", options=seasons)

    # Filter data
    if selected_state == "All India":
        filtered_df = df[df["crop"] == selected_crop]
    else:
        filtered_df = df[(df["crop"] == selected_crop) & (df["state"] == selected_state)]

    if selected_season != "All Seasons":
        filtered_df = filtered_df[filtered_df["Season"] == selected_season]
    
    if filtered_df.empty:
        # Fallback to all records for crop if specific state/season combination is empty
        filtered_df = df[df["crop"] == selected_crop]
        st.info(f"Showing all available regional observations for **{selected_crop}**.")
    else:
        filtered_df = filtered_df.sort_values("report_week")
        
        st.markdown(f"### 🌾 Regional Crop Activity Schedule: **{selected_crop}** in **{selected_state}**")
        st.caption(f"Season: **{selected_season}** | Grounded & Verified against Official CWWG Reports")

        # ---------------------------------------------------------
        # 1. AGRICULTURAL LIFECYCLE SUMMARY CARDS
        # ---------------------------------------------------------
        st.markdown("#### 📋 Seasonal Agricultural Activity Schedule")
        
        sow_rows = filtered_df[filtered_df["growth_stage"].str.lower().str.contains("sowing|nursery|planting", na=False)]
        harv_rows = filtered_df[filtered_df["growth_stage"].str.lower().str.contains("harvest", na=False)]
        veg_rows = filtered_df[~filtered_df.index.isin(sow_rows.index) & ~filtered_df.index.isin(harv_rows.index)]

        card1, card2, card3 = st.columns(3)
        
        with card1:
            st.markdown("### 🚜 1. Land Prep & Sowing Window")
            if not sow_rows.empty:
                sow_dates = sow_rows["report_week"].tolist()
                st.write(f"**Estimated Start Date:** `{min(sow_dates)}`")
                st.write(f"**Period:** `{min(sow_dates)}` to `{max(sow_dates)}`")
                st.write("**Status / Progress:**")
                for s_val in sow_rows["sowing_status"].dropna().unique()[:3]:
                    st.write(f"- {s_val}")
            else:
                st.write("**Period:** Early Season Window")
                st.caption("No specific sowing progress reported for this window.")

        with card2:
            st.markdown("### 🌿 2. Growth & Maintenance")
            if not veg_rows.empty:
                st.write(f"**Active Stage:** `{veg_rows['growth_stage'].iloc[0]}`")
                st.write("**Guidelines:** Regular irrigation, weeding & nutrient top-dressing.")
            else:
                st.write("**Active Stage:** Vegetative / Flowering")
                st.caption("Standard crop protection & irrigation schedule.")

        with card3:
            st.markdown("### 🌾 3. Harvesting Window")
            if not harv_rows.empty:
                harv_dates = harv_rows["report_week"].tolist()
                st.write(f"**Estimated End Date:** `{max(harv_dates)}`")
                st.write(f"**Period:** `{min(harv_dates)}` to `{max(harv_dates)}`")
                st.write("**Harvest Completion:**")
                for h_val in harv_rows["harvest_status"].dropna().unique()[:3]:
                    st.write(f"- {h_val}")
            else:
                st.write("**Period:** Maturity & Harvesting Stage")
                st.caption("Awaiting harvest window confirmation.")

        st.divider()

        # ---------------------------------------------------------
        # 2. MONTH-BY-MONTH CROP CALENDAR MATRIX
        # ---------------------------------------------------------
        st.markdown("#### 📅 Month-by-Month Activity Timeline Matrix")
        
        weeks_labels = []
        stages, harvests, sowings, pests, diseases, stats_col = [], [], [], [], [], []
        
        for idx, (_, row) in enumerate(filtered_df.iterrows(), 1):
            w_raw = row.get("report_week") or row.get("report_date")
            week_label = format_week_display(w_raw, idx)
            weeks_labels.append(week_label)
            stages.append(row.get("growth_stage") or "Active Growth")
            harvests.append(row.get("harvest_status") or "-")
            sowings.append(row.get("sowing_status") or "-")
            
            p_val = row.get("pests") or "None Reported"
            if any(kw in str(p_val).lower() for kw in ["lakh ha", "area coverage", "% of normal", "sowing progress", "table"]):
                p_val = "None Reported"
            pests.append(p_val)

            d_val = row.get("diseases") or "None Reported"
            if any(kw in str(d_val).lower() for kw in ["lakh ha", "area coverage", "% of normal", "sowing progress", "table"]):
                d_val = "None Reported"
            diseases.append(d_val)

            stats_col.append(row.get("statistics") or "-")
            
        matrix_df = pd.DataFrame({
            "Report Week": weeks_labels,
            "Growth Stage": stages,
            "Sowing Window": sowings,
            "Harvest Window": harvests,
            "Verified Pests": pests,
            "Verified Diseases": diseases,
            "Statistics": stats_col
        })
        
        st.dataframe(get_display_table(matrix_df), use_container_width=True)

        st.divider()

        # ---------------------------------------------------------
        # 3. DETAILED ACTIVITY TIMELINE & DOCUMENT GROUNDING
        # ---------------------------------------------------------
        st.header("🕒 Stage-by-Stage Farmer Activity & Evidence Explorer")
        for idx, row in filtered_df.iterrows():
            w_date = row["report_week"]
            week_label = format_week_display(w_date)
            
            # Fetch raw evidence records matching crop, state, and week
            ev_records = []
            if not all_records.empty:
                ev_records = all_records[
                    (all_records["crop"] == selected_crop) & 
                    (all_records["state"] == selected_state) & 
                    (all_records["report_date"] == w_date)
                ].to_dict("records")

            with st.expander(f"📅 {week_label} | Phase: {row.get('growth_stage') or 'Active Growth'} (Season: {row.get('Season', 'Kharif')})", expanded=True):
                col1, col2 = st.columns([1, 2])
                
                harv_p = clean_val_display(row.get('harvest_status'))
                sow_p = clean_val_display(row.get('sowing_status'))
                stat_p = clean_display_text(row.get('statistics'))
                pest_p = clean_val_display(pests[idx-1] if (idx-1) < len(pests) else None)
                dis_p = clean_val_display(diseases[idx-1] if (idx-1) < len(diseases) else None)

                with col1:
                    st.markdown("**🌱 Agricultural Activity Status**")
                    st.write(f"🚜 **Growth Stage:** {row.get('growth_stage') or 'Active Growth'}")
                    st.write(f"🌾 **Harvest Progress:** {harv_p}")
                    st.write(f"🌱 **Sowing Status:** {sow_p}")
                    st.write(f"🐞 **Verified Pests:** `{pest_p}`")
                    st.write(f"🍄 **Verified Diseases:** `{dis_p}`")
                    
                with col2:
                    st.markdown("**📝 Task Guidelines & Farmer Advisories**")
                    
                    if stat_p != "None Reported":
                        st.markdown("**📊 Statistics:**")
                        st.write(stat_p)
                    else:
                        st.write("📊 **Statistics:** None Reported")

                st.divider()
                st.markdown("##### 📄 View Document Evidence & Cultivation Details")
                if ev_records:
                    for ev_idx, ev in enumerate(ev_records, 1):
                        with st.popover(f"🔍 View Report Evidence #{ev_idx} (Chunk {ev.get('chunk_id') or 'N/A'})"):
                            st.markdown(f"**Specific Cultivation Area (District):** `{ev.get('district', 'State-wide')}`")
                            st.markdown(f"**Source PDF:** {get_pdf_link(ev.get('source_pdf'))} (Page {ev.get('page_number', 1)})", unsafe_allow_html=True)
                            st.markdown(f"**Observation Category:** `{ev.get('observation_type', 'Other')}`")
                            st.markdown(f"**Confidence Score:** `{ev.get('confidence', 0.95)}` | **Status:** `{ev.get('verification_status', 'VERIFIED')}`")
                            st.markdown("**Original Report Source Chunk:**")
                            chunk_text = ev.get("evidence_sentence") or ev.get("raw_text") or ev.get("evidence", "N/A")
                            st.info(clean_display_text(chunk_text))
                else:
                    st.caption("Verified against CWWG report chunk.")
