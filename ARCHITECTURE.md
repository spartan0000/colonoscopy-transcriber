# Architecture

## Data Model Overview

### TranscriptModel
- Created on start button press
- Stores LLM extracted draft data after /transcribe endpoint
- Purpose: crash recovery — if browser closes, draft can be retrieved
- Linked to Procedure via procedure_id once finalized
- Status: draft if procedure_id is None, finalized if procedure_id is set

### Procedure
- Created on submit via /write endpoint  
- Stores doctor verified final clinical data
- This is the legal record
- Has related Polyps and Findings tables
- Linked back to TranscriptModel via procedure_id

### Images
- Created by image upload endpoint
- Linked to TranscriptModel via transcript_id
- Ordered by captured_at timestamp for PDF generation
- File stored on filesystem, path and metadata in database

## Data Flows

### 1. Transcript Creation
Start button → POST /transcripts/start → TranscriptModel row created → transcript_id returned to browser and displayed

### 2. Image Capture (runs in parallel during procedure)
python -m capture/image_capture.py → user enters transcript_id → SPACE key captures frame → saved locally → POST /transcripts/{id}/images → filesystem storage → path + metadata written to Images table

### 3. Audio Transcription and LLM Extraction
Browser speech recognition transcribes in real time → procedure ends → browser sends transcribed text + cecum_reached_time + procedure_end_time → POST /transcribe/{transcript_id} → LLM extracts structured data → written to TranscriptModel as draft → full_report returned to browser for verification

### 4. Draft Recovery
If browser closes mid verification → reopen → GET /transcripts/{transcript_id}/draft → returns TranscriptModel draft if procedure_id is None → doctor continues verification

### 5. Verification and PDF Generation
Doctor reviews LLM extracted data in browser → edits if needed → submit → POST /write → write_transcription_record creates Procedure with verified data → transcript.procedure_id linked → PDF generated with images ordered by captured_at → PDF written to filesystem → pdf_url returned

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

## TODO
- Draft recovery endpoint GET /transcripts/{transcript_id}/draft - FIXED but see next item
- Build browser/UI to handle recovery flow - check to see if transcript id exists and offer to retrieve it to finish
- Images are linked to transcript_id which is the primary key for the temporary data in TranscriptModel: FIXED - images are now linked to procedure_ID
- Auth on /write endpoint to prevent direct URL access
- Add .order_by(Images.captured_at.asc()) to image query in /write endpoint FIXED
- Add Alembic for migrations
- Add auth to each test that hits a protected endpoint