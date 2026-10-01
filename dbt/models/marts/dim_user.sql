-- Вимір слухача: когорта першого заняття і підсумки активності.
select u.user_id,
       (u.first_seen_at at time zone 'UTC')::date                   as first_seen_date,
       min(d.activity_date) filter (where d.answers > 0)            as first_answer_date,
       date_trunc('month', min(d.activity_date) filter (where d.answers > 0))::date as cohort_month,
       max(d.activity_date)                                          as last_activity_date,
       count(d.activity_date)                                        as active_days,
       coalesce(sum(d.answers), 0)                                   as answers_total
from core.app_user u
left join {{ ref('fct_user_day') }} d using (user_id)
group by u.user_id, u.first_seen_at
