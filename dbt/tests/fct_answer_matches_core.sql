-- Звірка обсягу: вітрина містить рівно стільки відповідей, скільки core.answer.
select 1 from (select count(*) n from {{ ref('fct_answer') }}) f, (select count(*) n from core.answer) c where f.n <> c.n
