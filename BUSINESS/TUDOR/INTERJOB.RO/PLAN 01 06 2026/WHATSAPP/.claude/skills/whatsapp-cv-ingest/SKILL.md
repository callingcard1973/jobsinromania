---
name: whatsapp-cv-ingest
description: Discover NEW CV files received via WhatsApp Web on raspi storage and produce a clean batch of unprocessed PDFs for the CV pipeline. Use when asked to "check WhatsApp CVs", "pull new CVs", "ingest WhatsApp files", "what CVs came in", or as stage 1 of the whatsapp-cv pipeline. Triggers on any WhatsApp inbound-file / CV-intake request.
---

# whatsapp-cv-ingest

Enumerate inbound WhatsApp files on raspi (`192.168.100.20`) and hand the cv-extractor a batch of only-new PDFs. The WhatsApp Web gateway drops files; it never parses. Discovery + dedup-by-path lives here.

## Storage layout
`/opt/ACTIVE/SCRAPER_DATA/cvs/{date}/{sender_phone}/{file}` — sender phone is the path segment, and it is the dedup key in `fw_candidates`.

## Procedure
1. List storage over SSH (`plink -batch -pw 'REDACTED' tudor@192.168.100.20`).
2. Diff against `_workspace/_seen_paths.txt` — keep only paths not already seen.
3. Partition: PDFs → batch; photos/voice/docx → `skipped:unsupported` (logged, not dropped — manual-chase leads).
4. Write `_workspace/01_cv-ingestor_batch.json` (`{path, sender_phone, received_date, mime}`) and append forwarded paths to `_seen_paths.txt`.

## Why dedup-by-path, not by content
A candidate may resend the same CV; re-parsing wastes work but is harmless. Re-ingesting the same *file path* twice is pure noise. Path-level dedup is cheap and exact; content/candidate dedup happens later in candidate-match where it belongs.

## Failure modes
- Host unreachable → STOP, report the SSH error. An empty batch from a down host looks identical to "no new CVs" — never let that ambiguity flow downstream.
- Reachable, 0 new PDFs → OK/empty; pipeline short-circuits cleanly.
