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

    full_report = functions.generate_fake_data(extracted_data) #fake data for now, replace with real metadata extraction

    functions.write_transcription_record(db=db, full_report = full_report)



    return {
        "transcription_result": transcription_result,
        "extracted_data": extracted_data
    }