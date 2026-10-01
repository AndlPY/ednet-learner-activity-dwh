"""Контрольний приклад (п. 3.3 курсової): звіт Ф2 з PostgreSQL проти незалежного розрахунку DuckDB із сирого Parquet.

Два розрахунки DuckDB: (а) сирий KT1 — як для рис. 1.2; (б) KT1 з тим самим правилом очищення, що й у core.answer
(з повторних відповідей на запитання в межах сесії лишається остання). Очікування: (б) збігається з Ф2 до одиниці,
а (а) відрізняється лише на слухачів, чия активність у день трималася тільки на відкинутих повторах.
Вхід: logs/f2_result.csv — вивід psql -A -F, для sql/reports/f2_retention.sql. Результат — logs/control_example.log.
"""
import sys
from pathlib import Path
import duckdb

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "C:/ednet") / "parquet/kt1.parquet"
RETENTION = """WITH f AS (SELECT user_id, min(day) first_day FROM d GROUP BY 1),
     w AS (SELECT DISTINCT d.user_id, (d.day - f.first_day) // 7 AS week FROM d JOIN f USING (user_id))
SELECT week, count(*) FROM w WHERE week <= 26 GROUP BY 1 ORDER BY 1"""


def duck(dedup):
    con = duckdb.connect()
    con.sql("SET threads = 8")
    src = f"read_parquet('{RAW.as_posix()}')"
    if dedup:
        src = f"""(SELECT user_id, ts FROM {src}
                   QUALIFY row_number() OVER (PARTITION BY user_id, solving_id, question_id ORDER BY ts DESC) = 1)"""
    con.sql(f"CREATE TEMP TABLE d AS SELECT DISTINCT user_id, epoch_ms(ts)::DATE AS day FROM {src}")
    return dict(con.sql(RETENTION).fetchall())


pg = {}
for line in (ROOT / "logs/f2_result.csv").read_text(encoding="utf-8").splitlines():
    p = line.split(",")
    if p[0].isdigit():
        pg[int(p[0])] = int(p[1])
raw, clean = duck(False), duck(True)
lines = ["тиждень,DuckDB сирий KT1,DuckDB з правилом очищення,PostgreSQL Ф2,різниця Ф2 − сирий"]
lines += [f"{k},{raw[k]},{clean[k]},{pg[k]},{pg[k] - raw[k]}" for k in sorted(pg)]
lines.append(f"Ф2 = DuckDB з правилом очищення в усіх {len(pg)} тижнях: {all(pg[k] == clean[k] for k in pg)}")
lines.append(f"найбільша розбіжність із сирим KT1: {max(abs(pg[k] - raw[k]) for k in pg)} слухачів, "
             f"{max(abs(pg[k] - raw[k]) / raw[k] for k in pg) * 100:.2f} %")
(ROOT / "logs/control_example.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[-2:]))
