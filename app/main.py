from app.database.connection import SessionLocal
from app.services.functions import transcribe_get_timestamps, extract_json
from app.database.connection import SessionLocal, get_db

from app.database.models import ProcedureModel, PolypModel, PolypLocationLookup, EndoscopistLookup

from sqlalchemy.orm import Session

from app.api import transcription_route, procedure_query_route, write_db_generate_pdf_route


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




app.include_router(transcription_route.router)
app.include_router(procedure_query_route.router)
app.include_router(write_db_generate_pdf_route.router)
