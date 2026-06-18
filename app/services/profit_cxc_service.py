"""
Servicio Profit Plus CXC — BD carmal_a (192.168.60.15)
Tablas reales descubiertas:
  saFacturaVenta   → cabecera de facturas (doc_num, co_cli, total_neto, saldo, fec_emis, status, anulado)
  saCobro          → cobros registrados   (cob_num, co_cli, fecha, monto)
  saCobroTPReng    → formas de pago       (forma_pag, num_doc, mont_doc, co_ban)
  saCobroDocReng   → relación cobro-factura
  saCliente        → maestro de clientes  (co_cli, cli_des, rif_ci, tlf_cli)
"""
import pyodbc
import logging
from typing import List, Dict, Optional, Any
import os
import re

logger = logging.getLogger(__name__)

PROFIT_HOST = os.getenv("SQLSRV_HOST_CXC", "192.168.60.15")
PROFIT_DB   = "carmal_a"
PROFIT_USER = "profit"
PROFIT_PWD  = "profit"

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={PROFIT_HOST};"
    f"DATABASE={PROFIT_DB};"
    f"UID={PROFIT_USER};"
    f"PWD={PROFIT_PWD};"
    "Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=10;"
)

TOLERANCIA_BS = 1.0  # diferencia aceptable en Bs. para considerar montos iguales


def _get_conn():
    return pyodbc.connect(CONN_STR, timeout=10)


def _row_to_dict(cur, row) -> Dict:
    return {col[0].lower(): (float(v) if isinstance(v, __import__('decimal').Decimal) else v)
            for col, v in zip(cur.description, row)}


# ─────────────────────────────────────────────────────────────
# CONECTIVIDAD
# ─────────────────────────────────────────────────────────────

def test_connection() -> bool:
    try:
        conn = _get_conn()
        conn.cursor().execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Profit connection failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# TASAS DE CAMBIO — saTasa (co_mone, fecha, tasa_c)
# ─────────────────────────────────────────────────────────────

def get_tasas_por_fechas(
    fechas: List[str],
    co_mone: str = "USD"
) -> Dict[str, float]:
    """
    Para cada fecha de cobro FM, retorna la tasa oficial de Profit (saTasa).
    Si no existe la tasa exacta para ese día, usa la más reciente anterior.

    Args:
        fechas:   Lista de fechas en formato 'YYYY-MM-DD' (o datetime ISO).
        co_mone:  Código de moneda en Profit (default 'USD' = Dólar BCV).

    Returns:
        Dict { 'YYYY-MM-DD': tasa_float }
    """
    if not fechas:
        return {}

    from datetime import datetime, timedelta

    # Normalizar a YYYY-MM-DD y deduplicar
    fechas_norm = sorted({f[:10] for f in fechas if f and len(f) >= 10})
    if not fechas_norm:
        return {}

    min_fecha = fechas_norm[0]
    max_fecha = fechas_norm[-1]

    # Buffer de 30 días previos para garantizar fallback
    min_buf = (
        datetime.strptime(min_fecha, "%Y-%m-%d") - timedelta(days=30)
    ).strftime("%Y-%m-%d")

    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute(
            """
            SELECT CONVERT(date, fecha) AS dia, tasa_c
            FROM   saTasa
            WHERE  co_mone = ?
              AND  fecha   >= ?
              AND  fecha   <= DATEADD(day, 1, CONVERT(datetime, ?))
            ORDER  BY dia ASC
            """,
            (co_mone, min_buf, max_fecha),
        )
        # Dict de tasas disponibles: {'2026-05-15': 515.18, ...}
        tasas_raw = {}
        for row in cur.fetchall():
            dia_str = str(row[0])[:10]   # 'YYYY-MM-DD'
            tasas_raw[dia_str] = float(row[1])
        conn.close()

        if not tasas_raw:
            logger.warning(f"saTasa: sin datos para co_mone={co_mone} en rango {min_buf}…{max_fecha}")
            return {}

        # Para cada fecha solicitada, tomar la tasa exacta o la más reciente anterior
        fechas_disponibles = sorted(tasas_raw.keys())
        resultado: Dict[str, float] = {}

        for fecha in fechas_norm:
            if fecha in tasas_raw:
                resultado[fecha] = tasas_raw[fecha]
            else:
                # Tasa más reciente anterior a esta fecha
                anteriores = [f for f in fechas_disponibles if f <= fecha]
                if anteriores:
                    resultado[fecha] = tasas_raw[anteriores[-1]]
                else:
                    logger.warning(f"saTasa: sin tasa para {fecha} (co_mone={co_mone})")

        logger.info(
            f"saTasa: tasas cargadas para {len(resultado)} fechas "
            f"(co_mone={co_mone}, rango {min_fecha}…{max_fecha})"
        )
        return resultado

    except Exception as e:
        logger.error(f"get_tasas_por_fechas error: {e}")
        return {}




