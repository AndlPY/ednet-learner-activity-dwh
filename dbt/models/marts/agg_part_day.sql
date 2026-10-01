-- Попередньо агрегована вітрина: частина іспиту × день. Для звіту про успішність за частинами за період.
select answer_date, part_id,
       count(*)                                  as answers,
       count(*) filter (where is_correct)        as correct_answers,
       count(*) filter (where is_skipped)        as skipped,
       count(distinct user_id)                   as users
from {{ ref('fct_answer') }}
group by 1, 2
