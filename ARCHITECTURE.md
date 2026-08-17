# Architecture

## Data Model Overview

### UserModel
- One row per registered clinician/user (`/register`)
- Password stored as an Argon2 hash (`pwdlib`), never in plaintext
- Owns `ProcedureModel` and `TranscriptModel` rows via `user_id`
- `/login` issues a JWT (HS256, 24h expiry) with `sub` = user id; every other endpoint requires this token as a `Bearer` header and resolves it back to a `UserModel` via `get_current_user`

### TranscriptModel
- Created via `POST /transcripts/start`, which now takes `patient_name`, `patient_dob`, and `patient_nhi` up front instead of starting blank — owned by the requesting user
- `transcript_id` is the primary key and is a **UUID** (`uuid.uuid4()`, server-generated), not an auto-increment integer
- `endoscopist_id` defaults to `1` at creation — `/transcripts/start` doesn't currently collect who's actually performing the procedure (see TODO)
- Stores LLM extracted draft data after `/transcribe/{transcript_id}`
- Purpose: crash recovery — if browser closes, draft can be retrieved
- Linked to Procedure via `procedure_id` once finalized
- Status: `IN_PROGRESS` if `procedure_id` is None, `FINALIZED`-equivalent once linked
- `polyps` / `findings` are stored as raw JSONB at this stage (not relational rows) since the data isn't verified yet
- Carries the same five cecal-landmark boolean columns as `ProcedureModel` (below), but with **no constraint** tying them to `cecum_reached` — a draft can freely say "cecum reached" with no supporting landmarks, since the clinician may not have entered everything yet

### Procedure
- Created on submit via `POST /transcripts/{transcript_id}/write`
- Stores doctor verified final clinical data, owned by the submitting user (`user_id`)
- This is the legal record
- Has related Polyps and Findings tables
- Linked back to TranscriptModel via `procedure_id`
- `status` column (`TranscriptStatus` enum, defaults to `FINALIZED`) — reuses the same enum type as `TranscriptModel.status`, which conflates two different lifecycle concepts under one name (see TODO)
- Five cecal-landmark boolean columns: `terminal_ileum_intubated`, `ileocecal_valve_identified`, `appendiceal_orifice_identified`, `tripartite_fold_identified`, `other_landmarks_identified`
- New `check_cecum_reached_criteria` constraint: if `cecum_reached = true`, at least one of `terminal_ileum_intubated`, (`appendiceal_orifice_identified` AND `ileocecal_valve_identified`), `tripartite_fold_identified`, or `other_landmarks_identified` must also be `true`. This is the clinical standard for documenting a complete cecal intubation, not just asserting it happened.

### Images
- Created by image upload endpoint
- Linked to TranscriptModel via `transcript_id` (required) — now a UUID FK, matching the `TranscriptModel` PK type change
- Re-linked to `procedure_id` once the transcript is finalized via `/write` (nullable until then)
- Ordered by `captured_at` timestamp for PDF generation
- File stored on filesystem, path and metadata in database
- `anatomic_location` / `label_source` columns exist but are never populated by the current capture pipeline

## Data Flows

### 1. Registration and Login
`POST /register` → username/email uniqueness check → password hashed with Argon2 → `UserModel` row created
`POST /login` → verifies password → issues a JWT (24h expiry) → client attaches it as `Authorization: Bearer <token>` on every subsequent request → `get_current_user` decodes the token and loads the `UserModel`, raising a clean 401 if the token is missing/invalid/expired or the user no longer exists

### 2. Transcript Creation
Clinician enters patient name, DOB, and NHI → `POST /transcripts/start` (auth required) → `TranscriptModel` row created with that patient data, `user_id` from the token, and `endoscopist_id` hardcoded to `1` → `transcript_id` (UUID) returned to browser and displayed

### 3. Image Capture (runs in parallel during procedure)
`python -m capture/image_capture.py` → prompts for username/password and calls `POST /login` to obtain a token → user enters transcript_id → SPACE key captures frame → saved locally → `POST /transcripts/{id}/images` (Bearer token, checked against `transcript.user_id`) → filesystem storage → path + metadata written to Images table

### 4. Browser Transcription and LLM Extraction
Browser speech recognition transcribes the procedure to text in real time (no audio file is sent to the server) → procedure ends → browser sends the transcribed text as a file upload, plus `cecum_reached_time` and `procedure_end_time` → `POST /transcribe/{transcript_id}` (Bearer token, checked against `transcript.user_id`) → GPT extracts structured data including the five cecal-landmark booleans (`extract_json_from_text`) → `build_report` attaches the **real** patient metadata already stored on the `TranscriptModel` row (the old random-placeholder `generate_fake_data` path is retired/commented out) → mapped and written to `TranscriptModel` as a draft → `full_report` returned to browser for verification

> The original Whisper-based audio transcription path (`transcribe_get_timestamps` + `extract_json`) still exists in `services/functions.py` but is no longer called from the endpoint — kept in case the team reverts to server-side transcription instead of browser speech recognition.

