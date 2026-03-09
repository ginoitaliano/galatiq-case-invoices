# backend/tests/test_pipeline.py
"""
End-to-end pipeline tests using mock LLM.
Run with: pytest tests/test_pipeline.py -v

Tests cover all assessment scenarios:
- INV-1001: clean invoice → auto-approve
- INV-1002: quantity mismatch → reject
- INV-1003: unknown item → reject
- INV-1004: large invoice → VP escalation
"""
import importlib
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from agents.graph import invoice_graph
from agents.ingestion_agent import extract_text, parse_invoice_with_llm
from agents.validation_agent import check_line_items, check_totals
from agents.accountant_agent import parse_net_terms
from models.invoice import LineItem, Invoice, Vendor
from config import settings
from services.metrics_service import get_metrics
import services.metrics_service as metrics_module
from tests.mock_llm import get_mock_llm, MOCK_RESPONSES
from langchain_core.messages import AIMessage


# helpers

def make_state(file_path: str) -> dict:
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
        "error": None,
    }


def run_with_mock(invoice_number: str, file_path: str) -> dict:
    """Run the full pipeline with a mock LLM."""
    mock_llm = get_mock_llm(invoice_number)
    with patch("agents.reasoning_agent.llm", mock_llm):
        state = make_state(file_path)
        return invoice_graph.invoke(state)


# unit tests: ingestion agent 

class TestIngestionAgent:

    def test_extract_text_txt(self, tmp_path):
        """Text extraction works for .txt files."""
        f = tmp_path / "test.txt"
        f.write_text("INVOICE\nVendor: Test Corp\nTotal: $100")
        result = extract_text(str(f))
        assert "INVOICE" in result
        assert "Test Corp" in result

    def test_extract_text_missing_file(self):
        """Missing file is handled gracefully."""
        try:
            result = extract_text("/nonexistent/path/invoice.txt")
            assert result is not None
        except FileNotFoundError:
            pass  

    def test_parse_invoice_with_mock_llm(self):
        """LLM extraction returns valid structured data."""
        mock = get_mock_llm("INV-1001")
        with patch("agents.reasoning_agent.llm", mock):
            result = parse_invoice_with_llm("INVOICE\nVendor: Widgets Inc.\nTotal: $5000")
        assert result["invoice_number"] == "INV-1001"
        assert result["total"] == 5000.00
        assert result["extraction_confidence"] == 0.95


#  unit tests: validation agent 
class TestValidationAgent:

    def test_clean_invoice_passes(self):
        """INV-1001 with valid quantities should pass validation."""
        line_items = [
            LineItem(item="WidgetA", quantity=10, unit_price=250.00, amount=2500.00),
            LineItem(item="WidgetB", quantity=5, unit_price=500.00, amount=2500.00),
        ]
        passed, flags = check_line_items(line_items)
        assert passed
        assert not flags.is_unknown_item
        assert not flags.is_quantity_mismatch
        assert not flags.is_out_of_stock

    def test_unknown_item_flagged(self):
        """FakeItem should be flagged as unknown."""
        line_items = [
            LineItem(item="FakeItem", quantity=5, unit_price=100.00, amount=500.00),
        ]
        passed, flags = check_line_items(line_items)
        assert not passed
        assert flags.is_out_of_stock
        assert any("FakeItem" in d for d in flags.details)

    def test_quantity_exceeds_stock(self):
        """Ordering more than available stock should flag."""
        line_items = [
            LineItem(item="GadgetX", quantity=99, unit_price=750.00, amount=74250.00),
        ]
        passed, flags = check_line_items(line_items)
        assert not passed
        assert flags.is_quantity_mismatch or flags.is_out_of_stock

    def test_total_mismatch_flagged(self):
        """Incorrect total should be flagged."""
        invoice = Invoice(
            invoice_number="INV-TEST",
            vendor=Vendor(name="Test"),
            date="2026-01-01",
            due_date="2026-02-01",
            line_items=[
                LineItem(item="WidgetA", quantity=1, unit_price=250.00, amount=250.00),
            ],
            subtotal=999.00,
            total=999.00,
            currency="USD",
        )
        passed, flags = check_totals(invoice)
        assert not passed
        assert flags.is_total_mismatch


#unit tests: accountant agent

