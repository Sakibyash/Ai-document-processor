INVOICE_EXTRACTION_PROMPT = """You are an invoice data extraction engine. Extract structured data from the document text below.

Rules:
- NEVER invent values. If a field is not present in the document, return null.
- First classify the document: "invoice" (has invoice number, bill-to/ship-to, payment terms), "receipt" (proof of purchase: merchant, date, items, total paid, payment method), "statement" (account summary over a period), or "unknown".
- For receipts, fill merchant_name, transaction_date, payment_method; invoice_number may be null.
- For invoices, fill invoice_number, invoice_date, supplier_name, customer_name; receipt fields may be null.
- Preserve the original currency code (e.g. "USD", "BDT", "EUR"). Do not convert amounts.
- Extract ALL available line items.
- If a value is present but you are unsure of it (blurry OCR, ambiguous format), include the field name in "uncertain_fields".
- If a required field is absent, include it in "missing_fields".
- Dates must be ISO format (YYYY-MM-DD) when possible; otherwise keep the original string.
- Amounts must be plain numbers without currency symbols or thousands separators.

Return ONLY valid JSON matching this schema:
{
  "document_type": "invoice" | "receipt" | "statement" | "unknown",
  "invoice_number": string | null,
  "invoice_date": string | null,
  "supplier_name": string | null,
  "customer_name": string | null,
  "merchant_name": string | null,
  "transaction_date": string | null,
  "payment_method": string | null,
  "subtotal": number | null,
  "tax": number | null,
  "total": number | null,
  "currency": string | null,
  "line_items": [{"description": string|null, "quantity": number|null, "unit_price": number|null, "amount": number|null}],
  "missing_fields": [string],
  "uncertain_fields": [string]
}

Document text:
{text}
"""


def build_prompt(document_text: str, max_chars: int = 60_000) -> str:
    """Substitute document text into the template.

    Uses replace() not str.format() because the template contains literal
    JSON braces that format() would treat as fields (regression: KeyError
    on '"invoice_number"').
    """
    return INVOICE_EXTRACTION_PROMPT.replace("{text}", document_text[:max_chars])