### 5. Draft Recovery
If browser closes mid verification → reopen → `GET /transcripts/{transcript_id}/draft` (Bearer token, checked against `transcript.user_id`) → returns TranscriptModel draft, including the landmark fields, if `procedure_id` is None (400 if already finalized) → doctor continues verification

### 6. Verification and PDF Generation
Doctor reviews LLM extracted data in browser → edits if needed, including the cecal-landmark checkboxes → submit → `POST /transcripts/{transcript_id}/write` (transcript_id is now a **path param**, moved from a query param; Bearer token, checked against `transcript.user_id`) → `write_transcription_record` creates Procedure with verified data and `user_id` → Images for that `transcript_id` are re-linked to the new `procedure_id` → `transcript.procedure_id` set → PDF generated with images ordered by `captured_at` → PDF written to filesystem → `procedure_id` + `pdf_url` returned
- If `cecum_reached = true` and none of the landmark criteria are satisfied, the `check_cecum_reached_criteria` constraint fires; this is caught explicitly and returned as a `422` with a clinician-readable message rather than a raw `500`.

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

### UUID transcript ids
`transcript_id` switched from an auto-increment integer to a server-generated UUID. Non-sequential, non-guessable identifiers reduce the blast radius of anything that leaks or logs an id — relevant since `GET /images/{image_id}` still has no auth at all (see TODO). `procedure_id` and `image_id` remain sequential integers.

### Cecal intubation criteria enforced only at finalize, not at draft time
`ColonoscopyReport` (LLM output) and `TranscriptModel` accept `cecum_reached = true` with no supporting landmark evidence — the clinician may not have dictated all of it yet, or the LLM may not have caught it. The stricter rule (at least one landmark documented) is enforced only by the `CHECK` constraint on `ProcedureModel`, surfaced as a `422` from `/transcripts/{transcript_id}/write`. This keeps the draft phase permissive while keeping the legal record clinically rigorous.

## TODO

- `endoscopist_id` is hardcoded to `1` in `POST /transcripts/start` — `StartProcedureRequest` has no field for the actual performing endoscopist, so every transcript/procedure is currently attributed to endoscopist #1 regardless of who's really doing the case. Needs a field added to the start request (and a frontend picker) once there's a real endoscopist directory to select from.
- `check_cecum_consistency` (requires `cecum_reached_time` when `cecum_reached = true`) is **not** given the same friendly-422 treatment as the new `check_cecum_reached_criteria` — a `/write` submission that fails this older constraint still surfaces as a generic `500 "Failed to write to database due to integrity error"`. Worth extending the same `IntegrityError` branching to cover it (and the other named constraints: `check_bbps_*`, `check_time_order`, `uq_patient_procedure_date`).
- `GET /images/{image_id}` has no auth at all — no `Bearer` token required and no check that the requesting user owns the parent transcript/procedure, unlike every other resource endpoint. UUID transcript ids reduce but don't eliminate the exposure here, since `image_id` is still a sequential integer.
- `TranscriptModel.status` and `ProcedureModel.status` share the same `TranscriptStatus` enum (`IN_PROGRESS` / `FINALIZED`) for two different lifecycles — works today but is confusing; consider separate enums.
- `anatomic_location` and `label_source` on `Images` are never populated — auto/manual image labelling isn't implemented yet.
- Build browser/UI to handle the recovery flow — check whether a transcript_id exists and offer to retrieve it to finish.
- Add Alembic for migrations. This matters more now than before: the `transcripts.transcript_id` PK type change from `Integer` to `UUID`, plus every new landmark column and constraint, were all applied via `create_all` against a fresh schema — there's no migration path for an existing database with data in it.
- CORS currently allows all origins (`allow_origins=['*']`) — fine for local development, should be locked down before handling real auth tokens in production.

### Recently fixed
- `transcription_route.py` calling `functions.map_transcription(full_report)` without `user_id`, which 500'd every `/transcribe` call — now passes `user_id=current_user.id`.
- `POST /transcripts/{transcript_id}/images` writing to a hardcoded, never-created `./uploads/{filename}` path — now uses `UPLOADS_DIR` from `config.py` (created at import time, same pattern as `OUTPUT_DIR`).
- `config.py` and `logger.py` both independently calling `logging.basicConfig` — removed the dead/unused copy from `config.py`; `app.logger.logger` is the one every module imports.
- `get_current_user`'s `except` blocks used to `print()` the error and fall through instead of raising, which meant an invalid/expired token could hit `db.get(UserModel, user_id)` with `user_id` still undefined and blow up as an unhandled `500` instead of a clean `401`. Each branch now raises the appropriate `HTTPException` directly.
- Patient/procedure metadata used to be randomly generated via `generate_fake_data()` on every `/transcribe` call — now sourced from the real patient info entered at `/transcripts/start` via `build_report()`. (The old function is retired/commented out in `functions.py`.)
