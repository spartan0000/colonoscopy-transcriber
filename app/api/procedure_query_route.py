from app.services import functions

from app.models.colonoscopy import ColonoscopyReport
from app.database.models import ProcedureModel, PolypModel

from sqlalchemy.orm import Session

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.database.connection import get_db


router = APIRouter(tags = ['procedure_query'])

########
#need to decide what other data gets pulled from the db when calling this endpoint

@router.get("/procedures/{procedure_id}/full")
def get_full_procedure(procedure_id: int, db: Session = Depends(get_db)):
    procedure = db.query(ProcedureModel).filter(ProcedureModel.procedure_id == procedure_id).first()

    if not procedure:
        raise HTTPException(status_code=404, detail="Procedure not found")

    return {
        "procedure_id": procedure_id,
        "cecum_reached": procedure.cecum_reached,
        "bbps_right": procedure.bbps_right,
        "bbps_transverse": procedure.bbps_transverse,
        "bbps_left": procedure.bbps_left,
        "bbps_total": procedure.bbps_total,
        "polyps": [
            {
                "size_mm": p.size_mm,    
                "location_code": p.location_code
            }
            for p in procedure.polyps

        ],
        "findings": [
            {
                "description": f.description,
                "biopsy_taken": f.biopsy_taken,
            }
            for f in procedure.findings

        ]
    }