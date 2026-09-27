import pandas as pd
import pytest

from src.fifa_pipeline.config import STAGE_ORDER
from src.fifa_pipeline.transform import harmonise_stage


def test_stage_labels_are_harmonised():
    s = pd.Series(["quarter-final", "quarter-finals", "Semi-Final", "final"])
    assert harmonise_stage(s).tolist() == ["Quarts de finale", "Quarts de finale", "Demi-finales", "Finale"]


def test_unknown_stage_raises():
    with pytest.raises(ValueError):
        harmonise_stage(pd.Series(["play-in"]))


def test_all_stages_have_an_order(model):
    assert model["fact_match"]["stage"].isin(STAGE_ORDER).all()


def test_competition_split(model):
    t = model["dim_tournament"]
    assert set(t["competition"]) == {"Hommes", "Femmes"}
    assert (t.loc[t["competition"] == "Hommes", "year"] % 4 == 2).sum() >= 20


def test_points_are_3_1_0(model):
    ftm = model["fact_team_match"]
    assert set(ftm["points"]) <= {0, 1, 3}
    assert (ftm.loc[ftm["win"], "points"] == 3).all()


def test_shootout_winner_is_set(model):
    m = model["fact_match"]
    so = m[m["penalty_shootout"]]
    assert len(so) > 0
    assert so["winner_team_id"].notna().all()


def test_missing_birth_dates_are_nat_not_strings(model):
    bd = model["dim_player"]["birth_date"]
    assert pd.api.types.is_datetime64_any_dtype(bd)


def test_known_facts(model):
    t = model["dim_tournament"].set_index("year")
    assert t.loc[1998, "winner"] == "France"
    assert t.loc[2022, "winner"] == "Argentina"
    goals = model["fact_goal"]
    assert len(goals[goals["year"] == 2022]) == 172


def test_extra_time_goals_bucketed(model):
    g = model["fact_goal"]
    assert (g.loc[g["is_extra_time"], "minute_bucket"] == "Prolongations").all()
