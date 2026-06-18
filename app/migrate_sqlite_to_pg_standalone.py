"""
migrate_sqlite_to_pg_standalone.py
===================================
Standalone migration script: SQLite → PostgreSQL
- Reads column list from PostgreSQL schema so only matching columns are migrated
- Casts SQLite 0/1 integers to Python bool for PostgreSQL boolean columns
- Handles FK ordering by migrating independent tables first

Usage inside Docker container:
    python3 /tmp/migrate_sqlite_to_pg_standalone.py \
        --sqlite /tmp/production_sqlite_backup.db \
        --pg "postgresql://app_user:production_password@db:5432/production_db"
"""
import argparse
import sqlite3
import sys

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.extensions
except ImportError:
    print("[ERROR] psycopg2 not available.")
    sys.exit(1)


def get_pg_columns(pg_cursor, table: str) -> list[tuple[str, str]]:
    """Return list of (column_name, data_type) from PostgreSQL for a given table."""
    pg_cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    return pg_cursor.fetchall()


def get_sqlite_columns(sqlite_cursor, table: str) -> list[str]:
    """Return list of column names from SQLite for a given table."""
    sqlite_cursor.execute(f'PRAGMA table_info("{table}")')
    return [row[1] for row in sqlite_cursor.fetchall()]


def adapt_row(row: tuple, columns: list[str], pg_col_types: dict[str, str]) -> tuple:
    """Cast SQLite row values to PostgreSQL-compatible types."""
    result = []
    for col, val in zip(columns, row):
        pg_type = pg_col_types.get(col, "")
        if pg_type == "boolean" and isinstance(val, int):
            result.append(bool(val))
        else:
            result.append(val)
    return tuple(result)


def migrate(sqlite_path: str, pg_dsn: str) -> None:
    print(f"\n{'=' * 60}")
    print("  MIGRACIÓN SQLite → PostgreSQL (Standalone v2)")
    print(f"  Fuente: {sqlite_path}")
    print(f"{'=' * 60}\n")

    # ── Conectar SQLite ──────────────────────────────────────────────────────
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        print("[OK] Conectado a SQLite\n")
    except Exception as e:
        print(f"[ERROR] No se puede abrir SQLite: {e}")
        sys.exit(1)

    # ── Conectar PostgreSQL ──────────────────────────────────────────────────
    try:
        pg_conn = psycopg2.connect(pg_dsn)
        pg_conn.autocommit = False
        print("[OK] Conectado a PostgreSQL\n")
    except Exception as e:
        print(f"[ERROR] No se puede conectar a PostgreSQL: {e}")
        sys.exit(1)

    # ── Tablas SQLite ─────────────────────────────────────────────────────────
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    tables = [row[0] for row in sqlite_cursor.fetchall()]
    print(f"[INFO] Tablas encontradas en SQLite: {len(tables)}\n")

    # Migrate tables that are likely FK-independent first
    FK_PRIORITY = ["roles", "users", "support_departments", "support_priorities",
                   "support_status", "support_types", "logistics_routes",
                   "ai_functionalities", "audit_logs"]
    ordered_tables = [t for t in FK_PRIORITY if t in tables] + \
                     [t for t in tables if t not in FK_PRIORITY]

    results = []
    pg_cursor = pg_conn.cursor()

    for table in ordered_tables:
        # ── Columnas SQLite y filas ────────────────────────────────────────
        sqlite_cols = get_sqlite_columns(sqlite_cursor, table)

        sqlite_cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        src_count = sqlite_cursor.fetchone()[0]

        if src_count == 0:
            results.append((table, 0, 0, "SKIP (vacía)"))
            continue

        # ── Columnas PostgreSQL ────────────────────────────────────────────
        pg_cols_info = get_pg_columns(pg_cursor, table)
        if not pg_cols_info:
            results.append((table, src_count, 0, "ERROR: tabla no existe en PG"))
            continue

        pg_col_names = [c[0] for c in pg_cols_info]
        pg_col_types = {c[0]: c[1] for c in pg_cols_info}

        # ── Intersección de columnas (solo columnas que existen en ambos) ──
        common_cols = [c for c in sqlite_cols if c in pg_col_names]
        if not common_cols:
            results.append((table, src_count, 0, "ERROR: no hay columnas comunes"))
            continue

        # ── Revisar datos existentes ───────────────────────────────────────
        try:
            pg_cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            existing = pg_cursor.fetchone()[0]
        except Exception as e:
            pg_conn.rollback()
            results.append((table, src_count, 0, f"ERROR al contar: {e}"))
            continue

        if existing >= src_count:
            results.append((table, src_count, existing, "SKIP (ya sincronizada)"))
            continue

        # ── Insertar filas ─────────────────────────────────────────────────
        try:
            sel_cols = ", ".join([f'"{c}"' for c in common_cols])
            sqlite_cursor.execute(f'SELECT {sel_cols} FROM "{table}"')
            rows = sqlite_cursor.fetchall()

            col_list = ', '.join([f'"{c}"' for c in common_cols])
            placeholders = ', '.join(['%s'] * len(common_cols))
            insert_sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

            batch = []
            for row in rows:
                adapted = adapt_row(tuple(row), common_cols, pg_col_types)
                batch.append(adapted)
                if len(batch) >= 500:
                    psycopg2.extras.execute_batch(pg_cursor, insert_sql, batch)
                    batch = []

            if batch:
                psycopg2.extras.execute_batch(pg_cursor, insert_sql, batch)

            pg_conn.commit()

            pg_cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            final_count = pg_cursor.fetchone()[0]

            skipped_cols = [c for c in sqlite_cols if c not in pg_col_names]
            note = f" (ignoradas {len(skipped_cols)} cols extra: {','.join(skipped_cols[:3])})" if skipped_cols else ""
            status = ("OK" if final_count >= src_count else "WARN: conteo difiere") + note
            results.append((table, src_count, final_count, status))

        except Exception as e:
            pg_conn.rollback()
            results.append((table, src_count, 0, f"ERROR: {str(e).split(chr(10))[0][:80]}"))

    # ── Resumen ──────────────────────────────────────────────────────────────
    print(f"\n{'=' * 76}")
    print(f"  {'Tabla':<38} {'SQLite':>8} {'PG':>8}  Estado")
    print(f"  {'-' * 72}")
    errors = 0
    for table, src, pg, status in results:
        mark = "✅" if "OK" in status or "SKIP" in status else "⚠️ " if "WARN" in status else "❌"
        print(f"  {mark} {table:<38} {src:>8} {pg:>8}  {status}")
        if "ERROR" in status:
            errors += 1

    print(f"\n{'=' * 76}")
    print(f"  Tablas procesadas : {len(results)}")
    print(f"  Tablas con error  : {errors}")

    if errors:
        print("\n[ADVERTENCIA] Algunas tablas tuvieron errores.")
        sys.exit(1)
    else:
        print("\n[ÉXITO] Migración completada sin errores.\n")

    pg_cursor.close()
    pg_conn.close()
    sqlite_conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migracion SQLite -> PostgreSQL (Standalone v2)")
    parser.add_argument("--sqlite", required=True, help="Ruta al archivo production.db de SQLite")
    parser.add_argument("--pg", required=True, help="URL de conexión a PostgreSQL")
    args = parser.parse_args()
    migrate(args.sqlite, args.pg)
