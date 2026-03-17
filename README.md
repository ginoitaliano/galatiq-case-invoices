# Invoice Processing Automation

> Acme Corp loses $2M/year on manual invoice processing. This is the system that stops that.

A production-grade multi-agent invoice processing pipeline built on LangGraph, xAI Grok, Anthropic Claude as a fallback, and FastAPI; with a React dashboard, VP approval workflow, LangSmith observability, batch processor, and a full eval harness.

---

## What It Does

Invoices arrive as PDFs, CSVs, JSON, or text files. The system extracts structured data, validates against inventory, routes for approval, and processes payment — automatically, with a full audit trail at every step.

```
Invoice File (PDF / CSV / JSON / TXT)
     │
     ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  Ingestion  │────▶│  Validation  │────▶│  Accountant Agent   │
│   Agent     │     │    Agent     │     │   (specialized)     │
│             │     │              │     │  initial assessment │
│ LLM extract │     │ SQLite check │     │  → self critique    │
│ structured  │     │ fraud flags  │     │  → final decision   │
│ invoice     │     │ 3-way match  │     │  (reflection loop)  │
└─────────────┘     └──────┬───────┘     └──────────┬──────────┘
                           │ fail                    │
                           ▼                         ▼
                    ┌─────────────┐        ┌─────────────────┐
                    │  Rejection  │◀───────│   VP Approval   │
                    │  Handler    │ reject │   (dashboard)   │
                    │             │        │                 │
                    │ LLM notice  │        │  awaiting_vp    │
                    │ audit trail │        │  → approve      │
                    └─────────────┘        └────────┬────────┘
                                                    │ approve
                                                    ▼
                                           ┌─────────────────┐
                                           │  Payment Agent  │
                                           │                 │
                                           │  mock payment   │
                                           │  ref + audit    │
                                           └─────────────────┘
```

**Business outcome:** 30% error rate → near zero. 5-day processing → minutes. Replaced VP email chains with one-click dashboard approval for faster and seamless invoice tracking.

---

## Quick Start

### Prerequisites

* Python 3.12+
* Node.js 18+
* Tesseract OCR (optional, for scanned PDF extraction)

### 1. Clone & install

```bash
git clone https://github.com/ginoitaliano/galatiq-case-invoices.git
cd galatiq-case-invoices
pip install -r requirements.txt   # in a production environment, poetry should be used
cd frontend && npm install && cd ..
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```
GROK_API_KEY=your-key               # primary LLM (xAI)
ANTHROPIC_API_KEY=your-key          # fallback LLM
LANGCHAIN_API_KEY=your-key          # LangSmith observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=invoice-processor
VP_APPROVAL_THRESHOLD=10000.00
```

### 3. Set up inventory database

```bash
python data/setup_inventory.py
```

### 4. Run

```bash
# Terminal 1 — backend API
cd backend && uvicorn main:app --reload

# Terminal 2 — React dashboard
cd frontend && npm start
```

* Dashboard: `http://localhost:3000`
* API docs: `http://localhost:8000/docs`

---

## CLI Usage

Process a single invoice from the command line:

```bash
cd backend
python main.py --invoice_path=../data/invoices/invoice_1001.txt
```

Example output:

```
============================================================
  INVOICE PROCESSOR
============================================================
  Processing: ../data/invoices/invoice_1001.txt

  Invoice    : INV-1001
  Vendor     : Widgets Inc.
  Total      : $5,000.00
  Stage      : completed
  Payment    : PAY-20260307172626

  Audit trail (4 entries):
    [ingestion] extracted_invoice
    [validation] validation_passed
    [accountant] accountant_decision_approve
    [payment] payment_processed
============================================================
```

---

## Test Suite

17 tests covering unit, integration, and pipeline scenarios — all run without API credits via mock LLM.

```bash
cd backend
pytest tests/test_pipeline.py -v
```

```
17 passed in 8.18s
```

---

## Eval Harness

Assert expected pipeline behavior across all 4 assessment scenarios:

```bash
cd backend
python tools/eval_harness.py --mock --verbose
```

