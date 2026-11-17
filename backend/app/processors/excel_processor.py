"""Excel (.xlsx/.xls) and CSV parsing into plain text for the LLM."""
import pandas as pd

EXCEL_EXTS = {".xlsx", ".xls"}
CSV_EXTS = {".csv"}


def _df_to_text(df: pd.DataFrame, sheet_name: str = "") -> str:
    header = f"--- Sheet: {sheet_name} ---\n" if sheet_name else ""
    # Cap rows to keep prompts manageable
    df = df.head(500)
    return header + df.to_csv(index=False)


def extract_excel_text(path: str) -> str:
    sheets = pd.read_excel(path, sheet_name=None)
    return "\n\n".join(_df_to_text(df, name) for name, df in sheets.items())


def extract_csv_text(path: str) -> str:
    df = pd.read_csv(path)
    return _df_to_text(df)
