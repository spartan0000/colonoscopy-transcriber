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

## Data Model

### `users`
| Column | Type | Description |
|---|---|---|
| `id` | Integer PK | Auto-generated |
| `username` | String | Unique |
| `email` | String | Unique |
| `hashed_password` | String | Argon2 hash, never plaintext |

Owns `procedures` and `transcripts` via `user_id`.

### `transcripts`
Temporary holding record for a procedure in progress, before the doctor has verified and finalized it. All clinical fields are nullable since the row is created before anything is known.

| Column | Type | Description |
|---|---|---|
| `transcript_id` | Integer PK | Auto-generated |
| `procedure_id` | FK | Set once finalized via `/write`; NULL while still a draft |
| `user_id` | FK | Owning user |
| `patient_id`, `patient_name`, `patient_dob`, `endoscopist_id`, `procedure_date`, `indication` | — | Draft metadata (currently placeholder/random data) |
| `cecum_reached`, `cecum_reached_time`, `procedure_end_time` | — | Procedure milestones |
| `bbps_right`, `bbps_transverse`, `bbps_left` | Integer | Boston Bowel Prep Score per segment |
| `polyps`, `findings` | JSONB | Raw LLM-extracted draft data (not yet relational) |
| `status` | Enum | `in_progress` / `finalized` |
| `created_at`, `updated_at` | DateTime (TZ) | Auto-managed |

### `procedures`
| Column | Type | Description |
|---|---|---|
| `procedure_id` | Integer PK | Auto-generated |
| `user_id` | FK | Owning user |
| `patient_id` | String | Patient NHI number |
| `patient_name` | String | Patient full name |
| `patient_dob` | DateTime | Patient date of birth |
| `endoscopist_id` | FK | Reference to endoscopist |
| `procedure_date` | DateTime (TZ) | Date/time of procedure |
| `indication` | String | Free-text indication for the procedure |
| `cecum_reached` | Boolean | Whether cecum was reached |
| `cecum_reached_time` | DateTime | Time cecum was reached |
| `procedure_end_time` | DateTime | Time procedure ended |
| `withdrawal_time` | Float (computed) | Minutes from cecum to procedure end |
| `bbps_right` | Integer | Boston Bowel Prep Score — right colon (0–3) |
| `bbps_transverse` | Integer | Boston Bowel Prep Score — transverse colon (0–3) |
| `bbps_left` | Integer | Boston Bowel Prep Score — left colon (0–3) |
| `bbps_total` | Integer (computed) | Total BBPS (0–9) |
| `entered_by` | String | User who entered the record |
| `source_system` | String | Origin of the record |
| `status` | Enum | Defaults to `finalized` |
| `created_at` | DateTime (TZ) | Auto-set on insert |
| `updated_at` | DateTime (TZ) | Auto-set on update |

Constraints: unique on `(patient_id, procedure_date)`; BBPS scores checked 0–3; `cecum_reached_time` required whenever `cecum_reached` is true; `procedure_end_time` must not precede `cecum_reached_time`.

### `polyps`
| Column | Type | Description |
|---|---|---|
| `polyp_id` | Integer PK | Auto-generated |
| `procedure_id` | FK | Parent procedure (cascade delete) |
| `location_code` | FK | Anatomical location (lookup table) |
| `size_mm` | Float | Polyp size in millimeters (≥ 0) |
| `morphology` | String | sessile / pedunculated / semi_pedunculated / flat / other |
| `resection_method` | String | snare / cold_snare / hot_snare / biopsy_forceps / lift_and_resect / other |
| `resection_complete` | Boolean | Complete resection achieved |
| `retrieved` | Boolean | Specimen retrieved for pathology |
| `created_at` | DateTime (TZ) | Auto-set on insert |

### `finding`
Non-polyp endoscopic findings (diverticula, hemorrhoids, inflammation, etc.).

| Column | Type | Description |
|---|---|---|
| `finding_id` | Integer PK | Auto-generated |
| `procedure_id` | FK | Parent procedure (cascade delete) |
| `description` | Text | Free-text description of the finding |
| `location_code` | FK | Anatomical location (optional, same lookup table as polyps) |
| `biopsy_taken` | Boolean | Whether a biopsy was taken |
| `created_at` | DateTime (TZ) | Auto-set on insert |

### `images`
Still frames captured from the endoscopy monitor during the procedure.

| Column | Type | Description |
|---|---|---|
| `image_id` | Integer PK | Auto-generated |
| `transcript_id` | FK | Owning transcript (cascade delete), required |
| `procedure_id` | FK | Set once the transcript is finalized via `/write`; NULL until then |
| `image_path` | String | Filesystem path |
| `anatomic_location` | String | Not currently populated |
| `label_source` | String | auto vs manual labelling; not currently populated |
| `captured_at` | DateTime (TZ) | When the frame was captured — drives PDF ordering |
| `created_at` | DateTime (TZ) | Auto-set on insert |

