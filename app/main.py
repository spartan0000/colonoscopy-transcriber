from app.database.connection import SessionLocal
from app.services.functions import transcribe_get_timestamps, extract_json
from app.database.connection import SessionLocal, get_db

from app.database.models import ProcedureModel, PolypModel, PolypLocationLookup, TranscriptModel, EndoscopistLookup, Images

from sqlalchemy.orm import Session

from app.api import transcription_route, procedure_query_route, write_db_generate_pdf_route, transcript_retrieval_route, get_images_route


import random
from datetime import datetime

from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database.connection import TestSessionLocal, SessionLocal, engine
from app.database.seed_lookup_tables import init_db_deployment
from contextlib import asynccontextmanager

from pathlib import Path

from dotenv import load_dotenv
import os

from app.config import OUTPUT_DIR

@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("ENV") != 'test':
        init_db_deployment(SessionLocal, engine)

    yield

    

app = FastAPI(lifespan=lifespan)

app.mount("/files", StaticFiles(directory=OUTPUT_DIR), name="files")

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
app.include_router(transcript_retrieval_route.router)
app.include_router(get_images_route.router)
