import pandas as pd

from src.fifa_pipeline.quality import check_fk, check_unique, run_checks, to_frame


def test_no_blocking_check_fails(model):
    q = to_frame(run_checks(model))
    blocking = q[(q["severity"] == "bloquant") & (~q["passed"])]
    assert blocking.empty, blocking.to_string()


def test_unique_check_detects_duplicates():
    df = pd.DataFrame({"id": [1, 1, 2]})
    assert check_unique(df, "t", ["id"]).failed_rows == 1


def test_fk_check_detects_orphans():
    child = pd.DataFrame({"team_id": ["A", "Z"]})
    parent = pd.DataFrame({"team_id": ["A", "B"]})
    assert check_fk(child, "c", "team_id", parent, "team_id", "p").failed_rows == 1
