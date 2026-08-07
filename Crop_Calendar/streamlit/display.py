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
