---
name: whatsapp-cv-extract
description: Parse WhatsApp CV PDFs into structured candidate fields (name, email, phone, nationality, skills, target jobs) using the existing cv_extract.py parser. Use when asked to "parse the CVs", "extract candidate data", "read these CV PDFs", or as stage 2 of the whatsapp-cv pipeline. Triggers whenever WhatsApp CV PDFs need turning into structured records.
---

# whatsapp-cv-extract

Turn the ingested PDF batch into clean candidate records, reusing `backend/cv_extract.py`. Do NOT re-implement extraction and do NOT touch the database — this skill produces JSON only.

## The parser (reuse, don't rebuild)
`extract_and_parse_cv(path)` already does: poppler `pdftotext -layout` (fastest) → pypdf → pdfplumber fallback; precompiled regexes for email/phone; keyword maps for nationality, skills, and target-job verticals. It returns the canonical `fw_candidates` shape.

## Procedure
1. Read `_workspace/01_cv-ingestor_batch.json`.
2. For each PDF, call the host-side parser over SSH (raspi `/opt/ACTIVE/WHATSAPP/backend`).
3. Keep a record only if it has name OR email OR phone; otherwise count `unparseable`.
4. Normalize phone to digits/`+` form (downstream dedup key).
5. Write `_workspace/02_cv-extractor_parsed.json` + report parsed / unparseable / with-email / with-phone.

## Why the name-or-email-or-phone gate
A CV with none of these is unactionable — you cannot contact or dedup it. Forwarding it would inflate counts and create phantom duplicates. Drop at this boundary, not later.

## Failure modes
- Single corrupt PDF → fallback parsers, else count `unparseable`, continue. One bad file never aborts the batch.
- Entire batch unparseable (0/N) → this is a tool/dependency regression on the host (missing `pdftotext`), not bad CVs. Flag whatsapp-monitor.
