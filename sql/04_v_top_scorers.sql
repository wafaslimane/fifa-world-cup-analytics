-- Buteurs (hors CSC), par compétition
CREATE OR REPLACE VIEW v_top_scorers AS
SELECT g.competition, g.player_id, p.player_name, p.position,
       tm.team_name,
       COUNT(*)                                   AS goals,
       SUM(g.penalty::INT)                        AS penalty_goals,
       COUNT(DISTINCT g.tournament_id)            AS tournaments_scored,
       COUNT(DISTINCT g.match_id)                 AS matches_scored,
       MIN(g.year) AS first_year, MAX(g.year) AS last_year
FROM fact_goal g
JOIN dim_player p USING (player_id)
JOIN dim_team tm ON tm.team_id = g.player_team_id
WHERE NOT g.own_goal
GROUP BY ALL;
