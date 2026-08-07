import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add project root and local Streamlit module path to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parent))
from database.sqlite_manager import SQLiteManager
from display import get_display_table

# Page Configuration
st.set_page_config(
    page_title="India Crop Calendar AI Portal",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
    <style>
        .main-title {
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #1e7e34, #28a745, #007bff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
            text-align: center;
        }
        .subtitle {
            font-size: 1.15rem;
            color: #495057;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 1.25rem;
            border-left: 5px solid #28a745;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            text-align: center;
        }
        .metric-val {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1e7e34;
        }
        .metric-lbl {
            font-size: 0.95rem;
            color: #6c757d;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌱 India Crop Calendar AI Portal</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Document-Grounded Agricultural Activity Schedules Verified Against Official CWWG Reports</div>', unsafe_allow_html=True)

db = SQLiteManager()
records = db.load_all_records()
calendar = db.load_all_calendar()

# ---------------------------------------------------------
# EXECUTIVE METRICS ROW
# ---------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)

with m1:
    # Calculate unique PDFs from the records
    total_pdfs = len(set(r.get("source_pdf") for r in records if r.get("source_pdf"))) if records else 0
    st.metric(label="📁 PDFs Processed", value=total_pdfs, delta="Official CWWG")

with m2:
    st.metric(label="🔬 Verified Records", value=len(records), delta=None)

with m3:
    total_crops = len(set(r.get("crop") for r in records if r.get("crop"))) if records else 0
    st.metric(label="🌾 Crops Tracked", value=total_crops)

with m4:
    total_states = len(set(r.get("state") for r in records if r.get("state"))) if records else 0
    st.metric(label="🗺️ States Covered", value=total_states)

st.divider()

# ---------------------------------------------------------
# QUICK NAVIGATION CARDS
# ---------------------------------------------------------
st.markdown("### 🚀 Quick Access Operations")

col_a, col_b, col_c = st.columns(3)

with col_a:
    with st.container():
        st.markdown("#### 📅 Crop Calendar Schedule")
        st.write("Explore state-wise synthesized activity windows, gap thresholding, multi-year timelines, and state comparisons.")
        st.page_link("pages/Crop_Calendar.py", label="Open Crop Calendar Schedule ➔", icon="📅")

with col_b:
    with st.container():
        st.markdown("#### 🔍 Evidence Explorer")
        st.write("Trace every single extracted agricultural observation back to its source PDF report sentence, page number, and chunk ID.")
        st.page_link("pages/Evidence.py", label="Open Evidence Explorer ➔", icon="🔍")

with col_c:
    with st.container():
        st.markdown("#### 📈 Analytics Dashboard")
        st.write("Analyze statistical distributions of crops, growth stages, states, and reporting frequencies.")
        st.page_link("pages/Analytics.py", label="Open Analytics Dashboard ➔", icon="📈")

st.divider()

# ---------------------------------------------------------
# RECENT VERIFIED KNOWLEDGE ACTIVITY
# ---------------------------------------------------------
st.markdown("### 📋 Recent Authenticated Agricultural Observations")
if records:
    df_rec = pd.DataFrame(records)
    display_cols = ["crop", "state", "report_date", "growth_stage", "observation_type", "confidence", "source_pdf"]
    display_cols = [c for c in display_cols if c in df_rec.columns]
    
    df_display = df_rec[display_cols].head(15).copy()
    df_display.columns = [c.replace("_", " ").title() for c in display_cols]
    
    st.dataframe(get_display_table(df_display), use_container_width=True)
else:
    st.info("No records loaded in database.")

st.divider()
st.caption("Document-Grounded Agricultural Intelligence System | Official CWWG Verification Pipeline © 2026")


