-- Зерно факту денної активності: не більше одного рядка на слухача за день.
select user_id, activity_date from {{ ref('fct_user_day') }} group by 1, 2 having count(*) > 1
