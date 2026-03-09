# backend/services/invoice_service.py
from datetime import datetime
from typing import Optional
from agents.graph import invoice_graph
from agents.state import InvoiceState


#In production, this would be the replaced with Postgres queries

invoice_store: dict = {}


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
    """
    Run the full invoice pipeline.
    Called as a background task from the API layer.
    """
    initial_state = build_initial_state(file_path)
    result = invoice_graph.invoke(initial_state)
    invoice_store[file_path] = result
    return result


def get_all_invoices() -> list:
    """Return summary of all processed invoices."""
    return [
        {
            "file_path": fp,
            "invoice_number": (
                result.get("invoice").invoice_number
                if result.get("invoice") else "UNKNOWN"
            ),
            "vendor": (
                result.get("invoice").vendor.name
                if result.get("invoice") else "UNKNOWN"
            ),
            "amount": (
                result.get("invoice").total
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
    for fp, result in invoice_store.items():
        invoice = result.get("invoice")
        if invoice and invoice.invoice_number == invoice_number:
            return {
                "invoice": invoice.dict() if invoice else None,
                "current_stage": result.get("current_stage"),
                "validation_passed": result.get("validation_passed"),
                "validation_flags": (
                    result.get("validation_flags").dict()
                    if result.get("validation_flags") else None
                ),
                "finance_reasoning": result.get("finance_reasoning"),
                "requires_vp_approval": result.get("requires_vp_approval"),
                "payment_status": result.get("payment_status"),
                "payment_reference": result.get("payment_reference"),
                "rejection_reason": result.get("rejection_reason"),
                "audit_trail": [
                    entry.dict()
                    for entry in result.get("audit_trail", [])
                ],
                "error": result.get("error")
            }
    return None