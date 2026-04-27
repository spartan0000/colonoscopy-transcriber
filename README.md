# Colonoscopy Transcription Tool

An AI-powered backend service that ingests audio recordings of colonoscopy procedures and automatically extracts structured clinical data — procedure milestones, bowel prep scores, polyp findings, and other endoscopic findings — eliminating manual documentation burden for endoscopists.

A separate React/JS frontend application connects to this service and provides the clinician-facing UI for audio upload, report review, and PDF access.

---

## Overview

During a colonoscopy, the endoscopist narrates findings aloud in real time: polyp sizes, locations, resection techniques, bowel prep quality, landmarks reached. This tool captures that audio and transforms it into structured data, ready to populate an electronic medical record or reporting system.

**Current capabilities:**
- Transcribe procedure audio using Azure Whisper with timestamped segments
- Extract structured procedure data (cecum reached, withdrawal time, BBPS scores, polyp inventory, non-polyp findings) via GPT with Pydantic-enforced schemas
- Persist procedures, polyps, and findings to a PostgreSQL database via a two-step transcribe → review → write workflow
- Generate a formatted PDF procedure report on write
- Serve generated PDFs via static file endpoint
- Retrieve full procedure records (with polyps and findings) via a REST endpoint

**Planned:**
- Link polyp records to histopathology results once available
- Calculate endoscopist KPIs (adenoma detection rate, withdrawal time compliance, etc.)
- Recommend surveillance intervals based on polyp burden and histology
- Source patient metadata from primary data system (currently placeholder)

---

## Architecture

