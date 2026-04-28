from fastapi import APIRouter, UploadFile, File, Depends, Form
from app.database.connection import get_db

from app.services import functions

from app.models.colonoscopy import ColonoscopyReport
from app.logger import logger


from sqlalchemy.orm import Session

import uuid

from dateutil.parser import isoparse

from datetime import datetime

def get_draft_id():
    return str(uuid.uuid4())

router = APIRouter(tags=['transcription'])


@router.post("/transcribe")
async def transcribe(cecum_reached_time: datetime | None = Form(None), procedure_end_time: datetime | None = Form(None), file: UploadFile = File(...)):
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

    transcription_result = await functions.transcribe_get_timestamps(file)
    

    ###Logging what comes back from the transcribe LLM
    print("\n---TRANSCRIPTION OUTPUT---")
    print(f"TRANSCRIPT: {transcription_result}")
    ##################################################################
    
    
    logger.info(f"Transcription with timestamps: {transcription_result}")

    extracted_data, status = await functions.extract_json(transcription_result)

    
    #Logging what comes back from the chat LLM #######################
    print("\n---LLM OUTPUT---")
    print(f"LLM OUTPUT: {extracted_data}")
    logger.info(f"LLM extracted structured data: {extracted_data}")
    ###################################################################

    
    extracted_data_with_timestamps = functions.add_time_stamps(extracted_data, cecum_reached_time, procedure_end_time)

    logger.info(f"Added time stamps: {extracted_data_with_timestamps}")

    full_report = functions.generate_fake_data(extracted_data_with_timestamps) #fake data for now, replace with real metadata extraction

    logger.info(f"Full report: {full_report}")
    


    return {
        'report': full_report,
        'status': status
    }

