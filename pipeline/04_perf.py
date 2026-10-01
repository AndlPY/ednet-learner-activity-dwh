"""Вимірювання продуктивності: EXPLAIN (ANALYZE, BUFFERS) кожного запиту 3 рази, медіана часу виконання.

Порівнюються: (а) функціональні задачі на нормалізованому core і на вітринах marts;
(б) пошук історії слухача в журналі дій до і після складеного індексу.
Результат: logs/perf.csv і logs/perf_plans.txt; ці числа — таблиці й рисунок п. 3.3 курсової.
"""
import csv
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = {**os.environ, "PGHOST": "localhost", "PGPORT": os.getenv("PGPORT", "5433"), "PGUSER": "postgres",
       "PGPASSWORD": os.getenv("PGPASSWORD", "postgres"), "PGDATABASE": "ednet", "PGCLIENTENCODING": "UTF8"}
PSQL = os.getenv("PSQL", "C:/ednet/pg/pgsql/bin/psql.exe")
P = dict(date_from="2019-01-01", date_to="2019-03-31", as_of="2019-12-01", days=30, min_answers=100)


def sql(q):
    out = subprocess.run([PSQL, "-X", "-At", "-c", q], env=ENV, capture_output=True, text=True, encoding="utf-8")
    if out.returncode:
        raise RuntimeError(out.stderr)
    return out.stdout.strip()


def explain(q, runs=3):
    times, plan = [], None
    for _ in range(runs):
        plan = json.loads(sql("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + q))[0]
        times.append(plan["Execution Time"])
    top = plan["Plan"]
    return statistics.median(times), top.get("Actual Rows"), plan


def read(name):
    q = (ROOT / "sql/reports" / name).read_text(encoding="utf-8")
    q = q.replace(":'date_from'", f"'{P['date_from']}'").replace(":'date_to'", f"'{P['date_to']}'")
    q = q.replace(":'as_of'", f"'{P['as_of']}'").replace(":days", str(P["days"])).replace(":min_answers", str(P["min_answers"]))
    return "\n".join(l for l in q.splitlines() if not l.strip().startswith("--")).rstrip().rstrip(";")


CORE = {
    "Ф1": f"""SELECT date_trunc('week', a.answered_at AT TIME ZONE 'UTC')::date AS week_start,
                     count(DISTINCT a.user_id), count(*),
                     round(100.0 * avg((a.user_answer IS NOT DISTINCT FROM q.correct_answer)::int), 1)
              FROM core.answer a JOIN core.question q USING (question_id)
              WHERE a.answered_at >= '{P['date_from']}' AND a.answered_at < '{P['date_to']}'::date + 1
              GROUP BY 1 ORDER BY 1""",
    "Ф2": """WITH d AS (SELECT DISTINCT user_id, (answered_at AT TIME ZONE 'UTC')::date AS day FROM core.answer),
                  f AS (SELECT user_id, min(day) AS first_day FROM d GROUP BY 1)
             SELECT (d.day - f.first_day) / 7 AS week_index, count(DISTINCT d.user_id)
             FROM d JOIN f USING (user_id) WHERE (d.day - f.first_day) / 7 <= 26 GROUP BY 1 ORDER BY 1""",
    "Ф3": f"""SELECT p.part_id, p.name_uk, count(*),
                     round(100.0 * avg((a.user_answer IS NOT DISTINCT FROM q.correct_answer)::int), 1)
              FROM core.answer a JOIN core.question q USING (question_id)
              JOIN core.bundle b USING (bundle_id) JOIN core.part p USING (part_id)
              WHERE a.answered_at >= '{P['date_from']}' AND a.answered_at < '{P['date_to']}'::date + 1
              GROUP BY 1, 2 ORDER BY 1""",
    "Ф4": f"""SELECT user_id, max((answered_at AT TIME ZONE 'UTC')::date) AS last_day, count(*) AS answers
              FROM core.answer GROUP BY user_id
              HAVING count(*) >= {P['min_answers']}
                 AND max((answered_at AT TIME ZONE 'UTC')::date) <= '{P['as_of']}'::date - {P['days']}
                 AND max((answered_at AT TIME ZONE 'UTC')::date) >  '{P['as_of']}'::date - 180
              ORDER BY answers DESC LIMIT 50""",
}
MARTS = {"Ф1": "f1_weekly_activity.sql", "Ф2": "f2_retention.sql", "Ф3": "f3_accuracy_by_part.sql", "Ф4": "f4_inactive_learners.sql"}

if __name__ == "__main__":
    out = ROOT / "logs"
    rows, plans = [], []
    for task in ("Ф1", "Ф2", "Ф3", "Ф4"):
        for level, q in (("core", CORE[task]), ("marts", read(MARTS[task]))):
            ms, n, plan = explain(q, runs=1 if (level == "core" and task == "Ф2") else 3)
            rows.append({"experiment": task, "variant": level, "ms": round(ms, 1), "rows": n})
            plans.append(f"==== {task} {level}: {ms:.1f} ms\n{json.dumps(plan['Plan'], ensure_ascii=False)[:3000]}\n")
            print(rows[-1], flush=True)
    # індекс: історія дій одного активного слухача
    uid = sql("SELECT user_id FROM marts.dim_user ORDER BY answers_total DESC OFFSET 100 LIMIT 1")
    q = f"SELECT occurred_at, action_type_id, item_id FROM core.action WHERE user_id = {uid} ORDER BY occurred_at DESC LIMIT 100"
    sql("DROP INDEX IF EXISTS core.action_user_time_idx")
    ms, n, plan = explain(q)
    rows.append({"experiment": "історія слухача", "variant": "без індексу", "ms": round(ms, 1), "rows": n})
    plans.append(f"==== історія без індексу: {ms:.1f} ms\n{json.dumps(plan['Plan'], ensure_ascii=False)[:3000]}\n")
    t = time.time()
    sql("CREATE INDEX action_user_time_idx ON core.action (user_id, occurred_at)")
    build = time.time() - t
    size = sql("SELECT pg_size_pretty(pg_relation_size('core.action_user_time_idx'))")
    ms, n, plan = explain(q)
    rows.append({"experiment": "історія слухача", "variant": "з індексом", "ms": round(ms, 2), "rows": n,
                 "note": f"побудова індексу {build:.0f} с, розмір {size}"})
    plans.append(f"==== історія з індексом: {ms:.2f} ms\n{json.dumps(plan['Plan'], ensure_ascii=False)[:3000]}\n")
    print(rows[-2:], flush=True)
    with open(out / "perf.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["experiment", "variant", "ms", "rows", "note"])
        w.writeheader()
        w.writerows(rows)
    (out / "perf_plans.txt").write_text("\n".join(plans), encoding="utf-8")
