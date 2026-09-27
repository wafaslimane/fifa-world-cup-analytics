-- Effet pays hôte : bilan du pays organisateur vs son bilan historique hors organisation
CREATE OR REPLACE VIEW v_host_performance AS
WITH hosts AS (
    SELECT h.tournament_id, h.team_id FROM fact_host h
),
tt AS (
    SELECT tt.*, (h.team_id IS NOT NULL) AS is_host
    FROM v_team_tournament tt
    LEFT JOIN hosts h USING (tournament_id, team_id)
)
SELECT competition, team_name, year, is_host, points, matches,
       ROUND(points / matches, 2) AS points_per_match, finish, final_position
FROM tt
WHERE team_id IN (SELECT team_id FROM hosts);
