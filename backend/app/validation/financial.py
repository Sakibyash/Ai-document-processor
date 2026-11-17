"""Financial validation using Decimal arithmetic to avoid float rounding errors."""
from decimal import Decimal, InvalidOperation

from app.schemas import InvoiceExtraction, ValidationIssue, ValidationResult

TOLERANCE = Decimal("0.01")
REQUIRED_FIELDS = ["invoice_number", "invoice_date", "supplier_name", "total"]


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def validate_invoice(inv: InvoiceExtraction) -> ValidationResult:
    issues: list[ValidationIssue] = []

    # Missing required fields
    for field in REQUIRED_FIELDS:
        if getattr(inv, field, None) in (None, ""):
            issues.append(ValidationIssue(field=field, message=f"Missing required field: {field}", severity="error"))

    subtotal = _to_decimal(inv.subtotal)
    tax = _to_decimal(inv.tax)
    total = _to_decimal(inv.total)

    # Total = subtotal + tax (when all present)
    if subtotal is not None and tax is not None and total is not None:
        expected = subtotal + tax
        if abs(expected - total) > TOLERANCE:
            issues.append(
                ValidationIssue(
                    field="total",
                    message=f"Total mismatch: subtotal ({subtotal}) + tax ({tax}) = {expected}, but total is {total}",
                    severity="error",
                )
            )

    # Line items: amount ≈ quantity * unit_price; sum check vs subtotal
    line_sum = Decimal("0")
    any_line_amount = False
    for i, item in enumerate(inv.line_items):
        qty = _to_decimal(item.quantity)
        price = _to_decimal(item.unit_price)
        amount = _to_decimal(item.amount)
        if qty is not None and price is not None and amount is not None:
            expected_line = qty * price
            if abs(expected_line - amount) > TOLERANCE:
                issues.append(
                    ValidationIssue(
                        field=f"line_items[{i}].amount",
                        message=f"Line item {i}: quantity*unit_price = {expected_line}, amount is {amount}",
                        severity="warning",
                    )
                )
        if amount is not None:
            line_sum += amount
            any_line_amount = True

    if any_line_amount and subtotal is not None and abs(line_sum - subtotal) > TOLERANCE:
        issues.append(
            ValidationIssue(
                field="subtotal",
                message=f"Line items sum ({line_sum}) does not match subtotal ({subtotal})",
                severity="warning",
            )
        )

    # Uncertain fields -> warnings
    for field in inv.uncertain_fields:
        issues.append(ValidationIssue(field=field, message=f"Uncertain extraction: {field}", severity="warning"))

    has_error = any(i.severity == "error" for i in issues)
    return ValidationResult(valid=not has_error, issues=issues)