```
=================================================================
  AGENT EVAL HARNESS
=================================================================

  [HAPPY PATH]
    ✓ INV-1001 — Clean invoice under $10K — should auto-approve
      Stage: completed | Duration: 9.0s

  [VALIDATION FAILURE]
    ✓ INV-1002 — Quantity exceeds available stock — should reject
      Stage: rejected | Duration: 0.1s
      Flags: is_quantity_mismatch

    ✓ INV-1003 — Zero stock item FakeItem — should reject
      Stage: rejected | Duration: 0.1s
      Flags: is_out_of_stock

  [ESCALATION]
    ✓ INV-1004 — Invoice over $10K threshold — should escalate to VP
      Stage: awaiting_vp | Duration: 0.1s

=================================================================
  RESULT: 4/4 passed  ALL PASSING
=================================================================
```

---

## Batch Processor

Process all invoices in a folder in one run:

```bash
cd backend
python tools/batch_process.py --mock --delay 0 --folder ../data/invoices
```

---

## Dashboard Demo (No API Credits)

Seed all 4 invoice scenarios directly into the dashboard:

```bash
curl -X POST http://localhost:8000/api/v1/invoices/seed
```

Then open `http://localhost:3000` — INV-1001 approved, INV-1002 and INV-1003 rejected with flags, INV-1004 waiting in the VP queue.

---

## Design Decisions

### Provider-agnostic LLM

Grok is the primary LLM, Claude is the fallback. The `llm_utils.py` layer abstracts the provider — switching a client from Grok to Claude (or any OpenAI-compatible API) is a one-line config change. This matters for enterprise deployments where clients may have existing API agreements or data residency requirements.

### Adapter pattern for SAP integration

The inventory lookup in `validation_agent.py` calls a single `get_inventory_item()` function backed by SQLite. In production, that function is swapped for a SAP BAPI call or REST adapter — without touching any agent logic. This is the correct pattern for enterprise integrations that need to swap data sources per client.

### Reflection loop in the accountant agent

The accountant makes three LLM calls: initial assessment → self-critique → final decision. This materially reduces false approvals on edge cases (borderline amounts, unusual payment terms, overdue invoices). The confidence score from the final decision feeds directly into VP escalation logic.

### VP approval as a graph pause, not a polling loop

When an invoice requires VP approval, LangGraph routes to a terminal `await_vp` node and stops. The VP acts via the dashboard, which calls the approvals API to resume the graph with a decision. No polling, no timeouts, no state held in memory between requests.

### Criteria-driven prompts over role-play framing

Agent prompts are structured around explicit decision criteria rather than persona framing. Criteria-driven prompts produce more consistent, auditable decisions — especially important when rejection notices need to hold up under vendor scrutiny.

### LangSmith from day one

Every agent run is traced automatically via `LANGCHAIN_TRACING_V2=true`. When something breaks at a client site, the trace shows exactly which agent failed, what inputs it received, and what it returned — without any additional instrumentation.

---

## Validation Scenarios Covered

| Invoice | Scenario | Expected outcome |
| --- | --- | --- |
| INV-1001 | Clean invoice, $5K, known items | Auto-approved, payment processed |
| INV-1002 | GadgetX qty 99, only 5 in stock | Rejected: quantity mismatch |
| INV-1003 | FakeItem, zero stock | Rejected: out of stock |
| INV-1004 | $12,500, exceeds $10K threshold | Escalated to VP |
| INV-1008 | SuperGizmo, MegaSprocket: unknown | Rejected: unknown items |
| INV-1009 | Negative quantity | Rejected: data integrity issue |
| INV-1013 | Deliberate total mismatch | Rejected: subtotal mismatch |
| INV-1016 | WidgetC: not in catalog | Rejected: unknown item |

---

## Security & Production Considerations

This is a working prototype. Production deployment would require:

**Authentication & Authorization**

* JWT auth on all API endpoints
* Role-based access control: AP staff, VP, and auditors have different permissions
* The VP approval endpoint is the highest risk surface and must be scoped to VP role only

