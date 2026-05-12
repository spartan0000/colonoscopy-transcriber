from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from app.database.connection import get_db
from app.database.models import TranscriptModel

from app.services import functions

from app.models.colonoscopy import ColonoscopyReport
from app.logger import logger


from sqlalchemy.orm import Session

import uuid

from dateutil.parser import isoparse

from datetime import datetime

router = APIRouter(tags=['transcripts'])

@router.get("/transcripts/{transcript_id}")
def get_transcript(transcript_id: int, db: Session = Depends(get_db)):
    transcript = db.query(TranscriptModel).filter_by(transcript_id=transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return {
        'transcript_id': transcript.transcript_id,
        'procedure_id': transcript.procedure_id,
        'patient_id': transcript.patient_id,
        'patient_name': transcript.patient_name,
        'procedure_date': transcript.procedure_date,
        'endoscopist_id': transcript.endoscopist_id,
        'indication': transcript.indication,
        'cecum_reached': transcript.cecum_reached,
        'cecum_reached_time': transcript.cecum_reached_time,
        'procedure_end_time': transcript.procedure_end_time,
        'bbps_right': transcript.bbps_right,
        'bbps_transverse': transcript.bbps_transverse,
        'bbps_left': transcript.bbps_left,
        'polyp': transcript.polyps,
        'findings': transcript.findings,
        'status': transcript.status,
        'created_at': transcript.created_at,
        
    }