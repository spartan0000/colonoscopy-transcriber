import pytest 

from datetime import datetime, date

from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportFinal, ColonoscopyReportWithMetadataFinal, ProcedureMetadataFinal, ColonoscopyReportWithTime, ProcedureMetadata, ColonoscopyReportWithMetadata
from app.database.models import ProcedureModel, PolypModel, FindingModel, EndoscopistLookup, PolypLocationLookup, TranscriptModel, UserModel
from app.services.functions import map_procedure, map_findings, map_polyp

from app.services import functions

from app.api.write_db_generate_pdf_route import CONSTRAINT_ERROR_MESSAGES

from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from tests.conftest import procedure_factory
from unittest.mock import patch, AsyncMock



def test_end_to_end(db_session, test_user):
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
        terminal_ileum_intubated = True,
        
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

    functions.write_transcription_record(db_session, full_report, user_id=test_user.id)

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

def test_withdrawal_time_cecum_not_reached(db_session, test_user):
    proc1 = ProcedureModel(
        user_id = test_user.id,
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

def test_times_wrong_order(db_session, test_user):
    proc1 = ProcedureModel(
        user_id = test_user.id,
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
        terminal_ileum_intubated = True,
        
    )
    db_session.add(proc1)
    with pytest.raises(IntegrityError) as e:
        db_session.commit()
    
    assert "check_time_order" in str(e.value)

def test_unique_patient_date(db_session, test_user):
    proc1 = ProcedureModel(
        user_id = test_user.id,
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
        terminal_ileum_intubated = True,
        
    )

    proc2 = ProcedureModel(
        user_id = test_user.id,
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

def test_bbps_null_value(db_session, test_user): #does a null value for a segment result in null for the total (expected behavior)
    proc1 = ProcedureModel(
        user_id = test_user.id,
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
        terminal_ileum_intubated = True,
        
    )

    db_session.add(proc1)
    db_session.commit()

    r = db_session.query(ProcedureModel).first()

    assert r.bbps_total == None
    assert r.bbps_right == None

def test_bbps_insert_update_total(db_session, test_user): #does the null bbps_total value update once you enter a valid value for a segment
    proc1 = ProcedureModel(
        user_id = test_user.id,
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
        terminal_ileum_intubated = True,
        
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
        terminal_ileum_intubated = True,
        
    )
    db_session.add(proc1)
    with pytest.raises(IntegrityError) as e:
        db_session.commit()

def test_full_pipeline(db_session, test_user): #does raw JSON (from the LLM) end up in the database in correct format?
    raw = {
        'cecum_reached': True,
        'cecum_reached_time': datetime(2025,1,1,10,0),
        'procedure_end_time': datetime(2025,1,1,10,6),
        'bbps_right' : 3,
        'bbps_transverse' : 3,
        'bbps_left' : 3,
        'terminal_ileum_intubated': True,
        
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
    procedure = map_procedure(report, metadata, user_id=test_user.id)
    for polyp in report.polyps:
        procedure.polyps.append(map_polyp(polyp))

    db_session.add(procedure)
    db_session.commit()

    saved = db_session.query(ProcedureModel).first()

    assert len(saved.polyps) == 1
    assert saved.polyps[0].size_mm == 5.0

def test_transcript_creation_retrieval(db_session, client_db, auth_header, test_user): 
    #this test passes without the cecum landmarks because the TranscriptModel does not have the same constraint
    #as the ProcedureModel which is the finalized report.  This is intentional as the TranscriptModel is a work in progress
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

    transcript = functions.map_transcription(full_report, user_id=test_user.id)
    db_session.add(transcript)
    db_session.commit()

    print(f"transcript ID: {transcript.transcript_id}")
    response = client_db.get(f"/transcripts/{transcript.transcript_id}/report", headers=auth_header)

    assert response.status_code == 200
    data = response.json()

    assert data['report']['metadata']['patient_name'] == 'bob thebuilder'

def test_full_pipeline_with_api_endpoint(db_session, client_db, auth_header, test_user): #does raw JSON (from the LLM) end up in the database in correct format and can we retrieve it with the api endpoint
    raw = {
        'cecum_reached': True,
        'cecum_reached_time': datetime(2025,1,1,10,0),
        'procedure_end_time': datetime(2025,1,1,10,6),
        'bbps_right' : 3,
        'bbps_transverse' : 3,
        'bbps_left' : 3,
        'terminal_ileum_intubated': True,
        
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
    procedure = map_procedure(report, metadata, user_id=test_user.id)
    for polyp in report.polyps:
        procedure.polyps.append(map_polyp(polyp))

    db_session.add(procedure)
    db_session.commit()

    #retrieve data via api endpoint
    response = client_db.get(f"/procedures/{procedure.procedure_id}/full", headers=auth_header)
    
    data = response.json()
    print(data)

    assert response.status_code == 200
    assert len(data['polyps']) == 1
    assert data['cecum_reached'] == True

# add tests for the new cecal intubation criteria fields in the ProcedureModel
def test_cecal_intubation_constraint(db_session, procedure_factory):
    #since the factory already does the commit - the integrity error should be raised here when we try to create the procedure.
    #originally had a separate flush with pytest.raises but that didnt' raise anything because the flush was called after the original commit where the error probably happened
    with pytest.raises(IntegrityError) as e:
        procedure1 = procedure_factory(
            terminal_ileum_intubated = None,
            ileocecal_valve_identified = None,
            appendiceal_orifice_identified = None,
            tripartite_fold_identified = None,
            other_landmarks_identified = None,
        )

# def test_constraint_exists(db_session):
#     result = db_session.execute(text("SELECT conname FROM pg_constraint WHERE conname = 'check_cecum_reached_criteria'")).fetchall()
#     print(result)
#     assert len(result) == 1

def test_cecum_reached_terminal_ileum_only(procedure_factory):
    #just testing constraints here - in reality, if you've intubated the TI, then you've obviously identified the ICV as well.
    procedure1 = procedure_factory(
        cecum_reached = True,
        terminal_ileum_intubated = True,
        ileocecal_valve_identified = False,
        appendiceal_orifice_identified = False,
        tripartite_fold_identified = False,
        other_landmarks_identified = False
    )
    #should not raise an integrity error- the procedure factory fixture commits to the db so just running this will raise an error if there is a contraint violation


def test_cecum_reached_appendiceal_orifice_and_icv(procedure_factory):
    procedure1 = procedure_factory(
        cecum_reached = True,
        terminal_ileum_intubated = False,
        ileocecal_valve_identified = True,
        appendiceal_orifice_identified = True,
        tripartite_fold_identified = True,
        other_landmarks_identified = False
    )

def test_finalize_returns_422_on_missing_landmarks(client_db, test_user, auth_header, transcript_factory, build_valid_report_payload):

    transcript = transcript_factory(user_id = test_user.id)
    payload = build_valid_report_payload(transcript.transcript_id) # the payload fixture has all the cecal landmarks as False and cecum reached True

    res = client_db.post(f"/transcripts/{transcript.transcript_id}/write", json=payload, headers=auth_header)

    assert res.status_code == 422


#this test follows the full lifecycle of a transcript from creation to finalization
#and checks that the endoscopist_id is preserved throughtout the process
#endoscopist_id is pulled from the user model when the transcript is created and should be preserved for the entire
#cycle of the transcript.

@pytest.mark.asyncio
@patch('app.services.functions.chat_client.responses.parse', new_callable=AsyncMock)
async def test_endoscopist_id_survives_full_lifecycle(mock_parse, db_session, client_db, auth_header, test_user):
     
    expected_endoscopist_id = test_user.endoscopist_id

    assert expected_endoscopist_id is not None


    mock_report = ColonoscopyReport(
        cecum_reached = True,
        terminal_ileum_intubated = True,
        
        
    )

    mock_response = AsyncMock()
    mock_response.output_parsed = mock_report
    mock_parse.return_value = mock_response

    #start a new transcript - this should pull the endoscopist_id from the user automatically
    start_res = client_db.post("/transcripts/start", headers=auth_header, json={
        "patient_name": "Bob the Builder",
        "patient_dob": "1980-01-01",
        "patient_nhi": "ABC1234"
    },
    )
    assert start_res.status_code == 200
    transcript_id = start_res.json()['transcript_id']

    transcript = db_session.query(TranscriptModel).filter_by(transcript_id=transcript_id).first()
    assert transcript.endoscopist_id == expected_endoscopist_id

    #now actually "transcribe" a procedure - this should also preserve the endoscopist_id
    transcript_res = client_db.post(f"/transcribe/{transcript_id}",
                                     headers=auth_header,
                                     files={"file": ("transcript.txt", b"cecum reached, terminal ileum intubated", "text/plain")},
                                     data={"procedure_end_time": datetime(2025,1,1,10,6).isoformat(), "cecum_reached_time": datetime(2025,1,1,10,0).isoformat()},
                                    )

    assert mock_parse.called
    
    assert transcript_res.status_code == 200
    #check that the endoscopist_id is preserved in the report returned by the transcribe endpoint
    assert transcript_res.json()['report']['metadata']['endoscopist_id'] == expected_endoscopist_id 

    db_session.refresh(transcript)

    #check that the endoscopist_id is preserved in the transcript model in the database
    assert transcript.endoscopist_id == expected_endoscopist_id 

    #add things the user would add to the report before finalizing it
    full_report = transcript_res.json()['report']
    full_report['report']['bbps_right'] = 3
    full_report['report']['bbps_transverse'] = 3
    full_report['report']['bbps_left'] = 3

    


    #test the finalizing endpoint /write which should also preserve the endoscopist_id
    #writes to the database

    print(f"Full Report: {full_report}")
    
    final_res = client_db.post(f"/transcripts/{transcript_id}/write", headers=auth_header, json=full_report)


    print(f"Final response: {final_res.json()}")
    assert final_res.status_code == 200

    procedure_id = final_res.json()['procedure_id']

    procedure = db_session.query(ProcedureModel).filter_by(procedure_id=procedure_id).first()
    #check that the endoscopist_id is preserved in the finalized procedure model in the database
    assert procedure.endoscopist_id == expected_endoscopist_id

#series of tests to test the constraints in the ProcedureModel table which is written to using the transcripts/transcript_id/write endpoint
def test_write_endpoint_check_constraint_cecum_reached(client_db, auth_header, test_user, transcript_factory, build_valid_report_payload):
    transcript = transcript_factory(user_id = test_user.id)

    payload = build_valid_report_payload(
        transcript.transcript_id,

    )

    res = client_db.post(f"transcripts/{transcript.transcript_id}/write", headers=auth_header, json = payload)

    assert res.status_code == 422
    assert res.json()['detail'] == CONSTRAINT_ERROR_MESSAGES['check_cecum_reached_criteria']

def test_write_endpoint_rejects_time_order_violation(client_db, auth_header, test_user, transcript_factory, build_valid_report_payload):
    transcript = transcript_factory(user_id = test_user.id)

    payload = build_valid_report_payload(
        transcript.transcript_id,
        cecum_reached_time = datetime(2025,1,1,10,6), #this time is after the procedure end time which violates the constraint
        procedure_end_time = datetime(2025,1,1,10,0),

    )

    res = client_db.post(f"/transcripts/{transcript.transcript_id}/write", headers=auth_header, json=payload)
    assert res.status_code == 422

    print(res.json()['detail'])

    assert res.json()['detail'] == CONSTRAINT_ERROR_MESSAGES['check_time_order']

def test_write_endpoint_rejects_duplicate_patient_procedure_date(client_db, auth_header, test_user, transcript_factory, procedure_factory, build_valid_report_payload):
    procedure_factory(user_id = test_user.id, patient_id = 'ABC1234', procedure_date = datetime(2025,1,1)) #the factory defaults are NHI ABC1234 and procedure date 2025-1-1

    transcript = transcript_factory(user_id = test_user.id)

    payload = build_valid_report_payload(
        transcript.transcript_id,
        metadata_overrides = {
            'patient_nhi' : 'ABC1234',
            'procedure_date' : datetime(2025,1,1)
        }
    )

    res = client_db.post(f"/transcripts/{transcript.transcript_id}/write", headers=auth_header, json = payload)

    assert res.status_code == 422
    assert res.json()['detail'] == CONSTRAINT_ERROR_MESSAGES['uq_patient_procedure_date']



