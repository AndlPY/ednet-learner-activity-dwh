-- Ефект індексу action_user_time_idx (п. 3.3 курсової): той самий запит з індексом і без нього.
-- Звичайний SQL без команд psql: DBeaver (Alt+X, два результати — два плани) або psql -e -f.
-- Індекс НЕ видаляється: планувальнику лише забороняється ним користуватися, у кінці — RESET
-- (у DBeaver сеанс живе довго, без RESET заборона лишилася б до перепідключення).
-- Запуск від імені etl_user (читає core).
-- 288017 — той самий слухач, що в замірах pipeline/04_perf.py (101-й за кількістю відповідей).

-- 1) з індексом
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT occurred_at, action_type_id, item_id
FROM core.action
WHERE user_id = 288017
ORDER BY occurred_at DESC
LIMIT 100;

-- 2) без індексу: використання індексів вимкнено в цьому сеансі
SET enable_indexscan = off;
SET enable_bitmapscan = off;
SET enable_indexonlyscan = off;

EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT occurred_at, action_type_id, item_id
FROM core.action
WHERE user_id = 288017
ORDER BY occurred_at DESC
LIMIT 100;

RESET enable_indexscan;
RESET enable_bitmapscan;
RESET enable_indexonlyscan;
