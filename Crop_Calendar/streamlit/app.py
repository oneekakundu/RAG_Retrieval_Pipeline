import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from database.sqlite import DatabaseManager

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
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, #1e7e34, #28a745, #007bff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        .subtitle {
            font-size: 1.25rem;
            color: #6c757d;
            text-align: center;
            margin-bottom: 2.5rem;
        }
        .card {
            background-color: #f8f9fa;
            border-radius: 12px;
            padding: 1.5rem;
            border-left: 5px solid #28a745;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            margin-bottom: 1.5rem;
        }
        .dark-mode .card {
            background-color: #212529;
            border-left: 5px solid #1e7e34;
        }
        .concept-btn {
            display: inline-block;
            background-color: #007bff;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            text-decoration: none;
            margin-right: 0.5rem;
            font-weight: 500;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌱 India Crop Calendar AI Portal</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-Driven Agricultural Information Extraction from Crop Weather Watch Group (CWWG) Reports</div>', unsafe_allow_html=True)

# Main layout split
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    ### 📖 Project Overview
    A crop calendar is a tool that provides timely information about the sowing, growing, and harvesting periods of crops in specific regions, along with typical pest and disease threats encountered at various growth stages. 
    
    Historically, crop calendars for India were either outdated or unavailable across all crops and states in a unified digital format. 
    
    This portal presents a **Custom Information Extraction Pipeline** that automatically:
    1. Downloads weekly CWWG PDF reports from the Ministry of Agriculture.
    2. Parses them semantically using **Docling** to preserve layout, headings, and tables.
    3. Segments observations into semantic chunks based on crop, state, or section changes.
    4. Identifies key agricultural variables using **GLiNER zero-shot NER** (Crop, State, District, Growth Stage, Pests, Diseases, and Advisories).
    5. Aggregates this information into an interactive SQLite database and a consolidated Crop Calendar.
    """)

    st.markdown("### 🔗 Conceptual Resources")
    st.markdown("""
    You can explore the following links to learn more about the crop calendar concept:
    *   [IRRI Rice Crop Calendar (Knowledge Bank)](http://www.knowledgebank.irri.org/step-by-step-production/pre-planting/crop-calendar)
    *   [Rice in Odisha Crop Calendar](https://rkb-odisha.in/rice-in-odisha/step-by-step-production/pre-planting/crop-calendar/)
    *   [FAO Crop Calendar App](https://cropcalendar.apps.fao.org/#/home?id=BD&crops=)
    """)

with col2:
    st.markdown("### 📊 Database Statistics")
    db = DatabaseManager()
    stats = db.get_stats()
    
    st.markdown(f"""
    <div class="card">
        <h4>📦 Extraction Summary</h4>
        <hr>
        <p>📁 <b>PDFs Processed:</b> {stats['total_pdfs']}</p>
        <p>🔬 <b>Evidence Records:</b> {stats['total_evidence']}</p>
        <p>📅 <b>Calendar Entries:</b> {stats['total_calendar']}</p>
        <p>🌾 <b>Crops Extracted:</b> {stats['total_crops']}</p>
        <p>🗺️ <b>States Tracked:</b> {stats['total_states']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 Use the sidebar to navigate between pages to explore the Evidence logs, view the consolidated Crop Calendar, or analyze agricultural trends.")

st.divider()
st.caption("Developed with Antigravity AI Code Assistant using Docling & GLiNER. © 2026")
