# backend/api/approvals.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import approval_service

router = APIRouter()


class VPDecisionRequest(BaseModel):
    decision: str   # "approved" or "rejected"
    note: str = ""


@router.get("/approvals/pending")
async def get_pending_approvals():
    pending = approval_service.get_pending_approvals()
    return {
        "pending": pending,
        "count": len(pending)
    }


@router.post("/approvals/{invoice_number}/decide")
async def vp_decision(invoice_number: str, request: VPDecisionRequest):
    if request.decision not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'approved' or 'rejected'"
        )

    result = approval_service.process_vp_decision(
        invoice_number=invoice_number,
        decision=request.decision,
        note=request.note
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {invoice_number} not found"
        )

    return result