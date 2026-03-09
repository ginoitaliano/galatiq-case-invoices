# backend/agents/validation_agent.py
import sqlite3
from datetime import datetime

from agents.state import InvoiceState, AuditEntry, ValidationFlags
from config import settings





# swap this for SAP/Oracle in production without touching agents
def get_inventory_item(item_name: str) -> dict | None:
    """
    Look up an item in the inventory DB.
    Tries exact match first, then case insensetive match.
    to handle inconsistent naming in the legacy DB.
    Returns None if not found.
    """
    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.cursor()

  
    cursor.execute(
        "SELECT item, stock, unit_price FROM inventory WHERE item = ?",
        (item_name,)
    )
    row = cursor.fetchone()

    
    if not row:
        cursor.execute(
            "SELECT item, stock, unit_price FROM inventory WHERE LOWER(item) = LOWER(?)",
            (item_name,)
        )
        row = cursor.fetchone()

    conn.close()

    if row:
        return {
            "item": row[0],
            "stock": row[1],
            "unit_price": row[2]
        }
    return None


#Validation checks:
def check_line_items(line_items: list) -> tuple[bool, ValidationFlags]:
    """
    Check each line item against the inventory DB
    Returns (passed, flags)
    """
    flags = ValidationFlags(
        is_fraudulent=False,
        is_out_of_stock=False,
        is_unknown_item=False,
        is_data_integrity_issue=False,
        is_quantity_mismatch=False,
        is_total_mismatch=False,
        details=[]
    )

    passed = True

    for line_item in line_items:
      
        item_name = (
            line_item.get("item")
            if isinstance(line_item, dict)
            else line_item.item
        )
        quantity = (
            line_item.get("quantity")
            if isinstance(line_item, dict)
            else line_item.quantity
        )
        unit_price = (
            line_item.get("unit_price")
            if isinstance(line_item, dict)
            else line_item.unit_price
        )

        # catches INV-1009
        if quantity <= 0:
            flags.is_data_integrity_issue = True
            flags.details.append(
                f"{item_name}: invalid quantity {quantity} , must be greater than zero"
            )
            passed = False
            continue

       
        # catches INV-1008, INV-1016
        inventory_item = get_inventory_item(item_name)

        if inventory_item is None:
            flags.is_unknown_item = True
            flags.details.append(
                f"{item_name}: not found in inventory database"
            )
            passed = False
            continue

       
        # catches INV-1003 FakeItem
        if inventory_item["stock"] == 0:
            flags.is_out_of_stock = True
            flags.details.append(
                f"{item_name}: zero stock , item may be fraudulent or discontinued"
            )
            passed = False
            continue

       
        # catches INV-1002 GadgetX x20
        if quantity > inventory_item["stock"]:
            flags.is_quantity_mismatch = True
            flags.details.append(
                f"{item_name}: requested {quantity} units, "
                f"only {inventory_item['stock']} in stock"
            )
            passed = False

       
        # catches fraudulent price inflation
        if inventory_item["unit_price"] > 0:
            price_diff = abs(unit_price - inventory_item["unit_price"])
            tolerance = inventory_item["unit_price"] * 0.20
            if price_diff > tolerance:
                flags.is_fraudulent = True
                flags.details.append(
                    f"{item_name}: price mismatch — "
                    f"invoice ${unit_price:,.2f} vs "
                    f"DB ${inventory_item['unit_price']:,.2f} "
                    f"(exceeds 20% tolerance)"
                )
                passed = False

    return passed, flags


def check_totals(invoice) -> tuple[bool, ValidationFlags]:
    """
    Verify line items add up to the stated subtotal.
    Catches INV-1013 deliberate total bug.
    Allows $0.10 rounding tolerance.
    """
    issues = []

    line_total = sum(
        item.get("amount") if isinstance(item, dict) else item.amount
        for item in invoice.line_items
    )

    if abs(line_total - invoice.subtotal) > 0.10:
        issues.append(
            f"Subtotal mismatch — line items sum to "
            f"${line_total:,.2f}, invoice states ${invoice.subtotal:,.2f}"
        )

    flags = ValidationFlags(
        is_fraudulent=False,
        is_out_of_stock=False,
        is_unknown_item=False,
        is_data_integrity_issue=False,
        is_quantity_mismatch=False,
        is_total_mismatch=len(issues) > 0,
        details=issues
    )

    return len(issues) == 0, flags


#Agent:

def validation_agent(state: InvoiceState) -> InvoiceState:
 
    timestamp = datetime.now().isoformat()
    invoice = state.get("invoice")

    # guardrail:
    if not invoice:
        state["validation_passed"] = False
        state["current_stage"] = "failed"
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="validation",
            action="skipped",
            message="No invoice object in state — ingestion likely failed",
            flags=None
        ))
        return state

    try:
       
        items_passed, flags = check_line_items(invoice.line_items)
        totals_passed, totals_flags = check_totals(invoice)

        
        if not totals_passed:
            flags.is_total_mismatch = True
            flags.details.extend(totals_flags.details)

       
        validation_passed = items_passed and totals_passed

        state["validation_passed"] = validation_passed
        state["validation_flags"] = flags
        state["current_stage"] = "finance_review" if validation_passed else "failed"

      
        status = "passed" if validation_passed else "failed"
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="validation",
            action=f"validation_{status}",
            message=(
                f"Validation passed for {invoice.invoice_number}"
                if validation_passed
                else f"Validation failed: {', '.join(flags.details)}"
            ),
            flags=flags
        ))

    except Exception as e:
        state["validation_passed"] = False
        state["error"] = f"Validation error: {str(e)}"
        state["current_stage"] = "failed"
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="validation",
            action="failed",
            message=str(e),
            flags=None
        ))

    return state