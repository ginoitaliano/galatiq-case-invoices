#!/usr/bin/env python3
# backend/tools/eval_harness.py
"""
Agent eval harness — runs known invoices and asserts expected outcomes.
This is how you verify agent reliability, not just agent functionality.

Usage:
    python tools/eval_harness.py --mock           no API credits needed
    python tools/eval_harness.py --verbose --mock
    python tools/eval_harness.py --invoice INV-1002 --mock
    python tools/eval_harness.py                   live API

Integrates with LangSmith for trace visibility.
"""
import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class EvalCase:
    """A single eval case with expected outcomes."""
    invoice_number: str
    description: str
    file_path: str

    # expected outcomes
    expected_stage: str
    expected_flags: list[str] = field(default_factory=list)
    expected_payment_status: Optional[str] = None
    expected_vp_required: Optional[bool] = None
    should_have_rejection: bool = False

    # metadata
    category: str = "general"


# eval suite 
EVAL_CASES = [
    EvalCase(
        invoice_number="INV-1001",
        description="Clean invoice under $10K — should auto-approve",
        file_path="../data/invoices/invoice_1001.txt",
        expected_stage="completed",
        expected_payment_status="success",
        expected_vp_required=False,
        category="happy_path",
    ),
    EvalCase(
        invoice_number="INV-1002",
        description="Quantity exceeds available stock — should reject",
        file_path="../data/invoices/invoice_1002.txt",
        expected_stage="rejected",
        expected_flags=["is_quantity_mismatch"],
        should_have_rejection=True,
        category="validation_failure",
    ),
    EvalCase(
        invoice_number="INV-1003",
        description="Zero stock item FakeItem — should reject",
        file_path="../data/invoices/invoice_1003.txt",
        expected_stage="rejected",
        expected_flags=["is_out_of_stock"],
        should_have_rejection=True,
        category="validation_failure",
    ),
    EvalCase(
        invoice_number="INV-1004",
        description="Invoice over $10K threshold — should escalate to VP",
        file_path="../data/invoices/invoice_1004.json",
        expected_stage="awaiting_vp",
        expected_vp_required=True,
        category="escalation",
    ),
]


@dataclass
class EvalResult:
    case: EvalCase
    passed: bool
    failures: list[str] = field(default_factory=list)
    actual_stage: str = ""
    actual_flags: list[str] = field(default_factory=list)
    error: Optional[str] = None
    duration_seconds: float = 0.0


