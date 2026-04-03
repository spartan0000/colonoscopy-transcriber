# Colonoscopy Transcription Tool

> **Work in Progress** — Active development. Core transcription pipeline is functional; database persistence and histology integration are in progress.

An AI-powered backend service that ingests audio recordings of colonoscopy procedures and automatically extracts structured clinical data — procedure milestones, polyp findings, and resection details — eliminating manual documentation burden for endoscopists.

---

## Overview

During a colonoscopy, the endoscopist narrates findings aloud in real time: polyp sizes, locations, resection techniques, landmarks reached. This tool captures that audio and transforms it into structured data, ready to populate an electronic medical record or reporting system.

**Current capabilities:**
- Transcribe procedure audio using Azure Whisper with timestamped segments
- Extract structured procedure data (cecum reached, withdrawal time, polyp inventory) via GPT with Pydantic-enforced schemas
- Persist procedures and polyp records to a PostgreSQL database

**Planned:**
- Link polyp records to histopathology results once available
- Calculate endoscopist KPIs (adenoma detection rate, withdrawal time compliance, etc.)
- Recommend surveillance intervals based on polyp burden and histology
- Generate structured PDF procedure reports

---

## Architecture

```
Audio File (m4a/mp3)
        │
        ▼
  Azure Whisper API
  (timestamped transcript)
        │
        ▼
  Azure GPT (structured extraction)
  + Pydantic schema validation
        │
        ▼
  ColonoscopyReport JSON
  ┌─────────────────────┐
  │ cecum_reached        │
  │ cecum_reached_time   │
  │ withdrawal_time      │
  │ polyps[]             │
  │   ├─ location        │
  │   ├─ size_mm         │
  │   ├─ morphology      │
  │   ├─ resection_method│
  │   └─ retrieved       │
  └─────────────────────┘
        │
        ▼
  PostgreSQL (procedures + polyps)
        │
        ▼
  [Planned] Histology linkage → KPIs → Surveillance intervals
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
| Config | python-dotenv + YAML prompts |
| Package Manager | uv |
| Python | ≥ 3.13 |

---

## Data Model

### `procedures`
| Column | Type | Description |
|---|---|---|
| `procedure_id` | Integer PK | Auto-generated |
| `patient_id` | String | Patient identifier |
| `endoscopist_id` | FK | Reference to endoscopist |
| `procedure_date` | DateTime (TZ) | Date/time of procedure |
| `cecum_reached` | Boolean | Whether cecum was reached |
| `withdrawal_time` | Float | Minutes from cecum to procedure end |
| `source_system` | String | Origin of the record |

### `polyps`
| Column | Type | Description |
|---|---|---|
| `polyp_id` | Integer PK | Auto-generated |
| `procedure_id` | FK | Parent procedure (cascade delete) |
| `location_code` | FK | Anatomical location |
| `size_mm` | Float | Polyp size in millimeters |
| `morphology` | Enum | sessile / pedunculated / flat / other |
| `resection_method` | Enum | cold_snare / hot_snare / biopsy_forceps / lift_and_resect / other |
| `resection_complete` | Boolean | Complete resection achieved |
| `retrieved` | Boolean | Specimen retrieved for pathology |

### Lookup Tables
- **`polyp_location_lookup`** — cecum, ascending colon, hepatic flexure, transverse colon, splenic flexure, descending colon, sigmoid colon, rectum, anus, other
- **`endoscopist_lookup`** — registered endoscopists

---

## API Endpoints

### `POST /transcribe`
Upload a procedure audio file and receive structured findings.

**Request:** `multipart/form-data` with an audio file field (`.m4a`, `.mp3`, etc.)

**Response:**
```json
{
  "cecum_reached": true,
  "cecum_reached_time": "00:04:12",
  "procedure_end_time": "00:18:45",
  "withdrawal_time": 14.55,
  "polyps": [
    {
      "polyp_id": "1",
      "size_mm": 6.0,
      "location": "sigmoid_colon",
      "morphology": "sessile",
      "resection_method": "cold_snare",
      "resection_complete": true,
      "retrieved": true
    }
  ]
}
```

### `POST /test_db`
Development endpoint — creates a dummy procedure record to verify database connectivity.

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

   Create a `.env` file in the project root and fill in your credentials:
   ```env
   # PostgreSQL
   PSQL_DATABASE_URL=postgresql://user:password@localhost:5432/colonoscopy

   # Azure GPT (structured extraction)
   

   # Azure Whisper (transcription)
   

   # Azure Transcription
   
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

## Project Structure

```
colonoscopy-transcription/
├── app/
│   ├── main.py                    # FastAPI app, route definitions
│   ├── database/
│   │   ├── connection.py          # SQLAlchemy engine and session
│   │   ├── models.py              # ORM models (procedures, polyps, lookups)
│   │   ├── seed_data.py           # Synthetic procedure data for testing
│   │   └── seed_lookup_tables.py  # Reference data (locations, endoscopists)
│   ├── functions/
│   │   ├── clients.py             # Azure OpenAI async client setup
│   │   └── functions.py           # Transcription and extraction logic
│   ├── models/
│   │   └── colonoscopy.py         # Pydantic schemas for API I/O
│   ├── prompts/
│   │   ├── transcription_prompt.yaml  # Whisper system prompt
│   │   └── extraction_prompt.yaml     # GPT extraction system prompt
│   └── data/
│       ├── test_audio_1.m4a       # Sample audio for development
│       └── send_test_data.py      # Script to POST test audio to the API
├── docker-compose.yaml
├── pyproject.toml
└── .env
```

---

## Roadmap

- [x] Audio transcription pipeline (Whisper + timestamped segments)
- [x] Structured data extraction (GPT + Pydantic)
- [x] PostgreSQL schema — procedures and polyps
- [ ] Wire `/transcribe` response to database persistence
- [ ] CRUD endpoints for procedures and polyps
- [ ] Histology data ingestion and polyp linkage
- [ ] Endoscopist KPI calculations (adenoma detection rate, withdrawal time)
- [ ] Surveillance interval recommendations (based on polyp count, size, histology)
- [ ] PDF procedure report generation
- [ ] Authentication and multi-tenant support

---

## License

Private / not yet licensed.
