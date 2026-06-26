from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from app.database.connection import get_db
from app.database.models import TranscriptModel

from app.services import functions

from app.models.colonoscopy import ColonoscopyReportWithTime, ColonoscopyReportWithMetadata, ProcedureMetadata, Finding, Polyp, Images
from app.logger import logger


from sqlalchemy.orm import Session

import uuid

from dateutil.parser import isoparse

from datetime import datetime

router = APIRouter(tags=['transcripts'])

@router.get("/transcripts/{transcript_id}")
def get_transcript(transcript_id: int, db: Session = Depends(get_db)):
    print(f"Retrieving transcript with ID: {transcript_id}")
    logger.info(f"Retrieving transcript with ID: {transcript_id}")
    transcript = db.query(TranscriptModel).filter_by(transcript_id=transcript_id).first()
    images = db.query(Images).filter_by(transcript_id = transcript_id).all()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    


    metadata = ProcedureMetadata(
        patient_NHI = transcript.patient_id,
        patient_name = transcript.patient_name,
        procedure_date = transcript.procedure_date,
        endoscopist_id = transcript.endoscopist_id,
        indication = transcript.indication,
        patient_dob = transcript.patient_dob,
    )

    scope = ColonoscopyReportWithTime(
        cecum_reached = transcript.cecum_reached,
        cecum_reached_time = transcript.cecum_reached_time,
        procedure_end_time = transcript.procedure_end_time,
        bbps_right = transcript.bbps_right,
        bbps_transverse = transcript.bbps_transverse,
        bbps_left = transcript.bbps_left,
        polyps = transcript.polyps,
        findings = transcript.findings,

    )

    report = ColonoscopyReportWithMetadata(
        metadata = metadata,
        report = scope
    )

    
    #may need to tweak this return depending on how we want to actually display images - static files vs binaries

    return {
        'transcript_id': transcript.transcript_id,
        'report': report,
        'status': transcript.status,
        'images': [
            {
                'image_id': img.image_id, #the image id is then used by the get_images endpont to pull images and display in the browser
                'image_path': img.image_path,
                'anatomic_location': img.anatomic_location,
                'captured_at': img.captured_at
            }
            for img in images
        ]

    }