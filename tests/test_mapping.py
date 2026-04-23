import pytest
from pydantic import ValidationError
from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportWithMetadata, ProcedureMetadata, Finding, Polyp
from app.database.models import ProcedureModel, PolypModel, FindingModel
from app.services.functions import map_polyp, map_findings, map_procedure
from datetime import date

from sqlalchemy.exc import IntegrityError

#test mapping functions - answers the question - given clean input from the pydantic models, does the mapping function produce the expected sqlalchemy model structures
#no db connection required.  db connection and writing is in the test_db.py file


def test_map_polyp():
    p = Polyp(
        polyp_id = 1,
        size_mm = 5.0,
        location = 'ascending_colon',
        morphology = 'sessile',
        resection_method = 'snare',
        resection_complete = True,
        retrieved = True,
    )
    mapped = map_polyp(p)

    assert mapped.size_mm == p.size_mm
    assert mapped.location_code == p.location
    assert mapped.morphology == p.morphology
    assert mapped.resection_method == p.resection_method
    assert mapped.retrieved == p.retrieved

def test_map_polyp_optional_fields():
    p = Polyp(
        polyp_id = 1,
        location = 'cecum',

    )

    mapped = map_polyp(p)
    assert mapped.resection_method == None
    assert mapped.resection_complete == None
    assert mapped.retrieved == None

def test_missing_size_is_none():

    p = Polyp(
        polyp_id = 1,
        
        location = 'ascending_colon',
        
    )

    assert p.size_mm == None

def test_map_polyp_relationship():
    p = Polyp(
        polyp_id = 1,
        size_mm = 5.0,
        location = 'ascending_colon',

    )
    procedure = ProcedureModel(
        patient_id = "ABC1234",
        patient_name = "Test Patient",
        procedure_date = date.today(),
        endoscopist_id = 1,
        cecum_reached = True,
        withdrawal_time = 1.0,
        created_at = date.today()

    )

    polyp = map_polyp(p)
    procedure.polyps.append(polyp)

    assert polyp in procedure.polyps
    assert polyp.procedure == procedure

def test_mapping_does_not_mutate(): #test that the mapping function does not mutate the original pydantic model
    p = Polyp(
        polyp_id = 1,
        size_mm = 5.0,
        location = 'ascending_colon',
        morphology = 'sessile',
    )

    _ = map_polyp(p)

    assert p.size_mm == 5.0
    assert p.location == 'ascending_colon'

def test_map_procedure():
    metadata = ProcedureMetadata(
        patient_name = "test patient",
        patient_NHI = "ABC1234",
        procedure_date = date.today(),
        endoscopist_id = 1
    )

    report = ColonoscopyReport(
        cecum_reached = True,
        withdrawal_time = 5.0
    )

    proc = map_procedure(report, metadata)

    assert proc.patient_id == "ABC1234"
    assert proc.patient_name == "test patient"
    assert proc.cecum_reached == True
    assert proc.withdrawal_time == 5.0


def test_full_mapping():
    metadata = ProcedureMetadata(
        patient_name = "test patient",
        patient_NHI = "ABC1234",
        procedure_date = date.today(),
        endoscopist_id = 1
    )

    report = ColonoscopyReport(
        cecum_reached = True,
        withdrawal_time = 5.0,
        polyps = [
            {
                'polyp_id': 1,
                'size_mm': 5.0,
                'location': 'ascending_colon',
                'morphology': 'sessile',
            }
        ]
    )

    procedure = map_procedure(report, metadata)

    for polyp in report.polyps:
        procedure.polyps.append(map_polyp(polyp))
    
    assert len(procedure.polyps) ==  1



