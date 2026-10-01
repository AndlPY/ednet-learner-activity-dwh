-- Ф3. Кількість X за кожним Y: відповіді й частка правильних за частинами іспиту за період.
SELECT p.part_id, p.name_uk, p.section,
       sum(a.answers)                                                   AS answers,
       round(100.0 * sum(a.correct_answers) / sum(a.answers), 1)        AS correct_pct,
       round(100.0 * sum(a.skipped) / sum(a.answers), 2)                AS skipped_pct
FROM marts.agg_part_day a
JOIN core.part p USING (part_id)
WHERE a.answer_date BETWEEN :'date_from' AND :'date_to'
GROUP BY p.part_id, p.name_uk, p.section
ORDER BY p.part_id;