# ─────────────────────────────────────────────────────────────
# FASE 1 — CRUCE DE IDENTIDAD: cod_cliente (FM) → co_cli (Profit)
# ─────────────────────────────────────────────────────────────
# Según el documento API de FM:
#   Pedidos  → campo: codigo_cliente   (ID del cliente en sistema administrativo)
#   Recibos  → campo: cod_cliente      (código único del cliente en sistema central)
# Ese código ES el co_cli de Profit Plus. El cruce es directo.

def buscar_cliente_por_rif(rif: str = "", nombre: str = "", telefono: str = "") -> Optional[Dict]:
    """
    Dado un dato de FM (RIF, nombre o teléfono), retorna el co_cli de Profit.
    Prioridad: rif exacto → rif parcial → nombre → teléfono.
    El campo RIF en FM puede venir como 'J-123456', 'V-12345678' o solo números.
    """
    if not any([rif, nombre, telefono]):
        return None

    try:
        conn = _get_conn()
        cur  = conn.cursor()

        # Normalizar RIF (quitar V-, J-, E-, G-, separadores)
        rif_num = re.sub(r'[^0-9]', '', rif) if rif else ""
        rif_clean = rif.upper().strip() if rif else ""

        # 1. RIF exacto o parcial (co_cli en Profit es el RIF/Cédula fiscal)
        if rif_num:
            cur.execute("""
                SELECT TOP 1 co_cli, cli_des, rif_ci, tlf_cli
                FROM saCliente
                WHERE REPLACE(REPLACE(REPLACE(rif_ci,'-',''),'V',''),'J','') LIKE ?
                   OR rif_ci LIKE ?
                ORDER BY co_cli
            """, (f"%{rif_num}%", f"%{rif_clean}%"))
            row = cur.fetchone()
            if row:
                conn.close()
                return _row_to_dict(cur, row)

        # 2. Por nombre (primeras 2 palabras)
        if nombre and len(nombre) >= 4:
            words = nombre.strip().split()[:2]
            like  = "%" + " ".join(words) + "%"
            cur.execute("""
                SELECT TOP 1 co_cli, cli_des, rif_ci, tlf_cli
                FROM saCliente WHERE cli_des LIKE ? ORDER BY co_cli
            """, (like,))
            row = cur.fetchone()
            if row:
                conn.close()
                return _row_to_dict(cur, row)

        # 3. Por teléfono (8 últimos dígitos)
        if telefono:
            tel_num = re.sub(r'[^0-9]', '', telefono)[-8:]
            cur.execute("""
                SELECT TOP 1 co_cli, cli_des, rif_ci, tlf_cli
                FROM saCliente WHERE REPLACE(tlf_cli,' ','') LIKE ? ORDER BY co_cli
            """, (f"%{tel_num}%",))
            row = cur.fetchone()
            if row:
                conn.close()
                return _row_to_dict(cur, row)

        conn.close()
        return None
    except Exception as e:
        logger.error(f"buscar_cliente_por_rif error: {e}")
        return None

# Alias para compatibilidad
buscar_cliente_por_cedula = buscar_cliente_por_rif


def get_catalogo_vendedores() -> Dict[str, str]:
    """
    Retorna todos los vendedores activos de Profit como {co_ven: ven_des}.
    co_ven es el código del vendedor (ej: 'V033', 'A001').
    ven_des es la descripción/nombre del vendedor.
    """
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute("""
            SELECT co_ven, ven_des
            FROM saVendedor
            WHERE inactivo = 0 OR inactivo IS NULL
            ORDER BY co_ven
        """)
        rows = cur.fetchall()
        conn.close()
        return {str(r[0]).strip(): str(r[1]).strip() for r in rows if r[0] and r[1]}
    except Exception as e:
        logger.error(f"get_catalogo_vendedores error: {e}")
        return {}


