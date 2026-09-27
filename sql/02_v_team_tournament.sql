-- Parcours d'une équipe sur une édition : bilan et phase atteinte
CREATE OR REPLACE VIEW v_team_tournament AS
WITH agg AS (
    SELECT tournament_id, competition, year, team_id,
           COUNT(*)              AS matches,
           SUM(win::INT)         AS wins,
           SUM(draw::INT)        AS draws,
           SUM(lose::INT)        AS losses,
           SUM(goals_for)        AS goals_for,
           SUM(goals_against)    AS goals_against,
           SUM(points)           AS points,
           MAX(stage_order)      AS best_stage_order,
           arg_max(stage, stage_order) AS best_stage
    FROM fact_team_match
    GROUP BY tournament_id, competition, year, team_id
)
SELECT a.*, tm.team_name, tm.confederation_code,
       s.position AS final_position,
       COALESCE(s.position_label,
                CASE WHEN a.best_stage_order = 1 THEN 'Éliminé en poules'
                     ELSE 'Éliminé en ' || lower(a.best_stage) END) AS finish
FROM agg a
JOIN dim_team tm USING (team_id)
LEFT JOIN fact_standing s ON s.tournament_id = a.tournament_id AND s.team_id = a.team_id;
