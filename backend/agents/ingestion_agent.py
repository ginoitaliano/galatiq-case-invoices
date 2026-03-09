# backend/agents/ingestion_agent.py
import pdfplumber
import pytesseract
import fitz
import json
import io
from pathlib import Path
from datetime import datetime
from pydantic import ValidationError
import PIL.Image

from agents.state import InvoiceState, AuditEntry
from agents.reasoning_agent import call_llm, INGESTION_PERSONA
from models.invoice import Invoice
from config import settings



#TEXT Extraction
def extract_text(file_path: str) -> str:
    """Extract raw text from any supported file type."""
    path = Path(file_path)

    # plain text formats
    if path.suffix.lower() in [".txt", ".json", ".csv"]:
        return path.read_text(encoding="utf-8", errors="ignore")

    # PDF digital first
    if path.suffix.lower() == ".pdf":
        try:
            with pdfplumber.open(file_path) as pdf:
                text = "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
                if text.strip():
                    return text
        except Exception:
            pass

        # OCR fallback for scanned PDFs
        try:
            doc = fitz.open(file_path)
            text_parts = []
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = PIL.Image.open(io.BytesIO(pix.tobytes("png")))
                text_parts.append(pytesseract.image_to_string(img))
            return "\n".join(text_parts)
        except Exception as e:
            return f"ERROR: {str(e)}"

    return f"ERROR: Unsupported file type: {path.suffix}"




def parse_invoice_with_llm(raw_text: str) -> dict:
    """Send raw text to Claude, get structured JSON back."""
    response = call_llm(
        persona=INGESTION_PERSONA,
        user_message=f"Extract invoice data from this document:\n\n{raw_text}"
    )
    clean = response.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


#Agent

def ingestion_agent(state: InvoiceState) -> InvoiceState:
    """Extract structured invoice data from raw files."""
    file_path = state["file_path"]
    timestamp = datetime.now().isoformat()

    try:
        #  extract raw text
        raw_text = extract_text(file_path)
        state["raw_text"] = raw_text

        if raw_text.startswith("ERROR:"):
            raise ValueError(raw_text)

        #  LLM parses raw text into structured dict
        extracted = parse_invoice_with_llm(raw_text)

        #  Pydantic validates dict into Invoice object
        invoice = Invoice(
            invoice_number=extracted.get("invoice_number", "UNKNOWN"),
            vendor=extracted.get("vendor", {"name": "UNKNOWN"}),
            date=extracted.get("date", ""),
            due_date=extracted.get("due_date", ""),
            line_items=extracted.get("line_items", []),
            subtotal=extracted.get("subtotal", 0.0),
            tax_rate=extracted.get("tax_rate"),
            tax_amount=extracted.get("tax_amount"),
            total=extracted.get("total", 0.0),
            currency=extracted.get("currency", "USD"),
            payment_terms=extracted.get("payment_terms"),
            notes=extracted.get("notes")
        )

        #  write to state
        state["invoice"] = invoice
        state["extraction_confidence"] = extracted.get("extraction_confidence", 0.5)
        state["current_stage"] = "validation"

        #  human review if confidence is low
        if state["extraction_confidence"] < settings.extraction_confidence_threshold:
            state["requires_vp_approval"] = True

        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="ingestion",
            action="extracted_invoice",
            message=f"Successfully extracted {invoice.invoice_number} from {file_path}",
            flags=None
        ))

    except ValidationError as e:
        state["error"] = f"Pydantic validation failed: {str(e)}"
        state["current_stage"] = "failed"
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="ingestion",
            action="validation_failed",
            message=str(e),
            flags=None
        ))

    except json.JSONDecodeError as e:
        state["error"] = f"Claude returned malformed JSON: {str(e)}"
        state["current_stage"] = "failed"
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="ingestion",
            action="json_parse_failed",
            message=str(e),
            flags=None
        ))

    except Exception as e:
        state["error"] = f"Unexpected error: {str(e)}"
        state["current_stage"] = "failed"
        state["audit_trail"].append(AuditEntry(
            timestamp=timestamp,
            agent="ingestion",
            action="failed",
            message=str(e),
            flags=None
        ))

    return state