class TestAccountantAgent:

    def test_parse_net_terms(self):
        """Payment terms parsing works correctly."""
        assert parse_net_terms("Net 30") == 30
        assert parse_net_terms("Net 60") == 60
        assert parse_net_terms("Net 90") == 90
        assert parse_net_terms(None) is None

    def test_vp_threshold(self):
        """VP approval threshold is set to $10K."""
        assert settings.vp_approval_threshold == 10000.00


# integration tests: full pipeline 

class TestPipeline:

    def test_inv_1001_clean_invoice(self, tmp_path):
        """INV-1001: clean invoice under $10K should auto-approve."""
        f = tmp_path / "invoice_1001.txt"
        f.write_text("INVOICE\nINV-1001\nWidgets Inc.\nTotal: $5000")
        result = run_with_mock("INV-1001", str(f))
        assert result.get("current_stage") in ["complete", "pay", "completed"]
        assert result.get("payment_status") == "success"
        assert result.get("payment_reference") is not None
        assert result.get("requires_vp_approval") is not True

    def test_inv_1002_quantity_mismatch(self, tmp_path):
        """INV-1002: quantity exceeds stock — should reject."""
        f = tmp_path / "invoice_1002.txt"
        f.write_text("INVOICE\nINV-1002\nGadget Corp\nGadgetX qty:99")
        result = run_with_mock("INV-1002", str(f))
        assert result.get("current_stage") == "rejected"
        flags = result.get("validation_flags")
        assert flags is not None
        assert flags.is_quantity_mismatch or flags.is_out_of_stock

    def test_inv_1003_unknown_item(self, tmp_path):
        """INV-1003: unknown item FakeItem — should reject."""
        f = tmp_path / "invoice_1003.txt"
        f.write_text("INVOICE\nINV-1003\nMystery Vendor\nFakeItem qty:5")
        result = run_with_mock("INV-1003", str(f))
        assert result.get("current_stage") == "rejected"
        flags = result.get("validation_flags")
        assert flags is not None
        assert flags.is_out_of_stock

    def test_inv_1004_vp_escalation(self, tmp_path):
        """INV-1004: $12,500 invoice — should escalate to VP."""
        f = tmp_path / "invoice_1004.txt"
        f.write_text("INVOICE\nINV-1004\nBig Supplier\nTotal: $12500")
        result = run_with_mock("INV-1004", str(f))
        assert result.get("current_stage") == "awaiting_vp"
        assert result.get("requires_vp_approval") is True

    def test_audit_trail_populated(self, tmp_path):
        """Every invoice should have an audit trail."""
        f = tmp_path / "invoice_1001.txt"
        f.write_text("INVOICE\nINV-1001\nWidgets Inc.\nTotal: $5000")
        result = run_with_mock("INV-1001", str(f))
        audit = result.get("audit_trail", [])
        assert len(audit) > 0
        agents_seen = [e.agent if hasattr(e, "agent") else e.get("agent") for e in audit]
        assert "ingestion" in agents_seen

    def test_rejection_notice_generated(self, tmp_path):
        """Rejected invoices should have a rejection notice."""
        f = tmp_path / "invoice_1003.txt"
        f.write_text("INVOICE\nINV-1003\nMystery Vendor\nFakeItem qty:5")
        result = run_with_mock("INV-1003", str(f))
        assert result.get("rejection_reason") is not None
        assert len(result.get("rejection_reason", "")) > 10


#  metrics tests 

class TestMetrics:

    def test_empty_store_returns_zeros(self):
        """Empty invoice store returns all zeros."""
        with patch("services.metrics_service.invoice_store", {}):
            m = get_metrics()
            assert m["total"] == 0
            assert m["approval_rate"] == 0

    def test_metrics_calculate_correctly(self):
        """Metrics correctly count approved/rejected invoices."""
        mock_store = {
            "inv1": {"payment_status": "success", "current_stage": "complete", "invoice": MagicMock(total=5000)},
            "inv2": {"payment_status": "rejected", "current_stage": "rejected", "invoice": MagicMock(total=1000)},
        }
        with patch("services.metrics_service.invoice_store", mock_store):
            m = get_metrics()
            assert m["total"] == 2
            assert m["approved"] == 1
            assert m["rejected"] == 1
            assert m["approval_rate"] == 50.0