def get_nombres_clientes_lote(codigos: List[str]) -> Dict[str, Dict]:
    """
    Dado una lista de cod_cliente (co_cli de Profit / cod_cliente de FM),
    retorna un dict { co_cli: {nombre, rif, telefono} } en UNA sola consulta SQL.
    Úsalo para enriquecer los recibos de FM con datos reales del cliente.
    """
    if not codigos:
        return {}

    codigos_uniq = list({str(c).strip() for c in codigos if c})
    if not codigos_uniq:
        return {}

    try:
        conn = _get_conn()
        cur  = conn.cursor()

        placeholders = ",".join("?" * len(codigos_uniq))
        cur.execute(
            f"SELECT co_cli, cli_des, rif, telefonos "
            f"FROM saCliente WHERE co_cli IN ({placeholders})",
            codigos_uniq,
        )
        rows = cur.fetchall()
        conn.close()
        return {
            str(row[0]).strip(): {
                "nombre":   str(row[1]).strip() if row[1] else "",
                "rif":      str(row[2]).strip() if row[2] else "",
                "telefono": str(row[3]).strip() if row[3] else "",
            }
            for row in rows
        }

    except Exception as e:
        logger.error(f"get_nombres_clientes_lote error: {e}")
        return {}


# ─────────────────────────────────────────────────────────────
# FASE 2 — FACTURAS PENDIENTES POR CLIENTE
# ─────────────────────────────────────────────────────────────

def get_facturas_por_cliente(co_cli: str) -> List[Dict]:
    """
    Retorna facturas con saldo pendiente de un cliente usando saFacturaVenta.
    """
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute("""
            SELECT TOP 50
                f.doc_num,
                f.co_cli,
                ISNULL(c.cli_des, f.co_cli)  AS nombre_cliente,
                CONVERT(varchar, f.fec_emis, 23) AS fecha,
                ISNULL(f.total_neto, 0)       AS monto_total,
                ISNULL(f.saldo, 0)            AS saldo_pendiente,
                f.status,
                f.anulado,
                ISNULL(f.co_mone, 'VES')      AS moneda
            FROM saFacturaVenta f
            LEFT JOIN saCliente c ON c.co_cli = f.co_cli
            WHERE f.co_cli = ?
              AND ISNULL(f.anulado, 0) = 0
              AND f.status NOT IN ('A','C')
              AND ISNULL(f.saldo, 0) > 0
            ORDER BY f.fec_emis DESC
        """, (co_cli,))
        rows = cur.fetchall()
        result = [_row_to_dict(cur, r) for r in rows]
        conn.close()
        return result
    except Exception as e:
        logger.error(f"get_facturas_por_cliente({co_cli}) error: {e}")
        return []


