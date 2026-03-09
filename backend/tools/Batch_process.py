#!/usr/bin/env python3
# backend/tools/batch_process.py
"""
Batch processor , run all invoices in a folder through the pipeline.

Usage:
    python tools/batch_process.py
    python tools/batch_process.py --folder data/invoices
    python tools/batch_process.py --folder data/invoices --delay 2
    python tools/batch_process.py --mock   ← no API credits needed
"""
import argparse
import time
import json
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

SUPPORTED_EXTENSIONS = [".txt", ".json", ".csv", ".pdf"]


def print_header():
    print("\n" + "="*60)
    print("  GALATIQ — BATCH INVOICE PROCESSOR")
    print("="*60)


def print_result(file_path: str, result: dict, elapsed: float):
    stage = result.get("current_stage", "unknown")
    invoice = result.get("invoice")
    invoice_num = invoice.invoice_number if invoice else "UNKNOWN"
    vendor = invoice.vendor.name if invoice and invoice.vendor else "UNKNOWN"
    total = f"${invoice.total:,.2f}" if invoice else "N/A"
    error = result.get("error")

    status_icon = {
        "completed": "✓",
        "complete": "✓",
        "rejected": "✗",
        "awaiting_vp": "...",
        "failed": "!",
    }.get(stage, "?")

    print(f"\n  {status_icon}  {invoice_num} | {vendor} | {total}")
    print(f"     Stage: {stage} | Time: {elapsed:.1f}s")

    if result.get("payment_reference"):
        print(f"     Payment: {result['payment_reference']}")

    if result.get("rejection_reason"):
        snippet = result["rejection_reason"][:80].replace("\n", " ")
        print(f"     Rejection: {snippet}...")

    if error:
        print(f"     Error: {error}")

    flags = result.get("validation_flags")
    if flags:
        active_flags = []
        if flags.is_fraudulent: active_flags.append("FRAUD")
        if flags.is_unknown_item: active_flags.append("UNKNOWN_ITEM")
        if flags.is_quantity_mismatch: active_flags.append("QTY_MISMATCH")
        if flags.is_out_of_stock: active_flags.append("OUT_OF_STOCK")
        if flags.is_total_mismatch: active_flags.append("TOTAL_MISMATCH")
        if active_flags:
            print(f"     Flags: {', '.join(active_flags)}")


def print_summary(results: list):
    total = len(results)
    approved = sum(1 for r in results if r.get("payment_status") == "success")
    rejected = sum(1 for r in results if r.get("current_stage") == "rejected")
    vp_pending = sum(1 for r in results if r.get("current_stage") == "awaiting_vp")
    failed = sum(1 for r in results if r.get("current_stage") == "failed")

    total_paid = sum(
        r.get("invoice").total for r in results
        if r.get("payment_status") == "success" and r.get("invoice")
    )

    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print(f"  Total processed : {total}")
    print(f"  Approved        : {approved} ({round(approved/total*100) if total else 0}%)")
    print(f"  Rejected        : {rejected} ({round(rejected/total*100) if total else 0}%)")
    print(f"  Awaiting VP     : {vp_pending}")
    print(f"  Failed          : {failed}")
    print(f"  Total paid      : ${total_paid:,.2f}")
    print("="*60 + "\n")


def save_results(results: list, output_path: str):
    """Save results to JSON for audit trail."""
    serializable = []
    for r in results:
        entry = {
            "invoice_number": r.get("invoice").invoice_number if r.get("invoice") else "UNKNOWN",
            "vendor": r.get("invoice").vendor.name if r.get("invoice") and r.get("invoice").vendor else "UNKNOWN",
            "total": r.get("invoice").total if r.get("invoice") else None,
            "current_stage": r.get("current_stage"),
            "payment_status": r.get("payment_status"),
            "payment_reference": r.get("payment_reference"),
            "requires_vp_approval": r.get("requires_vp_approval"),
            "rejection_reason": r.get("rejection_reason"),
            "error": r.get("error"),
            "finance_reasoning": r.get("finance_reasoning"),
        }
        serializable.append(entry)

    with open(output_path, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"  Results saved to: {output_path}")


def run_pipeline_mock(file_path: str) -> dict:
    """Run pipeline with mock LLM — no API credits needed."""
    from unittest.mock import patch
    from tests.mock_llm import get_mock_llm, MOCK_RESPONSES
    from agents.graph import invoice_graph

    # infer invoice number from filename
    stem = Path(file_path).stem  
    invoice_number = "INV-" + stem.split("_")[-1] if "_" in stem else "INV-1001"
    invoice_number = invoice_number.upper()

    if invoice_number not in MOCK_RESPONSES:
        invoice_number = "INV-1001"

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


def main():
    parser = argparse.ArgumentParser(description="Batch process invoices through Galatiq pipeline")
    parser.add_argument("--folder", default="data/invoices", help="Folder containing invoice files")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between invoices (avoid rate limits)")
    parser.add_argument("--save", default="../data/batch_results.json", help="Output JSON file for results")
    parser.add_argument("--dry-run", action="store_true", help="List files without processing")
    parser.add_argument("--mock", action="store_true", help="Use mock LLM — no API credits needed")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        print(f"ERROR: Folder not found: {folder}")
        return

    files = sorted([
        f for f in folder.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS
    ])

    if not files:
        print(f"No invoice files found in {folder}")
        return

    print_header()
    print(f"\n  Found {len(files)} invoice(s) in {folder}")
    print(f"  Mode: {'MOCK (no API credits)' if args.mock else 'LIVE (API)'}")
    print(f"  Delay between invoices: {args.delay}s")

    if args.dry_run:
        print("\n  DRY RUN — files that would be processed:")
        for f in files:
            print(f"    {f.name}")
        return

    if args.mock:
        pipeline_fn = run_pipeline_mock
    else:
        from services.invoice_service import run_pipeline
        pipeline_fn = run_pipeline

    results = []
    for i, file_path in enumerate(files, 1):
        print(f"\n  [{i}/{len(files)}] Processing {file_path.name}...")
        start = time.time()
        try:
            result = pipeline_fn(str(file_path))
            elapsed = time.time() - start
            print_result(str(file_path), result, elapsed)
            results.append(result)
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ! ERROR processing {file_path.name}: {str(e)}")
            results.append({"current_stage": "failed", "error": str(e)})

        if i < len(files):
            time.sleep(args.delay)

    print_summary(results)
    save_results(results, args.save)


if __name__ == "__main__":
    main()
