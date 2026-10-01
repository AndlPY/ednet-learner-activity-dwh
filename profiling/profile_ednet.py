"""Профілювання EdNet у DuckDB: обсяги, ключі, кардинальність, пропуски, дублікати, діапазони, сироти.

Результат — JSON з усіма метриками і CSV для рисунків; шлях виводу — другий аргумент.
Запуск: python profiling/profile_ednet.py C:/ednet ../Курсова/assets/data
"""
import json
import sys
import time
from pathlib import Path

import duckdb

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "C:/ednet")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out")
OUT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect()
con.sql("SET threads = 12; SET memory_limit = '8GB'")
kt1 = f"read_parquet('{(RAW / 'parquet/kt1.parquet').as_posix()}')"
kt4 = f"read_parquet('{(RAW / 'parquet/kt4.parquet').as_posix()}')"
c = (RAW / "contents").as_posix()
for t in ("questions", "lectures", "payments", "coupons"):
    con.sql(f"CREATE VIEW {t} AS SELECT * FROM read_csv('{c}/{t}.csv', header=true, all_varchar=true)")
con.sql(f"CREATE VIEW kt1 AS SELECT * FROM {kt1}")
con.sql(f"CREATE VIEW kt4 AS SELECT * FROM {kt4}")

P = {}


def one(sql):
    return con.sql(sql).fetchone()


def rows(sql):
    r = con.sql(sql)
    return [dict(zip(r.columns, x)) for x in r.fetchall()]


t0 = time.time()
# ---------- обсяги й ключі
for lvl in ("kt1", "kt4"):
    n, users, tmin, tmax = one(f"SELECT count(*), count(DISTINCT user_id), min(ts), max(ts) FROM {lvl}")
    P[lvl] = {"rows": n, "users": users,
              "ts_min": str(one(f"SELECT epoch_ms({tmin})::VARCHAR")[0]), "ts_max": str(one(f"SELECT epoch_ms({tmax})::VARCHAR")[0])}
    cols = [r["column_name"] for r in rows(f"DESCRIBE {lvl}")]
    P[lvl]["nulls"] = dict(zip(cols, one("SELECT " + ", ".join(f"count(*) - count({x})" for x in cols) + f" FROM {lvl}")))
    P[lvl]["distinct"] = dict(zip(cols, one("SELECT " + ", ".join(f"approx_count_distinct({x})" for x in cols) + f" FROM {lvl}")))
    P[lvl]["exact_duplicate_rows"] = one(f"SELECT count(*) - (SELECT count(*) FROM (SELECT DISTINCT * FROM {lvl})) FROM {lvl}")[0]
    q = one(f"""SELECT quantile_cont(n, [0.25, 0.5, 0.75, 0.9, 0.99]), max(n), avg(n)
                FROM (SELECT user_id, count(*) n FROM {lvl} GROUP BY 1)""")
    P[lvl]["events_per_user"] = {"q25_50_75_90_99": q[0], "max": q[1], "avg": q[2]}
print("обсяги", round(time.time() - t0), "с")

# ---------- KT1: ключ, значення, діапазони
P["kt1"]["dup_user_ts_question"] = one("SELECT count(*) - count(DISTINCT (user_id, ts, question_id)) FROM kt1")[0]
P["kt1"]["dup_user_solving_question"] = one("SELECT count(*) - count(DISTINCT (user_id, solving_id, question_id)) FROM kt1")[0]
P["kt1"]["user_answer"] = rows("SELECT user_answer, count(*) n FROM kt1 GROUP BY 1 ORDER BY 2 DESC")
P["kt1"]["elapsed_time_ms"] = dict(zip(["min", "p50", "p99", "max", "le0", "gt_1h"], one(
    "SELECT min(elapsed_time), quantile_cont(elapsed_time, 0.5), quantile_cont(elapsed_time, 0.99), max(elapsed_time),"
    " count(*) FILTER (WHERE elapsed_time <= 0), count(*) FILTER (WHERE elapsed_time > 3600000) FROM kt1")))
