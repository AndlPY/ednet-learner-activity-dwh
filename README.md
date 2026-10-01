# EdNet Learner Activity DWH

PostgreSQL + dbt warehouse built on the [EdNet](https://github.com/riiid/ednet) dataset: 95M answers and 131M app events from Santa, a Korean TOEIC-prep app (784K learners, 2017–2019).

Raw zip archives go through profiling, a normalized core model and a dbt star schema. On top of that there are reports, access roles, backups and benchmarks. Next step is a product analytics layer (retention, funnel, Power BI).

## Results

- Retention report: 30 s on the normalized model, 0.86 s on the marts
- Learner history lookup: 2.8 s → 0.4 ms with a composite index on 131M rows
- Full mart rebuild with 18 dbt tests: 6.6 min
- Backup restore verified on all 22 tables (row counts + same report output)
- Retention recomputed independently in DuckDB from raw Parquet: matches in all 27 weeks

## How it's built

```
zip archives → Parquet (Python, DuckDB) → raw → core (SQL) → marts (dbt) → reports
```

- **raw** – typed copy of the source, duplicates included, so any step can be re-run without the archives
- **core** – 16 tables in BCNF with PK/FK/CHECK constraints. Solving sessions got their own table: in the flat source, session time repeats on every answer row and disagrees in 462K sessions. Keys are added after the bulk load.
- **marts** – `fct_answer`, `fct_user_day`, `agg_part_day`, `dim_user`, `dim_question`, `dim_date`

Data issues found during profiling and handled in `sql/load/10_core.sql`: ~461K duplicate events, ~0.7M repeated answers within a session (latest kept), `-1` used instead of NULL, inconsistent session times. A foreign key caught a bug in my own cleaning rule during the first full load.

## Benchmarks

Median of 3 warm runs, PostgreSQL 17.6, `pipeline/04_perf.py`:

| Report | core | marts |
|---|---:|---:|
| Weekly active learners | 5,502 ms | 479 ms |
| Retention by week | 30,101 ms | 863 ms |
| Accuracy by TOEIC part | 2,496 ms | 0.8 ms |
| Inactive learners | 3,167 ms | 44 ms |

## Access and backups

Three group roles: `loader` (raw, core), `transformer` (reads core, builds marts), `analyst` (reads marts, 60 s timeout). Passwords come from `.env`. Backups are `pg_dump` in directory format with 8 jobs; the restore goes into a separate database and is checked against the original.

## Running it

Needs PostgreSQL 17, Python 3.11 with `duckdb`, dbt-postgres 1.12, ~60 GB of disk.

```bash
cp .env.example .env                              # set passwords
python pipeline/01_zip_to_parquet.py C:/ednet     # archives from riiid/ednet
python pipeline/02_load.py C:/ednet               # raw → core, ~40 min
psql -d ednet -v etl_pw=... -v dbt_pw=... -v analyst_pw=... -f sql/admin/roles.sql
cd dbt && dbt build --profiles-dir .              # marts + tests, ~7 min
```

## License

Code is [MIT](LICENSE). EdNet is CC BY-NC 4.0 and isn't included here. Dataset paper: Choi et al., *EdNet: A Large-Scale Hierarchical Dataset in Education*, AIED 2020.
