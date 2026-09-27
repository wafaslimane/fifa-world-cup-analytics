"""Extract: download the source CSV files and write a manifest (rows + checksum)."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

import requests

from .config import RAW_DIR, SOURCE_BASE_URL, SOURCE_FILES

log = logging.getLogger(__name__)


def download_sources(force: bool = False) -> dict:
    """Download every source file into data/raw. Skips existing files unless force=True."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"source": SOURCE_BASE_URL, "extracted_at": datetime.now(timezone.utc).isoformat(), "files": {}}

    for name in SOURCE_FILES:
        path = RAW_DIR / f"{name}.csv"
        if force or not path.exists():
            url = f"{SOURCE_BASE_URL}/{name}.csv"
            log.info("Downloading %s", url)
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            path.write_bytes(resp.content)
        content = path.read_bytes()
        manifest["files"][name] = {
            "rows": content.count(b"\n") - 1,
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    (RAW_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    m = download_sources(force=True)
    for f, meta in m["files"].items():
        print(f"{f:<22} {meta['rows']:>6} lignes")
