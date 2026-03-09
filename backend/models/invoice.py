#backend/models/invoice.py
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List
from enum import Enum
import pycountry


class PaymentTerms(str,Enum):
  NET_30 = "Net 30"
  NET_60 = "Net 60"
  NET_90 = "Net 90"
  NET_120 = "Net 120"
  NET_180 = "Net 180"
  NET_360 = "Net 360"


class LineItem(BaseModel):
    item: str
    quantity: int
    unit_price: float
    amount: float
    note: Optional[str] = None

class Vendor(BaseModel):
    name: str
    address: Optional[str] = None

class Invoice(BaseModel):
    invoice_number: str
    vendor: Vendor
    date: str
    due_date: str
    line_items: List[LineItem]
    subtotal: float
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    total: float
    payment_terms: Optional[PaymentTerms] = None
    notes: Optional[str] = None
    currency: str = "USD"
   
    @field_validator("currency")
    @classmethod
    def validate_currency(cls,v):
        valid_currencies = {c.alpha_3 for c in pycountry.currencies}
        if v.upper() not in valid_currencies:
            raise ValueError(f"{v} is not a valid ISO 4217 currency code")
        return v.upper()

    @model_validator(mode="after")
    def validate_due_date(self):    
        if self.due_date and self.date:
            if self.due_date < self.date:
                raise ValueError("Due date cannot be before the date")
        return self


class InvoiceResponse(BaseModel):
    invoice_number: str
    vendor: Vendor
    date: str
    due_date: str
    line_items: List[LineItem]
    subtotal: float
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    total: float
    currency: str
    payment_terms: Optional[PaymentTerms] = None