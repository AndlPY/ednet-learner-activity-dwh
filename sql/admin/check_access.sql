-- Перевірка прав від імені analyst_user: перший запит має пройти, решта — завершитися відмовою.
\set ON_ERROR_STOP off
\echo '1) SELECT з вітрини'
SELECT count(*) AS dim_user_rows FROM marts.dim_user;
\echo '2) SELECT з оперативного рівня'
SELECT count(*) FROM core.answer;
\echo '3) зміна вітрини'
DELETE FROM marts.dim_user WHERE user_id = 1;
\echo '4) створення таблиці'
CREATE TABLE marts.tmp_x (id int);
