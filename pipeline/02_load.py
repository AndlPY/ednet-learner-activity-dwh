"""Завантаження: Parquet → raw (DuckDB, бінарний COPY) → core (SQL у PostgreSQL) → ключі.

Кожен крок з таймінгом пишеться в logs/load.log — ці числа наводяться в п. 3.1 курсової.
Запуск: python pipeline/02_load.py C:/ednet
Змінні середовища: PGHOST, PGPORT (5433), PGUSER, PGPASSWORD, PGDATABASE (ednet), PSQL — шлях до psql.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import duckdb

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "C:/ednet")
ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "load.log"
LOG.parent.mkdir(exist_ok=True)
ENV = {**os.environ, "PGHOST": os.getenv("PGHOST", "localhost"), "PGPORT": os.getenv("PGPORT", "5433"),
       "PGUSER": os.getenv("PGUSER", "postgres"), "PGPASSWORD": os.getenv("PGPASSWORD", "postgres"),
       "PGDATABASE": os.getenv("PGDATABASE", "ednet"), "PGCLIENTENCODING": "UTF8"}
PSQL = os.getenv("PSQL", "C:/ednet/pg/pgsql/bin/psql.exe")


def log(msg):
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def psql(file):
    t = time.time()
    out = subprocess.run([PSQL, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", "\\timing on", "-f", str(file)],
                         env=ENV, capture_output=True, text=True, encoding="utf-8")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(out.stdout + out.stderr)
    if out.returncode:
        log(f"ПОМИЛКА {file.name}: {out.stderr.strip()[-500:]}")
        sys.exit(1)
    log(f"{file.name}: {time.time() - t:.0f} с")


def load_raw():
    con = duckdb.connect()
    con.sql("INSTALL postgres; LOAD postgres; SET threads = 8")
    dsn = " ".join(f"{k}={ENV['PG' + k.upper()]}" for k in ("host", "port", "user", "password")) + f" dbname={ENV['PGDATABASE']}"
    con.sql(f"ATTACH '{dsn}' AS pg (TYPE postgres)")
    for level in ("kt1", "kt4"):
        t = time.time()
        con.sql(f"INSERT INTO pg.raw.{level} SELECT * FROM read_parquet('{(RAW / 'parquet' / f'{level}.parquet').as_posix()}')")
        log(f"raw.{level}: {time.time() - t:.0f} с")
    for name in ("questions", "lectures", "payments", "coupons"):
        con.sql(f"INSERT INTO pg.raw.{name} SELECT * FROM read_csv('{(RAW / 'contents' / f'{name}.csv').as_posix()}', header=true, all_varchar=true)")
    log("raw.довідники: готово")


if __name__ == "__main__":
    steps = sys.argv[2:] or ["raw", "core"]
    t0 = time.time()
    if "raw" in steps:
        psql(ROOT / "sql/ddl/01_schemas_raw.sql")
        load_raw()
        subprocess.run([PSQL, "-X", "-q", "-c", "ANALYZE raw.kt1; ANALYZE raw.kt4;"], env=ENV)
    if "core" in steps:
        psql(ROOT / "sql/ddl/02_core.sql")
        psql(ROOT / "sql/load/10_core.sql")
        psql(ROOT / "sql/ddl/03_core_keys.sql")
    log(f"усього: {time.time() - t0:.0f} с")
