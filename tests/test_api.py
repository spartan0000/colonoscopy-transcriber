import pytest 
import sys

from datetime import datetime

from fastapi.testclient import TestClient
from app.main import app

from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportWithMetadata, ProcedureMetadata
from app.database.models import ProcedureModel, PolypModel, FindingModel, EndoscopistLookup, PolypLocationLookup
from app.services.functions import map_procedure, map_findings, map_polyp

from app.services import functions

from sqlalchemy.exc import IntegrityError


def test_get_procedure(db_session, client_db):
    
    
    procedure = ProcedureModel(
        patient_name = 'santa claus',
        patient_id = '123',
        endoscopist_id = 1,
        procedure_date = datetime(2025,1,1),
        cecum_reached = True,
        withdrawal_time = 10
    )

    db_session.add(procedure)
    db_session.commit()

    response = client_db.get(f"/procedures/{procedure.procedure_id}/full")
    print(f"Status: {response.status_code}")
    print(f"Body: {response.text}")


    assert response.status_code == 200

    
    data = response.json()

    assert data['polyps'] == []

