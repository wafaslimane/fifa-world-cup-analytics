-- Matchs lisibles (noms d'équipes) pour l'explorateur
CREATE OR REPLACE VIEW v_matches AS
SELECT m.match_id, m.competition, m.year, m.stage, m.stage_order, m.group_name, m.match_date,
       h.team_name AS home_team, a.team_name AS away_team,
       m.home_team_score, m.away_team_score, m.total_goals,
       CASE WHEN m.penalty_shootout
            THEN m.home_team_score || '–' || m.away_team_score
                 || ' (' || m.home_team_score_penalties || '–' || m.away_team_score_penalties || ' tab)'
            ELSE m.home_team_score || '–' || m.away_team_score END AS score,
       m.extra_time, m.penalty_shootout,
       w.team_name AS winner, m.stadium_name, m.city_name, m.country_name
FROM fact_match m
JOIN dim_team h ON h.team_id = m.home_team_id
JOIN dim_team a ON a.team_id = m.away_team_id
LEFT JOIN dim_team w ON w.team_id = m.winner_team_id;
