-- Правильних відповідей не може бути більше, ніж відповідей.
select * from {{ ref('fct_user_day') }} where correct_answers > answers or answers < 0
