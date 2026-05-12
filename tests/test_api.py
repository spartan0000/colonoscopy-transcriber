import pytest 
import sys

from datetime import datetime

from fastapi.testclient import TestClient
from app.main import app

from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportWithMetadata, ProcedureMetadata
from app.database.models import ProcedureModel, PolypModel, FindingModel, EndoscopistLookup, PolypLocationLookup
from app.services.functions import map_procedure, map_findings, map_polyp, map_transcription

from app.services import functions

from sqlalchemy.exc import IntegrityError


def test_get_procedure(db_session, client_db):
    
    
    procedure = ProcedureModel(
        patient_name = 'santa claus',
        patient_id = '123',
        endoscopist_id = 1,
        procedure_date = datetime(2025,1,1),
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        
    )

    db_session.add(procedure)
    db_session.commit()

    response = client_db.get(f"/procedures/{procedure.procedure_id}/full")
    

    assert response.status_code == 200

    
    data = response.json()

    assert data['polyps'] == []
    assert data['findings'] == []

def test_get_procedure_with_polyps(db_session, client_db, procedure):
    proc = procedure
    db_session.add(proc)
    db_session.commit()

    polyp = PolypModel(
        procedure = proc,
        size_mm = 2.0,
        location_code = 'cecum',
        morphology = 'sessile'
    )

    db_session.add(polyp)
    db_session.commit()

    response = client_db.get(f"/procedures/{procedure.procedure_id}/full")

    data = response.json()

    assert response.status_code == 200
    assert len(data['polyps']) == 1
    assert data['polyps'][0]['size_mm'] == 2.0

def test_get_procedure_not_found(client_db): #test the Procedure not found http exception
    res = client_db.get(f"/procedures/99999/full")

    assert res.status_code == 404

def test_invalid_procedure_id(client_db):
    res = client_db.get("/procedures/abc/full") #actually did this error on accident on an earlier test but testing it for real this time as an expected error
    assert res.status_code == 422

def test_polyps_procedure_relationship(client_db, db_session): #making sure that polyps relationship attaches it to the correct procedure
    p1 = ProcedureModel(
        patient_name = 'santa claus',
        patient_id = 'ABC1234',
        endoscopist_id = 1,
        procedure_date = datetime(2025,1,1),
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        created_at = datetime(2025,1,1)
    )

    p2 = ProcedureModel(
        patient_name = 'papa smurf',
        patient_id = 'DEF1234',
        endoscopist_id = 1,
        procedure_date = datetime(2025,1,1),
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        created_at = datetime(2025,1,1)
    )

    db_session.add_all([p1,p2])
    db_session.commit()

    polyp = PolypModel(
        procedure = p1,
        polyp_id = 1,
        location_code = 'cecum',
        morphology = 'sessile',
        size_mm = 2.0
    )

    db_session.add(polyp)
    db_session.commit()

    res = client_db.get(f"/procedures/{p2.procedure_id}/full")

    data = res.json()

    assert data['polyps'] == []

def test_multiple_polyps(db_session, client_db, procedure):
    proc = procedure

    polyp1 = PolypModel(
        procedure = proc,
        location_code = 'cecum',
        morphology = 'sessile',
        size_mm = 1.0
    )
    polyp2 = PolypModel(
        procedure = proc,
        location_code = 'transverse_colon',
        morphology = 'sessile',
        size_mm = 2.0
    )

    db_session.add_all([polyp1,polyp2])
    db_session.commit()

    res = client_db.get(f"/procedures/{proc.procedure_id}/full")
    data = res.json()

    assert len(data['polyps']) == 2

def test_get_procedure_with_findings(db_session, client_db, procedure):
    proc = procedure
    db_session.add(proc)
    db_session.commit()

    finding = FindingModel(
        procedure = proc,
        description = 'something weird',
        biopsy_taken = True,
        created_at = datetime(2025,1,1)
    )

    db_session.add(finding)
    db_session.commit()

    response = client_db.get(f"/procedures/{procedure.procedure_id}/full")

    data = response.json()

    assert response.status_code == 200
    assert len(data['findings']) == 1

def test_transcript_not_found(client_db):
    res = client_db.get("/transcripts/99999")
    assert res.status_code == 404

