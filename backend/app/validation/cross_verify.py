"""Cross-document verification: compare two extracted records field-by-field."""
from decimal import Decimal

from app.schemas import ValidationIssue, ValidationResult

NUMERIC_FIELDS = ["subtotal", "tax", "total"]
TEXT_FIELDS = ["document_type", "invoice_number", "invoice_date", "supplier_name", "customer_name",
               "merchant_name", "transaction_date", "payment_method", "currency"]
TOLERANCE = Decimal("0.01")


def _dec(v) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def compare_records(a: dict, b: dict) -> ValidationResult:
    """a = primary (e.g. PDF invoice), b = secondary (e.g. Excel record)."""
    issues: list[ValidationIssue] = []

    for field in TEXT_FIELDS:
        va, vb = a.get(field), b.get(field)
        if va and vb and str(va).strip().lower() != str(vb).strip().lower():
            issues.append(
                ValidationIssue(field=field, message=f"{field} mismatch: '{va}' vs '{vb}'", severity="warning")
            )

    for field in NUMERIC_FIELDS:
        da, db = _dec(a.get(field)), _dec(b.get(field))
        if da is not None and db is not None and abs(da - db) > TOLERANCE:
            issues.append(
                ValidationIssue(
                    field=field,
                    message=f"{field} mismatch: {da} vs {db} (difference {da - db})",
                    severity="error",
                )
            )

    has_error = any(i.severity == "error" for i in issues)
    return ValidationResult(valid=not has_error, issues=issues)
