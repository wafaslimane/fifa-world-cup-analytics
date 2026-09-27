"""Central configuration: paths and data source."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
WAREHOUSE_DIR = ROOT / "data" / "warehouse"
WAREHOUSE_PATH = WAREHOUSE_DIR / "fifa.duckdb"
SQL_DIR = ROOT / "sql"
REPORTS_DIR = ROOT / "reports"

# Fjelstul World Cup Database (CC-BY-SA 4.0) - https://github.com/jfjelstul/worldcup
SOURCE_BASE_URL = "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv"

SOURCE_FILES = [
    "tournaments",
    "matches",
    "goals",
    "teams",
    "team_appearances",
    "tournament_standings",
    "host_countries",
    "players",
]

# Harmonisation of inconsistent stage labels found in the source
STAGE_MAPPING = {
    "group stage": "Phase de groupes",
    "second group stage": "2e phase de groupes",
    "final round": "Poule finale",
    "round of 16": "8es de finale",
    "quarter-final": "Quarts de finale",
    "quarter-finals": "Quarts de finale",
    "semi-final": "Demi-finales",
    "semi-finals": "Demi-finales",
    "third-place match": "Match pour la 3e place",
    "final": "Finale",
}

STAGE_ORDER = {
    "Phase de groupes": 1,
    "2e phase de groupes": 2,
    "Poule finale": 3,
    "8es de finale": 4,
    "Quarts de finale": 5,
    "Demi-finales": 6,
    "Match pour la 3e place": 7,
    "Finale": 8,
}

# Goal-timing buckets (regulation minute)
MINUTE_BINS = [0, 15, 30, 45, 60, 75, 90, 120]
MINUTE_LABELS = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "Prolongations"]
