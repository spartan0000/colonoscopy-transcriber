# Architecture

## Data Model Overview

### UserModel
- One row per registered clinician/user (`/register`)
- Password stored as an Argon2 hash (`pwdlib`), never in plaintext
- `endoscopist_id` — nullable FK to `endoscopist_lookup`, linking a login to a specific endoscopist. **`/register` has no field to set this**, so every newly registered user currently has `endoscopist_id = NULL` unless it's set directly in the database (see TODO)
- Owns `ProcedureModel` and `TranscriptModel` rows via `user_id`
- `/login` issues a JWT (HS256, 24h expiry) with `sub` = user id; every other endpoint requires this token as a `Bearer` header and resolves it back to a `UserModel` via `get_current_user`

### TranscriptModel
- Created via `POST /transcripts/start`, which takes `patient_name`, `patient_dob`, and `patient_nhi` up front — owned by the requesting user
- `transcript_id` is the primary key and is a **UUID** (`uuid.uuid4()`, server-generated), not an auto-increment integer
- `endoscopist_id` is copied from `current_user.endoscopist_id` at creation time — meaning it inherits the same NULL gap described above until every user has one assigned
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
- `check_cecum_reached_criteria` constraint: if `cecum_reached = true`, at least one of `terminal_ileum_intubated`, (`appendiceal_orifice_identified` AND `ileocecal_valve_identified`), `tripartite_fold_identified`, or `other_landmarks_identified` must also be `true` — the clinical standard for documenting a complete cecal intubation, not just asserting it happened

### Images
- Created by image upload endpoint
- Linked to TranscriptModel via `transcript_id` (required) — a UUID FK, matching the `TranscriptModel` PK type
- Re-linked to `procedure_id` once the transcript is finalized via `/write` (nullable until then)
- Ordered by `captured_at` timestamp for PDF generation
- File stored on filesystem, path and metadata in database
- `anatomic_location` / `label_source` columns exist but are never populated by the current capture pipeline
- Now only retrievable by the owning user (see Data Flows below) — the `GET /images/{image_id}` auth gap noted in earlier versions of this doc is fixed

## Data Flows

