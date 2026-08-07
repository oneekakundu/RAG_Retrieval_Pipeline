import pandas as pd


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


def get_pdf_link(pdf_name: str) -> str:
    """Return an HTML hyperlink string for the given PDF filename.

    Clicking the link will open or download the stored PDF directly in browser via base64 data URI.
    """
    if not pdf_name or str(pdf_name).strip().lower() in ["n/a", "none", "nan", "null", "unknown.pdf", ""]:
        return "N/A"

    import base64
    from pathlib import Path
    from urllib.parse import quote

    clean_name = str(pdf_name).strip()
    filename = Path(clean_name).name

    try:
        try:
            import config
        except ImportError:
            from Crop_Calendar import config

        pdf_path = config.RAW_PDFS_DIR / filename
        if not pdf_path.exists():
            matches = list(config.RAW_PDFS_DIR.glob(f"*{filename}*"))
            if matches:
                pdf_path = matches[0]

        if pdf_path.exists():
            b64_pdf = base64.b64encode(pdf_path.read_bytes()).decode("utf-8")
            return f'<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_path.name}" target="_blank" style="text-decoration: underline; color: #1E88E5; font-weight: bold;">📄 {filename}</a>'
    except Exception:
        pass

    encoded_filename = quote(filename)
    return f'<a href="/app/static/{encoded_filename}" download="{filename}" target="_blank" style="text-decoration: underline; color: #1E88E5; font-weight: bold;">📄 {filename}</a>'


def format_pdf_dataframe_column(df: pd.DataFrame, col_name: str = None) -> tuple:
    """Format a DataFrame's PDF filename or Evidence chunk column(s) into clickable links for st.dataframe.

    Returns a tuple of (modified_dataframe, column_config_dict).
    """
    if df is None or df.empty:
        return df, {}

    import streamlit as st
    import re
    from pathlib import Path
    from urllib.parse import quote

    df_copy = df.copy()
    col_config = {}

    target_cols = [col_name] if col_name else [
        "PDF Name", "Pdf Name", "pdf_name", "Source Pdf", "Source PDF", "source_pdf", 
        "Filename", "Source Document"
    ]

    # Pre-cache available raw PDFs for quick lookup
    raw_pdfs = set()
    try:
        try:
            import config
        except ImportError:
            from Crop_Calendar import config
        if hasattr(config, "RAW_PDFS_DIR") and config.RAW_PDFS_DIR.exists():
            raw_pdfs = set(p.name for p in config.RAW_PDFS_DIR.glob("*.pdf"))
    except Exception:
        pass

    def extract_pdf_filename(val):
        if not val or str(val).strip().lower() in ["n/a", "none", "nan", "null", "unknown.pdf", ""]:
            return None
        s = str(val).strip()
        if raw_pdfs and s in raw_pdfs:
            return s
        name_path = Path(s).name
        if raw_pdfs and name_path in raw_pdfs:
            return name_path
        # Strip chunk ID suffix if present e.g. _p1_c2
        base = re.sub(r"_p\d+(_c\d+)?$", "", s)
        if not base.endswith(".pdf"):
            base += ".pdf"
        base_name = Path(base).name
        if raw_pdfs and base_name in raw_pdfs:
            return base_name
        if raw_pdfs:
            for p in raw_pdfs:
                if base_name.replace(".pdf", "") in p:
                    return p
        return base_name if base_name.endswith(".pdf") else None

    for col in target_cols:
        if col in df_copy.columns:
            def to_pdf_url(val):
                pdf_file = extract_pdf_filename(val)
                if not pdf_file:
                    return None
                return f"/app/static/{quote(pdf_file)}"

            df_copy[col] = df_copy[col].apply(to_pdf_url)
            col_config[col] = st.column_config.LinkColumn(
                label=col,
                display_text=r"/app/static/(.*)",
                help="Click to open or download the source PDF report"
            )

    return df_copy, col_config




