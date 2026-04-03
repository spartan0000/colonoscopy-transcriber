from fastapi import APIRouter, UploadFile, File, Depends
from app.database.connection import get_db

from app.services import functions

from app.models.colonoscopy import ColonoscopyReport

from sqlalchemy.orm import Session

router = APIRouter(tags=['transcription'])

@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), db: Session=Depends(get_db)):
    """
    handle transcription of uploaded audio file, extract relevant information, return structured JSON output
    """

    transcription_result = await functions.transcribe_get_timestamps(file)
    extracted_data = await functions.extract_json(transcription_result)

    #write to database

    functions.write_transcription_record(db, transcription_result, extracted_data)###this function currently doesn't do any writing.  need to implement actual writing logic

    

    return {
        "transcription_result": transcription_result,
        "extracted_data": extracted_data
    }