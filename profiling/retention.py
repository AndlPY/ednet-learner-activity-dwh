"""Утримання за KT1 незалежно від PostgreSQL (для рис. 1.2 і контрольного прикладу п. 3.3).

Визначення (таке саме, як у вітрині marts.fct_user_day): день = календарна дата UTC;
тиждень k = (дата відповіді − дата першої відповіді) div 7; утримання k = частка слухачів з ≥1 відповіддю на тижні k.
"""
import sys
from pathlib import Path
import duckdb

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "C:/ednet")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out")
con = duckdb.connect()
con.sql("SET threads = 12")
con.sql(f"""CREATE TEMP TABLE d AS SELECT DISTINCT user_id, epoch_ms(ts)::DATE AS day
            FROM read_parquet('{(RAW / 'parquet/kt1.parquet').as_posix()}')""")
con.sql(f"""COPY (
  WITH f AS (SELECT user_id, min(day) first_day FROM d GROUP BY 1),
       w AS (SELECT DISTINCT d.user_id, (d.day - f.first_day) // 7 AS week FROM d JOIN f USING (user_id))
  SELECT week, count(*) AS active_users, count(*) / (SELECT count(*) FROM f)::DOUBLE AS retention
  FROM w WHERE week <= 26 GROUP BY 1 ORDER BY 1) TO '{(OUT / 'ednet_retention_kt1.csv').as_posix()}' (HEADER)""")
print(con.sql(f"SELECT * FROM read_csv('{(OUT / 'ednet_retention_kt1.csv').as_posix()}') WHERE week IN (0,1,2,4,8,12,26)").fetchall())