### Lookup Tables
- **`polyp_location_lookup`** — cecum, ascending_colon, hepatic_flexure, transverse_colon, splenic_flexure, descending_colon, sigmoid_colon, rectum, anus, other
- **`endoscopist_lookup`** — registered endoscopists

---

## API Endpoints

Every endpoint below except `/register`, `/login`, `/files/{filename}`, and `/images/{image_id}` requires an `Authorization: Bearer <token>` header. Ownership is enforced per-resource — a user can only read or write transcripts/procedures/images they created (403 otherwise).

### `POST /register`
Creates a user account. Body: `{ "username", "email", "password" }`. Returns 409 if the username or email is already taken.

### `POST /login`
Body: `{ "username_or_email", "password" }`. Returns `{ "access_token", "token_type": "bearer" }` on success (401 otherwise).

### `POST /transcripts/start`
Creates a new draft `TranscriptModel` row for the authenticated user. Returns `{ "transcript_id": ... }`.

### `POST /transcribe/{transcript_id}`
Accepts the browser-transcribed procedure text (as a file upload) plus optional `cecum_reached_time` / `procedure_end_time` form fields. Runs GPT extraction against the transcript, writes the structured draft onto the `TranscriptModel` row, and returns the full report for the clinician to review. **Does not create the final `Procedure` record.**

**Request:** `multipart/form-data` — `file` (the transcribed text), `cecum_reached_time`, `procedure_end_time`.

**Response:**
```json
{
  "report": {
    "metadata": {
      "patient_name": "Bob Marley",
      "patient_NHI": "ABC1234",
      "procedure_date": "2025-04-01",
      "endoscopist_id": 2
    },
    "report": {
      "cecum_reached": true,
      "cecum_reached_time": "2025-04-01T00:04:12",
      "procedure_end_time": "2025-04-01T00:18:45",
      "bbps_right": 3,
      "bbps_transverse": 3,
      "bbps_left": 2,
      "polyps": [
        {
          "size_mm": 6.0,
          "location": "sigmoid_colon",
          "morphology": "sessile",
          "resection_method": "cold_snare",
          "resection_complete": true,
          "retrieved": true
        }
      ],
      "findings": []
    }
  },
  "status": "success",
  "transcript_id": 1
}
```

> **Note:** Patient metadata is currently populated with placeholder data. Real metadata sourcing from a primary system is planned.

---

### `GET /transcripts/{transcript_id}/report`
Returns the current draft report for a transcript, including any linked images (ordered by `captured_at`).

### `GET /transcripts/{transcript_id}/draft`
Draft recovery endpoint — returns the raw draft fields if the transcript hasn't been finalized yet (400 if it has).

### `POST /transcripts/{transcript_id}/images`
Called by `capture/image_capture.py` to upload a captured still frame. **Request:** `multipart/form-data` with `image` (file) and `captured_at` (form field). Returns `{ "image_id": ... }`.

### `GET /images/{image_id}`
Serves a captured image file. **Not currently authenticated** — see `ARCHITECTURE.md` TODOs.

---

### `POST /write`
Query param: `transcript_id`. Body: `ColonoscopyReportWithMetadataFinal` (the reviewed/edited output of `/transcribe`). On success:
1. Persists the procedure, polyps, and findings to PostgreSQL
2. Re-links any images uploaded against `transcript_id` to the new `procedure_id`
3. Generates a formatted PDF procedure report
4. Saves the PDF to disk and returns a URL to retrieve it

**Response:**
```json
{
  "procedure_id": 1,
  "pdf_url": "/files/colonoscopy_report_ABC1234.pdf"
}
```

---

### `GET /procedures/{procedure_id}/full`
Retrieve a stored procedure record with its associated polyps and findings.

**Response:**
```json
{
  "procedure_id": 1,
  "cecum_reached": true,
  "bbps_right": 3,
  "bbps_transverse": 3,
  "bbps_left": 3,
  "bbps_total": 9,
  "polyps": [
    {
      "size_mm": 6.0,
      "location_code": "sigmoid_colon"
    }
  ],
  "findings": [
    {
      "description": "diverticula in the sigmoid colon",
      "biopsy_taken": false
    }
  ]
}
```

Returns `404` if the procedure does not exist, `403` if it belongs to another user, `422` if `procedure_id` is not a valid integer.

---

### `GET /files/{filename}`
Serves generated PDF reports as static files. URLs are returned by `POST /write`.

---

## Getting Started

