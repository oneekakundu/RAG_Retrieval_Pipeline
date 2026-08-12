import re
from pathlib import Path
from urllib.parse import quote, unquote
import pandas as pd
import streamlit as st

# GitHub Raw Base URL for deployed Streamlit Cloud compatibility
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/oneekakundu/Webscraping-/main/Crop_Calendar/streamlit/static"


def get_display_table(df: pd.DataFrame, index_label: str = "No.") -> pd.DataFrame:
    """Return a copy of df for Streamlit display with a 1-based visual row number index.

    This is a display-only transformation. The original DataFrame, its index,
    and underlying data remain unchanged.
    """
    if df is None:
        return df

    display_df = df.copy()

    if isinstance(display_df.index, pd.RangeIndex) and display_df.index.start == 0 and display_df.index.step == 1:
        display_df.index = pd.RangeIndex(start=1, stop=len(display_df) + 1, step=1)
    else:
        original_index_name = display_df.index.name or "Index"
        if original_index_name in display_df.columns:
            original_index_name = f"{original_index_name}_orig"

        display_df.insert(0, original_index_name, display_df.index)
        display_df.index = pd.RangeIndex(start=1, stop=len(display_df) + 1, step=1)

    display_df.index.name = index_label
    return display_df


def _extract_pdf_filename(val: str) -> str:
    """Extract clean PDF filename from raw value, stripping chunk suffixes if present."""
    if not val or str(val).strip().lower() in ["n/a", "none", "nan", "null", "unknown.pdf", ""]:
        return None
    s = str(val).strip()
    filename = Path(s).name
    # Strip chunk suffix if present e.g. _p1_c2
    base_name = re.sub(r"_p\d+(_c\d+)?$", "", filename)
    if not base_name.endswith(".pdf"):
        base_name += ".pdf"
    return Path(base_name).name


def get_pdf_link(pdf_name: str) -> str:
    """Return an HTML hyperlink string for the given PDF filename.

    Clicking the link opens or downloads the stored PDF directly from GitHub Raw CDN.
    """
    filename = _extract_pdf_filename(pdf_name)
    if not filename:
        return "N/A"

    encoded_filename = quote(filename)
    url = f"{GITHUB_RAW_BASE}/{encoded_filename}"
    return f'<a href="{url}" download="{filename}" target="_blank" style="text-decoration: underline; color: #1E88E5; font-weight: bold;">📄 {filename}</a>'


def format_pdf_dataframe_column(df: pd.DataFrame, col_name: str = None) -> tuple:
    """Format a DataFrame's PDF filename or Evidence chunk column(s) into clickable links for st.dataframe.

    Returns a tuple of (modified_dataframe, column_config_dict).
    """
    if df is None or df.empty:
        return df, {}

    df_copy = df.copy()
    col_config = {}

    target_cols = [col_name] if col_name else [
        "PDF Name", "Pdf Name", "pdf_name", "Source Pdf", "Source PDF", "source_pdf", 
        "Filename", "Source Document"
    ]

    for col in target_cols:
        if col in df_copy.columns:
            def to_pdf_url(val):
                filename = _extract_pdf_filename(val)
                if not filename:
                    return None
                return f"{GITHUB_RAW_BASE}/{quote(filename)}"

            df_copy[col] = df_copy[col].apply(to_pdf_url)
            col_config[col] = st.column_config.LinkColumn(
                label=col,
                display_text=r".*/([^/]+)$",
                help="Click to open or download the source PDF report"
            )

    return df_copy, col_config