P["kt1"]["ts_before_2017"] = one("SELECT count(*) FROM kt1 WHERE ts < 1483228800000")[0]
P["kt1"]["orphan_questions"] = one("SELECT count(*) FROM kt1 WHERE question_id NOT IN (SELECT question_id FROM questions)")[0]
P["kt1"]["accuracy"] = one("""SELECT avg((k.user_answer = q.correct_answer)::int) FROM kt1 k JOIN questions q USING (question_id)""")[0]
print("kt1", round(time.time() - t0), "с")

# ---------- KT4: типи дій, джерела, платформи, префікси ідентифікаторів
P["kt4"]["action_type"] = rows("SELECT action_type, count(*) n FROM kt4 GROUP BY 1 ORDER BY 2 DESC")
P["kt4"]["source"] = rows("SELECT source, count(*) n FROM kt4 GROUP BY 1 ORDER BY 2 DESC")
P["kt4"]["platform"] = rows("SELECT platform, count(*) n FROM kt4 GROUP BY 1 ORDER BY 2 DESC")
P["kt4"]["item_prefix"] = rows("SELECT left(item_id, 1) prefix, count(*) n, count(DISTINCT item_id) items FROM kt4 GROUP BY 1 ORDER BY 2 DESC")
P["kt4"]["action_x_prefix"] = rows("SELECT action_type, left(item_id,1) prefix, count(*) n FROM kt4 GROUP BY 1,2 ORDER BY 1,3 DESC")
P["kt4"]["dup_user_ts_action_item"] = one("SELECT count(*) - count(DISTINCT (user_id, ts, action_type, item_id)) FROM kt4")[0]
P["kt4"]["orphans"] = {
    "q": one("SELECT count(DISTINCT item_id) FROM kt4 WHERE item_id LIKE 'q%' AND item_id NOT IN (SELECT question_id FROM questions)")[0],
    "l": one("SELECT count(DISTINCT item_id) FROM kt4 WHERE item_id LIKE 'l%' AND item_id NOT IN (SELECT lecture_id FROM lectures)")[0],
    "e": one("SELECT count(DISTINCT item_id) FROM kt4 WHERE item_id LIKE 'e%' AND item_id NOT IN (SELECT explanation_id FROM questions)")[0],
    "b": one("SELECT count(DISTINCT item_id) FROM kt4 WHERE item_id LIKE 'b%' AND item_id NOT IN (SELECT bundle_id FROM questions)")[0],
    "p": one("SELECT count(DISTINCT item_id) FROM kt4 WHERE item_id LIKE 'p%' AND item_id NOT IN (SELECT payment_item_id FROM payments)")[0],
    "c": one("SELECT count(DISTINCT item_id) FROM kt4 WHERE item_id LIKE 'c%' AND item_id NOT IN (SELECT coupon_id FROM coupons)")[0],
}
P["kt4_users_in_kt1"] = one("SELECT count(DISTINCT user_id) FROM kt4 WHERE user_id IN (SELECT DISTINCT user_id FROM kt1)")[0]
print("kt4", round(time.time() - t0), "с")

