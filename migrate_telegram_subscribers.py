#!/usr/bin/env python3
"""
migrate_telegram_subscribers.py
Crea la tabla telegram_subscribers en la base de datos de producción.
Ejecutar desde el servidor o localmente apuntando a la DB correcta.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("migrate_telegram")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./production.db")


def run_migration():
    engine = create_engine(DATABASE_URL)
    
    create_sql = """
    CREATE TABLE IF NOT EXISTS telegram_subscribers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        chat_id     TEXT    NOT NULL,
        report_type TEXT    DEFAULT 'MP',
        is_active   INTEGER DEFAULT 1,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # PostgreSQL variant (usa SERIAL)
    create_sql_pg = """
    CREATE TABLE IF NOT EXISTS telegram_subscribers (
        id          SERIAL PRIMARY KEY,
        name        TEXT    NOT NULL,
        chat_id     TEXT    NOT NULL,
        report_type TEXT    DEFAULT 'MP',
        is_active   BOOLEAN DEFAULT TRUE,
        created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    try:
        with engine.connect() as conn:
            if "postgresql" in DATABASE_URL.lower():
                conn.execute(text(create_sql_pg))
                log.info("Tabla telegram_subscribers creada en PostgreSQL ✅")
            else:
                conn.execute(text(create_sql))
                log.info("Tabla telegram_subscribers creada en SQLite ✅")
            conn.commit()

            # Insertar suscriptor inicial de ejemplo
            check = conn.execute(text("SELECT COUNT(*) as c FROM telegram_subscribers")).fetchone()
            if check.c == 0:
                conn.execute(text("""
                    INSERT INTO telegram_subscribers (name, chat_id, report_type, is_active)
                    VALUES ('Gerencia - Delicias de Belén', '+584126036358', 'MP', 1)
                """))
                conn.commit()
                log.info("Suscriptor inicial creado: +584126036358 ✅")
            else:
                log.info(f"La tabla ya tiene {check.c} suscriptor(es), no se inserta el inicial.")

        log.info("Migración completada exitosamente 🎉")
    except Exception as e:
        log.error(f"Error en migración: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 55)
    print("  Migración: telegram_subscribers")
    print(f"  DB: {DATABASE_URL[:60]}...")
    print("=" * 55)
    run_migration()
