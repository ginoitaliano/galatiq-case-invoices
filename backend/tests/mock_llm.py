# backend/tests/mock_llm.py
"""
Mock LLM for testing without burning API credits.
Returns deterministic responses based on invoice content.

Call sequence per invoice:
  Call 1     = ingestion extraction (returns JSON)
  Calls 2-4  = accountant reflection loop (returns finance decision JSON)
  Call 5+    = rejection notice (returns plain string)

Note: invoices that fail validation skip the accountant entirely,
so their call sequence is: 1 (ingestion) → 2 (rejection notice)
"""
import json
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage


MOCK_RESPONSES = {
    # INV-1001: clean invoice, should auto-approve
    "INV-1001": {
        "invoice_number": "INV-1001",
        "vendor": {"name": "Widgets Inc.", "address": None},
        "date": "2026-01-15",
        "due_date": "2026-02-01",
        "line_items": [
            {"item": "WidgetA", "quantity": 10, "unit_price": 250.00, "amount": 2500.00},
            {"item": "WidgetB", "quantity": 5, "unit_price": 500.00, "amount": 2500.00},
        ],
        "subtotal": 5000.00,
        "tax_rate": 0.0,
        "tax_amount": 0.0,
        "total": 5000.00,
        "currency": "USD",
        "payment_terms": "Net 30",
        "extraction_confidence": 0.95,
    },
    # INV-1002: quantity mismatch — should flag
    "INV-1002": {
        "invoice_number": "INV-1002",
        "vendor": {"name": "Gadget Corp", "address": None},
        "date": "2026-01-16",
        "due_date": "2026-02-15",
        "line_items": [
            {"item": "GadgetX", "quantity": 99, "unit_price": 750.00, "amount": 74250.00},
        ],
        "subtotal": 74250.00,
        "tax_rate": 0.0,
        "tax_amount": 0.0,
        "total": 74250.00,
        "currency": "USD",
        "payment_terms": "Net 30",
        "extraction_confidence": 0.92,
    },
    # INV-1003: zero stock item — should flag as out of stock
    "INV-1003": {
        "invoice_number": "INV-1003",
        "vendor": {"name": "Mystery Vendor", "address": None},
        "date": "2026-01-17",
        "due_date": "2026-02-16",
        "line_items": [
            {"item": "FakeItem", "quantity": 5, "unit_price": 100.00, "amount": 500.00},
        ],
        "subtotal": 500.00,
        "tax_rate": 0.0,
        "tax_amount": 0.0,
        "total": 500.00,
        "currency": "USD",
        "payment_terms": "Net 30",
        "extraction_confidence": 0.88,
    },
    # INV-1004: large invoice — should escalate to VP
    "INV-1004": {
        "invoice_number": "INV-1004",
        "vendor": {"name": "Big Supplier LLC", "address": None},
        "date": "2026-01-18",
        "due_date": "2026-02-17",
        "line_items": [
            {"item": "WidgetA", "quantity": 20, "unit_price": 250.00, "amount": 5000.00},
            {"item": "WidgetB", "quantity": 15, "unit_price": 500.00, "amount": 7500.00},
        ],
        "subtotal": 12500.00,
        "tax_rate": 0.0,
        "tax_amount": 0.0,
        "total": 12500.00,
        "currency": "USD",
        "payment_terms": "Net 60",
        "extraction_confidence": 0.97,
    },
}

MOCK_FINANCE_DECISIONS = {
    "INV-1001": json.dumps({
        "decision": "approve",
        "reasoning": "Invoice total of $5,000 is mathematically correct. 10x WidgetA at $250 ($2,500) + 5x WidgetB at $500 ($2,500) = $5,000. No tax applied. Amount is under $10K threshold. No red flags detected.",
        "confidence": 0.95,
        "risk_level": "low",
        "payment_urgency": "normal",
        "flags": [],
        "requires_escalation": False,
    }),
    "INV-1002": json.dumps({
        "decision": "reject",
        "reasoning": "Quantity of 99 GadgetX exceeds available inventory of 5 units. Cannot approve until delivery is confirmed and inventory reconciled.",
        "confidence": 0.98,
        "risk_level": "high",
        "payment_urgency": "can_wait",
        "flags": ["quantity_exceeds_stock"],
        "requires_escalation": False,
    }),
    "INV-1003": json.dumps({
        "decision": "reject",
        "reasoning": "FakeItem has zero stock — item may be fraudulent or discontinued. Cannot approve payment.",
        "confidence": 0.99,
        "risk_level": "high",
        "payment_urgency": "can_wait",
        "flags": ["zero_stock_item"],
        "requires_escalation": False,
    }),
    "INV-1004": json.dumps({
        "decision": "escalate_to_vp",
        "reasoning": "Invoice total of $12,500 exceeds the $10,000 VP approval threshold. Mathematics checks out: 20x WidgetA ($5,000) + 15x WidgetB ($7,500) = $12,500. Escalating for VP sign-off.",
        "confidence": 0.97,
        "risk_level": "medium",
        "payment_urgency": "normal",
        "flags": ["above_vp_threshold"],
        "requires_escalation": True,
    }),
}

MOCK_REJECTION_NOTICES = {
    "INV-1002": (
        "Dear Gadget Corp, Invoice INV-1002 has been rejected. "
        "The quantity of 99 GadgetX units exceeds our available inventory of 5 units. "
        "Please resubmit with a corrected quantity or await inventory replenishment. "
        "Contact accounts@acmecorp.com with questions."
    ),
    "INV-1003": (
        "Dear Mystery Vendor, Invoice INV-1003 has been rejected. "
        "The line item 'FakeItem' has zero stock and cannot be fulfilled. "
        "Please verify the item and resubmit with approved catalog items only. "
        "Contact accounts@acmecorp.com with questions."
    ),
}


def get_mock_llm(invoice_number: str = "INV-1001"):
    """
    Returns a mock LLM that returns deterministic responses.
    Patch this in place of agents.reasoning_agent.llm during tests.
    """
    mock = MagicMock()
    call_count = {"n": 0}

    def mock_invoke(messages):
        call_count["n"] += 1
        n = call_count["n"]

        # Call 1 — ingestion extraction
        if n == 1:
            payload = MOCK_RESPONSES.get(invoice_number, MOCK_RESPONSES["INV-1001"])
            return AIMessage(content=json.dumps(payload))

        # Calls 2-4 — accountant reflection loop
        if n in [2, 3, 4]:
            finance = MOCK_FINANCE_DECISIONS.get(invoice_number, MOCK_FINANCE_DECISIONS["INV-1001"])
            return AIMessage(content=finance)

        # Call 5+ — rejection notice
        notice = MOCK_REJECTION_NOTICES.get(
            invoice_number,
            f"Dear Vendor, Invoice {invoice_number} has been rejected. "
            f"Please review the flagged issues and resubmit a corrected invoice. "
            f"Contact accounts@acmecorp.com with questions."
        )
        return AIMessage(content=notice)

    mock.invoke = mock_invoke
    return mock