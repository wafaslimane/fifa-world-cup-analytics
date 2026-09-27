-- Poids des confédérations par édition
CREATE OR REPLACE VIEW v_confederation_tournament AS
SELECT competition, year, confederation_code,
       COUNT(DISTINCT team_id)   AS teams,
       SUM(wins)                 AS wins,
       SUM(matches)              AS matches,
       ROUND(SUM(points) / SUM(matches), 2) AS points_per_match,
       COUNT(*) FILTER (WHERE final_position <= 4) AS semi_finalists
FROM v_team_tournament
GROUP BY ALL;