def get_resumen_cxc_cliente(co_cli: str,
                             rif: str = "",
                             cedula: str = "",   # alias de rif
                             nombre: str = "",
                             telefono: str = "") -> Dict:
    """
    Resumen CxC de un cliente.
    Según el doc de FM: cod_cliente / codigo_cliente es el co_cli de Profit.
    El cruce es DIRECTO: FM.cod_cliente == Profit.co_cli.
    Si co_cli no viene o falla, fallback por rif/nombre/teléfono.
    """
    rif_efectivo = rif or cedula
    cliente_info = None

    # Intento 1: cruce directo FM.cod_cliente → Profit.co_cli
    if co_cli and not co_cli.startswith('CLI'):
        facturas = get_facturas_por_cliente(co_cli)
        if facturas:
            return {
                "co_cli":    co_cli,
                "rif":       rif_efectivo,
                "cedula":    rif_efectivo,
                "nombre":    nombre,
                "total_facturas":  len(facturas),
                "total_adeudado":  round(sum(float(f.get('saldo_pendiente') or 0) for f in facturas), 2),
                "moneda":    facturas[0].get('moneda', 'VES') if facturas else 'VES',
                "facturas":  [
                    {
                        "nro_factura":     str(f.get('doc_num', '')),
                        "fecha":           str(f.get('fecha', '')),
                        "monto_total":     float(f.get('monto_total') or 0),
                        "saldo_pendiente": float(f.get('saldo_pendiente') or 0),
                        "tipo_doc":        'FA',
                        "estatus":         str(f.get('status', 'P')),
                    }
                    for f in facturas
                ],
                "cliente_encontrado": True,
            }

    # Intento 2: fallback por RIF/nombre/teléfono
    if not co_cli or co_cli.startswith('CLI'):
        cliente_info = buscar_cliente_por_rif(rif_efectivo, nombre, telefono)
        if cliente_info:
            co_cli = cliente_info['co_cli']
        else:
            return {
                "co_cli": co_cli, "rif": rif_efectivo, "cedula": rif_efectivo,
                "nombre": nombre,
                "total_facturas": 0, "total_adeudado": 0.0,
                "moneda": "VES", "facturas": [],
                "cliente_encontrado": False,
            }

    facturas = get_facturas_por_cliente(co_cli)
    total    = sum(float(f.get('saldo_pendiente') or 0) for f in facturas)

    return {
        "co_cli":    co_cli,
        "nombre":    (cliente_info or {}).get('cli_des', nombre) or nombre,
        "rif":       (cliente_info or {}).get('rif_ci',  rif_efectivo) or rif_efectivo,
        "cedula":    (cliente_info or {}).get('rif_ci',  rif_efectivo) or rif_efectivo,
        "total_facturas":  len(facturas),
        "total_adeudado":  round(total, 2),
        "moneda":    facturas[0].get('moneda', 'VES') if facturas else 'VES',
        "facturas":  [
            {
                "nro_factura":    str(f.get("doc_num", "")),
                "fecha":          str(f.get("fecha", "")),
                "monto_total":    float(f.get("monto_total") or 0),
                "saldo_pendiente": float(f.get("saldo_pendiente") or 0),
                "tipo_doc":       "FA",
                "estatus":        str(f.get("status", "P")),
            }
            for f in facturas
        ],
        "cliente_encontrado": True,
    }


# ─────────────────────────────────────────────────────────────
# FASE 2 — COBROS REGISTRADOS EN PROFIT
# ─────────────────────────────────────────────────────────────

