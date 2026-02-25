"""
stitch_sync.py
Integración de production-report con Stitch Import API (stitchdata.com)
Sincroniza tablas clave de PostgreSQL hacia el data warehouse Stitch.

Instalación:
    pip install python-stitch-client python-dotenv sqlalchemy psycopg2-binary

Uso:
    python stitch_sync.py                  # Sync completo
    python stitch_sync.py --table dispatch # Solo tabla dispatch
    python stitch_sync.py --dry-run        # Validar sin enviar
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN — establecer en variables de entorno o .env
# ─────────────────────────────────────────────────────────────
STITCH_CLIENT_ID = int(os.getenv("STITCH_CLIENT_ID", "0"))
STITCH_TOKEN = os.getenv("STITCH_TOKEN", "")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://app_user:production_password@localhost:5434/production_db",
)

# Tablas a sincronizar con Stitch
# Formato: { tabla_origen: { "key_names": [...], "sequence_col": "..." } }
TABLES_CONFIG = {
    "logistics_dispatch": {
        "key_names": ["id"],
        "sequence_col": "created_at",
        "description": "Despachos logísticos",
    },
    "production_planning": {
        "key_names": ["id"],
        "sequence_col": "created_at",
        "description": "Planificación de producción",
    },
    "production_reports": {
        "key_names": ["id"],
        "sequence_col": "fecha",
        "description": "Reportes de producción",
    },
    "logistics_inventory": {
        "key_names": ["id"],
        "sequence_col": "created_at",
        "description": "Inventario logístico",
    },
    "ai_audit_log": {
        "key_names": ["id"],
        "sequence_col": "created_at",
        "description": "Logs de auditoría IA",
    },
}


def get_engine():
    """Crear motor SQLAlchemy para PostgreSQL."""
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def fetch_table_rows(table: str, sequence_col: str, since: str | None = None) -> Generator[dict[str, Any], None, None]:
    """Leer filas de una tabla PostgreSQL, opcionalmente desde una fecha."""
    engine = get_engine()
    with engine.connect() as conn:
        if since:
            stmt = text(f"SELECT * FROM {table} WHERE {sequence_col} > :since ORDER BY {sequence_col}")
            result = conn.execute(stmt, {"since": since})
        else:
            stmt = text(f"SELECT * FROM {table} ORDER BY {sequence_col}")
            result = conn.execute(stmt)

        cols = list(result.keys())
        for row in result:
            record = dict(zip(cols, row))
            # Serializar tipos no-JSON
            for k, v in record.items():
                if isinstance(v, datetime):
                    record[k] = v.isoformat()
            yield record


def push_to_stitch(
    table_name: str,
    records: list[dict],
    key_names: list[str],
    dry_run: bool = False,
) -> int:
    """Enviar registros a Stitch Import API."""
    if not records:
        log.info(f"  [{table_name}] Sin registros para sincronizar")
        return 0

    if dry_run:
        log.info(f"  [{table_name}] DRY RUN — {len(records)} registros NO enviados")
        return len(records)

    try:
        import singer  # type: ignore
    except ImportError:
        log.warning("  'singer-python' no instalado. Usando python-stitch-client.")

    try:
        from stitchclient import Client  # type: ignore

        with Client(STITCH_CLIENT_ID, STITCH_TOKEN) as client:
            sequence = int(datetime.now(timezone.utc).timestamp() * 1000)
            for i, record in enumerate(records):
                client.push(
                    {
                        "action": "upsert",
                        "table_name": table_name,
                        "sequence": sequence + i,
                        "key_names": key_names,
                        "data": record,
                    }
                )
        log.info(f"  [{table_name}] ✅ {len(records)} registros enviados a Stitch")
        return len(records)

    except ImportError:
        log.error("  Instala: pip install python-stitch-client")
        log.info(f"  [{table_name}] Muestra de datos (primeros 2):")
        for r in records[:2]:
            log.info(f"    {r}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Sincronizar datos con Stitch")
    parser.add_argument("--table", help="Sincronizar solo esta tabla", default=None)
    parser.add_argument("--since", help="Fecha mínima ISO 8601 (ej: 2026-01-01)", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar datos, no enviar")
    args = parser.parse_args()

    if not STITCH_TOKEN and not args.dry_run:
        log.warning("⚠️  STITCH_TOKEN no configurado. Ejecutando en modo dry-run.")
        args.dry_run = True

    tables = {args.table: TABLES_CONFIG[args.table]} if args.table else TABLES_CONFIG
    total_synced = 0

    log.info("=" * 50)
    log.info("  Stitch Sync — production-report → Data Warehouse")
    log.info("=" * 50)
    log.info(f"  Tablas: {list(tables.keys())}")
    log.info(f"  Dry run: {args.dry_run}")
    if args.since:
        log.info(f"  Desde: {args.since}")
    log.info("")

    for table, config in tables.items():
        log.info(f"📤 Sincronizando: {table} ({config['description']})")
        try:
            records = list(fetch_table_rows(table, config["sequence_col"], args.since))
            log.info(f"  Registros encontrados: {len(records)}")
            count = push_to_stitch(table, records, config["key_names"], args.dry_run)
            total_synced += count
        except Exception as e:
            log.error(f"  ❌ Error en {table}: {e}")

    log.info("")
    log.info(f"✅ Sincronización completada. Total: {total_synced} registros")


if __name__ == "__main__":
    main()
