# backend/services/invoice_service.py
from typing import Optional
from agents.graph import invoice_graph
from agents.state import InvoiceState
import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager


DB_PATH = Path(__file__).parent.parent.parent / "data" / "invoices.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                file_path TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """) 

def save_invoice(file_path: str, result: dict):
    """Save invoice result to SQLite."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO invoices (file_path, data) VALUES (?,?),"
        (file_path, json.dumps(result, default=str))
    )

def load_all_invoices() -> dict:
    """Load all invoices from SQLite."""
    with get_db() as conn:
        rows = conn.execute("SELECT file_path, data FROM invoices").fetchall()
        return {row[0]: json.loads(row[1]) for row in rows}
   

def build_initial_state(file_path: str) -> InvoiceState:
    """Build a clean initial state for a new invoice"""
    return {
        "file_path": file_path,
        "raw_text": None,
        "invoice": None,
        "extraction_confidence": None,
        "validation_passed": None,
        "validation_flags": None,
        "finance_reasoning": None,
        "finance_confidence": None,
        "three_way_match": None,
        "requires_vp_approval": None,
        "delivery_confirmed": None,
        "vp_decision": None,
        "vp_note": None,
        "vp_timestamp": None,
        "payment_status": None,
        "payment_reference": None,
        "rejection_reason": None,
        "audit_trail": [],
        "current_stage": "ingestion",
        "error": None
    }

def run_pipeline(file_path: str) -> dict:
    """Run the full invoice pipeline."""
    init_db()
    initial_state = build_initial_state(file_path)
    result = invoice_graph.invoke(initial_state)
    save_invoice(file_path, result)
    return result

def get_all_invoices() -> list:
    """Return summary of all processed invoices."""
    invoice_store = load_all_invoices()
    return [
        {
            "file_path": fp,
            "invoice_number": (
                result.get("invoice", {}).get("invoice_number", "UNKNOWN")
                if result.get("invoice") else "UNKNOWN"
            ),
            "vendor": (
                result.get("invoice", {}).get("vendor", {}).get("name", "UNKNOWN")
                if result.get("invoice") else "UNKNOWN"
            ),
            "amount": (
                result.get("invoice", {}).get("total", 0)
                if result.get("invoice") else 0
            ),
            "current_stage": result.get("current_stage"),
            "payment_status": result.get("payment_status"),
            "validation_passed": result.get("validation_passed"),
            "requires_vp_approval": result.get("requires_vp_approval"),
        }
        for fp, result in invoice_store.items()
    ]

def get_invoice_by_number(invoice_number: str) -> Optional[dict]:
    """Return full details for a specific invoice."""
    invoice_store = load_all_invoices()
    for fp, result in invoice_store.items():
        invoice = result.get("invoice")
        if invoice and invoice.get("invoice_number") == invoice_number:
            return {
                "invoice": invoice,
                "current_stage": result.get("current_stage"),
                "validation_passed": result.get("validation_passed"),
                "validation_flags": result.get("validation_flags"),
                "finance_reasoning": result.get("finance_reasoning"),
                "requires_vp_approval": result.get("requires_vp_approval"),
                "payment_status": result.get("payment_status"),
                "payment_reference": result.get("payment_reference"),
                "rejection_reason": result.get("rejection_reason"),
                "audit_trail": result.get("audit_trail", []),
                "error": result.get("error")
            }

    return None