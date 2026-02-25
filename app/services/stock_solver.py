
from sqlalchemy import text
from app.external_db import engine_a

class StockSolver:
    @staticmethod
    def get_diagnostics():
        issues = []
        try:
            with engine_a.connect() as conn:
                # 1. Check for Negative Stock / Overdraws
                # Logic: Where exits > entry quantity (approximate check via negative stock_actual, 
                # but better to check inconsistent balance if stock_actual is trusted or calc it)
                # For this solver, we focus on what we fixed: Negative Stock Actual
                
                q_neg = text("""
                    SELECT rowguid, co_art, numero_lote, stock_actual, cantidad
                    FROM saLoteEntrada
                    WHERE stock_actual < 0
                """)
                neg_rows = conn.execute(q_neg).fetchall()
                
                for row in neg_rows:
                    issues.append({
                        "id": str(row.rowguid),
                        "type": "NEGATIVE_STOCK",
                        "severity": "high",
                        "title": f"Stock Negativo: {row.numero_lote}",
                        "description": f"El lote {row.numero_lote} ({row.co_art}) tiene stock negativo de {row.stock_actual:.2f}.",
                        "meta": {"current_stock": float(row.stock_actual), "initial_qty": float(row.cantidad)}
                    })

                # 2. Check for Warehouse Mismatch (Line vs Entry)
                # Logic: saLoteSalida.rowguid_reng -> saTrasladoReng (no alma) -> saTraslado.alm_orig
                # Actually, simpler check: saLoteSalida.co_alma != saLoteEntrada.co_alma
                # Limiting to recent issues or active ones?
                
                q_mismatch = text("""
                    SELECT TOP 20 LS.rowguid, LS.numero_lote, LS.co_alma as salida_alma, LE.co_alma as entrada_alma, LS.co_art
                    FROM saLoteSalida LS
                    JOIN saLoteEntrada LE ON LS.Rowguid_Lote = LE.rowguid
                    WHERE LS.co_alma != LE.co_alma
                """)
                mis_rows = conn.execute(q_mismatch).fetchall()
                
                for row in mis_rows:
                    issues.append({
                        "id": str(row.rowguid),
                        "type": "WAREHOUSE_MISMATCH",
                        "severity": "medium",
                        "title": f"Conflicto Almacén: {row.numero_lote}",
                        "description": f"Salida desde '{row.salida_alma}' pero el lote pertenece a '{row.entrada_alma}'.",
                        "meta": {"correct_alma": row.entrada_alma}
                    })

                # 3. Check for Stuck in Warehouse 99 (P1-99 )
                # ... (Existing logic) ...
                
                # 4. Check for Customer Return Inconsistencies (Supervisor Belén)
                # Rule A: Validate Header Math (Total = Bruto + Imp)
                # The user specifically reported cases where Total = Subtotal (ignoring Tax)
                q_ret_header = text("""
                    SELECT doc_num, rowguid, total_neto, total_bruto, monto_imp, co_cli
                    FROM saDevolucionCliente
                    WHERE anulado = 0
                    AND ABS(total_neto - (total_bruto + monto_imp)) > 0.1
                """)
                rows_bad_header = conn.execute(q_ret_header).fetchall()
                
                for row in rows_bad_header:
                    diff = float(row.total_neto - (row.total_bruto + row.monto_imp))
                    issues.append({
                        "id": str(row.rowguid),
                        "type": "RETURN_MATH_ERROR",
                        "severity": "critical",
                        "title": f"Error Matemático en Devolución: {row.doc_num}",
                        "description": f"El Total Neto ({row.total_neto:,.2f}) no coincide con Subtotal + Impuestos. Diferencia: {diff:,.2f}.",
                        "meta": {"diff": diff}
                    })

                # Rule B: Line Totals vs Header Totals
                # Compare Header Total Neto vs Sum(Line Net + Line Tax)
                q_ret_lines = text("""
                    SELECT H.doc_num, H.co_cli, H.total_neto, H.total_bruto, H.monto_imp,
                           SUM(L.reng_neto) as sum_neto, SUM(L.monto_imp) as sum_imp,
                           H.rowguid
                    FROM saDevolucionCliente H
                    JOIN saDevolucionClienteReng L ON H.doc_num = L.doc_num
                    WHERE H.anulado = 0
                    GROUP BY H.doc_num, H.co_cli, H.total_neto, H.total_bruto, H.monto_imp, H.rowguid
                    HAVING ABS(H.total_neto - (SUM(L.reng_neto) + SUM(L.monto_imp))) > 0.1
                """)
                bad_lines = conn.execute(q_ret_lines).fetchall()
                
                for row in bad_lines:
                     # Avoid dupes
                     # if row.doc_num in [x['title'] for x in issues]: continue
                     
                     real_total = row.sum_neto + row.sum_imp
                     diff = float(row.total_neto - real_total)
                     
                     issues.append({
                        "id": str(row.rowguid),
                        "type": "RETURN_LINE_MISMATCH",
                        "severity": "critical",
                        "title": f"Diferencia Renglones Devolución: {row.doc_num}",
                        "description": f"Cabecera ({row.total_neto:,.2f}) difiere de la Suma de Renglones ({real_total:,.2f}). Diferencia: {diff:,.2f}",
                        "meta": {"diff": diff, "real_total": float(real_total)}
                    })


                # Rule C: Return vs Credit Note (Monto Validation)
                # Strategy: Find recent returns and try to find matching N/C
                q_ret_nc = text("""
                    SELECT top 50 H.doc_num, H.co_cli, H.total_neto, H.fec_emis, H.rowguid, H.co_mone
                    FROM saDevolucionCliente H
                    WHERE H.anulado = 0 AND H.status = '0' 
                    ORDER BY H.fec_emis DESC
                """)
                recent_returns = conn.execute(q_ret_nc).fetchall()
                
                for ret in recent_returns:
                    # Look for N/C for this Client on the same day (or close?)
                    # Let's search by Date and Client first
                    q_nc_candidates = text("""
                        SELECT rowguid, nro_doc, total_neto, doc_orig, nro_orig
                        FROM saDocumentoVenta 
                        WHERE co_tipo_doc = 'N/CR' 
                        AND co_cli = :cli 
                        AND CAST(fec_emis AS DATE) = CAST(:date AS DATE)
                    """)
                    candidates = conn.execute(q_nc_candidates, {
                        "cli": ret.co_cli, 
                        "date": ret.fec_emis
                    }).fetchall()
                    
                    match_found = False
                    best_match = None
                    
                    for nc in candidates:
                        # Check logic:
                        # 1. Exact Amount Match
                        if abs(nc.total_neto - ret.total_neto) < 0.1:
                            match_found = True
                            break
                        # 2. Origin Match (if exists)
                        if nc.nro_orig and nc.nro_orig.strip() == ret.doc_num.strip():
                            match_found = True
                            best_match = nc
                            break
                            
                    if not match_found:
                        if candidates:
                            # Found N/C on same day but amount differs -> Mismatch
                            # Pick the first one or the one closest?
                            # Let's verify if manual fix needed
                            issues.append({
                                "id": str(ret.rowguid),
                                "type": "NC_MISMATCH",
                                "severity": "medium",
                                "title": f"Diferencia N/C vs Devolución: {ret.doc_num}",
                                "description": f"Devolución de {ret.total_neto:,.2f}. N/C encontradas ({len(candidates)}) pero montos no coinciden (Ej: {candidates[0].total_neto:,.2f}).",
                                "meta": {"nc_doc": candidates[0].nro_doc, "nc_guid": str(candidates[0].rowguid)}
                            })
                        else:
                            # No N/C found at all
                            issues.append({
                                "id": str(ret.rowguid),
                                "type": "NC_MISSING",
                                "severity": "medium",
                                "title": f"Falta Nota de Crédito: {ret.doc_num}",
                                "description": f"No se halló ninguna N/C del cliente {ret.co_cli} para la fecha {ret.fec_emis}.",
                                "meta": {}
                            })
                
                # Check saLoteSalida for warehouse 99 ... (Existing code continuing)
                target_99 = 'P1-99 '
                
                # Check saLoteEntrada
                q_99_in = text("""
                    SELECT rowguid, co_art, numero_lote, co_alma, stock_actual, tipo_doc, rowguid_doc
                    FROM saLoteEntrada
                    WHERE co_alma = :alma
                """)
                rows_99_in = conn.execute(q_99_in, {"alma": target_99}).fetchall()
                
                for row in rows_99_in:
                    issues.append({
                        "id": str(row.rowguid),
                        "type": "STUCK_IN_99_IN",
                        "severity": "high",
                        "title": f"Atascado en P1-99 (Entrada): {row.numero_lote}",
                        "description": f"Lote {row.numero_lote} incorrectamente en P1-99. Stock: {row.stock_actual}",
                        "meta": {"doc_type": row.tipo_doc}
                    })

                # Check saLoteSalida
                q_99_out = text("""
                    SELECT rowguid, co_art, numero_lote, co_alma, cantidad, tipo_doc, rowguid_reng
                    FROM saLoteSalida
                    WHERE co_alma = :alma
                """)
                rows_99_out = conn.execute(q_99_out, {"alma": target_99}).fetchall()
                
                for row in rows_99_out:
                    issues.append({
                        "id": str(row.rowguid),
                        "type": "STUCK_IN_99_OUT",
                        "severity": "high",
                        "title": f"Atascado en P1-99 (Salida): {row.numero_lote}",
                        "description": f"Salida de lote {row.numero_lote} desde P1-99. Cantidad: {row.cantidad}",
                        "meta": {"doc_type": row.tipo_doc}
                    })

                # Rule E: Confirmed Transfers Without Movement (Supervisor Belén)
                # Logic: saTraslado.confirma = 1 but no saLoteSalida/Entrada for its lines
                q_tras_bad = text("""
                    SELECT TOP 50 T.tras_num, T.fecha, TR.co_art, TR.total_art, TR.rowguid
                    FROM saTraslado T
                    JOIN saTrasladoReng TR ON T.tras_num = TR.tras_num
                    WHERE T.confirma = '1' AND T.anulado = 0
                    AND NOT EXISTS (
                        SELECT 1 FROM saLoteSalida LS WHERE LS.rowguid_reng = TR.rowguid
                    )
                    ORDER BY T.fecha DESC
                """)
                res_tras = conn.execute(q_tras_bad).fetchall()
                
                for row in res_tras:
                    issues.append({
                        "id": str(row.rowguid),
                        "type": "TRANSFER_WITHOUT_MOVEMENT",
                        "severity": "critical",
                        "title": f"Traslado sin Movimiento: {row.tras_num.strip()}",
                        "description": f"El traslado {row.tras_num.strip()} está confirmado pero no afectó el inventario (falta saLoteSalida) para el artículo {row.co_art.strip()}.",
                        "meta": {"art": row.co_art.strip(), "qty": float(row.total_art)}
                    })

        except Exception as e:
            print(f"Solver Error: {e}")
            
        return issues

    @staticmethod
    def fix_issue(issue_id, issue_type):
        try:
            with engine_a.connect() as conn:
                trans = conn.begin()
                
                if issue_type == "NEGATIVE_STOCK":
                    # ... (Existing logic) ...
                    # Verify it exists
                    q_check = text("SELECT co_art, numero_lote FROM saLoteEntrada WHERE rowguid = :guid")
                    row = conn.execute(q_check, {"guid": issue_id}).fetchone()
                    
                    if not row:
                        return {"success": False, "message": "Registro no encontrado"}
                        
                    # Calculate exits
                    q_calc = text("""
                        SELECT ISNULL(SUM(cantidad), 0) 
                        FROM saLoteSalida 
                        WHERE Rowguid_Lote = :guid
                    """)
                    total_exits = conn.execute(q_calc, {"guid": issue_id}).scalar()
                    
                    # Update
                    q_upd = text("""
                        UPDATE saLoteEntrada 
                        SET cantidad = :new_qty, stock_actual = 0 
                        WHERE rowguid = :guid
                    """)
                    conn.execute(q_upd, {"new_qty": total_exits, "guid": issue_id})
                    
                    trans.commit()
                    return {"success": True, "message": f"Stock corregido. Nueva cantidad base: {total_exits}"}

                elif issue_type == "WAREHOUSE_MISMATCH":
                    # ... (Existing logic) ...
                    # Get correct warehouse
                    q_correct = text("""
                        SELECT LE.co_alma 
                        FROM saLoteEntrada LE
                        JOIN saLoteSalida LS ON LE.rowguid = LS.Rowguid_Lote
                        WHERE LS.rowguid = :guid
                    """)
                    correct_alma = conn.execute(q_correct, {"guid": issue_id}).scalar()
                    
                    if not correct_alma:
                        return {"success": False, "message": "No se pudo determinar el almacén correcto"}
                        
                    q_fix = text("UPDATE saLoteSalida SET co_alma = :alma WHERE rowguid = :guid")
                    conn.execute(q_fix, {"alma": correct_alma, "guid": issue_id})
                    
                    trans.commit()
                    return {"success": True, "message": f"Almacén de salida actualizado a '{correct_alma}'"}

                elif issue_type == "STUCK_IN_99_OUT":
                    # Logic: Find correct warehouse from saTraslado (Header) via rowguid_reng -> saTrasladoReng -> saTraslado
                    # Or saAjusteReng -> saAjuste
                    
                    q_info = text("SELECT tipo_doc, rowguid_reng FROM saLoteSalida WHERE rowguid = :guid")
                    info = conn.execute(q_info, {"guid": issue_id}).fetchone()
                    
                    if not info: return {"success": False, "message": "Registro no encontrado"}
                    
                    tipo, reng_guid = info.tipo_doc.strip(), info.rowguid_reng
                    correct_alma = None
                    
                    if tipo == 'TRAS':
                         # Get Header Origin
                         q_tras = text("""
                            SELECT T.alm_orig 
                            FROM saTraslado T
                            JOIN saTrasladoReng TR ON T.tras_num = TR.tras_num
                            WHERE TR.rowguid = :rguid
                         """)
                         correct_alma = conn.execute(q_tras, {"rguid": reng_guid}).scalar()
                    elif tipo == 'AJU':
                         # Get Header Alma
                         q_aju = text("""
                            SELECT A.co_alma 
                            FROM saAjuste A
                            JOIN saAjusteReng AR ON A.ajue_num = AR.ajue_num
                            WHERE AR.rowguid = :rguid
                         """)
                         correct_alma = conn.execute(q_aju, {"rguid": reng_guid}).scalar()
                    
                    if not correct_alma:
                        return {"success": False, "message": "No se pudo determinar el almacén correcto del documento padre"}
                        
                    # Fix
                    q_fix = text("UPDATE saLoteSalida SET co_alma = :alma WHERE rowguid = :guid")
                    conn.execute(q_fix, {"alma": correct_alma, "guid": issue_id})
                    trans.commit()
                    return {"success": True, "message": f"Movido de P1-99 a '{correct_alma}'"}

                elif issue_type == "STUCK_IN_99_IN":
                    # Logic: Find correct warehouse from saTraslado (Header Dest) or saAjuste
                    
                    # Entry logic is trickier. rowguid_doc usually links to the Header or Line?
                    # For Traslado, saLoteEntrada usually linked via... it's complex.
                    # Usually: saLoteEntrada is created from a Receipt or Transfer.
                    # If TRAS, we want alm_dest.
                    
                    # Assuming we can trace back via similar logic or using rowguid_doc if it links to saTrasladoReng?
                    # Let's try to verify if rowguid_doc is the Line GUID (saTrasladoReng)
                    
                    q_info = text("SELECT tipo_doc, rowguid_doc FROM saLoteEntrada WHERE rowguid = :guid")
                    info = conn.execute(q_info, {"guid": issue_id}).fetchone()
                    
                    if not info: return {"success": False, "message": "Registro no encontrado"}
                    
                    tipo, doc_guid = info.tipo_doc.strip(), info.rowguid_doc
                    correct_alma = None
                    
                    if tipo == 'TRAS':
                         # If doc_guid is Line GUID
                         q_tras = text("""
                            SELECT T.alm_dest
                            FROM saTraslado T
                            JOIN saTrasladoReng TR ON T.tras_num = TR.tras_num
                            WHERE TR.rowguid = :rguid
                         """)
                         correct_alma = conn.execute(q_tras, {"rguid": doc_guid}).scalar()
                    elif tipo == 'AJU':
                         q_aju = text("""
                            SELECT A.co_alma 
                            FROM saAjuste A
                            JOIN saAjusteReng AR ON A.ajue_num = AR.ajue_num
                            WHERE AR.rowguid = :rguid
                         """)
                         correct_alma = conn.execute(q_aju, {"rguid": doc_guid}).scalar()
                         
                    if not correct_alma:
                         # Fallback: maybe rowguid_doc is the Header GUID? 
                         # Try Header check
                         if tipo == 'TRAS':
                             q_H = text("SELECT alm_dest FROM saTraslado WHERE rowguid = :guid")
                             correct_alma = conn.execute(q_H, {"guid": doc_guid}).scalar()

                    if not correct_alma:
                        return {"success": False, "message": "No se pudo determinar el almacén destino correcto"}
                        
                    # Fix
                    q_fix = text("UPDATE saLoteEntrada SET co_alma = :alma WHERE rowguid = :guid")
                    conn.execute(q_fix, {"alma": correct_alma, "guid": issue_id})
                    trans.commit()
                    return {"success": True, "message": f"Movido de P1-99 a '{correct_alma}'"}

                    return {"success": True, "message": f"Movido de P1-99 a '{correct_alma}'"}

                elif issue_type == "RETURN_MATH_ERROR":
                    # Fix: Recalculate total_neto = total_bruto + monto_imp
                    # Verify first
                    q_chk = text("SELECT total_bruto, monto_imp, total_neto FROM saDevolucionCliente WHERE rowguid = :guid")
                    row = conn.execute(q_chk, {"guid": issue_id}).fetchone()
                    if not row: return {"success": False, "message": "Registro no encontrado"}
                    
                    new_total = row.total_bruto + row.monto_imp
                    # Calculate difference to adjust Balance (Saldo) without losing payments
                    # diff = new_total - old_total
                    # new_saldo = old_saldo - diff (Wait, if net increases, saldo increases)
                    # new_saldo = old_saldo + (new_total - old_total)
                    
                    q_upd = text("""
                        UPDATE saDevolucionCliente 
                        SET saldo = saldo + (:new_tot - total_neto),
                            total_neto = :new_tot 
                        WHERE rowguid = :guid
                    """)
                    conn.execute(q_upd, {"new_tot": new_total, "guid": issue_id})
                    
                    trans.commit()
                    return {"success": True, "message": f"Total corregido a {new_total:,.2f} (Saldo ajustado)"}

                elif issue_type == "RETURN_LINE_MISMATCH":
                    # Fix: Recalculate Header based on Lines
                    # 1. Calculate Sums
                    q_sums = text("""
                        SELECT SUM(reng_neto) as sum_bruto, SUM(monto_imp) as sum_imp
                        FROM saDevolucionClienteReng 
                        WHERE doc_num = (SELECT doc_num FROM saDevolucionCliente WHERE rowguid = :guid)
                    """)
                    sums = conn.execute(q_sums, {"guid": issue_id}).fetchone()
                    
                    if not sums: return {"success": False, "message": "No se pudieron calcular los renglones"}
                    
                    new_bruto = sums.sum_bruto or 0
                    new_imp = sums.sum_imp or 0
                    new_neto = new_bruto + new_imp
                    
                    # 2. Update Header (Preserve Saldo diff)
                    q_upd = text("""
                        UPDATE saDevolucionCliente 
                        SET saldo = saldo + (:n - total_neto),
                            total_bruto = :b, 
                            monto_imp = :i, 
                            total_neto = :n
                        WHERE rowguid = :guid
                    """)
                    conn.execute(q_upd, {"b": new_bruto, "i": new_imp, "n": new_neto, "guid": issue_id})
                    
                    trans.commit()
                    return {"success": True, "message": f"Cabecera ajustada a Renglones: {new_neto:,.2f}"}

                    return {"success": True, "message": f"Cabecera ajustada a Renglones: {new_neto:,.2f}"}

                elif issue_type == "NC_MISMATCH":
                    # Fix: Synchronize N/C amount to Return amount
                    # 1. Get Return Data
                    q_ret = text("SELECT total_bruto, monto_imp, total_neto, nro_doc, co_cli, fec_emis FROM saDevolucionCliente WHERE rowguid = :guid")
                    ret = conn.execute(q_ret, {"guid": issue_id}).fetchone()
                    
                    if not ret: return {"success": False, "message": "Devolución no encontrada"}
                    
                    # 2. Find the target N/C again (Heuristic)
                    q_nc_find = text("""
                        SELECT rowguid, nro_doc, total_neto 
                        FROM saDocumentoVenta 
                        WHERE co_tipo_doc = 'N/CR' 
                        AND co_cli = :cli 
                        AND CAST(fec_emis AS DATE) = CAST(:date AS DATE)
                    """)
                    candidates = conn.execute(q_nc_find, {
                        "cli": ret.co_cli, 
                        "date": ret.fec_emis
                    }).fetchall()
                    
                    target_nc = None
                    if candidates:
                        target_nc = candidates[0] # Assume first one is the intended link
                    
                    if not target_nc:
                         return {"success": False, "message": "No se encontró la N/C para corregir"}

                    # 3. Update N/C
                    q_upd = text("""
                        UPDATE saDocumentoVenta 
                        SET total_bruto = :b, monto_imp = :i, total_neto = :n, saldo = :n 
                        WHERE rowguid = :nc_guid
                    """)
                    conn.execute(q_upd, {
                        "b": ret.total_bruto, 
                        "i": ret.monto_imp, 
                        "n": ret.total_neto, 
                        "nc_guid": target_nc.rowguid
                    })
                    
                    trans.commit()
                    return {"success": True, "message": f"N/CR {target_nc.nro_doc} sincronizada con Devolución ({ret.total_neto:,.2f})"}

                else:
                    return {"success": False, "message": "Tipo de problema desconocido"}

        except Exception as e:
            return {"success": False, "message": str(e)}
