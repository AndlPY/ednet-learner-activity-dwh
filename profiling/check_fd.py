"""Перевірка функціональних залежностей, від яких залежить рівень нормалізації (п. 2.2 курсової).

Залежність X → Y виконується, якщо для кожного значення X є рівно одне значення Y.
Запуск: python profiling/check_fd.py C:/ednet ../Курсова/assets/data
"""
import json
import sys
from pathlib import Path

import duckdb

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "C:/ednet")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out")
con = duckdb.connect()
con.sql("SET threads = 12; SET memory_limit = '8GB'")
con.sql(f"CREATE VIEW kt1 AS SELECT * FROM read_parquet('{(RAW / 'parquet/kt1.parquet').as_posix()}')")
con.sql(f"CREATE VIEW q AS SELECT * FROM read_csv('{(RAW / 'contents/questions.csv').as_posix()}', header=true, all_varchar=true)")


def fd(view, lhs, rhs):
    """Кількість значень LHS, для яких RHS неоднозначний, і загальна кількість значень LHS."""
    bad, total = con.sql(f"""SELECT count(*) FILTER (WHERE n > 1), count(*)
                             FROM (SELECT {lhs}, count(DISTINCT {rhs}) n FROM {view} GROUP BY {lhs})""").fetchone()
    return {"violations": bad, "lhs_values": total}


con.sql("CREATE TEMP TABLE a AS SELECT k.*, q.bundle_id, q.part FROM kt1 k JOIN q USING (question_id)")
R = {
    "questions: question_id -> bundle_id": fd("q", "question_id", "bundle_id"),
    "questions: bundle_id -> explanation_id": fd("q", "bundle_id", "explanation_id"),
    "questions: bundle_id -> part": fd("q", "bundle_id", "part"),
    "questions: explanation_id -> bundle_id": fd("q", "explanation_id", "bundle_id"),
    "kt1: (user_id, solving_id) -> ts": fd("a", "user_id, solving_id", "ts"),
    "kt1: (user_id, solving_id) -> elapsed_time": fd("a", "user_id, solving_id", "elapsed_time"),
    "kt1: (user_id, solving_id) -> bundle_id": fd("a", "user_id, solving_id", "bundle_id"),
    "kt1: (user_id, ts) -> solving_id": fd("a", "user_id, ts", "solving_id"),
    "kt1: (user_id, solving_id, question_id) -> user_answer": fd("a", "user_id, solving_id, question_id", "user_answer"),
}
R["kt1: sessions"] = con.sql("SELECT count(*) FROM (SELECT DISTINCT user_id, solving_id FROM kt1)").fetchone()[0]
R["kt1: rows per session q50/q99/max"] = con.sql(
    "SELECT quantile_cont(n,0.5), quantile_cont(n,0.99), max(n) FROM (SELECT user_id, solving_id, count(*) n FROM kt1 GROUP BY 1,2)").fetchone()
R["kt1: solving_id 1..N без пропусків (частка користувачів)"] = con.sql(
    "SELECT avg((mx = cnt)::int) FROM (SELECT user_id, max(solving_id) mx, count(DISTINCT solving_id) cnt FROM kt1 GROUP BY 1)").fetchone()[0]
(OUT / "ednet_fd.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
