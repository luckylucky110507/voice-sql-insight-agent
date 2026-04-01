from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")
CSV_PATH = DATA_DIR / "business_metrics.csv"
DB_PATH = DATA_DIR / "voice_sql_agent.db"
TABLE_NAME = "business_metrics"


def initialize_database() -> Path:
    """Create or refresh the SQLite database from the sample CSV."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dataframe = pd.read_csv(CSV_PATH)
    dataframe["month"] = pd.to_datetime(dataframe["month"]).dt.strftime("%Y-%m-%d")

    with sqlite3.connect(DB_PATH) as connection:
        dataframe.to_sql(TABLE_NAME, connection, if_exists="replace", index=False)
        connection.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_month
            ON {TABLE_NAME} (month)
            """
        )
        connection.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_region
            ON {TABLE_NAME} (region)
            """
        )
        connection.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_product
            ON {TABLE_NAME} (product_line)
            """
        )

    return DB_PATH