### Prerequisites
- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for PostgreSQL)
- Azure OpenAI access with a GPT deployment (Whisper deployment optional — only needed for the legacy audio path)
- A webcam or capture device if you want to exercise `capture/image_capture.py`

### Setup

1. **Clone and install dependencies**
   ```bash
   git clone <repo-url>
   cd colonoscopy-transcription
   uv sync
   ```

2. **Configure environment**

   Create a `.env` file in the project root:
   ```env
   # PostgreSQL — connection is assembled from these parts (see app/database/connection.py)
   DB_USER=
   DB_PASS=
   DB_NAME=
   DB_HOST_PROD=localhost
   DB_HOST_TEST=localhost

   # Auth
   JWT_KEY=
   ALGORITHM=HS256

   # Azure GPT (structured extraction)
   AZURE_OPENAI_API_KEY=
   AZURE_ENDPOINT=
   AZURE_GPT_API_VERSION=

   # Azure Whisper (legacy audio transcription path, optional)
   AZURE_WHISPER_ENDPOINT=
   AZURE_WHISPER_API_VERSION=
   AZURE_TRANSCRIBE_ENDPOINT=
   AZURE_TRANSCRIBE_API_VERSION=

   # Frontend base URL (used by capture/image_capture.py to reach the API)
   API_BASE_URL=
   ```

   The test suite loads its own `.env.test` (see **Running Tests** below) rather than this file.

3. **Start the database**
   ```bash
   docker compose up -d
   ```

4. **Seed lookup tables**
   ```bash
   uv run python app/database/seed_lookup_tables.py
   ```

5. **Run the API server**
   ```bash
   uv run fastapi dev app/main.py
   ```

   The API and interactive docs will be available at `http://localhost:8000/docs`.

6. **(Optional) Run the image capture script**
   ```bash
   uv run python capture/image_capture.py
   ```
   Prompts for username/password (logs in via `/login`), then a `transcript_id`. Press SPACE to capture a frame and upload it, ESC to quit.

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

## Project Structure

```
colonoscopy-transcription/
├── app/
│   ├── main.py                        # FastAPI app entry point, router registration, static file mount
│   ├── config.py                      # App configuration (output directory, API base URL)
│   ├── logger.py                      # Shared logger instance used across routes/services
│   ├── api/
│   │   ├── register_login_route.py    # POST /register, POST /login, get_current_user auth dependency
│   │   ├── transcription_route.py     # POST /transcripts/start, POST /transcribe/{id}
│   │   ├── transcript_retrieval_route.py  # GET /transcripts/{id}/report, GET /transcripts/{id}/draft, POST /transcripts/{id}/images
│   │   ├── get_images_route.py        # GET /images/{image_id}
│   │   ├── procedure_query_route.py   # GET /procedures/{id}/full
│   │   └── write_db_generate_pdf_route.py  # POST /write (DB write + PDF generation)
│   ├── database/
│   │   ├── connection.py              # SQLAlchemy engine and session factory
│   │   ├── models.py                  # ORM models (users, transcripts, procedures, polyps, findings, images, lookups)
│   │   ├── seed_data.py               # Synthetic procedure data for development
│   │   ├── seed_lookup_tables.py      # Reference data (locations, endoscopists)
│   │   └── setup_test_db.py           # Standalone test database initialisation script
│   ├── services/
│   │   ├── clients.py                 # Azure OpenAI async client setup
│   │   ├── functions.py               # Transcription, extraction, mapping, and write logic
│   │   └── pdf_generator.py           # PDF report generation (fpdf2)
│   ├── models/
│   │   └── colonoscopy.py             # Pydantic schemas — draft models (for review) and
│   │                                  #   Final models (for database write)
│   ├── prompts/
│   │   ├── transcription_prompt.yaml  # Whisper system prompt (legacy path)
│   │   └── extraction_prompt.yaml     # GPT extraction system prompt
│   ├── data/
│   │   ├── test_audio_1.m4a           # Sample audio for development (legacy Whisper path)
│   │   └── send_test_data.py          # Script to POST test audio to the API
│   └── generated_pdfs/                # Output directory for generated PDF reports
├── capture/
│   └── image_capture.py               # Standalone OpenCV script: logs in, captures frames on SPACE, uploads them
├── tests/
│   ├── conftest.py                    # Shared fixtures and test DB setup
│   ├── test_pydantic_orm.py           # Pydantic model validation tests
│   ├── test_mapping.py                # Pydantic → SQLAlchemy mapping tests
│   ├── test_db.py                     # Database integration tests
│   ├── test_api.py                    # API endpoint tests
│   ├── test_pdf_generator.py          # PDF generation tests
│   ├── test_services.py               # Service function tests
│   └── test_image_capture.py          # Image capture script tests
├── docker-compose.yaml
├── pyproject.toml
└── .env
```

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
