-- Вимір дати: кожен календарний день періоду даних (UTC).
select d::date                                   as date_day,
       date_trunc('week', d)::date               as week_start,
       date_trunc('month', d)::date              as month_start,
       extract(isodow from d)::smallint          as iso_weekday,
       extract(isodow from d) in (6, 7)          as is_weekend
from generate_series('2017-04-01'::date, '2019-12-31'::date, interval '1 day') d
