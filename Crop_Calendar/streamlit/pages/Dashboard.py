import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import subprocess

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))
import config
from database.sqlite import DatabaseManager

st.set_page_config(page_title="Dashboard - Crop Calendar AI", page_icon="📊", layout="wide")

st.title("📊 System Dashboard & Control Center")
st.subheader("Real-time monitoring of extraction pipeline and assets")

db = DatabaseManager()
stats = db.get_stats()

# Visual KPIs
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric(label="📥 PDFs Downloaded", value=len(list(config.RAW_PDFS_DIR.glob("*.pdf"))))
with kpi2:
    st.metric(label="⚙️ JSON Parsed", value=len(list(config.DOCLING_JSON_DIR.glob("*.json"))))
with kpi3:
    st.metric(label="🔍 Evidence Extracted", value=stats["total_evidence"])
with kpi4:
    st.metric(label="📅 Crop Calendar Entries", value=stats["total_calendar"])

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.header("📂 Downloaded CWWG Report PDFs")
    pdf_files = list(config.RAW_PDFS_DIR.glob("*.pdf"))
    if pdf_files:
        pdf_details = []
        for pdf in pdf_files:
            # Check if JSON exists
            json_exists = (config.DOCLING_JSON_DIR / f"{pdf.stem}.json").exists()
            size_mb = pdf.stat().st_size / (1024 * 1024)
            pdf_details.append({
                "Filename": pdf.name,
                "Size (MB)": round(size_mb, 2),
                "Docling Parsed": "✅ Yes" if json_exists else "❌ No"
            })
        st.dataframe(pd.DataFrame(pdf_details), use_container_width=True)
    else:
        st.warning("No PDF reports downloaded yet.")

with col2:
    st.header("⚡ Pipeline Execution Panel")
    st.write("You can trigger the CWWG extraction pipeline below. It will download the weekly reports, parse them with Docling, chunk them semantically, run entity extraction via GLiNER, and rebuild the database.")
    
    # Run pipeline button
    if st.button("🚀 Run Extraction Pipeline", type="primary"):
        with st.spinner("Executing pipeline modules... This will take a few minutes (downloading, parsing with Docling, and extracting NER labels)."):
            # Trigger run_pipeline.py as subprocess
            pipeline_script = config.BASE_DIR / "run_pipeline.py"
            try:
                result = subprocess.run(
                    [sys.executable, str(pipeline_script)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                st.success("Pipeline executed successfully!")
                st.text_area("Pipeline Log Output:", value=result.stdout, height=300)
                st.rerun()
            except subprocess.CalledProcessError as e:
                st.error(f"Pipeline failed with exit code {e.returncode}")
                st.text_area("Pipeline Error Output:", value=e.stderr, height=300)

st.divider()
st.header("🗄️ Database Tables Status")
tab1, tab2 = st.tabs(["Evidence Log", "Crop Calendar Logs"])

with tab1:
    evidence_data = db.load_all_evidence()
    if evidence_data:
        st.dataframe(pd.DataFrame(evidence_data).head(50), use_container_width=True)
        st.caption(f"Showing first 50 rows of {len(evidence_data)} total evidence rows.")
    else:
        st.info("Evidence table is currently empty.")

with tab2:
    calendar_data = db.load_all_calendar()
    if calendar_data:
        st.dataframe(pd.DataFrame(calendar_data).head(50), use_container_width=True)
        st.caption(f"Showing first 50 rows of {len(calendar_data)} total calendar rows.")
    else:
        st.info("Crop Calendar table is currently empty.")
