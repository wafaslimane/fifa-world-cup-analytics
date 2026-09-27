-- Répartition temporelle des buts
CREATE OR REPLACE VIEW v_goal_timing AS
SELECT competition, year, minute_bucket,
       COUNT(*)                        AS goals,
       SUM(penalty::INT)               AS penalty_goals,
       SUM(is_stoppage_time::INT)      AS stoppage_time_goals
FROM fact_goal
GROUP BY ALL;
