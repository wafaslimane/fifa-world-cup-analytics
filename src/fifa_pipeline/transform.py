"""Transform: clean raw CSVs and model them as a star schema.

Output tables
-------------
dim_tournament, dim_team, dim_player            (dimensions)
fact_match, fact_team_match, fact_goal,
fact_standing, fact_host                        (facts)
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .config import MINUTE_BINS, MINUTE_LABELS, RAW_DIR, STAGE_MAPPING, STAGE_ORDER

log = logging.getLogger(__name__)

MISSING_TOKENS = ["not available", "not applicable", "", "NA"]


# --------------------------------------------------------------------------- helpers
def read_raw(name: str) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / f"{name}.csv", na_values=MISSING_TOKENS, keep_default_na=True)
    # strip whitespace on every text column
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()
    before = len(df)
    df = df.drop(columns=["key_id"], errors="ignore").drop_duplicates()
    if len(df) != before:
        log.warning("%s: %d doublons supprimés", name, before - len(df))
    return df


def competition_from_name(name: pd.Series) -> pd.Series:
    return np.where(name.str.contains("Women", case=False), "Femmes", "Hommes")


def harmonise_stage(stage: pd.Series) -> pd.Series:
    mapped = stage.str.lower().map(STAGE_MAPPING)
    unknown = stage[mapped.isna()].unique()
    if len(unknown):
        raise ValueError(f"Phases inconnues non mappées : {unknown}")
    return mapped


def to_bool(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        df[c] = df[c].astype(int).astype(bool)
    return df


# --------------------------------------------------------------------------- dimensions
def build_dim_tournament(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["competition"] = competition_from_name(df["tournament_name"])
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    df["duration_days"] = (df["end_date"] - df["start_date"]).dt.days + 1
    df["decade"] = (df["year"] // 10 * 10).astype(int)
    df = to_bool(df, ["host_won"])
    return df[[
        "tournament_id", "tournament_name", "competition", "year", "decade",
        "start_date", "end_date", "duration_days", "host_country", "winner",
        "host_won", "count_teams",
    ]].sort_values("year").reset_index(drop=True)


def build_dim_team(raw: pd.DataFrame) -> pd.DataFrame:
    return raw[[
        "team_id", "team_name", "team_code", "mens_team", "womens_team",
        "region_name", "confederation_code", "confederation_name",
    ]].pipe(to_bool, ["mens_team", "womens_team"]).reset_index(drop=True)


def build_dim_player(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["given_name"] = df["given_name"].fillna("")
    df["player_name"] = (df["given_name"] + " " + df["family_name"]).str.strip()
    df["birth_date"] = pd.to_datetime(df["birth_date"], errors="coerce")
    # A player can be flagged on several positions: keep the first in field order
    positions = {"goal_keeper": "Gardien", "defender": "Défenseur", "midfielder": "Milieu", "forward": "Attaquant"}
    df["position"] = "Inconnu"
    for col, label in reversed(positions.items()):
        df.loc[df[col] == 1, "position"] = label
    df = to_bool(df, ["female"])
    return df[[
        "player_id", "player_name", "family_name", "given_name", "birth_date",
        "female", "position", "count_tournaments",
    ]].reset_index(drop=True)


# --------------------------------------------------------------------------- facts
def build_fact_match(raw: pd.DataFrame, dim_tournament: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["stage"] = harmonise_stage(df["stage_name"])
    df["stage_order"] = df["stage"].map(STAGE_ORDER)
    df["match_date"] = pd.to_datetime(df["match_date"])
    df["total_goals"] = df["home_team_score"] + df["away_team_score"]
    df = to_bool(df, ["group_stage", "knockout_stage", "replayed", "replay", "extra_time", "penalty_shootout"])

    # Winner including penalty shoot-outs (None = draw)
    home_wins = (df["home_team_win"] == 1) | (
        df["penalty_shootout"] & (df["home_team_score_penalties"] > df["away_team_score_penalties"])
    )
    away_wins = (df["away_team_win"] == 1) | (
        df["penalty_shootout"] & (df["away_team_score_penalties"] > df["home_team_score_penalties"])
    )
    df["winner_team_id"] = np.select([home_wins, away_wins], [df["home_team_id"], df["away_team_id"]], default=None)
    df["result"] = df["result"].map({"home team win": "Victoire domicile", "away team win": "Victoire extérieur", "draw": "Nul"})

    df = df.merge(dim_tournament[["tournament_id", "competition", "year"]], on="tournament_id", how="left")
    return df[[
        "match_id", "tournament_id", "competition", "year", "stage", "stage_order", "group_name",
        "group_stage", "knockout_stage", "replay", "match_date", "stadium_name", "city_name", "country_name",
        "home_team_id", "away_team_id", "home_team_score", "away_team_score", "total_goals",
        "extra_time", "penalty_shootout", "home_team_score_penalties", "away_team_score_penalties",
        "result", "winner_team_id",
    ]].sort_values(["match_date", "match_id"]).reset_index(drop=True)


def build_fact_team_match(raw: pd.DataFrame, fact_match: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["stage"] = harmonise_stage(df["stage_name"])
    df = to_bool(df, ["win", "lose", "draw", "extra_time", "penalty_shootout"])
    # Modern scoring (3/1/0) applied to every edition so eras are comparable
    df["points"] = np.where(df["win"], 3, np.where(df["draw"], 1, 0))
    df["won_incl_shootout"] = df["team_id"].eq(
        df["match_id"].map(fact_match.set_index("match_id")["winner_team_id"])
    )
    df["result"] = df["result"].map({"win": "Victoire", "lose": "Défaite", "draw": "Nul"})
    df = df.merge(fact_match[["match_id", "competition", "year", "stage_order"]], on="match_id", how="left")
    return df[[
        "match_id", "tournament_id", "competition", "year", "stage", "stage_order", "team_id", "opponent_id",
        "goals_for", "goals_against", "goal_differential", "result", "win", "draw", "lose",
        "points", "penalty_shootout", "won_incl_shootout",
    ]].reset_index(drop=True)


def build_fact_goal(raw: pd.DataFrame, fact_match: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df = to_bool(df, ["own_goal", "penalty"])
    df["stage"] = harmonise_stage(df["stage_name"])
    df["is_extra_time"] = df["match_period"].str.startswith("extra time")
    df["is_stoppage_time"] = df["minute_stoppage"] > 0
    df["minute_bucket"] = pd.cut(
        df["minute_regulation"], bins=MINUTE_BINS, labels=MINUTE_LABELS, right=True, include_lowest=True
    ).astype(str)
    df.loc[df["is_extra_time"], "minute_bucket"] = "Prolongations"
    df = df.merge(fact_match[["match_id", "competition", "year"]], on="match_id", how="left")
    return df[[
        "goal_id", "match_id", "tournament_id", "competition", "year", "stage",
        "team_id", "player_id", "player_team_id", "minute_regulation", "minute_stoppage",
        "match_period", "minute_bucket", "is_extra_time", "is_stoppage_time", "own_goal", "penalty",
    ]].reset_index(drop=True)


def build_fact_standing(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[["tournament_id", "position", "team_id"]].copy()
    df["position_label"] = df["position"].map({1: "Vainqueur", 2: "Finaliste", 3: "3e", 4: "4e"})
    return df


def build_fact_host(raw: pd.DataFrame) -> pd.DataFrame:
    return raw[["tournament_id", "team_id", "performance"]].copy()


# --------------------------------------------------------------------------- orchestration
def build_model() -> dict[str, pd.DataFrame]:
    raw = {n: read_raw(n) for n in [
        "tournaments", "teams", "players", "matches", "team_appearances",
        "goals", "tournament_standings", "host_countries",
    ]}
    dim_tournament = build_dim_tournament(raw["tournaments"])
    fact_match = build_fact_match(raw["matches"], dim_tournament)
    return {
        "dim_tournament": dim_tournament,
        "dim_team": build_dim_team(raw["teams"]),
        "dim_player": build_dim_player(raw["players"]),
        "fact_match": fact_match,
        "fact_team_match": build_fact_team_match(raw["team_appearances"], fact_match),
        "fact_goal": build_fact_goal(raw["goals"], fact_match),
        "fact_standing": build_fact_standing(raw["tournament_standings"]),
        "fact_host": build_fact_host(raw["host_countries"]),
    }
