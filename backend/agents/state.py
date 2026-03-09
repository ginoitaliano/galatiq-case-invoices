# backend/agents/state.py
from typing import Optional, List, TypedDict
from pydantic import BaseModel
from models.invoice import Invoice


class ValidationFlags(BaseModel):
    details: List[str] = []
    is_fraudulent: bool
    is_out_of_stock: bool
    is_unknown_item: bool
    is_data_integrity_issue: bool
    is_quantity_mismatch: bool
    is_total_mismatch: bool


class AuditEntry(BaseModel):
    timestamp: str
    agent: str
    message: str
    action: str
    flags: Optional[ValidationFlags] = None


class InvoiceState(TypedDict):

    # ingestion
    file_path: str
    raw_text: Optional[str]
    invoice: Optional[Invoice]
    extraction_confidence: Optional[float]

    # validation
    validation_passed: Optional[bool]         
    validation_flags: Optional[ValidationFlags]  

    # accountant
    finance_reasoning: Optional[str]
    finance_confidence: Optional[float]
    three_way_match: Optional[bool]
    requires_vp_approval: Optional[bool]
    delivery_confirmed: Optional[bool]

    # VP (set by UI)
    vp_decision: Optional[str]
    vp_note: Optional[str]                   
    vp_timestamp: Optional[str]              

    # payment
    payment_status: Optional[str]
    payment_reference: Optional[str]          

    # rejection
    rejection_reason: Optional[str]

    # pipeline control
    audit_trail: List[AuditEntry]
    current_stage: str                        
    error: Optional[str]                     














































