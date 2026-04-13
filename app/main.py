from app.database.connection import SessionLocal
from app.services.functions import transcribe_get_timestamps, extract_json
from app.database.connection import SessionLocal, get_db

from app.database.models import ProcedureModel, PolypModel, PolypLocationLookup, EndoscopistLookup

from sqlalchemy.orm import Session

from app.api.transcription_route import router as transcription_router

import random
from datetime import datetime

from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
import os


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins = ['*'],
    allow_credentials = False,
    allow_methods = ['*'],
    allow_headers = ['*'],
)


load_dotenv()

#for development and testing of the db connection only.
###################################################
@app.post("/test_db")
async def test_db(db: Session = Depends(get_db)):
     
    dummy = ProcedureModel(
        patient_id = "abcd1234",
        endoscopist_id = 2,
        procedure_date = datetime.now(),
        cecum_reached = True,
        withdrawal_time = 420,
        entered_by = "test",
        source_system = "test",
        created_at = datetime.now(),
        updated_at = datetime.now(),
    )

    db.add(dummy)
    db.commit()
    db.refresh(dummy)
    
    return {'dummy': dummy.procedure_id}
##################################################



app.include_router(transcription_router)

