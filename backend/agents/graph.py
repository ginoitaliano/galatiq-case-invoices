# backend/agents/graph.py
from datetime import datetime
import langgraph
from langgraph.graph import StateGraph, END  
from agents.state import AuditEntry, InvoiceState
from agents.ingestion_agent import ingestion_agent
from agents.validation_agent import validation_agent
from agents.accountant_agent import accountant_agent
from agents.payment_agent import payment_agent
from agents.rejection_handler import rejection_handler



def vp_hold(state: InvoiceState) -> InvoiceState:
    state["current_stage"] = "awaiting_vp"
    state["audit_trail"].append(AuditEntry(
        timestamp=datetime.now().isoformat(),
        agent="graph",
        action="awaiting_vp_decision",
        message="Invoice routed to VP — amount requires approval",
        flags=None
    ))
    return state


def route_after_validation(state: InvoiceState) -> str:
    """After validation, did it pass or fail?"""
    if not state.get("validation_passed"):
        return "reject"
    return "finance_review"


def route_after_finance(state: InvoiceState) -> str:
    
    if state.get("requires_vp_approval"):   
        return "await_vp"

    flags = state.get("validation_flags")  

    if flags and (flags.is_fraudulent or flags.is_data_integrity_issue):
        return "reject"

    return "pay"


def route_after_vp(state: InvoiceState) -> str:
    decision = state.get("vp_decision")
    if decision == "approve":
        return "pay"
    if decision == "reject":
        return "reject"
    return END          


def guarded(agent_fn):
    """Wrap any agent to catch unknown state keys during development."""
    def wrapper(state: InvoiceState):
        result = agent_fn(state)
        valid_keys = InvoiceState.__annotations__.keys()
        unknown = [k for k in result if k not in valid_keys]
        if unknown:
            raise KeyError(f"{agent_fn.__name__} wrote unknown state keys: {unknown}")
        return result
    return wrapper

def build_graph():
    graph = StateGraph(InvoiceState)

    # register nodes
    graph.add_node("ingest",         guarded(ingestion_agent))
    graph.add_node("validate",       guarded(validation_agent))
    graph.add_node("finance_review", guarded(accountant_agent))
    graph.add_node("await_vp",       guarded(vp_hold))
    graph.add_node("pay",            guarded(payment_agent))
    graph.add_node("reject",         guarded(rejection_handler))

    # define edges
    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "validate")

    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "finance_review": "finance_review",
            "reject": "reject"
        }
    )

    graph.add_conditional_edges(
        "finance_review",
        route_after_finance,
        {
            "pay": "pay",
            "await_vp": "await_vp",
            "reject": "reject"
        }
    )

    graph.add_conditional_edges(
        "await_vp",
        route_after_vp,
        {
            "pay": "pay",
            "reject": "reject",
            END: END
        }
    )

    graph.add_edge("pay", END)
    graph.add_edge("reject", END)

    return graph.compile()


# compile once and export
invoice_graph = build_graph()