```
Audio File (m4a/mp3)
        │
        ▼
  POST /transcribe
  ┌──────────────────────────────┐
  │ Azure Whisper API            │
  │ (timestamped transcript)     │
  │           │                  │
  │           ▼                  │
  │ Azure GPT (structured        │
  │ extraction) + Pydantic       │
  └──────────────────────────────┘
        │
        ▼
  ColonoscopyReportWithMetadata JSON
  ┌─────────────────────────────────┐
  │ metadata                         │
  │   ├─ patient_name               │
  │   ├─ patient_NHI                │
  │   ├─ procedure_date             │
  │   └─ endoscopist_id             │
  │ report                           │
  │   ├─ cecum_reached              │
  │   ├─ cecum_reached_time         │
  │   ├─ withdrawal_time            │
  │   ├─ bbps_right/transverse/left │
  │   ├─ bbps_total                 │
  │   ├─ polyps[]                   │
  │   │   ├─ location               │
  │   │   ├─ size_mm                │
  │   │   ├─ morphology             │
  │   │   ├─ resection_method       │
  │   │   └─ retrieved              │
  │   └─ findings[]                 │
  │       ├─ description            │
  │       ├─ location               │
  │       └─ biopsy_taken           │
  └─────────────────────────────────┘
        │
        ▼ (user reviews / edits in frontend)
  POST /write
        │
        ├──▶ PostgreSQL (procedures + polyps + findings)
        │
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
| Speech-to-Text | Azure Whisper |
| LLM Extraction | Azure OpenAI (GPT) |
| Data Validation | Pydantic v2 |
| PDF Generation | fpdf2 |
| Config | python-dotenv + YAML prompts |
| Package Manager | uv |
| Python | ≥ 3.13 |
| Testing | pytest + FastAPI TestClient |

---

## Data Model

### `procedures`
| Column | Type | Description |
|---|---|---|
| `procedure_id` | Integer PK | Auto-generated |
| `patient_id` | String | Patient NHI number |
| `patient_name` | String | Patient full name |
| `endoscopist_id` | FK | Reference to endoscopist |
| `procedure_date` | DateTime (TZ) | Date/time of procedure |
| `cecum_reached` | Boolean | Whether cecum was reached |
| `cecum_reached_time` | Time | Time cecum was reached |
| `procedure_end_time` | Time | Time procedure ended |
| `withdrawal_time` | Float (computed) | Minutes from cecum to procedure end |
| `bbps_right` | Integer | Boston Bowel Prep Score — right colon (0–3) |
| `bbps_transverse` | Integer | Boston Bowel Prep Score — transverse colon (0–3) |
| `bbps_left` | Integer | Boston Bowel Prep Score — left colon (0–3) |
| `bbps_total` | Integer (computed) | Total BBPS (0–9) |
| `entered_by` | String | User who entered the record |
| `source_system` | String | Origin of the record |
| `created_at` | DateTime (TZ) | Auto-set on insert |
| `updated_at` | DateTime (TZ) | Auto-set on update |

Constraints: unique on `(patient_id, procedure_date)`.

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

### Lookup Tables
- **`polyp_location_lookup`** — cecum, ascending_colon, hepatic_flexure, transverse_colon, splenic_flexure, descending_colon, sigmoid_colon, rectum, anus, other
- **`endoscopist_lookup`** — registered endoscopists

---

## API Endpoints

### `POST /transcribe`
Upload a procedure audio file. The audio is transcribed and structured data is extracted. Returns a `ColonoscopyReportWithMetadata` object for review before committing to the database. **Does not write to the database.**

**Request:** `multipart/form-data` with an audio file field (`.m4a`, `.mp3`, etc.) and optional timestamps (`cecum_reached_time`, `procedure_end_time`).

**Response:**
```json
{
  "metadata": {
    "patient_name": "Bob Marley",
    "patient_NHI": "ABC1234",
    "procedure_date": "2025-04-01",
    "endoscopist_id": 2
  },
  "report": {
    "cecum_reached": true,
    "cecum_reached_time": "00:04:12",
    "procedure_end_time": "00:18:45",
    "withdrawal_time": 14.55,
    "bbps_right": 3,
    "bbps_transverse": 3,
    "bbps_left": 2,
    "bbps_total": 8,
    "polyps": [
      {
        "polyp_id": 1,
        "size_mm": 6.0,
        "location": "sigmoid_colon",
        "morphology": "sessile",
        "resection_method": "cold_snare",
        "resection_complete": true,
        "retrieved": true
      }
    ],
    "findings": [
      {
        "finding_id": 1,
        "description": "diverticula in the sigmoid colon",
        "location": "sigmoid_colon",
        "biopsy_taken": false
      }
    ]
  }
}
```

> **Note:** Patient metadata is currently populated with placeholder data. Real metadata sourcing from a primary system is planned.

---

### `POST /write`
Accepts a `ColonoscopyReportWithMetadataFinal` body (the output of `/transcribe`, after clinician review and confirmation) and:
1. Persists the procedure, polyps, and findings to PostgreSQL
2. Generates a formatted PDF procedure report
3. Saves the PDF to disk and returns a URL to retrieve it

**Request body:** `ColonoscopyReportWithMetadataFinal` (JSON)

**Response:**
```json
{
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

Returns `404` if the procedure does not exist. Returns `422` if `procedure_id` is not a valid integer.

---

### `GET /files/{filename}`
Serves generated PDF reports as static files. URLs are returned by `POST /write`.

---

## Getting Started

### Prerequisites
- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for PostgreSQL)
- Azure OpenAI access with Whisper and GPT deployments

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
   # PostgreSQL (production)
   PSQL_DATABASE_URL=postgresql://user:password@localhost:5432/colonoscopy_db

   # PostgreSQL (test database — used by the test suite)
   TEST_DATABASE_URL=postgresql://user:password@localhost:5432/colonoscopy_test

   # Azure GPT (structured extraction)
   AZURE_OPENAI_API_KEY=
   AZURE_ENDPOINT=
   AZURE_GPT_API_VERSION=

   # Azure Whisper (transcription)
   AZURE_WHISPER_ENDPOINT=
   AZURE_WHISPER_API_VERSION=

   # HNZ secondary LLM endpoint (optional)
   HNZ_ENDPOINT=
   HNZ_API_KEY=
   HNZ_API_VERSION=

   # Azure transcription endpoint
   AZURE_TRANSCRIBE_ENDPOINT=
   AZURE_TRANSCRIBE_API_VERSION=

   # Frontend base URL (for returning asset URLs)
   API_BASE_URL=
   ```

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

---

## Running Tests

The test suite uses a dedicated test database (set `TEST_DATABASE_URL` in `.env`). Each test function gets its own database session that is rolled back after the test, so tests are isolated and repeatable.

```bash
uv run pytest
```

### Test modules

| File | What it covers |
|---|---|
| `tests/test_pydantic_orm.py` | Pydantic model validation — valid inputs, invalid inputs, field coercions, BBPS fields, boolean coercion for `cecum_reached` |
| `tests/test_mapping.py` | Mapping functions (`map_polyp`, `map_findings`, `map_procedure`) — ensures Pydantic → SQLAlchemy conversion is correct without touching the database |
| `tests/test_db.py` | Database integration — constraint enforcement (negative size, missing morphology, FK violations, unique patient/date), cascade deletes, end-to-end write pipeline |
| `tests/test_api.py` | API endpoint tests — `GET /procedures/{id}/full` with various scenarios (no polyps, with polyps, with findings, not found, invalid ID, multi-procedure isolation) |
| `tests/test_pdf_generator.py` | PDF generation — verifies the PDF output is produced correctly from a procedure report |
| `tests/test_services.py` | Service function tests — transcription, extraction, and mapping logic |

### Key test fixtures (`conftest.py`)

- `db_session` — isolated transaction-scoped SQLAlchemy session (rolls back after each test)
- `client_db` — FastAPI `TestClient` with the DB dependency overridden to use the test session
- `client_no_db` — FastAPI `TestClient` with no DB dependency (for tests that don't write to the database)
- `procedure` — a pre-seeded `ProcedureModel` fixture for tests that need an existing procedure
- `seed_lookup` — auto-used fixture that seeds polyp locations and endoscopist lookup tables before each test

---

## Project Structure

```
colonoscopy-transcription/
├── app/
│   ├── main.py                        # FastAPI app entry point, router registration, static file mount
│   ├── config.py                      # App configuration (output directory, API base URL)
│   ├── api/
│   │   ├── transcription_route.py     # POST /transcribe
│   │   ├── procedure_query_route.py   # GET /procedures/{id}/full
│   │   └── write_db_generate_pdf_route.py  # POST /write (DB write + PDF generation)
│   ├── database/
│   │   ├── connection.py              # SQLAlchemy engine and session factory
│   │   ├── models.py                  # ORM models (procedures, polyps, findings, lookups)
│   │   ├── seed_data.py               # Synthetic procedure data for development
│   │   ├── seed_lookup_tables.py      # Reference data (locations, endoscopists)
│   │   └── setup_test_db.py           # Test database initialisation
│   ├── services/
│   │   ├── clients.py                 # Azure OpenAI async client setup
│   │   ├── functions.py               # Transcription, extraction, mapping, and write logic
│   │   └── pdf_generator.py           # PDF report generation (fpdf2)
│   ├── models/
│   │   └── colonoscopy.py             # Pydantic schemas — draft models (for review) and
│   │                                  #   Final models (for database write)
│   ├── prompts/
│   │   ├── transcription_prompt.yaml  # Whisper system prompt
│   │   └── extraction_prompt.yaml     # GPT extraction system prompt
│   ├── data/
│   │   ├── test_audio_1.m4a           # Sample audio for development
│   │   └── send_test_data.py          # Script to POST test audio to the API
│   └── generated_pdfs/                # Output directory for generated PDF reports
├── tests/
│   ├── conftest.py                    # Shared fixtures and test DB setup
│   ├── test_pydantic_orm.py           # Pydantic model validation tests
│   ├── test_mapping.py                # Pydantic → SQLAlchemy mapping tests
│   ├── test_db.py                     # Database integration tests
│   ├── test_api.py                    # API endpoint tests
│   ├── test_pdf_generator.py          # PDF generation tests
│   └── test_services.py              # Service function tests
├── docker-compose.yaml
├── pyproject.toml
└── .env
```

---

## Roadmap

- [x] Audio transcription pipeline (Whisper + timestamped segments)
- [x] Structured data extraction (GPT + Pydantic)
- [x] PostgreSQL schema — procedures, polyps, and non-polyp findings
- [x] Boston Bowel Prep Score (BBPS) capture and persistence
- [x] Two-step workflow: `/transcribe` returns structured JSON for review, `/write` persists to database
- [x] `GET /procedures/{id}/full` — retrieve a procedure with polyps and findings
- [x] PDF procedure report generation
- [x] Pydantic validation test suite
- [x] Mapping layer test suite (Pydantic → ORM)
- [x] Database integration test suite (constraints, cascades, pipeline)
- [x] API endpoint test suite
- [x] PDF generation test suite
- [ ] Patient metadata sourcing from primary system (currently placeholder data)
- [ ] Expand `GET /procedures/{id}/full` response (BBPS, withdrawal time, patient details)
- [ ] CRUD endpoints for procedures and polyps
- [ ] Histology data ingestion and polyp linkage
- [ ] Endoscopist KPI calculations (adenoma detection rate, withdrawal time)
- [ ] Surveillance interval recommendations (based on polyp count, size, histology)
- [ ] Authentication and multi-tenant support

---

## License

Private / not yet licensed.
