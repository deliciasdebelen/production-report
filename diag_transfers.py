    queries = [
        "SELECT TOP 1 * FROM saLoteEntrada"
    ]
    try:
        with engine_a.connect() as conn:
            for q in queries:
                res = conn.execute(text(q)).fetchone()
                if res:
                    print(f"Columns in {q.split()[-1]}: {list(res._mapping.keys())}")
    try:
        with engine_a.connect() as conn:
            # 1. Inspect saTrasladoReng
            res_reng = conn.execute(text("SELECT TOP 1 * FROM saTrasladoReng")).fetchone()
            if res_reng:
                cols = list(res_reng._mapping.keys())
                print(f"Columns in saTrasladoReng: {cols}")
                # Heuristic: Find something that looks like quantity
                qty_col = next((c for c in cols if 'can' in c or 'total' in c or 'cant' in c), 'total_art')
                art_col = next((c for c in cols if 'art' in c), 'co_art')
            else:
                qty_col = 'total_art'
                art_col = 'co_art'

            # 2. Execute dynamic query
            query = f"""
            SELECT TOP 10 T.tras_num, T.fecha, TR.{art_col}, TR.{qty_col}, TR.rowguid
            FROM saTraslado T
            JOIN saTrasladoReng TR ON T.tras_num = TR.tras_num
            WHERE T.confirma = '1' AND T.anulado = 0
            AND NOT EXISTS (
                SELECT 1 FROM saLoteSalida LS WHERE LS.rowguid_reng = TR.rowguid
            )
            ORDER BY T.fecha DESC
            """
            print(f"Executing query with qty_col={qty_col}, art_col={art_col}...")
            res = conn.execute(text(query)).fetchall()
            
            if not res:
                print("No se encontraron traslados confirmados sin movimientos de lote (saLoteSalida).")
            else:
                print(f"Se encontraron {len(res)} renglones con posibles fallos:")
                for row in res:
                    m = row._mapping
                    print(f"Num: {m['tras_num']}, Art: {m[art_col]}, Cant: {m[qty_col]}, GUID: {m['rowguid']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_transfers()
