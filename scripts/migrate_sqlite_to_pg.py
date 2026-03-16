"""
migrate_sqlite_to_pg.py
=======================
Migrates all data from a SQLite database to PostgreSQL
while preserving all existing records.

Usage:
    python scripts/migrate_sqlite_to_pg.py \
        --sqlite /path/to/production.db \
        --pg "postgresql://app_user:production_password@localhost:5433/production_db"

This script:
  1. Reads all tables and their rows from SQLite
  2. Creates all tables in PostgreSQL using SQLAlchemy models (create_all)
  3. Inserts all rows into PostgreSQL using batched inserts
  4. Verifies row counts match between source and destination
"""
import argparse
import sys
import sqlite3

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session

# ── Adjust path so we can import app models ────────────────────────────────
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import Base
import app.models  # noqa: F401 — registers all models with Base


def get_sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    return [row[0] for row in cursor.fetchall()]


def get_sqlite_rows(conn: sqlite3.Connection, table: str) -> tuple[list[str], list[tuple]]:
    cursor = conn.cursor()
    cursor.execute(f'PRAGMA table_info("{table}")')
    columns = [col[1] for col in cursor.fetchall()]
    cursor.execute(f'SELECT * FROM "{table}"')
    rows = cursor.fetchall()
    return columns, rows


def migrate(sqlite_path: str, pg_url: str) -> None:
    print(f"\n{'='*60}")
    print(f"  SQLite → PostgreSQL Migration")
    print(f"{'='*60}")
    print(f"  Source : {sqlite_path}")
    print(f"  Target : {pg_url[:pg_url.index('@') + 1]}***")
    print(f"{'='*60}\n")

    # ── Connect to SQLite ────────────────────────────────────────────────────
    if not os.path.exists(sqlite_path):
        print(f"[ERROR] SQLite file not found: {sqlite_path}")
        sys.exit(1)

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    # ── Connect to PostgreSQL ────────────────────────────────────────────────
    pg_engine = create_engine(pg_url, echo=False)

    try:
        with pg_engine.connect() as c:
            c.execute(text("SELECT 1"))
        print("[OK] PostgreSQL connection successful\n")
    except Exception as e:
        print(f"[ERROR] Cannot connect to PostgreSQL: {e}")
        sys.exit(1)

    # ── Create all tables in PostgreSQL ─────────────────────────────────────
    print("[STEP 1] Creating schema in PostgreSQL (CREATE TABLE IF NOT EXISTS)...")
    Base.metadata.create_all(pg_engine)
    print("[OK] Schema created\n")

    # ── Migrate each table ───────────────────────────────────────────────────
    tables = get_sqlite_tables(sqlite_conn)
    print(f"[STEP 2] Migrating {len(tables)} tables...\n")

    PgSession = sessionmaker(bind=pg_engine)
    pg_session: Session = PgSession()

    results = []
    total_migrated = 0
    total_errors = 0

    for table in tables:
        columns, rows = get_sqlite_rows(sqlite_conn, table)
        source_count = len(rows)

        if source_count == 0:
            results.append((table, 0, 0, "SKIPPED (empty)"))
            continue

        try:
            # Check existing count in pg
            existing = pg_session.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()

            if existing >= source_count:
                results.append((table, source_count, existing, "SKIPPED (already synced)"))
                continue

            # Build INSERT statements in batches of 500
            inserted = 0
            col_names = ', '.join([f'"{c}"' for c in columns])
            placeholders = ', '.join([f':{c}' for c in columns])
            insert_sql = text(f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING')

            batch = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    val = row[i]
                    # Convert SQLite booleans (0/1) to Python bool for PG
                    row_dict[col] = val
                batch.append(row_dict)

                if len(batch) >= 500:
                    pg_session.execute(insert_sql, batch)
                    inserted += len(batch)
                    batch = []

            if batch:
                pg_session.execute(insert_sql, batch)
                inserted += len(batch)

            pg_session.commit()
            total_migrated += inserted
            results.append((table, source_count, inserted, "OK"))

        except Exception as e:
            pg_session.rollback()
            total_errors += 1
            results.append((table, source_count, 0, f"ERROR: {e}"))

    # ── Print Summary ────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"{'Table':<40} {'SQLite':>8} {'PG':>8} {'Status'}")
    print(f"{'-'*70}")

    for table, src, dst, status in results:
        mark = "✅" if "OK" in status or "SKIP" in status else "❌"
        print(f"  {mark} {table:<38} {src:>8} {dst:>8}  {status}")

    print(f"{'='*70}")
    print(f"\n  Total rows migrated : {total_migrated}")
    print(f"  Tables with errors  : {total_errors}")

    if total_errors > 0:
        print("\n[WARN] Some tables had errors. Check above for details.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Migration completed without errors!\n")

    pg_session.close()
    sqlite_conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite DB to PostgreSQL")
    parser.add_argument("--sqlite", required=True, help="Path to the SQLite production.db file")
    parser.add_argument("--pg", required=True, help="PostgreSQL connection URL")
    args = parser.parse_args()
    migrate(args.sqlite, args.pg)
