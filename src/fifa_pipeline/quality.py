"""Data-quality checks run on the modelled tables before loading.

Each check returns a CheckResult. Severity 'bloquant' stops the pipeline,
'alerte' is reported but does not block.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass
class CheckResult:
    check: str
    table: str
    category: str      # Unicité, Complétude, Intégrité, Cohérence, Validité
    severity: str      # bloquant | alerte
    failed_rows: int
    total_rows: int

    @property
    def passed(self) -> bool:
        return self.failed_rows == 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["passed"] = self.passed
        return d


def _r(check, table, category, severity, failed, total) -> CheckResult:
    return CheckResult(check, table, category, severity, int(failed), int(total))


def check_unique(df, table, cols) -> CheckResult:
    return _r(f"Clé unique ({', '.join(cols)})", table, "Unicité", "bloquant", df.duplicated(cols).sum(), len(df))


def check_not_null(df, table, cols, severity="bloquant") -> CheckResult:
    return _r(f"Non null ({', '.join(cols)})", table, "Complétude", severity, df[cols].isna().any(axis=1).sum(), len(df))


def check_fk(df, table, col, ref, ref_col, ref_name) -> CheckResult:
    missing = ~df[col].dropna().isin(ref[ref_col])
    return _r(f"{col} → {ref_name}.{ref_col}", table, "Intégrité", "bloquant", missing.sum(), len(df))


def run_checks(m: dict[str, pd.DataFrame]) -> list[CheckResult]:
    t, tm, pl = m["dim_tournament"], m["dim_team"], m["dim_player"]
    fm, ftm, fg, fs = m["fact_match"], m["fact_team_match"], m["fact_goal"], m["fact_standing"]
    res: list[CheckResult] = []

    # Unicité
    res += [
        check_unique(t, "dim_tournament", ["tournament_id"]),
        check_unique(tm, "dim_team", ["team_id"]),
        check_unique(pl, "dim_player", ["player_id"]),
        check_unique(fm, "fact_match", ["match_id"]),
        check_unique(ftm, "fact_team_match", ["match_id", "team_id"]),
        check_unique(fg, "fact_goal", ["goal_id"]),
        check_unique(fs, "fact_standing", ["tournament_id", "position"]),
    ]

    # Complétude
    res += [
        check_not_null(fm, "fact_match", ["tournament_id", "match_date", "home_team_id", "away_team_id",
                                          "home_team_score", "away_team_score", "stage"]),
        check_not_null(fg, "fact_goal", ["match_id", "team_id", "minute_regulation"]),
        check_not_null(pl, "dim_player", ["birth_date"], severity="alerte"),
    ]

    # Intégrité référentielle
    res += [
        check_fk(fm, "fact_match", "tournament_id", t, "tournament_id", "dim_tournament"),
        check_fk(fm, "fact_match", "home_team_id", tm, "team_id", "dim_team"),
        check_fk(fm, "fact_match", "away_team_id", tm, "team_id", "dim_team"),
        check_fk(ftm, "fact_team_match", "match_id", fm, "match_id", "fact_match"),
        check_fk(fg, "fact_goal", "match_id", fm, "match_id", "fact_match"),
        check_fk(fg, "fact_goal", "player_id", pl, "player_id", "dim_player"),
        check_fk(fs, "fact_standing", "team_id", tm, "team_id", "dim_team"),
    ]

    # Cohérence métier
    goals_per_match = fg.groupby("match_id").size().reindex(fm["match_id"], fill_value=0).values
    res.append(_r("Nb buts détaillés = score du match", "fact_goal", "Cohérence", "bloquant",
                  (goals_per_match != fm["total_goals"].values).sum(), len(fm)))

    res.append(_r("Chaque match a exactement 2 équipes", "fact_team_match", "Cohérence", "bloquant",
                  (ftm.groupby("match_id").size() != 2).sum(), ftm["match_id"].nunique()))

    one_result = ftm[["win", "draw", "lose"]].sum(axis=1) != 1
    res.append(_r("Un seul résultat par équipe (V/N/D)", "fact_team_match", "Cohérence", "bloquant",
                  one_result.sum(), len(ftm)))

    res.append(_r("Buts pour/contre ≥ 0", "fact_team_match", "Validité", "bloquant",
                  ((ftm["goals_for"] < 0) | (ftm["goals_against"] < 0)).sum(), len(ftm)))

    res.append(_r("Minute de but entre 1 et 120", "fact_goal", "Validité", "bloquant",
                  (~fg["minute_regulation"].between(1, 120)).sum(), len(fg)))

    winners = fs[fs["position"] == 1].merge(tm, on="team_id")[["tournament_id", "team_name"]]
    chk = t.merge(winners, on="tournament_id", how="left")
    res.append(_r("Vainqueur tournoi = 1er du classement", "dim_tournament", "Cohérence", "bloquant",
                  (chk["winner"] != chk["team_name"]).sum(), len(t)))

    res.append(_r("Match dans les dates du tournoi", "fact_match", "Validité", "bloquant",
                  (~fm.merge(t, on="tournament_id")
                   .pipe(lambda d: d["match_date"].between(d["start_date"], d["end_date"]))).sum(), len(fm)))

    return res


def to_frame(results: list[CheckResult]) -> pd.DataFrame:
    return pd.DataFrame([r.to_dict() for r in results])


def to_markdown(df: pd.DataFrame) -> str:
    lines = ["# Rapport qualité des données", "",
             f"**{df['passed'].sum()} / {len(df)} contrôles réussis**", "",
             "| Statut | Catégorie | Table | Contrôle | Sévérité | Lignes KO | Lignes |",
             "|---|---|---|---|---|---:|---:|"]
    for r in df.itertuples():
        status = "OK" if r.passed else ("KO" if r.severity == "bloquant" else "ALERTE")
        lines.append(f"| {status} | {r.category} | `{r.table}` | {r.check} | {r.severity} | {r.failed_rows} | {r.total_rows} |")
    return "\n".join(lines) + "\n"
