# backend/services/metrics_service.py
from services.invoice_service import invoice_store



def get_metrics() -> dict:
    """
    Compute dashboard metrics.
    Business impact view.
    """
    total = len(invoice_store)

    if total == 0:
        return {
            "total": 0,
            "approved": 0,
            "rejected": 0,
            "pending_vp": 0,
            "processing": 0,
            "failed": 0,
            "approval_rate": 0,
            "rejection_rate": 0,
            "total_paid": 0.0,
            "total_rejected_value": 0.0,
            "average_invoice_value": 0.0
        }

    results = list(invoice_store.values())

    approved = sum(
        1 for r in results
        if r.get("payment_status") == "success"
    )
    rejected = sum(
        1 for r in results
        if r.get("payment_status") == "rejected"
    )
    pending_vp = sum(
        1 for r in results
        if r.get("current_stage") == "awaiting_vp"
    )
    processing = sum(
        1 for r in results
        if r.get("current_stage") in [
            "ingestion", "validation", "finance_review"
        ]
    )
    failed = sum(
        1 for r in results
        if r.get("current_stage") == "failed"
    )

  
    total_paid = sum(
        r.get("invoice").total
        for r in results
        if r.get("payment_status") == "success"
        and r.get("invoice")
    )
    total_rejected_value = sum(
        r.get("invoice").total
        for r in results
        if r.get("payment_status") == "rejected"
        and r.get("invoice")
    )
    all_amounts = [
        r.get("invoice").total
        for r in results
        if r.get("invoice")
    ]
    average_invoice_value = (
        sum(all_amounts) / len(all_amounts)
        if all_amounts else 0
    )

    return {
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "pending_vp": pending_vp,
        "processing": processing,
        "failed": failed,
        "approval_rate": round((approved / total) * 100, 1),
        "rejection_rate": round((rejected / total) * 100, 1),
        "total_paid": round(total_paid, 2),
        "total_rejected_value": round(total_rejected_value, 2),
        "average_invoice_value": round(average_invoice_value, 2)
    }