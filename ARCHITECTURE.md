# Architecture

## Data Model Overview

### UserModel
- One row per registered clinician/user (`/register`)
- Password stored as an Argon2 hash (`pwdlib`), never in plaintext
- Owns `ProcedureModel` and `TranscriptModel` rows via `user_id`
- `/login` issues a JWT (HS256, 24h expiry) with `sub` = user id; every other endpoint requires this token as a `Bearer` header and resolves it back to a `UserModel` via `get_current_user`

### TranscriptModel
- Created on start button press (`POST /transcripts/start`), owned by the requesting user
- Stores LLM extracted draft data after `/transcribe/{transcript_id}`
- Purpose: crash recovery — if browser closes, draft can be retrieved
- Linked to Procedure via `procedure_id` once finalized
- Status: `IN_PROGRESS` if `procedure_id` is None, `FINALIZED`-equivalent once linked
- `polyps` / `findings` are stored as raw JSONB at this stage (not relational rows) since the data isn't verified yet

### Procedure
- Created on submit via `/write` endpoint
- Stores doctor verified final clinical data, owned by the submitting user (`user_id`)
- This is the legal record
- Has related Polyps and Findings tables
- Linked back to TranscriptModel via `procedure_id`
- `status` column (`TranscriptStatus` enum, defaults to `FINALIZED`) — reuses the same enum type as `TranscriptModel.status`, which conflates two different lifecycle concepts under one name (see TODO)

### Images
- Created by image upload endpoint
- Linked to TranscriptModel via `transcript_id` (required)
- Re-linked to `procedure_id` once the transcript is finalized via `/write` (nullable until then)
- Ordered by `captured_at` timestamp for PDF generation
- File stored on filesystem, path and metadata in database
- `anatomic_location` / `label_source` columns exist but are never populated by the current capture pipeline

## Data Flows

### 1. Registration and Login
`POST /register` → username/email uniqueness check → password hashed with Argon2 → `UserModel` row created
`POST /login` → verifies password → issues a JWT (24h expiry) → client attaches it as `Authorization: Bearer <token>` on every subsequent request → `get_current_user` decodes the token and loads the `UserModel`, raising 401 if the token is missing/invalid/expired or the user no longer exists

### 2. Transcript Creation
Start button → `POST /transcripts/start` (auth required) → TranscriptModel row created with `user_id` from the token → transcript_id returned to browser and displayed

### 3. Image Capture (runs in parallel during procedure)
`python -m capture/image_capture.py` → prompts for username/password and calls `POST /login` to obtain a token → user enters transcript_id → SPACE key captures frame → saved locally → `POST /transcripts/{id}/images` (Bearer token, checked against `transcript.user_id`) → filesystem storage → path + metadata written to Images table

### 4. Browser Transcription and LLM Extraction
Browser speech recognition transcribes the procedure to text in real time (no audio file is sent to the server) → procedure ends → browser sends the transcribed text as a file upload, plus `cecum_reached_time` and `procedure_end_time` → `POST /transcribe/{transcript_id}` (Bearer token, checked against `transcript.user_id`) → GPT extracts structured data (`extract_json_from_text`) → placeholder patient metadata attached (`generate_fake_data`) → mapped and written to TranscriptModel as a draft → `full_report` returned to browser for verification

> The original Whisper-based audio transcription path (`transcribe_get_timestamps` + `extract_json`) still exists in `services/functions.py` but is no longer called from the endpoint — kept in case the team reverts to server-side transcription instead of browser speech recognition.

### 5. Draft Recovery
If browser closes mid verification → reopen → `GET /transcripts/{transcript_id}/draft` (Bearer token, checked against `transcript.user_id`) → returns TranscriptModel draft if `procedure_id` is None (400 if already finalized) → doctor continues verification

### 6. Verification and PDF Generation
Doctor reviews LLM extracted data in browser → edits if needed → submit → `POST /write?transcript_id=...` (Bearer token, checked against `transcript.user_id`) → `write_transcription_record` creates Procedure with verified data and `user_id` → Images for that `transcript_id` are re-linked to the new `procedure_id` → `transcript.procedure_id` set → PDF generated with images ordered by `captured_at` → PDF written to filesystem → `procedure_id` + `pdf_url` returned

### 7. Procedure Retrieval
`GET /procedures/{procedure_id}/full` (Bearer token, checked against `procedure.user_id`) → returns the procedure with polyps and findings

## Key Design Decisions

### Browser speech recognition over server side LLM transcription
Real time feedback during procedure. No audio file to store and process. Doctor can see and correct transcription as it happens.

### State in database not browser
TranscriptModel written immediately after LLM extraction. Crash resilience — browser can close without losing work. Single source of truth.

### Two separate tables — TranscriptModel and Procedure
TranscriptModel: unverified LLM draft, temporary working document
Procedure: doctor verified legal record
Preserved separately for audit trail and research — can compare LLM accuracy to doctor corrections

### Images ordered by captured_at timestamp
Mirrors actual procedure sequence. Clinically correct ordering for the PDF report.

### Withdrawal time computed in database
Derived from cecum_reached_time and procedure_end_time. Single source of truth. Updates automatically if timestamps corrected.

### Doctor verification before PDF generation
PDF is a legal medical record. LLM extraction is not infallible. Doctor must review and approve before anything becomes the official document.

### JWT bearer auth with per-row ownership checks
Every procedure/transcript row carries a `user_id`. Each route independently loads the resource and compares `resource.user_id == current_user.id`, returning 403 on mismatch, rather than filtering the query by user up front. Simple to reason about one endpoint at a time, but the ownership check is duplicated across every route file instead of centralized in a dependency.

## TODO

- `transcription_route.py` calling `functions.map_transcription(full_report)` without `user_id` — FIXED, now passes `user_id=current_user.id`.
- `POST /transcripts/{transcript_id}/images` writing to a hardcoded, never-created `./uploads/{filename}` path — FIXED, now uses `UPLOADS_DIR` from `config.py` (created at import time, same pattern as `OUTPUT_DIR`).
- `config.py` and `logger.py` both independently calling `logging.basicConfig` — FIXED, removed the dead/unused copy from `config.py`; `app.logger.logger` is the one every module imports.
- `GET /images/{image_id}` has no auth at all — no `Bearer` token required and no check that the requesting user owns the parent transcript/procedure, unlike every other resource endpoint.
- `TranscriptModel.status` and `ProcedureModel.status` share the same `TranscriptStatus` enum (`IN_PROGRESS` / `FINALIZED`) for two different lifecycles — works today but is confusing; consider separate enums.
- `anatomic_location` and `label_source` on `Images` are never populated — auto/manual image labelling isn't implemented yet.
- Patient/procedure metadata is still randomly generated via `generate_fake_data()` — no real metadata source wired up.
- Build browser/UI to handle the recovery flow — check whether a transcript_id exists and offer to retrieve it to finish.
- Add Alembic for migrations.
- CORS currently allows all origins (`allow_origins=['*']`) — fine for local development, should be locked down before handling real auth tokens in production.
