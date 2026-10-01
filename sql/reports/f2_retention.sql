-- Ф2. Утримання: частка слухачів, які відповідали на k-му тижні від першої відповіді.
-- Вимірюваний відповідник проблеми незавершення (п. 1.1 курсової).
WITH cohort AS (SELECT count(*) AS n FROM marts.dim_user WHERE first_answer_date IS NOT NULL)
SELECT week_index,
       count(DISTINCT user_id)                                  AS active_learners,
       round(100.0 * count(DISTINCT user_id) / (SELECT n FROM cohort), 2) AS retention_pct
FROM marts.fct_user_day
WHERE answers > 0 AND week_index BETWEEN 0 AND 26
GROUP BY week_index
ORDER BY week_index;
