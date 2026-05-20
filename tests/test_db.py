import pytest 

from datetime import datetime, date

from app.models.colonoscopy import ColonoscopyReportFinal, ColonoscopyReportWithMetadataFinal, ProcedureMetadataFinal, ColonoscopyReportWithTime, ProcedureMetadata, ColonoscopyReportWithMetadata
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

    mock_extracted_data = ColonoscopyReportFinal(
        
        cecum_reached = True,
        cecum_reached_time=datetime(2025,1,1,10,0),
        procedure_end_time=datetime(2025,1,1,10,6),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        
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

    metadata = ProcedureMetadataFinal(
        patient_name = "Papa Smurf",
        patient_NHI = "ABCD1234",
        procedure_date = today.date(),
        patient_dob = datetime(1950,1,1),
        endoscopist_id = 1

    )

    full_report = ColonoscopyReportWithMetadataFinal(
        
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

##################################################################################
### need to also test new constraints around procedure times, withdrawal times ###
##################################################################################

def test_withdrawal_time_computed(db_session, procedure):
    proc1 = procedure

    db_session.add(proc1)
    db_session.commit()
    db_session.refresh(proc1)

    assert proc1.withdrawal_time == 6.0

def test_withdrawal_time_cecum_not_reached(db_session, procedure):
    proc1 = ProcedureModel(
        patient_id = "ABC1234",
        patient_name = "santa claus",
        procedure_date = datetime(2024,1,1),
        patient_dob = datetime(1980,1,1),
        endoscopist_id = 1,
        cecum_reached = False,
        cecum_reached_time = None,
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        
    )
    db_session.add(proc1)
    db_session.commit()
    db_session.refresh(proc1)

    assert proc1.withdrawal_time is None

def test_times_wrong_order(db_session):
    proc1 = ProcedureModel(
        patient_id = "ABC1234",
        patient_name = "santa claus",
        procedure_date = datetime(2024,1,1),
        patient_dob = datetime(1980,1,1),
        endoscopist_id = 1,
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,6),
        procedure_end_time = datetime(2025,1,1,10,0),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        
    )
    db_session.add(proc1)
    with pytest.raises(IntegrityError) as e:
        db_session.commit()
    
    assert "check_time_order" in str(e.value)

def test_unique_patient_date(db_session):
    proc1 = ProcedureModel(
        patient_id = "ABC1234",
        patient_name = "santa claus",
        procedure_date = datetime(2024,1,1),
        patient_dob = datetime(1980,1,1),
        endoscopist_id = 1,
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        
    )

    proc2 = ProcedureModel(
        patient_id = "ABC1234",
        patient_name = "santa claus",
        procedure_date = datetime(2024,1,1),
        patient_dob = datetime(1980,1,1),
        endoscopist_id = 1,
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        
    )

    db_session.add(proc1)
    db_session.commit()

    db_session.add(proc2)

    with pytest.raises(IntegrityError):
        db_session.commit() 

def test_bbps_computed_column(db_session, procedure): #does the bbps_total computed column work correctly
    proc1 = procedure

    db_session.add(proc1)
    db_session.commit()

    r = db_session.query(ProcedureModel).first()
    assert r.bbps_total == 9

def test_bbps_null_value(db_session): #does a null value for a segment result in null for the total (expected behavior)
    proc1 = ProcedureModel(
        patient_id = "ABC1234",
        patient_name = "santa claus",
        procedure_date = datetime(2024,1,1),
        patient_dob = datetime(1980,1,1),
        endoscopist_id = 1,
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = None,
        bbps_transverse = 3,
        bbps_left = 3,
        
    )

    db_session.add(proc1)
    db_session.commit()

    r = db_session.query(ProcedureModel).first()

    assert r.bbps_total == None
    assert r.bbps_right == None

def test_bbps_insert_update_total(db_session): #does the null bbps_total value update once you enter a valid value for a segment
    proc1 = ProcedureModel(
        patient_id = "ABC1234",
        patient_name = "santa claus",
        procedure_date = datetime(2024,1,1),
        endoscopist_id = 1,
        patient_dob = datetime(1980,1,1),
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = None,
        bbps_transverse = 3,
        bbps_left = 3,
        
    )

    db_session.add(proc1)
    db_session.commit()

    proc1.bbps_right = 2

    db_session.commit()
    db_session.refresh(proc1)

    assert proc1.bbps_total == 8

def test_bbps_invalid_value(db_session):
    proc1 = ProcedureModel(
        patient_id = "ABC1234",
        patient_name = "santa claus",
        procedure_date = datetime(2024,1,1),
        endoscopist_id = 1,
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = 9, #invalid value - test check constraint
        bbps_transverse = 3,
        bbps_left = 3,
        
    )
    db_session.add(proc1)
    with pytest.raises(IntegrityError) as e:
        db_session.commit()

def test_full_pipeline(db_session): #does raw JSON (from the LLM) end up in the database in correct format?
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
        'patient_dob': date(1960,1,1),
        'procedure_date': datetime(2025,1,1)
    }
    
    metadata = ProcedureMetadataFinal(**raw_metadata)
    report = ColonoscopyReportFinal(**raw)
    procedure = map_procedure(report, metadata)
    for polyp in report.polyps:
        procedure.polyps.append(map_polyp(polyp))

    db_session.add(procedure)
    db_session.commit()

    saved = db_session.query(ProcedureModel).first()

    assert len(saved.polyps) == 1
    assert saved.polyps[0].size_mm == 5.0

def test_transcript_creation_retrieval(db_session, client_db):
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
        metadata = metadata,
        report = report
    )

    transcript = functions.map_transcription(full_report)
    db_session.add(transcript)
    db_session.commit()

    print(f"transcript ID: {transcript.transcript_id}")
    response = client_db.get(f"/transcripts/{transcript.transcript_id}")

    assert response.status_code == 200
    data = response.json()

    assert data['report']['metadata']['patient_name'] == 'bob thebuilder'

def test_full_pipeline_with_api_endpoint(db_session, client_db): #does raw JSON (from the LLM) end up in the database in correct format and can we retrieve it with the api endpoint
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
    #validate the data
    metadata = ProcedureMetadataFinal(**raw_metadata)
    report = ColonoscopyReportFinal(**raw)

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

