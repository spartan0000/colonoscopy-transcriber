import pytest 

from datetime import datetime

from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportWithMetadata, ProcedureMetadata
from app.database.models import ProcedureModel, PolypModel, FindingModel, EndoscopistLookup, PolypLocationLookup
from app.services.functions import map_procedure, map_findings, map_polyp

from app.services import functions

from sqlalchemy.exc import IntegrityError



def test_end_to_end(db_session):
    #mock LLM outputs
    today = datetime.today()
    mock_transcription = {
        'transcription_result': {
            'entire_text': 'fake transcription text',
            'segments': []
        },
        
    }

    mock_extracted_data = ColonoscopyReport(
        cecum_reached = True,
        withdrawal_time = 500,
        polyps = [
            {
                'polyp_id': 1,
                'size_mm': 5,
                'location': 'sigmoid_colon',
                'morphology': 'sessile',
                'resection_method': 'snare',
                'resection_complete': True,
                'retrieved': True
            },
            {
                'polyp_id': 2,
                'size_mm': 10,
                'location': 'transverse_colon',
                'morphology': 'pedunculated',
                'resection_method': 'biopsy_forceps',
                'resection_complete': False,
                'retrieved': False
            }

        ],

    )

    metadata = ProcedureMetadata(
        patient_name = "Papa Smurf",
        patient_NHI = "ABCD1234",
        procedure_date = today.date(),
        endoscopist_id = 1

    )

    full_report = ColonoscopyReportWithMetadata(
        metadata = metadata,
        report = mock_extracted_data
    )

    #write to db

    functions.write_transcription_record(db_session, full_report)

    procedure = db_session.query(ProcedureModel).filter_by(patient_id = "ABCD1234").first()

    assert procedure is not None
    assert procedure.patient_name == "Papa Smurf"
    assert procedure.endoscopist_id == 1
    assert procedure.cecum_reached == True
    assert procedure.polyps[0].size_mm == 5
    assert procedure.polyps[0].location_code == "sigmoid_colon"

def test_polyp_size_constraint(db_session, procedure):
    
    polyp = PolypModel(
        procedure = procedure,
        location_code = "sigmoid_colon",
        size_mm = -5,
        morphology = "sessile"

    )

    db_session.add(polyp)
    

    with pytest.raises(IntegrityError) as e:
        db_session.commit()
    print(e.value.orig)

def test_missing_morphology(db_session, procedure):
    polyp = PolypModel(
        procedure = procedure,
        location_code = "cecum",
        size_mm = 2.0,
        morphology = None
    )
    db_session.add(polyp)

    with pytest.raises(IntegrityError) as e:
        db_session.commit()
    print(e.value.orig)

def test_lookup_table_dependency(db_session, procedure):
    db_session.query(PolypLocationLookup).delete()
    db_session.commit()

    polyp = PolypModel(
        procedure = procedure,
        size_mm = 1.0,
        location_code = 'cecum',
        morphology = 'sessile'
    )

    db_session.add(polyp)

    with pytest.raises(IntegrityError) as e:
        db_session.commit()
    print(e.value.orig)

def test_delete_procedure_cascade(db_session, procedure):
    p = PolypModel(
        procedure = procedure,
        polyp_id = 1,
        size_mm = 3,
        morphology = 'sessile',
        location_code = 'cecum'
    )
    db_session.add(p)
    db_session.commit()

    db_session.delete(procedure)
    db_session.commit()

    r = db_session.query(PolypModel).all()
    assert len(r) == 0

def test_unique_patient_date(db_session):
    proc1 = ProcedureModel(
        patient_id = "ABC1234",
        patient_name = "santa claus",
        procedure_date = datetime(2024,1,1),
        endoscopist_id = 1,
        cecum_reached = True,
        withdrawal_time = 10
    )

    proc2 = ProcedureModel(
        patient_id = "ABC1234",
        patient_name = "santa claus",
        procedure_date = datetime(2024,1,1),
        endoscopist_id = 1,
        cecum_reached = True,
        withdrawal_time = 10
    )

    db_session.add(proc1)
    db_session.commit()

    db_session.add(proc2)

    with pytest.raises(IntegrityError):
        db_session.commit() 

def test_full_pipeline(db_session): #does raw JSON (from the LLM) end up in the database in correct format?
    raw = {
        'cecum_reached': True,
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
        'procedure_date': datetime(2025,1,1)
    }
    
    metadata = ProcedureMetadata(**raw_metadata)
    report = ColonoscopyReport(**raw)
    procedure = map_procedure(report, metadata)
    for polyp in report.polyps:
        procedure.polyps.append(map_polyp(polyp))

    db_session.add(procedure)
    db_session.commit()

    saved = db_session.query(ProcedureModel).first()

    assert len(saved.polyps) == 1
    assert saved.polyps[0].size_mm == 5.0

def test_full_pipeline_with_api_endpoint(db_session, client_db): #does raw JSON (from the LLM) end up in the database in correct format and can we retrieve it with the api endpoint
    raw = {
        'cecum_reached': True,
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
        'procedure_date': datetime(2025,1,1)
    }
    #validate the data
    metadata = ProcedureMetadata(**raw_metadata)
    report = ColonoscopyReport(**raw)

    #persist in the database
    procedure = map_procedure(report, metadata)
    for polyp in report.polyps:
        procedure.polyps.append(map_polyp(polyp))

    db_session.add(procedure)
    db_session.commit()

    #retrieve data via api endpoint
    response = client_db.get(f"/procedures/{procedure.procedure_id}/full")
    
    data = response.json()
    print(data)

    assert response.status_code == 200
    assert len(data['polyps']) == 1
    assert data['cecum_reached'] == True

