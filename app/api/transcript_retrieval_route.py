from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from app.database.connection import get_db
from app.database.models import TranscriptModel, Images, UserModel
import pathlib
from app.services import functions

from app.models.colonoscopy import ColonoscopyReportWithTime, ColonoscopyReportWithMetadata, ProcedureMetadata, Finding, Polyp
from app.logger import logger
from app.api.register_login_route import get_current_user

from sqlalchemy import asc
from sqlalchemy.orm import Session

import uuid

from dateutil.parser import isoparse

from datetime import datetime

router = APIRouter(tags=['transcripts'])

### Generates a full report including images - 
@router.get("/transcripts/{transcript_id}/report")
def get_transcript(transcript_id: int, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    print(f"Retrieving transcript with ID: {transcript_id}")
    logger.info(f"Retrieving transcript with ID: {transcript_id}")
    transcript = db.query(TranscriptModel).filter_by(transcript_id=transcript_id).first()
    
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    if transcript.user_id != current_user.id:
        raise HTTPException(status_code=403, detail = "Not authorized")
    
    images = db.query(Images).filter_by(transcript_id = transcript_id).order_by(asc(Images.captured_at)).all() #get all images associated sorted by captured at timestamp

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




#Some auxiliary endpoints below

#upload endpoint called from capture.py which sends images to fastapi server for persistent storage and also metadata gets sent to database

@router.post("/transcripts/{transcript_id}/images")
def upload_image_api(transcript_id: int, 
                     image: UploadFile = File(...), 
                     current_user: UserModel = Depends(get_current_user),
                     captured_at: str = Form(...), 
                     db: Session = Depends(get_db)):
    transcript = db.query(TranscriptModel).filter_by(transcript_id = transcript_id).first()
    if not transcript:
        raise HTTPException(status_code = 404, detail = "Transcript not found")
    if transcript.user_id != current_user.id:
        raise HTTPException(status_code=403, detail = "Not authorized")
    
    filename = f"transcript_{transcript_id}_{captured_at}.png"
    filepath = f"./uploads/{filename}"

    with open(filepath, "wb") as f:
        f.write(image.file.read())
    image_record = Images(
        transcript_id = transcript_id,
        image_path = filepath,
        captured_at = captured_at,
        anatomic_location = None
    )

    db.add(image_record)
    db.commit()
    db.refresh(image_record)

    return {'image_id': image_record.image_id}



#need a recovery endpoint - need to also fix the frontend UI to look for this endpoint by default
#draft version of a transcript in case the browser closes or something else happens during initial session

@router.get("/transcripts/{transcript_id}/draft") #if user has a draft transcript, they can retrieve it here.
def get_transcript_draft(transcript_id: int, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    transcript = db.query(TranscriptModel).filter_by(transcript_id=transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail = "Transcript not found")
    if transcript.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if transcript.procedure_id is not None:
        raise HTTPException(status_code=400, detail = "Transcript has already been finalized")
    return {
        'transcript_id': transcript.transcript_id,
        'status': transcript.status,
        'patient_name': transcript.patient_name,
        'patient_dob': transcript.patient_dob,
        'patient_id': transcript.patient_id,
        'procedure_date': transcript.procedure_date,
        'endoscopist_id': transcript.endoscopist_id,
        'indication': transcript.indication,
        'cecum_reached': transcript.cecum_reached,
        'cecum_reached_time': transcript.cecum_reached_time,
        'procedure_end_time': transcript.procedure_end_time,
        'bbps_right': transcript.bbps_right,
        'bbps_transverse': transcript.bbps_transverse,
        'bbps_left': transcript.bbps_left,
        'polyps': transcript.polyps,
        'findings': transcript.findings,
    }
