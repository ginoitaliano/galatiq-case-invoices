# backend/api/invoices.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from services import invoice_service
from tests.mock_llm import MOCK_RESPONSES, MOCK_FINANCE_DECISIONS
from models.invoice import Invoice, Vendor, LineItem
from agents.state import ValidationFlags, AuditEntry
from datetime import datetime
import json

router = APIRouter()


class ProcessInvoiceRequest(BaseModel):
    file_path: str


@router.post("/invoices/process")
async def process_invoice(
    request: ProcessInvoiceRequest,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(
        invoice_service.run_pipeline,
        request.file_path
    )
    return {
        "message": f"Processing started for {request.file_path}",
        "status": "processing"
    }

#Display without API calls
@router.post("/invoices/seed")
async def seed_invoices():
    """
    Seed the invoice store with mock data for dashboard demo.
    Use when API credits are unavailable.
    """
    seeded = []

    scenarios = [
        ("INV-1001", "completed",  "success",  False, None),
        ("INV-1002", "rejected",   "rejected",  False, ValidationFlags(
            is_fraudulent=False, is_out_of_stock=False, is_unknown_item=False,
            is_data_integrity_issue=False, is_quantity_mismatch=True,
            is_total_mismatch=False, details=["GadgetX: requested 99 units, only 5 in stock"]
        )),
        ("INV-1003", "rejected",   "rejected",  False, ValidationFlags(
            is_fraudulent=False, is_out_of_stock=True, is_unknown_item=False,
            is_data_integrity_issue=False, is_quantity_mismatch=False,
            is_total_mismatch=False, details=["FakeItem: zero stock, item may be fraudulent or discontinued"]
        )),
        ("INV-1004", "awaiting_vp", None,       True,  None),
    ]

    for inv_number, stage, payment_status, requires_vp, flags in scenarios:
        raw = MOCK_RESPONSES[inv_number]
        finance = json.loads(MOCK_FINANCE_DECISIONS[inv_number])

        invoice = Invoice(
            invoice_number=raw["invoice_number"],
            vendor=Vendor(**raw["vendor"]),
            date=raw["date"],
            due_date=raw["due_date"],
            line_items=[LineItem(**item) for item in raw["line_items"]],
            subtotal=raw["subtotal"],
            tax_rate=raw.get("tax_rate"),
            tax_amount=raw.get("tax_amount"),
            total=raw["total"],
            currency=raw["currency"],
            payment_terms=raw.get("payment_terms"),
        )

        state = {
            "file_path": f"data/invoices/{inv_number.lower()}.txt",
            "raw_text": None,
            "invoice": invoice,
            "extraction_confidence": raw["extraction_confidence"],
            "validation_passed": stage not in ["rejected"] or requires_vp,
            "validation_flags": flags,
            "finance_reasoning": finance.get("reasoning"),
            "finance_confidence": finance.get("confidence"),
            "three_way_match": True,
            "requires_vp_approval": requires_vp,
            "delivery_confirmed": True,
            "vp_decision": None,
            "vp_note": None,
            "vp_timestamp": None,
            "payment_status": payment_status,
            "payment_reference": f"PAY-{inv_number}-DEMO" if payment_status == "success" else None,
            "rejection_reason": (
                f"Invoice {inv_number} rejected: {', '.join(flags.details)}"
                if flags else None
            ),
            "audit_trail": [
                AuditEntry(
                    timestamp=datetime.now().isoformat(),
                    agent="seed",
                    action="demo_data",
                    message=f"Seeded {inv_number} for dashboard demo",
                    flags=flags
                )
            ],
            "current_stage": stage,
            "error": None,
        }

        invoice_service.invoice_store[inv_number] = state
        seeded.append(inv_number)

    return {
        "message": f"Seeded {len(seeded)} invoices for demo",
        "invoices": seeded
    }


@router.get("/invoices")
async def get_all_invoices():
    return {
        "invoices": invoice_service.get_all_invoices(),
        "total": len(invoice_service.invoice_store)
    }


@router.get("/invoices/{invoice_number}")
async def get_invoice(invoice_number: str):
    result = invoice_service.get_invoice_by_number(invoice_number)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {invoice_number} not found"
        )
    return result