-- Факт відповіді. Зерно: одна (остання) відповідь слухача на запитання в сесії.
{{ config(post_hook=["create index if not exists fct_answer_date_idx on {{ this }} (answer_date)"]) }}
select a.user_id,
       a.solving_id,
       a.question_id,
       b.part_id,
       a.answered_at,
       (a.answered_at at time zone 'UTC')::date     as answer_date,
       a.user_answer is null                        as is_skipped,
       coalesce(a.user_answer = q.correct_answer, false) as is_correct
from core.answer a
join core.question q using (question_id)
join core.bundle b using (bundle_id)