**Data**

* Replace SQLite with Postgres for the app database
* Encrypt invoice data at rest — invoices contain sensitive vendor and pricing information
* Audit trail is append-only by design; in production, back it to an immutable log store

**Infrastructure**

* The `invoice_store` is currently in-memory — in production, replace with Redis or Postgres so the API can restart without losing state
* LangGraph graph state should be checkpointed to Postgres using LangGraph's built-in checkpointer for long-running VP approval workflows

**LLM**

* Retry logic with exponential backoff for API rate limits
* Set token budget limits per invoice to prevent runaway costs on malformed inputs
* Log prompt/completion tokens per agent node via LangSmith for cost attribution per client

---

## Phase 2: Production Hardening

* **Real SAP integration**: swap `get_inventory_item()` for SAP BAPI adapter. The interface is already defined; the implementation is a one-function change.
* **Real payment API**: replace `mock_payment()` with actual banking API (Stripe Treasury, Plaid, or client's existing provider)
* **PDF OCR pipeline**: Tesseract is wired in; add confidence scoring and human-in-the-loop fallback for low-confidence extractions
* **Vendor portal**: self-service portal where vendors check invoice status and resubmit rejected invoices with corrections
* **Snowflake integration**: push processed invoice data to Snowflake for CFO-level reporting and cash flow forecasting

## Phase 3: Intelligence Layer

* **Cross-invoice knowledge graph** (Neo4j): detect patterns across invoices — duplicate submissions, vendor pricing drift, coordinated fraud across multiple vendors
* **Anomaly detection**: flag invoices that deviate statistically from a vendor's historical baseline across price, quantity, and frequency
* **Parallel eval infrastructure** (Daytona): run eval harness across 100+ invoice scenarios in parallel on every commit, with regression alerts
* **Fine-tuned extraction model**: replace general-purpose LLM extraction with a model fine-tuned on Acme Corp's specific invoice formats, reducing extraction errors and latency
* **Salesforce integration**: sync vendor approval status and payment history to Salesforce for account management visibility

---

## Project Structure

```
invoice-processor/
├── backend/
│   ├── main.py                  ← FastAPI app + CLI entry point
│   ├── config.py                ← pydantic-settings config
│   ├── agents/
│   │   ├── graph.py             ← LangGraph StateGraph
│   │   ├── state.py             ← InvoiceState TypedDict
│   │   ├── ingestion_agent.py   ← LLM extraction
│   │   ├── validation_agent.py  ← SQLite 3-way match
│   │   ├── accountant_agent.py  ← reflection loop
│   │   ├── payment_agent.py     ← mock payment
│   │   └── rejection_handler.py ← LLM rejection notice
│   ├── api/
│   │   ├── invoices.py          ← process, seed, get endpoints
│   │   ├── approvals.py         ← VP approval endpoint
│   │   └── metrics.py           ← dashboard metrics
│   ├── services/
│   │   ├── invoice_service.py   ← pipeline orchestration
│   │   ├── approval_service.py  ← VP decision logic
│   │   └── metrics_service.py   ← approval rate, totals
│   ├── tests/
│   │   ├── mock_llm.py          ← deterministic mock LLM
│   │   └── test_pipeline.py     ← 17 tests, no API credits needed
│   └── tools/
│       ├── batch_process.py     ← process invoice folders
│       ├── eval_harness.py      ← assert expected outcomes
│       └── langsmith_traces.py  ← pull & display traces
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── MetricsBar.tsx       ← total / approved / rejected
│       │   ├── InvoiceQueue.tsx     ← live invoice list
│       │   ├── InvoiceDetail.tsx    ← full invoice view
│       │   └── VPApprovalPanel.tsx  ← VP approve / reject UI
│       └── App.tsx
└── data/
    ├── invoices/                ← 19 test invoices (PDF/CSV/JSON/TXT)
    ├── setup_inventory.py       ← creates inventory.db
    └── inventory.db             ← SQLite mock SAP inventory
```

---

Built by [@Ginoitaliano](https://github.com/Ginoitaliano)
