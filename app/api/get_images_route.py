from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from fastapi.responses import FileResponse

from app.database.connection import get_db
from app.database.models import TranscriptModel, Images, UserModel

from app.services import functions

from app.models.colonoscopy import ColonoscopyReportWithTime, ColonoscopyReportWithMetadata, ProcedureMetadata, Finding, Polyp
from app.logger import logger
from app.api.register_login_route import get_current_user


from sqlalchemy.orm import Session

import uuid
import os

from dateutil.parser import isoparse

from datetime import datetime

router = APIRouter(tags=["images"])

@router.get("/images/{image_id}")
def get_image(image_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    img = db.query(Images).filter_by(image_id = image_id).first()
    if not img:
        raise HTTPException(status_code = 404, detail = "Image not found")
    if not os.path.exists(img.image_path):
        raise HTTPException(status_code = 404, detail = "Image file not found on disk")

    transcript = db.query(TranscriptModel).filter_by(transcript_id=img.transcript_id).first()
    if not transcript or transcript.user_id != current_user.id:
        raise HTTPException(status_code = 403, detail = "Not Authorized")
    
    return FileResponse(img.image_path, media_type = "image/png")
