from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from fastapi.responses import FileResponse

from app.database.connection import get_db
from app.database.models import TranscriptModel, Images

from app.services import functions

from app.models.colonoscopy import ColonoscopyReportWithTime, ColonoscopyReportWithMetadata, ProcedureMetadata, Finding, Polyp
from app.logger import logger


from sqlalchemy.orm import Session

import uuid
import os

from dateutil.parser import isoparse

from datetime import datetime

router = APIRouter(tags=["images"])

@router.get("/images/{image_id}")
def get_image(image_id: int, db: Session = Depends(get_db)):
    img = db.query(Images).filter_by(image_id = image_id).first()
    if not img:
        raise HTTPException(status_code = 404, detail = "Image not found")
    if not os.path.exists(img.image_path):
        raise HTTPException(status_code = 404, detail = "Image file not found on disk")
    return FileResponse(img.image_path, media_type = "image/png")
