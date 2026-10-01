-- raw → core. Ідемпотентно: 02_core.sql перестворює схему, тож повторний запуск дає той самий результат.
-- Правила очищення (з профілювання, п. 2.1 курсової):
--   -1 у довідниках і в item_id журналу дій → NULL; повні дублікати рядків відкидаються;
--   повторна відповідь на те саме запитання в тій самій сесії → лишається остання за часом;
--   час сесії = найраніший час її рядків; витрачений час сесії = значення першого рядка, ≤ 0 → NULL.
SET work_mem = '512MB';

INSERT INTO core.part VALUES
 (0, NULL, 'Загальні матеріали'), (1, 'listening', 'Фотографії'), (2, 'listening', 'Запитання — відповідь'),
 (3, 'listening', 'Діалоги'), (4, 'listening', 'Монологи'), (5, 'reading', 'Незавершені речення'),
 (6, 'reading', 'Доповнення тексту'), (7, 'reading', 'Розуміння прочитаного');

INSERT INTO core.tag
SELECT DISTINCT t::int FROM raw.questions, unnest(string_to_array(tags, ';')) t WHERE t <> '-1'
UNION
SELECT DISTINCT tags::int FROM raw.lectures WHERE tags <> '-1';

INSERT INTO core.content_item
SELECT question_id, 'q' FROM raw.questions
UNION ALL SELECT DISTINCT bundle_id, 'b' FROM raw.questions
UNION ALL SELECT DISTINCT explanation_id, 'e' FROM raw.questions
UNION ALL SELECT lecture_id, 'l' FROM raw.lectures
UNION ALL SELECT payment_item_id, 'p' FROM raw.payments
UNION ALL SELECT coupon_id, 'c' FROM raw.coupons;

INSERT INTO core.bundle
SELECT DISTINCT bundle_id, part::smallint, explanation_id FROM raw.questions;

INSERT INTO core.question
SELECT question_id, bundle_id, correct_answer,
       CASE WHEN deployed_at <> '-1' THEN to_timestamp(deployed_at::bigint / 1000.0) END
FROM raw.questions;

INSERT INTO core.question_tag
SELECT DISTINCT question_id, t::int FROM raw.questions, unnest(string_to_array(tags, ';')) t WHERE t <> '-1';

INSERT INTO core.lecture
SELECT lecture_id, NULLIF(part, '-1')::smallint, NULLIF(tags, '-1')::int, NULLIF(video_length, '-1')::int,
       CASE WHEN deployed_at <> '-1' THEN to_timestamp(deployed_at::bigint / 1000.0) END
FROM raw.lectures;

INSERT INTO core.payment_item
SELECT payment_item_id, NULLIF(type, '-1'), NULLIF(duaration, '-1')::bigint, NULLIF(number_of_questions, '-1')::int
FROM raw.payments;

INSERT INTO core.coupon SELECT coupon_id, coupon_type, duration::bigint FROM raw.coupons;

INSERT INTO core.action_type SELECT row_number() OVER (ORDER BY action_type), action_type FROM (SELECT DISTINCT action_type FROM raw.kt4) s;
INSERT INTO core.source      SELECT row_number() OVER (ORDER BY source), source FROM (SELECT DISTINCT source FROM raw.kt4 WHERE source IS NOT NULL) s;
INSERT INTO core.platform    SELECT row_number() OVER (ORDER BY platform), platform FROM (SELECT DISTINCT platform FROM raw.kt4 WHERE platform IS NOT NULL) s;

-- користувачі: об'єднання KT1 і KT4 (7 562 користувачі KT4 відсутні в KT1)
INSERT INTO core.app_user
SELECT user_id, to_timestamp(min(first_ts) / 1000.0)
FROM (SELECT user_id, min(ts) first_ts FROM raw.kt1 GROUP BY 1
      UNION ALL
      SELECT user_id, min(ts) FROM raw.kt4 GROUP BY 1) u
GROUP BY user_id;

-- сесії розв'язування: одна на (user_id, solving_id); набір визначається будь-яким запитанням сесії
INSERT INTO core.solving_session
SELECT k.user_id, k.solving_id, min(q.bundle_id), to_timestamp(min(k.ts) / 1000.0),
       NULLIF(greatest((array_agg(k.elapsed_time ORDER BY k.ts))[1], 0), 0)
FROM raw.kt1 k JOIN raw.questions q USING (question_id)
GROUP BY k.user_id, k.solving_id;

-- відповіді: остання за часом відповідь на запитання в межах сесії
INSERT INTO core.answer
SELECT DISTINCT ON (user_id, solving_id, question_id)
       user_id, solving_id, question_id, user_answer, to_timestamp(ts / 1000.0)
FROM raw.kt1
ORDER BY user_id, solving_id, question_id, ts DESC;

-- дії: без повних дублікатів
INSERT INTO core.action (user_id, occurred_at, action_type_id, item_id, source_id, platform_id, user_answer, cursor_time_ms)
SELECT d.user_id, to_timestamp(d.ts / 1000.0), t.action_type_id, NULLIF(d.item_id, '-1'), s.source_id, p.platform_id,
       d.user_answer, d.cursor_time
FROM (SELECT DISTINCT * FROM raw.kt4) d
JOIN core.action_type t ON t.name = d.action_type
LEFT JOIN core.source s ON s.name = d.source
LEFT JOIN core.platform p ON p.name = d.platform;