# ---------- довідники
P["contents"] = {t: one(f"SELECT count(*) FROM {t}")[0] for t in ("questions", "lectures", "payments", "coupons")}
P["contents"]["questions_distinct_bundles"] = one("SELECT count(DISTINCT bundle_id) FROM questions")[0]
P["contents"]["questions_distinct_explanations"] = one("SELECT count(DISTINCT explanation_id) FROM questions")[0]
P["contents"]["distinct_tags"] = one("SELECT count(DISTINCT t) FROM (SELECT unnest(string_split(tags, ';')) t FROM questions)")[0]
P["contents"]["question_tag_pairs"] = one("SELECT count(*) FROM (SELECT unnest(string_split(tags, ';')) t FROM questions)")[0]
P["contents"]["questions_tags_minus1"] = one("SELECT count(*) FROM questions WHERE tags = '-1'")[0]
P["contents"]["questions_deployed_minus1"] = one("SELECT count(*) FROM questions WHERE deployed_at = '-1'")[0]
P["contents"]["lectures_video_minus1"] = one("SELECT count(*) FROM lectures WHERE video_length = '-1'")[0]
P["contents"]["lectures_deployed_minus1"] = one("SELECT count(*) FROM lectures WHERE deployed_at = '-1'")[0]
P["contents"]["bundle_size"] = rows("SELECT n, count(*) bundles FROM (SELECT bundle_id, count(*) n FROM questions GROUP BY 1) GROUP BY 1 ORDER BY 1")
P["contents"]["bundle_part_conflicts"] = one("SELECT count(*) FROM (SELECT bundle_id FROM questions GROUP BY 1 HAVING count(DISTINCT part) > 1)")[0]
P["contents"]["bundle_expl_conflicts"] = one("SELECT count(*) FROM (SELECT bundle_id FROM questions GROUP BY 1 HAVING count(DISTINCT explanation_id) > 1)")[0]
P["contents"]["parts"] = rows("SELECT part, count(*) n FROM questions GROUP BY 1 ORDER BY 1")
P["contents"]["payments_types"] = rows("SELECT type, count(*) n FROM payments GROUP BY 1")
P["contents"]["coupon_types"] = rows("SELECT coupon_type, count(*) n FROM coupons GROUP BY 1")

# ---------- активність у часі (для рисунків)
con.sql("""CREATE TEMP TABLE first_seen AS SELECT user_id, min(ts) first_ts FROM kt1 GROUP BY 1""")
con.sql(f"""COPY (
  WITH w AS (SELECT DISTINCT k.user_id, ((k.ts - f.first_ts) / (7*86400000))::INT AS week
             FROM kt1 k JOIN first_seen f USING (user_id))
  SELECT week, count(*) AS active_users, count(*) / (SELECT count(*) FROM first_seen)::DOUBLE AS retention
  FROM w WHERE week <= 26 GROUP BY 1 ORDER BY 1) TO '{(OUT / 'ednet_retention_kt1.csv').as_posix()}' (HEADER)""")
con.sql(f"""COPY (
  SELECT n_bucket, count(*) users FROM (
    SELECT CASE WHEN n < 10 THEN '1–9' WHEN n < 50 THEN '10–49' WHEN n < 200 THEN '50–199'
                WHEN n < 1000 THEN '200–999' WHEN n < 5000 THEN '1000–4999' ELSE '5000+' END n_bucket
    FROM (SELECT user_id, count(*) n FROM kt1 GROUP BY 1)) GROUP BY 1) TO '{(OUT / 'ednet_events_per_user_kt1.csv').as_posix()}' (HEADER)""")
con.sql(f"""COPY (SELECT date_trunc('month', epoch_ms(ts))::DATE AS month_start, count(*) events, count(DISTINCT user_id) users
                 FROM kt1 GROUP BY 1 ORDER BY 1) TO '{(OUT / 'ednet_monthly_kt1.csv').as_posix()}' (HEADER)""")
con.sql(f"""COPY (SELECT date_trunc('month', epoch_ms(ts))::DATE AS month_start, count(*) events, count(DISTINCT user_id) users
                 FROM kt4 GROUP BY 1 ORDER BY 1) TO '{(OUT / 'ednet_monthly_kt4.csv').as_posix()}' (HEADER)""")
P["retention_first_week_active_share_by_week"] = rows(f"SELECT * FROM read_csv('{(OUT / 'ednet_retention_kt1.csv').as_posix()}') WHERE week IN (0,1,2,4,8,12,26)")
P["seconds_total"] = round(time.time() - t0)
(OUT / "ednet_profile.json").write_text(json.dumps(P, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("готово", P["seconds_total"], "с")