def get_cobros_profit(co_cli: str, fecha_desde: str = "", fecha_hasta: str = "") -> List[Dict]:
    """
    Cobros ya registrados en Profit para un cliente (saCobro + saCobroTPReng).
    Incluye la referencia bancaria (num_doc) para cruzar con el banco.
    """
    try:
        conn = _get_conn()
        cur  = conn.cursor()

        fecha_filter = ""
        params = [co_cli]
        if fecha_desde:
            fecha_filter += " AND c.fecha >= ?"
            params.append(fecha_desde)
        if fecha_hasta:
            fecha_filter += " AND c.fecha <= ?"
            params.append(fecha_hasta)

        cur.execute(f"""
            SELECT
                c.cob_num,
                c.co_cli,
                CONVERT(varchar, c.fecha, 23) AS fecha,
                ISNULL(c.monto, 0)            AS monto,
                tp.forma_pag,
                tp.num_doc                    AS referencia_banco,
                ISNULL(tp.mont_doc, 0)        AS monto_doc,
                tp.co_ban
            FROM saCobro c
            LEFT JOIN saCobroTPReng tp ON tp.cob_num = c.cob_num
            WHERE c.co_cli = ?
              AND ISNULL(c.anulado, 0) = 0
              {fecha_filter}
            ORDER BY c.fecha DESC
        """, params)

        rows = cur.fetchall()
        result = [_row_to_dict(cur, r) for r in rows]
        conn.close()
        return result
    except Exception as e:
        logger.error(f"get_cobros_profit({co_cli}) error: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# FASE 2 — MOTOR DE CONCILIACIÓN TRIPLE
# ─────────────────────────────────────────────────────────────

def conciliar_triple(
    pago_fm:      Dict,            # dict normalizado de FM (con tasa, monto_usd, tipo_pago)
    profit_data:  Dict,            # resultado de get_resumen_cxc_cliente
    banco_data:   Dict,            # resultado de validar_pago_fm
) -> Dict:
    """
    Etapa 3 del flujo: cruza FM + Banco + Profit y emite el veredicto.

    Escenarios:
      A — FM = Profit = Banco (o efectivo + Profit)  → completado  🟢
      B — FM < Profit, Banco OK                      → abono       🟡
      C — FM = Profit, Banco ≠                       → dif_banco   🔴
      D — Sin cobro en Profit pero banco confirma    → aplicar_cobro🟡
      E — Sin confirmación bancaria                  → pendiente   🟡
      F — Efectivo sin cobro en Profit               → pendiente   🟡
    """
    monto_fm    = float(pago_fm.get("monto", 0))
    monto_usd   = float(pago_fm.get("monto_usd", 0))
    tasa        = float(pago_fm.get("tasa", 0))
    tipo_pago   = pago_fm.get("tipo_pago", "transferencia")
    es_efectivo = tipo_pago == "efectivo"

    saldo_profit = float(profit_data.get("total_adeudado") or 0)
    monto_banco  = float(banco_data.get("monto_confirmado") or 0)
    banco_conf   = bool(banco_data.get("confirmado", False))
    tiene_profit = profit_data.get("cliente_encontrado", False) and saldo_profit > 0

    dif_fm_profit = round(monto_fm - saldo_profit, 2)
    dif_fm_banco  = round(monto_fm - monto_banco, 2) if banco_conf else None

    # USD equivalentes para el Δ
    dif_usd_profit = round(monto_usd - (saldo_profit / tasa if tasa > 0 else 0), 2) if monto_usd else None

    profit_ok = tiene_profit and abs(dif_fm_profit) <= TOLERANCIA_BS
    banco_ok  = banco_conf and (dif_fm_banco is not None) and abs(dif_fm_banco) <= TOLERANCIA_BS

    # ── Evaluar escenario ──
    if profit_ok and (banco_ok or es_efectivo):
        estatus  = "completado"
        tarea    = "cobro_total"
        semaforo = "verde"
        color    = "#28a745"
        label    = "✅ Completado"

    elif banco_ok and not profit_ok and dif_fm_profit > 0:
        estatus  = "pendiente"
        tarea    = "abono"
        semaforo = "amarillo"
        color    = "#f59e0b"
        label    = "⚠️ Abono Parcial"

    elif profit_ok and not banco_ok and banco_conf:
        estatus  = "diferencia"
        tarea    = "revisar_banco"
        semaforo = "rojo"
        color    = "#dc3545"
        label    = "❌ Dif. Bancaria"

    elif not banco_conf and tiene_profit and not es_efectivo:
        estatus  = "pendiente"
        tarea    = "adelanto"
        semaforo = "amarillo"
        color    = "#f59e0b"
        label    = "⚠️ Sin confirmar banco"

    elif es_efectivo and not profit_ok:
        estatus  = "pendiente"
        tarea    = "aplicar_cobro"
        semaforo = "amarillo"
        color    = "#f59e0b"
        label    = "💵 Efectivo — Aplicar"

    elif not tiene_profit and banco_ok:
        estatus  = "pendiente"
        tarea    = "aplicar_cobro"
        semaforo = "amarillo"
        color    = "#017e84"
        label    = "⚠️ Aplicar Cobro"

    else:
        estatus  = "diferencia"
        tarea    = "revisar"
        semaforo = "rojo"
        color    = "#dc3545"
        label    = "❌ Revisar"

    return {
        "estatus":          estatus,
        "tarea":            tarea,
        "semaforo":         semaforo,
        "color":            color,
        "label":            label,
        # Montos FM
        "monto_fm":         monto_fm,
        "monto_usd":        monto_usd,
        "tasa":             tasa,
        "tipo_pago":        tipo_pago,
        "tipo_label":       pago_fm.get("tipo_label", tipo_pago),
        "tipo_icono":       pago_fm.get("tipo_icono", "🏦"),
        # Profit
        "saldo_profit":     saldo_profit,
        "delta_fm_profit":  dif_fm_profit,
        "delta_usd_profit": dif_usd_profit,
        # Banco
        "banco_confirmado": banco_conf,
        "monto_banco":      monto_banco,
        "delta_fm_banco":   dif_fm_banco,
        "es_efectivo":      es_efectivo,
        # Diferencia principal (FM vs Profit)
        "diferencia":       dif_fm_profit,
        # Referencias
        "profit":           profit_data,
        "banco":            banco_data,
    }


def get_tables_schema() -> List[str]:
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        logger.error(f"Schema query error: {e}")
        return []


# Alias para compatibilidad con código anterior
get_facturas_por_nombre = lambda nombre: []
