# backend/agents/payment_agent.py
from datetime import datetime
from agents.state import InvoiceState, AuditEntry





def mock_payment(vendor: str, amount: float) -> dict:
    """
    Simulates a banking API payment call.
    In production: replace with real payment provider API.
    """
    print(f"Processing payment of ${amount:,.2f} to {vendor}")
    return {
        "status": "success",
        "reference": f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "vendor": vendor,
        "amount": amount,
        "timestamp": datetime.now().isoformat()
    }



def payment_agent(state: InvoiceState) -> InvoiceState:
    """
    Processes approved invoices through the mock payment API.
    Only reaches here if validation passed AND approved.
    """
    timestamp = datetime.now().isoformat()
    invoice = state.get("invoice")

    # guardrails
    if not invoice:
        state["error"] = "No invoice in state"
        state["current_stage"] = "failed"
        return state

    try:
        result = mock_payment(
            vendor=invoice.vendor.name,
            amount=invoice.total
        )

        # write to state
        state["payment_status"] = result["status"]
        state["payment_reference"] = result["reference"]
        state["current_stage"] = "completed"

        # audit trail
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="payment",
            action="payment_processed",
            message=f"Payment of ${invoice.total:,.2f} to {invoice.vendor.name} — ref: {result['reference']}",
            flags=None
        ))

    except Exception as e:
        state["payment_status"] = "failed"
        state["error"] = f"Payment failed: {str(e)}"
        state["current_stage"] = "failed"
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="payment",
            action="payment_failed",
            message=str(e),
            flags=None
        ))

    return state