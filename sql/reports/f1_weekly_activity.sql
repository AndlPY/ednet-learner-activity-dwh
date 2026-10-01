-- Ф1. Звіт за період: активні слухачі, відповіді й частка правильних по тижнях.
-- Параметри: :date_from, :date_to (psql -v). Джерело — вітрина fct_user_day.
SELECT date_trunc('week', activity_date)::date                      AS week_start,
       count(DISTINCT user_id) FILTER (WHERE answers > 0)           AS active_learners,
       sum(answers)                                                  AS answers,
       round(100.0 * sum(correct_answers) / nullif(sum(answers), 0), 1) AS correct_pct
FROM marts.fct_user_day
WHERE activity_date BETWEEN :'date_from' AND :'date_to'
GROUP BY 1
ORDER BY 1;
