-- KPI par édition : volume, intensité offensive, suspense
CREATE OR REPLACE VIEW v_tournament_kpis AS
WITH m AS (
    SELECT tournament_id,
           COUNT(*)                                        AS matches,
           SUM(total_goals)                                AS goals,
           AVG(CASE WHEN result = 'Nul' THEN 1 ELSE 0 END) AS draw_rate,
           AVG(CASE WHEN extra_time THEN 1 ELSE 0 END)     AS extra_time_rate,
           SUM(CASE WHEN penalty_shootout THEN 1 ELSE 0 END) AS shootouts,
           MAX(total_goals)                                AS max_goals_in_match
    FROM fact_match
    GROUP BY tournament_id
), g AS (
    SELECT tournament_id,
           SUM(CASE WHEN penalty  THEN 1 ELSE 0 END) AS penalty_goals,
           SUM(CASE WHEN own_goal THEN 1 ELSE 0 END) AS own_goals
    FROM fact_goal
    GROUP BY tournament_id
)
SELECT t.tournament_id, t.tournament_name, t.competition, t.year, t.decade,
       t.host_country, t.winner, t.host_won, t.count_teams, t.duration_days,
       m.matches, m.goals,
       ROUND(m.goals / m.matches, 2)          AS goals_per_match,
       ROUND(m.draw_rate, 3)                  AS draw_rate,
       ROUND(m.extra_time_rate, 3)            AS extra_time_rate,
       m.shootouts, m.max_goals_in_match,
       COALESCE(g.penalty_goals, 0)           AS penalty_goals,
       COALESCE(g.own_goals, 0)               AS own_goals
FROM dim_tournament t
JOIN m USING (tournament_id)
LEFT JOIN g USING (tournament_id);
