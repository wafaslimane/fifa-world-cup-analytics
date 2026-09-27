"""Pipeline entry point:  python -m src.fifa_pipeline.run"""
from __future__ import annotations

import logging
import sys
import time

from .config import RAW_DIR, REPORTS_DIR
from .extract import download_sources
from .load import load_warehouse, write_parquet
from .quality import run_checks, to_frame, to_markdown
from .transform import build_model

log = logging.getLogger("pipeline")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")
    t0 = time.perf_counter()

    log.info("1/4 Extraction")
    if not (RAW_DIR / "matches.csv").exists():
        download_sources()
    else:
        download_sources(force=False)  # refresh manifest only

    log.info("2/4 Transformation (nettoyage + modèle en étoile)")
    tables = build_model()

    log.info("3/4 Contrôles qualité")
    quality = to_frame(run_checks(tables))
    REPORTS_DIR.mkdir(exist_ok=True)
    (REPORTS_DIR / "data_quality.md").write_text(to_markdown(quality), encoding="utf-8")
    blocking = quality[(~quality["passed"]) & (quality["severity"] == "bloquant")]
    log.info("%d/%d contrôles OK", quality["passed"].sum(), len(quality))
    if not blocking.empty:
        log.error("Contrôles bloquants en échec :\n%s", blocking[["table", "check", "failed_rows"]].to_string())
        return 1

    log.info("4/4 Chargement (Parquet + DuckDB + vues SQL)")
    write_parquet(tables)
    load_warehouse(tables, quality)

    log.info("Pipeline terminé en %.1fs", time.perf_counter() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
