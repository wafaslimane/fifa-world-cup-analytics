-- Bilan historique par équipe et compétition
CREATE OR REPLACE VIEW v_team_all_time AS
SELECT competition, team_id, team_name, confederation_code,
       COUNT(DISTINCT tournament_id)                        AS participations,
       SUM(matches)::INT AS matches, SUM(wins)::INT AS wins, SUM(draws)::INT AS draws, SUM(losses)::INT AS losses,
       SUM(goals_for)::INT AS goals_for, SUM(goals_against)::INT AS goals_against,
       (SUM(goals_for) - SUM(goals_against))::INT AS goal_difference,
       SUM(points)::INT AS points,
       ROUND(SUM(wins) / SUM(matches), 3)                   AS win_rate,
       ROUND(SUM(points) / SUM(matches), 2)                 AS points_per_match,
       COUNT(*) FILTER (WHERE final_position = 1)           AS titles,
       COUNT(*) FILTER (WHERE final_position <= 2)          AS finals,
       COUNT(*) FILTER (WHERE final_position <= 4)          AS top4,
       MIN(year) AS first_year, MAX(year) AS last_year
FROM v_team_tournament
GROUP BY ALL;
