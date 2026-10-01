-- Вимір запитання: денормалізовано набір, частину й розділ іспиту.
select q.question_id,
       q.bundle_id,
       b.part_id,
       p.name_uk                                          as part_name,
       p.section,
       (select count(*) from core.question_tag t where t.question_id = q.question_id) as tag_count
from core.question q
join core.bundle b using (bundle_id)
join core.part p using (part_id)
