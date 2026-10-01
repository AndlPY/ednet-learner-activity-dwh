-- Факт денної активності. Зерно: слухач × календарний день (UTC).
-- week_index рахується від дня першої відповіді слухача — на цьому будується звіт про утримання.
{{ config(post_hook=["create index if not exists fct_user_day_date_idx on {{ this }} (activity_date)",
                     "create index if not exists fct_user_day_user_idx on {{ this }} (user_id, activity_date)"]) }}
with ans as (
    select user_id, answer_date as activity_date,
           count(*) as answers, count(*) filter (where is_correct) as correct_answers,
           count(distinct solving_id) as sessions
    from {{ ref('fct_answer') }}
    group by 1, 2
), act as (
    select user_id, (occurred_at at time zone 'UTC')::date as activity_date, count(*) as actions
    from core.action
    group by 1, 2
), first_answer as (
    select user_id, min(activity_date) as first_answer_date from ans group by 1
)
select coalesce(ans.user_id, act.user_id)                  as user_id,
       coalesce(ans.activity_date, act.activity_date)      as activity_date,
       coalesce(ans.answers, 0)                            as answers,
       coalesce(ans.correct_answers, 0)                    as correct_answers,
       coalesce(ans.sessions, 0)                           as sessions,
       coalesce(act.actions, 0)                            as actions,
       (coalesce(ans.activity_date, act.activity_date) - f.first_answer_date) / 7 as week_index
from ans
full join act on act.user_id = ans.user_id and act.activity_date = ans.activity_date
left join first_answer f on f.user_id = coalesce(ans.user_id, act.user_id)
