# Colonoscopy Transcription Tool

An AI-powered backend service that turns a colonoscopy procedure narration into structured clinical data — procedure milestones, bowel prep scores, polyp findings, and other endoscopic findings — eliminating manual documentation burden for endoscopists.

A separate React/JS frontend application connects to this service: it drives browser-based speech recognition during the procedure, displays the LLM-extracted draft for review, and shows the generated PDF. A small desktop capture script (`capture/image_capture.py`) handles still-image capture from an endoscopy monitor in parallel.

---

## Overview

During a colonoscopy, the endoscopist narrates findings aloud in real time: polyp sizes, locations, resection techniques, bowel prep quality, landmarks reached. The browser transcribes that narration to text as it happens (via the Web Speech API), and this service turns the transcript into structured data ready to populate an electronic medical record.

**Current capabilities:**
- User accounts with JWT-based authentication (`/register`, `/login`); every clinical resource is scoped to the owning user
- Draft/finalize workflow: `POST /transcripts/start` opens a draft, `POST /transcribe/{id}` extracts structured data into it, `POST /write` finalizes it into the permanent record
- Extract structured procedure data (cecum reached, withdrawal time, BBPS scores, polyp inventory, non-polyp findings) from browser-transcribed text via GPT with Pydantic-enforced schemas
- Draft recovery — if the browser closes mid-procedure, the in-progress transcript can be retrieved via `GET /transcripts/{id}/draft`
- Parallel still-image capture from an endoscopy monitor via a standalone OpenCV script, uploaded and linked to the transcript/procedure
- Persist procedures, polyps, and findings to a PostgreSQL database
- Generate a formatted PDF procedure report (with captured images, ordered by timestamp) on finalize
- Serve generated PDFs and captured images via file endpoints
- Retrieve full procedure records (with polyps and findings) via a REST endpoint

**Legacy/available but unused:**
- Server-side audio transcription via Azure Whisper (`transcribe_get_timestamps`) — the original design before the frontend switched to browser speech recognition. Kept in `app/services/functions.py` in case the team reverts to server-side transcription.

**Planned:**
- Link polyp records to histopathology results once available
- Calculate endoscopist KPIs (adenoma detection rate, withdrawal time compliance, etc.)
- Recommend surveillance intervals based on polyp burden and histology
- Source patient metadata from primary data system (currently placeholder/random data)
- Auth on the image retrieval endpoint (currently open — see `ARCHITECTURE.md`)

---

## Architecture

