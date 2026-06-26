from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from app.database.connection import get_db
from app.database.models import TranscriptModel, TranscriptStatus

from app.services import functions

from app.models.colonoscopy import ColonoscopyReport
from app.logger import logger


from sqlalchemy.orm import Session

import uuid

from dateutil.parser import isoparse

from datetime import datetime, date

def get_draft_id():
    return str(uuid.uuid4())

router = APIRouter(tags=['transcription'])



@router.post("/transcripts/start")
def start_procedure(db: Session = Depends(get_db)):
    fake_transcript = TranscriptModel(
        patient_id = 'ABC1234',
        patient_name = 'Santa Claus',
        endoscopist_id = 1,
        patient_dob = date(1945,1,1),
        procedure_date = date.today(),
        cecum_reached = False,
        polyps = [],
        findings = [],
        status = TranscriptStatus.IN_PROGRESS,
        created_at = datetime.now()

)
    db.add(fake_transcript)
    db.commit()
    db.refresh(fake_transcript)

    return {"transcript_id": fake_transcript.transcript_id}

@router.post("/transcribe/{transcript_id}")
async def transcribe(transcript_id: int,
                     cecum_reached_time: datetime | None = Form(None), 
                     procedure_end_time: datetime | None = Form(None), 
                     file: UploadFile = File(...),
                     db: Session = Depends(get_db)):
    
    transcript = db.query(TranscriptModel).filter_by(transcript_id = transcript_id).first()

    if not transcript:
        raise HTTPException(status_code = 404, detail = "transcript not found")

    """
    handle transcription of uploaded audio file, extract relevant information, return structured JSON output
    """
    print("CECUM_DEBUG:  ", cecum_reached_time)
    print("PROCEDURE END TIME DEBUG:  ", procedure_end_time)
    logger.info(f"Received cecum reached time: {cecum_reached_time}")
    logger.info(f"Received procedure end time: {procedure_end_time}")

    ###Logging the input to the endpoint
    contents = await file.read()
    # print("\n----UPLOAD DEBUG---")
    # print(f"FILENAME: {file.filename}")
    # print(f"CONTENT TYPE: {file.content_type}")
    # print(f"SIZE: {len(contents)}")
    # print("--------------\n")

    file.file.seek(0)
    ###

    #draft_id = get_draft_id()

    ##########BEGIN BLOCK
    ###This function gets taken out because we changed the front end to send transcribed text instead of audio, but leaving it here now in case we want to switch back later

    #transcription_result = await functions.transcribe_get_timestamps(file)
    

    ###Logging what comes back from the transcribe LLM
    #print("\n---TRANSCRIPTION OUTPUT---")
    #print(f"TRANSCRIPT: {transcription_result}")
    ##################################################################
    
    
    #logger.info(f"Transcription with timestamps: {transcription_result}")
    ##########END BLOCK


    ##########BEGIN BLOCK
    #This takes transcribed text from the front end and picks up where the above block left off
    
    transcription_result = contents.decode('utf-8')


    logger.info(f"Received transcription result: {transcription_result}")
    ##########END BLOCK

    #extracted_data, status = await functions.extract_json(transcription_result)

    extracted_data, status = await functions.extract_json_from_text(transcription_result)

    
    #Logging what comes back from the chat LLM #######################
    print("\n---LLM OUTPUT---")
    print(f"LLM OUTPUT: {extracted_data}")
    logger.info(f"LLM extracted structured data: {extracted_data}")
    ###################################################################

    
    extracted_data_with_timestamps = functions.add_time_stamps(extracted_data, cecum_reached_time, procedure_end_time)

    logger.info(f"Added time stamps: {extracted_data_with_timestamps}")

    full_report = functions.generate_fake_data(extracted_data_with_timestamps) #fake data for now, replace with real metadata extraction

    logger.info(f"Full report: {full_report}")
    
    try:
        updated = functions.map_transcription(full_report)

        transcript.patient_id = updated.patient_id
        transcript.patient_name = updated.patient_name
        transcript.procedure_date = updated.procedure_date
        transcript.endoscopist_id = updated.endoscopist_id
        transcript.patient_dob = updated.patient_dob
        transcript.indication = updated.indication
        transcript.cecum_reached = updated.cecum_reached
        transcript.cecum_reached_time = updated.cecum_reached_time
        transcript.procedure_end_time = updated.procedure_end_time
        transcript.bbps_left = updated.bbps_left
        transcript.bbps_transverse = updated.bbps_transverse
        transcript.bbps_right = updated.bbps_right
        transcript.polyps = updated.polyp
        transcript.findings = updated.findings


        
        db.commit()
        db.refresh(transcript)
        logger.info(f"Transcript created with ID: {transcript.transcript_id}")
    except Exception as e:
        logger.error(f"Failed to write transcript: {e}")
        raise HTTPException(status_code=500, detail="failed to save transcript to database")


    return {
        'report': full_report,
        'status': status,
        'transcript_id': transcript.transcript_id
    }

