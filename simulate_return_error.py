
from sqlalchemy import text
from app.external_db import engine_a

def simulate_error():
    doc_num = '0000000529'
    with engine_a.connect() as conn:
        print(f"--- Simulating Error on {doc_num} ---")
        
        # Current state
        row = conn.execute(text("SELECT total_neto, total_bruto, monto_imp, saldo FROM saDevolucionCliente WHERE doc_num = :d"), {"d": doc_num}).fetchone()
        print(f"Before: Net={row.total_neto}, Bruto={row.total_bruto}, Imp={row.monto_imp}, Saldo={row.saldo}")
        
        # Force Error: Set Net = Bruto (ignoring Tax, as in screenshot)
        # Screenshot showed Net=711.11, Bruto=711.11, Imp=113.78
        # Make sure to set Saldo to 711.11 too to mimic "perfectly wrong" state, or keep as is?
        # Screenshot showed N/CR had Saldo 824.89? No, N/CR is separate.
        # User implies Return was wrong.
        
        q_break = text("""
            UPDATE saDevolucionCliente 
            SET total_neto = 711.11, saldo = 711.11
            WHERE doc_num = :d
        """)
        conn.execute(q_break, {"d": doc_num})
        conn.commit()
        print("Error simulated: Net set to 711.11")

if __name__ == "__main__":
    simulate_error()
