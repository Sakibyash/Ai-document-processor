from typing import Literal

from pydantic import BaseModel, Field


class LineItemSchema(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None


class InvoiceExtraction(BaseModel):
    """Structured output expected from the LLM. None means 'not found' — never invented."""

    document_type: Literal["invoice", "receipt", "statement", "unknown"] = "unknown"
    invoice_number: str | None = None
    invoice_date: str | None = None  # ISO date string
    supplier_name: str | None = None
    customer_name: str | None = None
    # Receipt-specific fields (null for invoices)
    merchant_name: str | None = None
    transaction_date: str | None = None
    payment_method: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    currency: str | None = None
    line_items: list[LineItemSchema] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    uncertain_fields: list[str] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    field: str | None = None
    message: str
    severity: Literal["error", "warning", "info"] = "error"


class ValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
