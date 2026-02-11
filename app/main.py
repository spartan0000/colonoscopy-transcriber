from app.database.connection import SessionLocal
from app.functions.functions import get_timestamps, extract_json
from app.database.connection import SessionLocal, get_db

from app.database.models import Procedure, Polyp, PolypLocationLookup, EndoscopistLookup

from sqlalchemy.orm import Session

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



@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), db: Session=Depends(get_db)):
    

    transcript = await get_timestamps(file.file)
    output = await extract_json(transcript)

    procedure = Procedure(
        
        patient_id = random.randint(1000,9999),
        endoscopist_id = random.randint(1,4),
        procedure_date = datetime.now(),
        cecum_reached = output.get("cecum_reached", False),
        withdrawal_time = output.get("withdrawal_time", 0.0),
        entered_by = "test_user",
        source_system = "test_system",

        created_at = datetime.now(),
        updated_at = datetime.now(),
    )
    db.add(procedure)
    db.commit()   
    db.refresh(procedure)

    for polyp_data in output.get("polyps", []):
        polyp = Polyp(
            location_ref = db.query(PolypLocationLookup).filter_by(location_code=polyp_data.get("location", "other")).first(),
            size_mm = polyp_data.get("size_mm", 0.0),
            morphology = polyp_data.get("morphology"),
            resection_method = polyp_data.get("resection_method", "unknown"),
            resection_complete = polyp_data.get("resection_complete", False),
            retrieved = polyp_data.get("retrieved", False)
        )

        procedure.polyps.append(polyp)
    
    db.commit()

    


    return output


