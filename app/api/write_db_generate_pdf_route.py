from fastapi import APIRouter, UploadFile, File, Depends
from app.database.connection import get_db

from app.services import functions

from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportWithMetadata

from sqlalchemy.orm import Session

router = APIRouter(tags=['write_db_pdf'])

@router.post("/write")
def write_db_generate_pdf(full_report: ColonoscopyReportWithMetadata, db: Session = Depends(get_db)):
    #write to the database here once the data returns from the user

    functions.write_transcription_record(db=db, full_report = full_report)

    #insert pdf generating function here