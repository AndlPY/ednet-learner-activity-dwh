-- Ф4. Список за фільтром: слухачі, що дали щонайменше :min_answers відповідей,
-- але неактивні понад :days днів на дату :as_of. Впорядковано за кількістю відповідей.
SELECT user_id, first_answer_date, last_activity_date,
       :'as_of'::date - last_activity_date AS days_inactive,
       active_days, answers_total
FROM marts.dim_user
WHERE answers_total >= :min_answers
  AND last_activity_date <= :'as_of'::date - :days
  AND last_activity_date > :'as_of'::date - 180
ORDER BY answers_total DESC
LIMIT 50;