```
POST /register, POST /login
        │
        ▼
   JWT bearer token ──────────────────────────────────────────────┐
        │                                                          │
        ▼                                                          │
  POST /transcripts/start  ──▶  TranscriptModel (draft) created    │
        │                                                          │
        ├──────────────────────────────┐                          │
        ▼                              ▼                          │
  Browser speech recognition     capture/image_capture.py          │
  transcribes procedure           SPACE = capture frame            │
  narration to text live               │                          │
        │                              ▼                          │
        ▼                     POST /transcripts/{id}/images  ◀────┤ (Bearer token)
  POST /transcribe/{id}  ◀─────────────────────────────────────────┘
  ┌──────────────────────────────┐
  │ Azure GPT (structured        │
  │ extraction) + Pydantic       │
  └──────────────────────────────┘
        │
        ▼
  TranscriptModel updated with draft data
  full_report returned to browser
        │
        ▼ (user reviews / edits in frontend)
  GET /transcripts/{id}/draft   (crash recovery, if needed)
        │
        ▼
  POST /write?transcript_id=...
        │
        ├──▶ PostgreSQL (procedures + polyps + findings)
        ├──▶ Images re-linked from transcript_id to procedure_id
        └──▶ fpdf2 PDF generation
                    │
                    ▼
             GET /files/{filename}
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| Database | PostgreSQL 16 (Docker) |
| ORM | SQLAlchemy 2.0 |
| Auth | JWT (PyJWT) + Argon2 password hashing (pwdlib) |
| Speech-to-Text (primary) | Browser Web Speech API (frontend, not in this repo) |
| Speech-to-Text (legacy, unused) | Azure Whisper |
| LLM Extraction | Azure OpenAI (GPT) |
| Image Capture | OpenCV (`capture/image_capture.py`) |
| Data Validation | Pydantic v2 |
| PDF Generation | fpdf2 |
| Config | python-dotenv + YAML prompts |
| Package Manager | uv |
| Python | ≥ 3.13 |
| Testing | pytest + FastAPI TestClient |

---

## Getting Started

### Prerequisites
- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for PostgreSQL)
- Azure OpenAI access with a GPT deployment (Whisper deployment optional — only needed for the legacy audio path)
- A webcam or capture device if you want to exercise `capture/image_capture.py`

---

## Running Tests

The test suite uses a dedicated test database and loads `.env.test` (via `conftest.py`), with `DB_USER`, `DB_PASS`, and `DB_HOST_TEST` pointing at a `test_db` database. Each test function gets its own database session that is rolled back after the test, so tests are isolated and repeatable.

```bash
uv run pytest
```

### Test modules

| File | What it covers |
|---|---|
| `tests/test_pydantic_orm.py` | Pydantic model validation — valid inputs, invalid inputs, field coercions, BBPS fields, boolean coercion for `cecum_reached` |
| `tests/test_mapping.py` | Mapping functions (`map_polyp`, `map_findings`, `map_procedure`, `map_transcription`) — ensures Pydantic → SQLAlchemy conversion is correct without touching the database |
| `tests/test_db.py` | Database integration — constraint enforcement (negative size, missing morphology, FK violations, unique patient/date), cascade deletes, end-to-end write pipeline |
| `tests/test_api.py` | API endpoint tests — procedure retrieval, transcript start/draft/report, `/write` image re-linking, registration, and auth/ownership checks (403 on cross-user access) |
| `tests/test_pdf_generator.py` | PDF generation — verifies the PDF output is produced correctly from a procedure report |
| `tests/test_services.py` | Service function tests — transcription, extraction, and mapping logic |
| `tests/test_image_capture.py` | `capture/image_capture.py` — local frame saving, image upload, and the SPACE/ESC capture loop (OpenCV/requests mocked) |

### Key test fixtures (`conftest.py`)

- `db_session` — isolated transaction-scoped SQLAlchemy session (rolls back after each test)
- `client_db` — FastAPI `TestClient` with the DB dependency overridden to use the test session
- `client_no_db` — FastAPI `TestClient` with no DB dependency (for tests that don't write to the database)
- `test_user` — a seeded `UserModel` with a hashed password, for tests needing an authenticated user
- `auth_header` — logs `test_user` in and returns an `{"Authorization": "Bearer ..."}` header dict
- `procedure` — a pre-seeded `ProcedureModel` fixture owned by `test_user`
- `full_transcript` — a pre-seeded `TranscriptModel` fixture owned by `test_user`
- `transcript_factory` — factory fixture for creating multiple transcripts with custom attributes, owned by `test_user`
- `fake_frame` / `mock_cap` — fake webcam frame and mocked `cv2.VideoCapture` for `capture/image_capture.py` tests
- `seed_lookup` — auto-used fixture that seeds polyp locations and endoscopist lookup tables before each test

---

## Roadmap

- [x] User accounts and JWT authentication (`/register`, `/login`), per-resource ownership checks
- [x] Draft/finalize workflow — `/transcripts/start` → `/transcribe/{id}` → `/write`
- [x] Browser-driven speech-to-text with structured extraction (GPT + Pydantic)
- [x] Draft recovery endpoint for crash resilience
- [x] Parallel still-image capture and upload, linked to transcript then procedure
- [x] PostgreSQL schema — users, transcripts, procedures, polyps, and non-polyp findings
- [x] Boston Bowel Prep Score (BBPS) capture and persistence
- [x] `GET /procedures/{id}/full` — retrieve a procedure with polyps and findings
- [x] PDF procedure report generation (with captured images)
- [x] Pydantic validation, mapping, database integration, API, PDF, and image-capture test suites
- [x] Fix `/transcribe/{transcript_id}` 500 error caused by the missing `user_id` argument to `map_transcription`
- [ ] Auth on `GET /images/{image_id}`
- [ ] Patient metadata sourcing from primary system (currently placeholder data)
- [ ] Auto/manual image labelling (`anatomic_location`, `label_source`)
- [ ] CRUD endpoints for procedures and polyps
- [ ] Histology data ingestion and polyp linkage
- [ ] Endoscopist KPI calculations (adenoma detection rate, withdrawal time)
- [ ] Surveillance interval recommendations (based on polyp count, size, histology)
- [ ] Alembic migrations

---

## License

Private / not yet licensed.