### 1. Registration and Login
`POST /register` → username/email uniqueness check → password hashed with Argon2 → `UserModel` row created (with `endoscopist_id = NULL`, since there's no field to set it)
`POST /login` → verifies password → issues a JWT (24h expiry) → client attaches it as `Authorization: Bearer <token>` on every subsequent request → `get_current_user` decodes the token and loads the `UserModel`, raising a clean 401 if the token is missing/invalid/expired or the user no longer exists

### 2. Transcript Creation
Clinician enters patient name, DOB, and NHI → `POST /transcripts/start` (auth required) → `TranscriptModel` row created with that patient data, `user_id` from the token, and `endoscopist_id` copied from `current_user.endoscopist_id` → `transcript_id` (UUID) returned to browser and displayed

### 3. Image Capture (runs in parallel during procedure)
`python -m capture/image_capture.py` → prompts for username/password and calls `POST /login` to obtain a token → user enters transcript_id → SPACE key captures frame → saved locally → `POST /transcripts/{id}/images` (Bearer token, checked against `transcript.user_id`) → filesystem storage → path + metadata written to Images table

### 4. Browser Transcription and LLM Extraction
Browser speech recognition transcribes the procedure to text in real time (no audio file is sent to the server) → procedure ends → browser sends the transcribed text as a file upload, plus `cecum_reached_time` and `procedure_end_time` → `POST /transcribe/{transcript_id}` (Bearer token, checked against `transcript.user_id`) → GPT extracts structured data including the five cecal-landmark booleans (`extract_json_from_text`) → `add_time_stamps` now correctly threads those landmark booleans through onto the timestamped report (previously they were dropped here even though the LLM extracted them — fixed) → `build_report` attaches the real patient metadata already stored on the `TranscriptModel` row → mapped and written to `TranscriptModel` as a draft → `full_report` returned to browser for verification

> The original Whisper-based audio transcription path (`transcribe_get_timestamps` + `extract_json`) still exists in `services/functions.py` but is no longer called from the endpoint — kept in case the team reverts to server-side transcription instead of browser speech recognition.

### 5. Draft Recovery
If browser closes mid verification → reopen → `GET /transcripts/{transcript_id}/draft` (Bearer token, checked against `transcript.user_id`) → returns TranscriptModel draft, including the landmark fields, if `procedure_id` is None (400 if already finalized) → doctor continues verification

### 6. Verification and PDF Generation
Doctor reviews LLM extracted data in browser → edits if needed, including the cecal-landmark checkboxes → submit → `POST /transcripts/{transcript_id}/write` (transcript_id is a path param; Bearer token, checked against `transcript.user_id`) → `write_transcription_record` creates Procedure with verified data and `user_id` → Images for that `transcript_id` are re-linked to the new `procedure_id` → `transcript.procedure_id` set → PDF generated with images ordered by `captured_at` → PDF written to filesystem → `procedure_id` + `pdf_url` returned
- Constraint violations at this step are now translated into clinician-readable `422` responses via a lookup table (`CONSTRAINT_ERROR_MESSAGES` in `write_db_generate_pdf_route.py`) covering `check_cecum_reached_criteria`, `check_cecum_consistency`, `check_bbps_right/transverse/left`, `check_time_order`, and `uq_patient_procedure_date`. Any other integrity error still falls back to a generic `500`.

### 7. Procedure Retrieval
`GET /procedures/{procedure_id}/full` (Bearer token, checked against `procedure.user_id`) → returns the procedure with polyps and findings

### 8. Image Retrieval
`GET /images/{image_id}` (Bearer token required) → loads the image, then loads its parent `TranscriptModel` by `transcript_id` and checks `transcript.user_id == current_user.id` → 403 if it belongs to someone else, 404 if the image or its file on disk doesn't exist → serves the PNG

## How Data Flows Through the App

This traces each category of data from where it originates to where it ends up, cutting across the endpoint-by-endpoint flows above.

**User data (accounts/credentials).** Created once, at `/register`, and never touched again by any other endpoint — there's no profile-update or password-change endpoint yet. `UserModel.id` becomes the `user_id` foreign key stamped onto every `TranscriptModel` and `ProcedureModel` row that user creates, which is what makes the per-row ownership checks possible. `UserModel.endoscopist_id` is meant to flow forward into every transcript/procedure that user creates (see Transcript Creation above), but since nothing currently writes it, that link is inert until it's populated directly in the database.

**Patient data (name, DOB, NHI, indication, procedure date).** Enters the system once, at `/transcripts/start`, typed in by the clinician. From there it's carried on the `TranscriptModel` row for the lifetime of the draft — every later read (`/transcripts/{id}/report`, `/transcripts/{id}/draft`) pulls it back off that same row rather than asking for it again. At `/transcribe`, `build_report()` re-attaches this same patient data (now sourced from the DB, not regenerated) to whatever the LLM extracted, so the clinician sees patient + clinical findings together in one review payload. At `/write`, the clinician-confirmed metadata is copied one more time into the new `Procedure` row, becoming the permanent, legally-relevant copy — `TranscriptModel` and `Procedure` end up holding independent copies of the same patient fields by design (see "Two separate tables" below), not a shared reference.

**Clinical/procedure data (cecum reached, landmarks, BBPS, polyps, findings).** Originates as unstructured narration, captured by the browser's speech recognition, and enters the backend as plain text at `/transcribe`. GPT extraction (`extract_json_from_text`) turns that text into the structured `ColonoscopyReport` shape, including the five landmark booleans. `add_time_stamps` merges in the two clinician-supplied timestamps. The result is stored as JSONB (`polyps`, `findings`) plus individual columns (BBPS scores, landmarks, cecum fields) on the draft `TranscriptModel` — nothing is validated against clinical rules yet at this point. Only at `/write` does this data get parsed into the stricter `ColonoscopyReportFinal`/`PolypFinal`/`FindingFinal` schemas and split into normalized `PolypModel`/`FindingModel` rows tied to the new `Procedure`, at which point the database constraints (BBPS range, cecum/landmark consistency, time ordering) are enforced for the first time.

**Image data.** Captured on a separate physical device from the browser session — a webcam/monitor feed through `capture/image_capture.py`, which logs in independently and uploads each frame as it's captured. Each `Images` row starts life linked only to a `transcript_id`, with `procedure_id = NULL`, because images can be captured before the procedure is reviewed or finalized. At `/write`, every `Images` row matching that `transcript_id` is bulk-updated to point at the newly created `procedure_id`, which is what lets the PDF generator (and any later `GET /procedures/{id}` style lookups) find them by the permanent record instead of the temporary draft. Retrieval (`GET /images/{image_id}`) is authorized by walking back from the image to its transcript to check ownership, since `Images` itself doesn't carry a `user_id`.

**PDF output.** Generated once, at `/write`, from the final `ColonoscopyReportWithMetadataFinal` payload plus the now-linked images (queried by `procedure_id`, ordered by `captured_at`). Written to `OUTPUT_DIR` on the filesystem and served back out through the unauthenticated static mount at `GET /files/{filename}` — the PDF itself is not re-derivable from the database afterward; the file on disk is the artifact.

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
Every procedure/transcript row carries a `user_id`. Each route independently loads the resource and compares `resource.user_id == current_user.id`, returning 403 on mismatch, rather than filtering the query by user up front. `Images` has no `user_id` of its own, so its ownership check goes through the parent `TranscriptModel` instead. Simple to reason about one endpoint at a time, but the ownership check is duplicated across every route file instead of centralized in a dependency.

### UUID transcript ids
`transcript_id` switched from an auto-increment integer to a server-generated UUID. Non-sequential, non-guessable identifiers reduce the blast radius of anything that leaks or logs an id. `procedure_id` and `image_id` remain sequential integers, but `GET /images/{image_id}` is now auth-checked, so that's a smaller concern than it used to be.

### Cecal intubation criteria enforced only at finalize, not at draft time
`ColonoscopyReport` (LLM output) and `TranscriptModel` accept `cecum_reached = true` with no supporting landmark evidence — the clinician may not have dictated all of it yet, or the LLM may not have caught it. The stricter rule (at least one landmark documented) is enforced only by the `CHECK` constraint on `ProcedureModel`, surfaced as a `422` from `/transcripts/{transcript_id}/write`. This keeps the draft phase permissive while keeping the legal record clinically rigorous.

### Friendly constraint-error mapping at the write endpoint
Rather than let every database `CHECK`/`UNIQUE` violation surface as an opaque `500`, `write_db_generate_pdf_route.py` maps known constraint names to clinician-readable `422` messages via a small dict (`CONSTRAINT_ERROR_MESSAGES`). New constraints need a matching entry added here or they'll fall back to the generic 500.

## TODO

- **No way to set `UserModel.endoscopist_id` via the API.** `/register` doesn't accept it, and there's no profile/update endpoint. Every new user is created with `endoscopist_id = NULL`, which then propagates to `TranscriptModel.endoscopist_id` at `/transcripts/start` and will fail the `NOT NULL` FK on `ProcedureModel.endoscopist_id` at `/write` time (a plain `NOT NULL` violation isn't in `CONSTRAINT_ERROR_MESSAGES`, so it'd surface as the generic 500, not a helpful message). Needs either a field on `/register`, an admin/setup endpoint, or a self-service "claim your endoscopist profile" flow.
- Planned fix for the above will be to have every user be an endoscopist for now.  This assumption will need to be revisited in the future once non clinical or admin accounts are added.
- `TranscriptModel.status` and `ProcedureModel.status` share the same `TranscriptStatus` enum (`IN_PROGRESS` / `FINALIZED`) for two different lifecycles — works today but is confusing; consider separate enums.
- `anatomic_location` and `label_source` on `Images` are never populated — auto/manual image labelling isn't implemented yet.
- Build browser/UI to handle the recovery flow — check whether a transcript_id exists and offer to retrieve it to finish.
- Add Alembic for migrations. This matters more now than before: the `transcripts.transcript_id` PK type change from `Integer` to `UUID`, the new `UserModel.endoscopist_id` column, every landmark column, and their constraints were all applied via `create_all` against a fresh schema — there's no migration path for an existing database with data in it.
- CORS currently allows all origins (`allow_origins=['*']`) — fine for local development, should be locked down before handling real auth tokens in production.
- `CONSTRAINT_ERROR_MESSAGES` only covers the constraints that existed when it was written — any future `CHECK`/`UNIQUE` constraint (or the `NOT NULL` FK gap above) needs a matching entry or it silently falls back to a generic 500 with no clinician-facing explanation.

### Recently fixed
- `GET /images/{image_id}` had no auth at all — now requires a Bearer token and checks that the requesting user owns the image's parent transcript (403 otherwise).
- `POST /transcripts/start` hardcoded `endoscopist_id = 1` for every transcript — now pulled from `current_user.endoscopist_id` (though see the new TODO above: there's still no way to actually set that field on a user).
- `add_time_stamps()` was extracting the five cecal-landmark booleans from the LLM but silently dropping them when building `ColonoscopyReportWithTime` — they're now threaded through correctly, so landmark data reaches the draft and the review screen.
- Database constraint violations at `/write` used to mostly surface as a generic `500` (only `check_cecum_reached_criteria` had a friendly message) — now seven known constraints map to specific `422` messages via `CONSTRAINT_ERROR_MESSAGES`.
- `ProcedureMetadataFinal.indication` was typed as a bare `str` with a `default=None`, an inconsistent annotation — now properly `Optional[str]`.
- `transcription_route.py` calling `functions.map_transcription(full_report)` without `user_id`, which 500'd every `/transcribe` call — now passes `user_id=current_user.id`.
- `POST /transcripts/{transcript_id}/images` writing to a hardcoded, never-created `./uploads/{filename}` path — now uses `UPLOADS_DIR` from `config.py` (created at import time, same pattern as `OUTPUT_DIR`).
- `config.py` and `logger.py` both independently calling `logging.basicConfig` — removed the dead/unused copy from `config.py`; `app.logger.logger` is the one every module imports.
- `get_current_user`'s `except` blocks used to `print()` the error and fall through instead of raising, which meant an invalid/expired token could hit `db.get(UserModel, user_id)` with `user_id` still undefined and blow up as an unhandled `500` instead of a clean `401`. Each branch now raises the appropriate `HTTPException` directly.
- Patient/procedure metadata used to be randomly generated via `generate_fake_data()` on every `/transcribe` call — now sourced from the real patient info entered at `/transcripts/start` via `build_report()`.
