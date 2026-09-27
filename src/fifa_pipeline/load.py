"""Load: write modelled tables to Parquet + a DuckDB warehouse, then build SQL views."""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from .config import PROCESSED_DIR, SQL_DIR, WAREHOUSE_PATH

log = logging.getLogger(__name__)


def write_parquet(tables: dict[str, pd.DataFrame]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(PROCESSED_DIR / f"{name}.parquet", index=False)


def load_warehouse(tables: dict[str, pd.DataFrame], quality: pd.DataFrame | None = None,
                   db_path: Path = WAREHOUSE_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        for name, df in tables.items():
            con.register("tmp_df", df)
            con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM tmp_df")
            con.unregister("tmp_df")
            log.info("Table %-18s %6d lignes", name, len(df))
        if quality is not None:
            con.register("tmp_q", quality)
            con.execute("CREATE OR REPLACE TABLE data_quality_checks AS SELECT *, now() AS run_at FROM tmp_q")
            con.unregister("tmp_q")
        for sql_file in sorted(SQL_DIR.glob("*.sql")):
            con.execute(sql_file.read_text(encoding="utf-8"))
            log.info("Vue créée  %s", sql_file.stem)
    finally:
        con.close()
