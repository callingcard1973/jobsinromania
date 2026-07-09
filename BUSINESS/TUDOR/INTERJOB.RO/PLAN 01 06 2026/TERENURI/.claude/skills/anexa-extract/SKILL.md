---
name: anexa-extract
description: Extract structured fields (seller, email, phone, area ha, price, locality, county) from MADR Anexa 1B land-sale PDFs using a ZERO-TOKEN local stack — pdftotext for digital PDFs, tesseract OCR (ron+eng) for scanned ones, then regex / optional local Ollama. Use when parsing land-offer PDFs, OCR-ing scanned anexe, or extracting seller leads from MADR offers.
---

# anexa-extract (zero-token)

Parse Anexa 1B PDFs into land-offer leads without spending any Claude/API tokens. Runs on raspibig (.21): `pdftotext`, `pdftoppm`, `tesseract -l ron+eng` all present.

## The reality this handles
~70% of Anexă PDFs are **scanned images** (no text layer); ~30% born-digital. Layout varies per primărie, so brittle regex alone fails even on digital. The stack:

1. **Text**: `pdftotext -layout`. ≥200 chars → digital, done.
2. **OCR** (scanned): `pdftoppm -r 300 -png` → `tesseract <png> - -l ron+eng --psm 6`, concat pages. 300dpi + ron pack is the accuracy sweet spot for these forms.
3. **Extract**: lenient regex (OCR drops diacritics, garbles â/ţ — never anchor on them). Pull the header-paren hectares, "la preţul de X lei", `Subsemnatul NAME, CNP`, inline email, `tel: …`.
4. **Optional local LLM**: if an Ollama/llama-server endpoint on .21 responds, hand messy OCR text to it for JSON-schema extraction (vânzător/email/telefon/suprafață/preţ). Still **zero API cost**. NEVER call a paid API here.
5. **Gate**: <3 fields → `needs_review=1`. Don't waste effort on hopeless scans.

## What matters most
County + locality come FREE from the offer URL — don't depend on the PDF for them. **Email + phone are the lead-gold**, and OCR captures them reliably (we pulled a phone off a scanned anexă in testing). An offer with just an email is already an actionable land-broker lead.

## Audit
Record `_extract_mode` (digital|ocr) per row so coverage and OCR-yield stay measurable across runs.

## Failure modes
- tesseract/poppler absent → digital-only, flag rest `needs_ocr`, report the missing tool (don't silently under-cover).