def get_pipeline_fn(mock: bool, invoice_number: str):
    """Return either the real pipeline or the mock pipeline function."""
    if mock:
        from unittest.mock import patch
        from tests.mock_llm import get_mock_llm
        from agents.graph import invoice_graph

        def mock_pipeline(file_path: str) -> dict:
            mock_llm = get_mock_llm(invoice_number)
            with patch("agents.reasoning_agent.llm", mock_llm):
                state = {
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
                return invoice_graph.invoke(state)
        return mock_pipeline
    else:
        from services.invoice_service import run_pipeline
        return run_pipeline


def run_eval(case: EvalCase, mock: bool = False, verbose: bool = False) -> EvalResult:
    """Run a single eval case and check all assertions."""
    import time

    result = EvalResult(case=case, passed=False)
    start = time.time()
    pipeline_fn = get_pipeline_fn(mock, case.invoice_number)

    try:
        state = pipeline_fn(case.file_path)
        result.duration_seconds = time.time() - start

        actual_stage = state.get("current_stage", "unknown")
        result.actual_stage = actual_stage

        flags = state.get("validation_flags")
        if flags:
            result.actual_flags = [
                k for k, v in {
                    "is_fraudulent": flags.is_fraudulent,
                    "is_out_of_stock": flags.is_out_of_stock,
                    "is_unknown_item": flags.is_unknown_item,
                    "is_data_integrity_issue": flags.is_data_integrity_issue,
                    "is_quantity_mismatch": flags.is_quantity_mismatch,
                    "is_total_mismatch": flags.is_total_mismatch,
                }.items() if v
            ]

        failures = []

        # 1. stage check
        if actual_stage != case.expected_stage:
            failures.append(
                f"stage: expected '{case.expected_stage}' got '{actual_stage}'"
            )

        # 2. payment status check
        if case.expected_payment_status is not None:
            actual_payment = state.get("payment_status")
            if actual_payment != case.expected_payment_status:
                failures.append(
                    f"payment_status: expected '{case.expected_payment_status}' got '{actual_payment}'"
                )

        # 3. VP required check
        if case.expected_vp_required is not None:
            actual_vp = state.get("requires_vp_approval")
            if bool(actual_vp) != case.expected_vp_required:
                failures.append(
                    f"requires_vp_approval: expected {case.expected_vp_required} got {actual_vp}"
                )

        # 4. flag checks
        for expected_flag in case.expected_flags:
            if expected_flag not in result.actual_flags:
                failures.append(f"missing flag: {expected_flag}")

        # 5. rejection notice check
        if case.should_have_rejection:
            rejection = state.get("rejection_reason")
            if not rejection or len(rejection) < 10:
                failures.append("rejection_reason: missing or too short")

        # 6. audit trail check
        audit = state.get("audit_trail", [])
        if len(audit) == 0:
            failures.append("audit_trail: empty — no agent activity recorded")

        result.failures = failures
        result.passed = len(failures) == 0

        if verbose:
            print(f"\n    State keys returned: {[k for k, v in state.items() if v is not None]}")
            print(f"    Finance reasoning: {str(state.get('finance_reasoning', ''))[:100]}")

    except Exception as e:
        result.duration_seconds = time.time() - start
        result.error = str(e)
        result.failures = [f"exception: {str(e)}"]
        result.passed = False

    return result


def print_eval_results(results: list[EvalResult], verbose: bool = False):
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n" + "="*65)
    print("  GALATIQ AGENT EVAL HARNESS")
    print("="*65)

    categories = {}
    for r in results:
        cat = r.case.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    for category, cat_results in categories.items():
        print(f"\n  [{category.upper().replace('_', ' ')}]")
        for r in cat_results:
            icon = "✓" if r.passed else "✗"
            duration = f"{r.duration_seconds:.1f}s"
            print(f"\n    {icon} {r.case.invoice_number} — {r.case.description}")
            print(f"      Stage: {r.actual_stage} | Duration: {duration}")

            if r.actual_flags:
                print(f"      Flags: {', '.join(r.actual_flags)}")

            if not r.passed:
                for failure in r.failures:
                    print(f"      FAIL: {failure}")

            if r.error:
                print(f"      ERROR: {r.error}")

    print("\n" + "="*65)
    print(f"  RESULT: {passed}/{total} passed", end="")
    if passed == total:
        print("  ALL PASSING")
    else:
        print(f"  ({total - passed} failing)")
    print("="*65 + "\n")

    return passed == total


def save_eval_report(results: list[EvalResult], output_path: str):
    """Save eval results as JSON for LangSmith or CI integration."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "cases": [
            {
                "invoice_number": r.case.invoice_number,
                "description": r.case.description,
                "category": r.case.category,
                "passed": r.passed,
                "actual_stage": r.actual_stage,
                "actual_flags": r.actual_flags,
                "failures": r.failures,
                "duration_seconds": round(r.duration_seconds, 2),
                "error": r.error,
            }
            for r in results
        ]
    }
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Eval report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Galatiq agent eval harness")
    parser.add_argument("--verbose", action="store_true", help="Show detailed state output")
    parser.add_argument("--invoice", help="Run only a specific invoice number")
    parser.add_argument("--category", help="Run only a specific category")
    parser.add_argument("--save", default="../data/eval_report.json", help="Output JSON report")
    parser.add_argument("--mock", action="store_true", help="Use mock LLM — no API credits needed")
    args = parser.parse_args()

    cases = EVAL_CASES
    if args.invoice:
        cases = [c for c in cases if c.invoice_number == args.invoice]
    if args.category:
        cases = [c for c in cases if c.category == args.category]

    if not cases:
        print("No matching eval cases found.")
        return

    mode = "MOCK" if args.mock else "LIVE"
    print(f"\n  Running eval harness [{mode} mode]")

    results = []
    for i, case in enumerate(cases, 1):
        print(f"  Running {case.invoice_number} ({i}/{len(cases)})...", end=" ", flush=True)

        if not Path(case.file_path).exists():
            print(f"SKIP — file not found: {case.file_path}")
            result = EvalResult(case=case, passed=False, failures=[f"file not found: {case.file_path}"])
            results.append(result)
            continue

        result = run_eval(case, mock=args.mock, verbose=args.verbose)
        print("PASS" if result.passed else "FAIL")
        results.append(result)

    all_passed = print_eval_results(results, verbose=args.verbose)
    save_eval_report(results, args.save)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()