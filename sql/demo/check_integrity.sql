-- Демонстрація обмежень цілісності (п. 3.1 курсової): кожна з 4 вставок має завершитися помилкою.
-- Звичайний SQL без команд psql: однаково йде в DBeaver (Alt+X, на помилці «Ignore All») і в psql (-e -f).
-- Режим auto-commit: кожна вставка — окрема транзакція, відхилена вставка нічого не залишає.
-- Запуск від імені etl_user (має право INSERT у core).

-- 1) недопустимий варіант відповіді «e» (CHECK)
INSERT INTO core.answer VALUES (1, 1, 'q1', 'e', now());

-- 2) відповідь у неіснуючій сесії розв'язування (FOREIGN KEY)
INSERT INTO core.answer VALUES (999999999, 1, 'q1', 'a', now());

-- 3) повторна відповідь на те саме запитання в тій самій сесії (PRIMARY KEY)
INSERT INTO core.answer SELECT * FROM core.answer LIMIT 1;

-- 4) вид елемента змісту не збігається з префіксом ідентифікатора (CHECK)
INSERT INTO core.content_item VALUES ('q999999', 'l');
