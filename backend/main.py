# backend/main.py
import argparse
import sys
from fastapi import FastAPI
from api import invoices, approvals, metrics

app = FastAPI(title="Galatiq Case: Invoice Processing Automation", version="1.0.0")

app.include_router(invoices.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")


def run_cli(invoice_path: str):
    """Run a single invoice through the pipeline from the command line."""
    from services.invoice_service import run_pipeline

    print(f"\n{'='*60}")
    print(f"  GALATIQ — INVOICE PROCESSOR")
    print(f"{'='*60}")
    print(f"  Processing: {invoice_path}\n")

    result = run_pipeline(invoice_path)

    invoice = result.get("invoice")
    stage = result.get("current_stage", "unknown")
    flags = result.get("validation_flags")

    print(f"  Invoice    : {invoice.invoice_number if invoice else 'UNKNOWN'}")
    print(f"  Vendor     : {invoice.vendor.name if invoice else 'UNKNOWN'}")
    print(f"  Total      : ${invoice.total:,.2f}" if invoice else "  Total      : N/A")
    print(f"  Stage      : {stage}")

    if result.get("payment_reference"):
        print(f"  Payment    : {result['payment_reference']}")

    if result.get("requires_vp_approval"):
        print(f"  VP Required: Yes — log in to dashboard to approve")

    if flags and flags.details:
        print(f"  Flags      : {', '.join(flags.details)}")

    if result.get("rejection_reason"):
        snippet = result["rejection_reason"][:120].replace("\n", " ")
        print(f"  Rejection  : {snippet}")

    if result.get("error"):
        print(f"  Error      : {result['error']}")

    print(f"\n  Audit trail ({len(result.get('audit_trail', []))} entries):")
    for entry in result.get("audit_trail", []):
        agent = entry.agent if hasattr(entry, "agent") else entry.get("agent")
        action = entry.action if hasattr(entry, "action") else entry.get("action")
        print(f"    [{agent}] {action}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Galatiq Invoice Processor")
    parser.add_argument("--invoice_path", required=True, help="Path to invoice file")
    args = parser.parse_args()
    run_cli(args.invoice_path)