# Rapport qualité des données

**23 / 24 contrôles réussis**

| Statut | Catégorie | Table | Contrôle | Sévérité | Lignes KO | Lignes |
|---|---|---|---|---|---:|---:|
| OK | Unicité | `dim_tournament` | Clé unique (tournament_id) | bloquant | 0 | 30 |
| OK | Unicité | `dim_team` | Clé unique (team_id) | bloquant | 0 | 88 |
| OK | Unicité | `dim_player` | Clé unique (player_id) | bloquant | 0 | 10401 |
| OK | Unicité | `fact_match` | Clé unique (match_id) | bloquant | 0 | 1248 |
| OK | Unicité | `fact_team_match` | Clé unique (match_id, team_id) | bloquant | 0 | 2496 |
| OK | Unicité | `fact_goal` | Clé unique (goal_id) | bloquant | 0 | 3637 |
| OK | Unicité | `fact_standing` | Clé unique (tournament_id, position) | bloquant | 0 | 120 |
| OK | Complétude | `fact_match` | Non null (tournament_id, match_date, home_team_id, away_team_id, home_team_score, away_team_score, stage) | bloquant | 0 | 1248 |
| OK | Complétude | `fact_goal` | Non null (match_id, team_id, minute_regulation) | bloquant | 0 | 3637 |
| ALERTE | Complétude | `dim_player` | Non null (birth_date) | alerte | 78 | 10401 |
| OK | Intégrité | `fact_match` | tournament_id → dim_tournament.tournament_id | bloquant | 0 | 1248 |
| OK | Intégrité | `fact_match` | home_team_id → dim_team.team_id | bloquant | 0 | 1248 |
| OK | Intégrité | `fact_match` | away_team_id → dim_team.team_id | bloquant | 0 | 1248 |
| OK | Intégrité | `fact_team_match` | match_id → fact_match.match_id | bloquant | 0 | 2496 |
| OK | Intégrité | `fact_goal` | match_id → fact_match.match_id | bloquant | 0 | 3637 |
| OK | Intégrité | `fact_goal` | player_id → dim_player.player_id | bloquant | 0 | 3637 |
| OK | Intégrité | `fact_standing` | team_id → dim_team.team_id | bloquant | 0 | 120 |
| OK | Cohérence | `fact_goal` | Nb buts détaillés = score du match | bloquant | 0 | 1248 |
| OK | Cohérence | `fact_team_match` | Chaque match a exactement 2 équipes | bloquant | 0 | 1248 |
| OK | Cohérence | `fact_team_match` | Un seul résultat par équipe (V/N/D) | bloquant | 0 | 2496 |
| OK | Validité | `fact_team_match` | Buts pour/contre ≥ 0 | bloquant | 0 | 2496 |
| OK | Validité | `fact_goal` | Minute de but entre 1 et 120 | bloquant | 0 | 3637 |
| OK | Cohérence | `dim_tournament` | Vainqueur tournoi = 1er du classement | bloquant | 0 | 30 |
| OK | Validité | `fact_match` | Match dans les dates du tournoi | bloquant | 0 | 1248 |
