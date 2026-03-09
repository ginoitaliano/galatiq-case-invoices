# backend/agents/accountant_agent.py
from datetime import datetime, date
import re
import json

from agents.state import InvoiceState, AuditEntry
from agents.reasoning_agent import call_llm, ACCOUNTANT_PERSONA
from config import settings


#Deterministc check:

def calculate_days_until_due(due_date_str: str) -> int | None:
    try:
        due = date.fromisoformat(due_date_str)
        today = date.today()
        return (due - today).days
    except Exception:
        return None


def is_overdue(due_date_str: str) -> bool:
    days = calculate_days_until_due(due_date_str)
    return days is not None and days < 0


def parse_net_terms(payment_terms: str | None) -> int | None:
    """Extract the number of days from payment terms."""
    if not payment_terms:
        return None
    try:
        match = re.search(r'\d+', str(payment_terms))
        return int(match.group()) if match else None
    except Exception:
        return None


#Context Builder
def build_finance_context(state: InvoiceState) -> str:
    """Build rich context for the accountant agent to reason over."""
    invoice = state["invoice"]
    flags = state.get("validation_flags")
    days_until_due = calculate_days_until_due(invoice.due_date or "")
    net_terms = parse_net_terms(str(invoice.payment_terms) if invoice.payment_terms else None)

    context = f"""
INVOICE DETAILS:
- Invoice Number: {invoice.invoice_number}
- Vendor: {invoice.vendor.name}
- Total Amount: ${invoice.total:,.2f}
- Invoice Date: {invoice.date}
- Due Date: {invoice.due_date}
- Payment Terms: {invoice.payment_terms}
- Net Terms (days): {net_terms}
- Days Until Due: {days_until_due} ({'OVERDUE' if days_until_due and days_until_due < 0 else 'on time'})
- Currency: {invoice.currency}

LINE ITEMS:
{chr(10).join(
    f"  - {(item.get('item') if isinstance(item, dict) else item.item)}: "
    f"{(item.get('quantity') if isinstance(item, dict) else item.quantity)} units @ "
    f"${(item.get('unit_price') if isinstance(item, dict) else item.unit_price):,.2f}"
    for item in invoice.line_items
)}

VALIDATION RESULTS:
- Validation Passed: {state.get('validation_passed')}
- Flags Raised: {', '.join(flags.details) if flags and flags.details else 'None'}
- Fraud Flag: {flags.is_fraudulent if flags else False}
- Out of Stock Flag: {flags.is_out_of_stock if flags else False}
- Unknown Item Flag: {flags.is_unknown_item if flags else False}
- Data Integrity Flag: {flags.is_data_integrity_issue if flags else False}

APPROVAL THRESHOLD: ${settings.vp_approval_threshold:,.2f}
REQUIRES VP APPROVAL: {invoice.total >= settings.vp_approval_threshold}

DELIVERY CONFIRMATION: Not yet confirmed (3-way match pending)
"""
    return context.strip()


#Reflection loop

def run_reflection_loop(context: str) -> tuple:
    """
    Accountant thinks, then second-guesses, then decides.
    Returns (decision_dict, initial_assessment, critique)
    """

    # initial assessment
    initial_prompt = f"""
Here is an invoice that has passed technical validation and needs your financial review:

{context}

Give your INITIAL ASSESSMENT. Consider:
1. Is the amount reasonable for the items ordered?
2. Are the payment terms acceptable?
3. Any cash flow concerns given the due date?
4. Any red flags not caught by automated validation?
5. Should this be auto-approved, escalated to VP, or rejected?

Be specific. Reference actual numbers from the invoice.
"""
    initial_assessment = call_llm(
        persona=ACCOUNTANT_PERSONA,
        user_message=initial_prompt
    )

    # self critique
    critique_prompt = f"""
You just gave this initial assessment of an invoice:

{initial_assessment}

Now CRITIQUE your own assessment. Ask yourself:
1. Did I miss any payment term implications?
2. Was I too lenient or too strict?
3. Is the delivery confirmation issue a real blocker?
4. Did I consider the vendor relationship and history?
5. Am I protecting Acme Corp's interests appropriately?

Be honest. If your initial assessment was wrong, say so.
"""
    critique = call_llm(
        persona=ACCOUNTANT_PERSONA,
        user_message=critique_prompt
    )

    # final decision
    final_prompt = f"""
Based on your initial assessment and self-critique, give your FINAL DECISION.

Initial Assessment:
{initial_assessment}

Self-Critique:
{critique}

Respond in this exact JSON format:
{{
    "decision": "approve" | "escalate_to_vp" | "reject",
    "confidence": 0.0 to 1.0,
    "reasoning": "clear explanation of your final decision",
    "risk_level": "low" | "medium" | "high",
    "payment_urgency": "urgent" | "normal" | "can_wait",
    "flags": ["any final concerns worth noting"]
}}

Return ONLY the JSON. No extra text.
"""
    final_response = call_llm(
        persona=ACCOUNTANT_PERSONA,
        user_message=final_prompt
    )

    clean = final_response.replace("```json", "").replace("```", "").strip()
    return json.loads(clean), initial_assessment, critique


#agent

def accountant_agent(state: InvoiceState) -> InvoiceState:
    """
    Reviews validated invoices with a reflection loop.
    Decides: auto-approve, escalate to VP, or reject.
    """
    timestamp = datetime.now().isoformat()
    invoice = state.get("invoice")

    # guardrails
    if not invoice:
        state["error"] = "No invoice in state"
        state["current_stage"] = "failed"
        return state

    try:
        # build context
        context = build_finance_context(state)

        # run the reflection loop
        decision_dict, initial_assessment, critique = run_reflection_loop(context)

        decision = decision_dict.get("decision", "escalate_to_vp")
        confidence = decision_dict.get("confidence", 0.5)
        reasoning = decision_dict.get("reasoning", "")

        # store full reasoning : VP and dashboard will see this
        state["finance_reasoning"] = f"""
INITIAL ASSESSMENT:
{initial_assessment}

SELF-CRITIQUE:
{critique}

FINAL DECISION: {decision.upper()}
REASONING: {reasoning}
CONFIDENCE: {confidence}
RISK LEVEL: {decision_dict.get('risk_level', 'unknown')}
PAYMENT URGENCY: {decision_dict.get('payment_urgency', 'normal')}
        """.strip()

        state["finance_confidence"] = confidence

        # escalate if amount > threshold OR accountant says so
        requires_vp = (
            invoice.total >= settings.vp_approval_threshold or
            decision == "escalate_to_vp"
        )
        state["requires_vp_approval"] = requires_vp

        # delivery confirmation : simulated for prototype
        # in production: query SAP/ERP system
        state["delivery_confirmed"] = True
        state["three_way_match"] = True

        # set stage
        if decision == "reject":
            state["current_stage"] = "rejected"
        elif requires_vp:
            state["current_stage"] = "awaiting_vp"
        else:
            state["current_stage"] = "payment"

        # audit trail
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="accountant",
            action=f"accountant_decision_{decision}",
            message=f"Accountant decision: {decision} | Confidence: {confidence} | VP Required: {requires_vp}",
            flags=state.get("validation_flags")
        ))

    except Exception as e:
        # if accountant crashes, escalate to VP — never auto-approve on error
        state["requires_vp_approval"] = True
        state["error"] = f"Accountant agent error: {str(e)}"
        state["current_stage"] = "awaiting_vp"
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="accountant",
            action="failed",
            message=f"Accountant crashed, escalating to VP: {str(e)}",
            flags=None
        ))

    return state