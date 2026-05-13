import pytest
from pydantic import ValidationError
from app.models.colonoscopy import ColonoscopyReportFinal, ColonoscopyReportWithMetadataFinal, ProcedureMetadataFinal, FindingFinal, PolypFinal
from app.models.colonoscopy import ColonoscopyReportWithTime, ProcedureMetadata, ColonoscopyReportWithMetadata
from app.database.models import ProcedureModel, PolypModel, FindingModel
from app.services.functions import map_polyp, map_findings, map_procedure, map_transcription
from datetime import date, datetime

from sqlalchemy.exc import IntegrityError

#test mapping functions - answers the question - given clean input from the pydantic models, does the mapping function produce the expected sqlalchemy model structures
#no db connection required.  db connection and writing is in the test_db.py file


def test_map_polyp():
    p = PolypFinal(
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
    
    
    p = PolypFinal(
        polyp_id = 1,
        size_mm = 1.0,
        location = 'cecum',
        

    )

    mapped = map_polyp(p)

    assert mapped.morphology is None
    assert mapped.resection_method is None

    
def test_missing_size():
    with pytest.raises(ValidationError):
        p = PolypFinal(
            polyp_id = 1,
            
            location = 'ascending_colon',
            
        )

    
def test_map_polyp_relationship():
    p = PolypFinal(
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
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        created_at = date.today()

    )

    polyp = map_polyp(p)
    procedure.polyps.append(polyp)

    assert polyp in procedure.polyps
    assert polyp.procedure == procedure

def test_mapping_does_not_mutate(): #test that the mapping function does not mutate the original pydantic model
    p = PolypFinal(
        polyp_id = 1,
        size_mm = 5.0,
        location = 'ascending_colon',
        morphology = 'sessile',
    )

    _ = map_polyp(p)

    assert p.size_mm == 5.0
    assert p.location == 'ascending_colon'

def test_map_procedure():
    metadata = ProcedureMetadataFinal(
        patient_name = "test patient",
        patient_NHI = "ABC1234",
        procedure_date = date.today(),
        patient_dob = date(1910,1,1),
        endoscopist_id = 1
    )

    report = ColonoscopyReportFinal(
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = 2,
        bbps_transverse = 2,
        bbps_left = 3,
    )

    proc = map_procedure(report, metadata)

    assert proc.patient_id == "ABC1234"
    assert proc.patient_name == "test patient"
    assert proc.cecum_reached == True
    


def test_full_mapping():
    metadata = ProcedureMetadataFinal(
        patient_name = "test patient",
        patient_NHI = "ABC1234",
        patient_dob = date(1900,1,1),
        procedure_date = date.today(),
        endoscopist_id = 1
    )

    report = ColonoscopyReportFinal(
        cecum_reached = True,
        bbps_right = 2,
        bbps_transverse = 2,
        bbps_left = 3,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
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



def test_map_transcript():
    raw = {
        'cecum_reached': True,
        'cecum_reached_time': datetime(2025,1,1,10,0),
        'procedure_end_time': datetime(2025,1,1,10,6),
        'bbps_right' : 3,
        'bbps_transverse' : 3,
        'bbps_left' : 3,
        
        'polyps':[
            {
                'polyp_id': 1,
                'location': 'cecum',
                'morphology': 'sessile',
                'size_mm':5.0
            }
        ],
        'withdrawal_time': 100,

    }

    raw_metadata = {
        'patient_name': 'bob thebuilder',
        'patient_NHI': 'ABC1234',
        'endoscopist_id': 1,
        'patient_dob': date(1940,1,1),
        'procedure_date': datetime(2025,1,1)
    }

    metadata = ProcedureMetadata(**raw_metadata)
    report = ColonoscopyReportWithTime(**raw)

    full_report = ColonoscopyReportWithMetadata(
        metadata=metadata,
        report=report
    )

    mapped = map_transcription(full_report)

    assert mapped.patient_name == 'bob thebuilder'
    assert mapped.cecum_reached == True
    assert len(mapped.polyps) == 1