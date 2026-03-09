# backend/agents/rejection_handler.py
from datetime import datetime
from agents.state import InvoiceState, AuditEntry
from agents.reasoning_agent import call_llm, REJECTION_PERSONA



def generate_rejection_notice(state: InvoiceState) -> str:
    """
    Generate a professional rejection notice explaining why
    the invoice was rejected and what the vendor needs to fix.
    """
    invoice = state.get("invoice")
    flags = state.get("validation_flags")
    finance_reasoning = state.get("finance_reasoning", "")
    vp_note = state.get("vp_note", "")

    # Context
    rejection_context = f"""
Invoice {invoice.invoice_number if invoice else 'UNKNOWN'} has been rejected.

REJECTION REASONS:
{', '.join(flags.details) if flags and flags.details else 'See finance review'}

FINANCE REVIEW NOTES:
{finance_reasoning if finance_reasoning else 'N/A'}

VP NOTES:
{vp_note if vp_note else 'N/A'}

Write a professional rejection notice to the vendor that:
1. Clearly states the invoice was rejected
2. Lists specific reasons with reference to invoice details
3. Tells them exactly what to fix to resubmit
4. Is firm but professional in tone
"""

    return call_llm(
        persona=REJECTION_PERSONA,
        user_message=rejection_context
    )

#agent
def rejection_handler(state: InvoiceState) -> InvoiceState:
    """
    Handles rejected invoices.
    Generates rejection notice and logs everything.
    """
    timestamp = datetime.now().isoformat()
    invoice = state.get("invoice")
    flags = state.get("validation_flags")

    try:
        
        rejection_notice = generate_rejection_notice(state)

      
        state["payment_status"] = "rejected"
        state["rejection_reason"] = rejection_notice
        state["current_stage"] = "rejected"

        #human readable reason summary
        reason_summary = []

        if flags:
            if flags.is_fraudulent:
                reason_summary.append("fraud detected")
            if flags.is_out_of_stock:
                reason_summary.append("items out of stock")
            if flags.is_unknown_item:
                reason_summary.append("unknown items")
            if flags.is_data_integrity_issue:
                reason_summary.append("data integrity issues")
            if flags.is_quantity_mismatch:
                reason_summary.append("quantity exceeds stock")
            if flags.is_total_mismatch:
                reason_summary.append("total mismatch")

        if state.get("vp_note"):
            reason_summary.append(f"VP rejected: {state['vp_note']}")

        # audit trail
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="rejection_handler",
            action="invoice_rejected",
            message=f"Invoice rejected — reasons: {', '.join(reason_summary) if reason_summary else 'see finance review'}",
            flags=flags
        ))

    except Exception as e:
        state["payment_status"] = "rejected"
        state["rejection_reason"] = "Invoice rejected — error generating notice"
        state["error"] = str(e)
        state["current_stage"] = "rejected"
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="rejection_handler",
            action="failed",
            message=str(e),
            flags=None
        ))

    return state