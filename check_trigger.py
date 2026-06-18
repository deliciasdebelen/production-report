from check_reng_neto_audit import engine, text
res = engine.connect().execute(text("SELECT m.definition FROM sys.triggers tr JOIN sys.tables t ON tr.parent_id = t.object_id JOIN sys.sql_modules m ON tr.object_id = m.object_id WHERE tr.name = 'TR_ForzarTotalesEnDetalle'")).scalar()
print("=== TRIGGER DEF ===")
print(res)
