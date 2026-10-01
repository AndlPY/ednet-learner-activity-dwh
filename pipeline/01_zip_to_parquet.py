"""EdNet: архіви (один CSV на користувача) → один Parquet на рівень, з колонкою user_id.

Розпаковувати ~1 млн дрібних файлів на диск не потрібно: архів читається потоком,
членами паралельно в N процесах, кожен пише свій CSV-фрагмент; DuckDB зводить фрагменти в Parquet.
Запуск: python pipeline/01_zip_to_parquet.py C:/ednet
"""
import sys, os, time, zipfile
from multiprocessing import Pool
from pathlib import Path
import duckdb

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "C:/ednet")
OUT = RAW / "parquet"
WORKERS = min(6, os.cpu_count())   # кожен процес тримає каталог архіву (~0,5 ГБ на 784 тис. записів)

LEVELS = {
    "KT1": ("kt1.zip", "user_id BIGINT, ts BIGINT, solving_id BIGINT, question_id VARCHAR, user_answer VARCHAR, elapsed_time BIGINT"),
    "KT4": ("kt4.zip", "user_id BIGINT, ts BIGINT, action_type VARCHAR, item_id VARCHAR, cursor_time BIGINT, source VARCHAR, user_answer VARCHAR, platform VARCHAR"),
}


def work(args):
    zip_path, members, part_path = args
    z = zipfile.ZipFile(zip_path)
    rows = 0
    with open(part_path, "wb") as out:
        for name in members:
            uid = name.rsplit("/", 1)[1][1:-4].encode()          # KT1/u246317.csv → 246317
            lines = z.read(name).split(b"\n")[1:]                   # без заголовка
            out.write(b"".join(uid + b"," + l.rstrip(b"\r") + b"\n" for l in lines if l.strip()))
            rows += sum(1 for l in lines if l.strip())
    return rows, len(members)


def convert(level):
    zip_name, schema = LEVELS[level]
    zip_path = RAW / zip_name
    parts = RAW / f"parts_{level}"
    parts.mkdir(exist_ok=True)
    members = [n for n in zipfile.ZipFile(zip_path).namelist() if n.endswith(".csv")]
    chunks = [members[i::WORKERS * 4] for i in range(WORKERS * 4)]
    t = time.time()
    with Pool(WORKERS) as p:
        res = p.map(work, [(zip_path, c, parts / f"p{i:03}.csv") for i, c in enumerate(chunks)])
    rows = sum(r for r, _ in res)
    print(f"{level}: {len(members)} файлів, {rows} рядків, {time.time() - t:.0f} с на розбір архіву")
    OUT.mkdir(exist_ok=True)
    cols = ", ".join(f"'{c.split()[0]}': '{c.split()[1]}'" for c in schema.split(", "))
    t = time.time()
    duckdb.sql(f"""COPY (SELECT * FROM read_csv('{parts.as_posix()}/*.csv', header=false, columns={{{cols}}}, nullstr=''))
                   TO '{(OUT / f"{level.lower()}.parquet").as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    print(f"{level}: Parquet за {time.time() - t:.0f} с")
    for f in parts.glob("*.csv"):
        f.unlink()
    parts.rmdir()


def contents():
    z = zipfile.ZipFile(RAW / "contents.zip")
    (RAW / "contents").mkdir(exist_ok=True)
    for n in z.namelist():
        if n.startswith("contents/") and n.endswith(".csv"):
            (RAW / "contents" / Path(n).name).write_bytes(z.read(n))


if __name__ == "__main__":
    contents()
    for level in (sys.argv[2:] or ["KT1", "KT4"]):
        convert(level)
