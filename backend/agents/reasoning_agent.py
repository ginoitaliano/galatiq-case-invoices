from langchain_openai import ChatOpenAI
from config import settings
from utils.llm_utils import invoke_llm  

def get_llm():
    return ChatOpenAI(
        model="lightning-ai/llama-3.3-70b",
        base_url="https://lightning.ai/api/v1/",
        api_key=f"{settings.lightning_api_key}/ginoitaliano/experiment-lifecycle-project"
    )

# lazy — only created when first called
_llm = None

def call_llm(persona: str, user_message: str) -> str:
    global _llm
    if _llm is None:
        _llm = get_llm()
    return invoke_llm(_llm, persona, user_message)

INGESTION_PERSONA = """..."""

ACCOUNTANT_PERSONA = """
You are reviewing invoices for Acme Corp, a PE-backed manufacturing firm.

Your job is to protect Acme Corp's financial interests by applying 
rigorous accounts payable best practices:

EXPERTISE TO APPLY:
- Payment terms analysis (Net 30/60/90 implications for cash flow)
- 3-way matching: invoice vs purchase order vs delivery confirmation
- Fraud detection: duplicate invoices, inflated prices, unknown vendors
- Data integrity: mathematical accuracy, reasonable quantities and amounts

DECISION CRITERIA:
- Auto-approve: validation passed, amount under $10K, no red flags
- Escalate to VP: amount over $10K, or any ambiguity requiring human judgment
- Reject: fraud indicators, data integrity failures, unresolvable mismatches

REASONING STANDARDS:
- Always cite specific numbers from the invoice
- Never make vague statements like "looks reasonable"
- If uncertain, escalate — never auto-approve on doubt
- Show your mathematical work

EXAMPLE OF GOOD REASONING:
"The invoice total of $8,500 is mathematically correct — 
12x WidgetA at $250 ($3,000) + 7x WidgetB at $500 ($3,500) 
+ 4x GadgetX at $750 ($3,000) = $9,500 before 5% tax of $475 
= $9,975. However the invoice states $9,500 which excludes tax — 
this discrepancy requires clarification before payment."
"""

REJECTION_PERSONA = """..."""

if __name__ == "__main__":
    result = call_llm(
        persona="You are a helpful assistant.",
        user_message="Say hello in one word."
    )
    print(result)