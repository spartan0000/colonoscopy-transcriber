from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from pydantic import BaseModel
from app.database.connection import get_db
from app.database.models import TranscriptModel, TranscriptStatus, UserModel

from app.services import functions

from app.models.colonoscopy import ColonoscopyReport
from app.logger import logger
from app.api.register_login_route import get_current_user


from sqlalchemy.orm import Session

import uuid

from dateutil.parser import isoparse

from datetime import datetime, date

def get_draft_id():
    return str(uuid.uuid4())

router = APIRouter(tags=['transcription'])

class StartProcedureRequest(BaseModel):
    patient_name: str
    patient_dob: date
    patient_nhi: str

@router.post("/transcripts/start")
def start_procedure(start : StartProcedureRequest,
                    current_user: UserModel = Depends(get_current_user), 
                    db: Session = Depends(get_db), 
                    ):
    new_transcript = TranscriptModel(
        user_id = current_user.id,
        patient_name = start.patient_name,
        endoscopist_id = 1,
        patient_dob = start.patient_dob,
        patient_id = start.patient_nhi,
        procedure_date = date.today(),
        cecum_reached = False,
        polyps = [],
        findings = [],
        status = TranscriptStatus.IN_PROGRESS,
        created_at = datetime.now()

)
    db.add(new_transcript)
    db.commit()
    db.refresh(new_transcript)

    return {"transcript_id": new_transcript.transcript_id}



### Receives data from the UI that includes the transcribed text and procedure milestones
### Functions that receive audio for transcription are commented out as this was the original workflow
### Can switch back to receiving audio as I'm considering moving to transcription on local machine
### Rather than browser transcription which isn't that secure and another api call which is slow

@router.post("/transcribe/{transcript_id}")
async def transcribe(transcript_id: uuid.UUID,
                     cecum_reached_time: datetime | None = Form(None), 
                     procedure_end_time: datetime | None = Form(None), 
                     current_user: UserModel = Depends(get_current_user),
                     file: UploadFile = File(...),
                     db: Session = Depends(get_db)):
    
    transcript = db.query(TranscriptModel).filter_by(transcript_id = transcript_id).first()

    if not transcript:
        raise HTTPException(status_code = 404, detail = "transcript not found")
    
    if transcript.user_id != current_user.id:
        raise HTTPException(status_code = 403, detail = "Not authorized")

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

    full_report = functions.build_report(transcript, extracted_data_with_timestamps) #took out the fake data function - now uses user entered data retrieved from the database

    logger.info(f"Full report: {full_report}")
    
    try:
        updated = functions.map_transcription(full_report, user_id=current_user.id)

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

