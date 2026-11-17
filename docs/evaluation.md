# Evaluation

Fill in with **measured** numbers from your labeled test set — do not estimate.

## Test dataset

| Metric | Value |
|---|---|
| Total documents | |
| Digital PDFs | |
| Scanned PDFs / images (OCR) | |
| Excel / CSV | |
| Corrupted / unsupported files | |

## Extraction accuracy (field-level)

| Field | Correct / Total | Accuracy |
|---|---|---|
| invoice_number | | |
| invoice_date | | |
| supplier_name | | |
| customer_name | | |
| subtotal | | |
| tax | | |
| total | | |
| currency | | |
| line_items (exact match) | | |

## System metrics

| Metric | Value |
|---|---|
| Document processing success rate | |
| OCR success rate (scanned docs) | |
| Average processing time per document | |
| Failure rate | |
| Validation precision (errors that were real) | |
| Duplicate detection: true positives / false positives | |

## Notes

- Model used: `OPENAI_MODEL` value + version/date
- Prompt version: see `app/ai/prompts.py`
- Known failure modes observed:
