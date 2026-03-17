# backend/services/approval_service.py
from datetime import datetime
from typing import Optional
from agents.payment_agent import payment_agent
from agents.rejection_handler import rejection_handler
from services.invoice_service import load_all_invoices, save_invoice


def get_pending_approvals() -> list:
    """Return all invoices currently awaiting VP approval."""
    invoice_store = load_all_invoices()
    pending = []
    for fp, result in invoice_store.items():
        if result.get("current_stage") == "awaiting_vp":
            invoice = result.get("invoice")
            pending.append({
                "invoice_number": (
                    invoice.get("invoice_number") if invoice else "UNKNOWN"
                ),
                "vendor": (
                    invoice.get("vendor", {}).get("name") if invoice else "UNKNOWN"
                ),
                "amount": invoice.get("total", 0) if invoice else 0,
                "finance_reasoning": result.get("finance_reasoning"),
                "validation_flags": result.get("validation_flags"),
                "file_path": fp
            })
    return pending


def process_vp_decision(
    invoice_number: str,
    decision: str,
    note: str = ""
) -> Optional[dict]:
    """Record VP decision and trigger payment or rejection."""
    invoice_store = load_all_invoices()

    # find the invoice
    target_fp = None
    for fp, result in invoice_store.items():
        invoice = result.get("invoice")
        if invoice and invoice.get("invoice_number") == invoice_number:
            target_fp = fp
            break

    if not target_fp:
        return None

    result = invoice_store[target_fp]

    # record VP decision
    result["vp_decision"] = decision
    result["vp_note"] = note
    result["vp_timestamp"] = datetime.now().isoformat()

    # route based on decision
    if decision == "approved":
        result = payment_agent(result)
        result["current_stage"] = "completed"
    else:
        result = rejection_handler(result)
        result["current_stage"] = "rejected"

    # save updated result to SQLite
    save_invoice(target_fp, result)

    return {
        "invoice_number": invoice_number,
        "decision": decision,
        "payment_status": result.get("payment_status"),
        "payment_reference": result.get("payment_reference"),
        "rejection_reason": result.get("rejection_reason")
    }