from fastapi import APIRouter, UploadFile, File, Depends
from app.database.connection import get_db

from app.services import functions

from app.models.colonoscopy import ColonoscopyReport

from sqlalchemy.orm import Session

import uuid

def get_draft_id():
    return str(uuid.uuid4())

router = APIRouter(tags=['transcription'])

@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), db: Session=Depends(get_db)):
    """
    handle transcription of uploaded audio file, extract relevant information, return structured JSON output
    """
    ###Logging the input to the endpoint
    contents = await file.read()
    print("\n----UPLOAD DEBUG---")
    print(f"FILENAME: {file.filename}")
    print(f"CONTENT TYPE: {file.content_type}")
    print(f"SIZE: {len(contents)}")
    print("--------------\n")

    file.file.seek(0)
    ###

    #draft_id = get_draft_id()

    transcription_result = await functions.transcribe_get_timestamps(file)
    

    ###Logging what comes back from the transcribe LLM
    print("\n---TRANSCRIPTION OUTPUT---")
    print(f"TRANSCRIPT: {transcription_result}")
    ###

    extracted_data = await functions.extract_json(transcription_result)


    #Logging what comes back from the chat LLM
    print("\n---LLM OUTPUT---")
    print(f"LLM OUTPUT: {extracted_data}")





    full_report = functions.generate_fake_data(extracted_data) #fake data for now, replace with real metadata extraction

    #functions.write_transcription_record(db=db, full_report = full_report) #move this function to the write_db_generate_pdf route



    return full_report

