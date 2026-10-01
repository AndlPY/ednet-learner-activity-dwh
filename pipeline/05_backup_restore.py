"""Резервне копіювання core+marts (pg_dump, формат каталогу, 8 потоків) і перевірене відновлення в окрему базу.

raw не копіюється свідомо: він відтворюється з архівів джерела скриптом 02_load.py.
Перевірка відновлення: збіг кількості рядків у всіх таблицях і збіг результату звіту про утримання.
"""
import os, shutil, subprocess, sys, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # консоль Windows — cp1252, а вивід кириличний
ROOT = Path(__file__).resolve().parent.parent
BIN = Path(os.getenv("PGBIN", "C:/ednet/pg/pgsql/bin"))
ENV = {**os.environ, "PGHOST": "localhost", "PGPORT": os.getenv("PGPORT", "5433"), "PGUSER": "postgres",
       "PGPASSWORD": os.getenv("PGPASSWORD", "postgres"), "PGCLIENTENCODING": "UTF8"}
DUMP = Path(os.getenv("DUMP_DIR", "C:/ednet/backup/ednet_core_marts"))
LOG = ROOT / "logs" / "backup.log"


def run(args, db=None):
    cmd = [str(BIN / args[0])] + args[1:] + ([f"--dbname={db}"] if db else [])
    t = time.time()
    out = subprocess.run(cmd, env=ENV, capture_output=True, text=True, encoding="utf-8")
    if out.returncode:
        raise RuntimeError(out.stderr)
    return time.time() - t, out.stdout


def psql(q, db):
    return run(["psql", "-X", "-At", "-c", q], db)[1].strip()


def log(m):
    print(m, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(m + "\n")


COUNT_SQL = """SELECT string_agg(format('%s.%s=%s', schemaname, relname, n), ' ' ORDER BY schemaname, relname) FROM (
  SELECT schemaname, relname, (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', schemaname, relname), false, true, '')))[1]::text::bigint n
  FROM pg_stat_user_tables WHERE schemaname IN ('core','marts')) s"""
RETENTION = "SELECT string_agg(week_index || ':' || active_learners, ',' ORDER BY week_index) FROM (" \
            + (ROOT / "sql/reports/f2_retention.sql").read_text(encoding="utf-8").split(";")[0].split("\n", 2)[2] + ") r"

if __name__ == "__main__":
    shutil.rmtree(DUMP, ignore_errors=True)
    DUMP.parent.mkdir(parents=True, exist_ok=True)
    t, _ = run(["pg_dump", "-Fd", "-j", "8", "-Z", "zstd:3", "-n", "core", "-n", "marts", "-f", str(DUMP)], "ednet")
    size = sum(f.stat().st_size for f in DUMP.rglob("*") if f.is_file()) / 2**30
    log(f"pg_dump core+marts: {t:.0f} с, {size:.2f} ГБ")
    psql("DROP DATABASE IF EXISTS ednet_restore", "postgres")
    psql("CREATE DATABASE ednet_restore", "postgres")
    t, _ = run(["pg_restore", "-j", "8", "--no-owner", "-d", "ednet_restore", str(DUMP)])
    log(f"pg_restore: {t:.0f} с")
    a, b = psql(COUNT_SQL, "ednet"), psql(COUNT_SQL, "ednet_restore")
    log(f"кількість рядків збігається: {a == b}")
    log(f"  {b}")
    r1, r2 = psql(RETENTION, "ednet"), psql(RETENTION, "ednet_restore")
    log(f"звіт про утримання збігається: {r1 == r2}")
