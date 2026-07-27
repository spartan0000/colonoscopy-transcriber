import pytest 
import sys
import os
from dotenv import load_dotenv
import jwt

from datetime import date, datetime

from fastapi.testclient import TestClient
from app.main import app

from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportWithMetadata, ProcedureMetadata, ColonoscopyReportFinal, ProcedureMetadataFinal, ColonoscopyReportWithMetadataFinal
from app.database.models import ProcedureModel, PolypModel, FindingModel, EndoscopistLookup, PolypLocationLookup, TranscriptModel, Images, TranscriptStatus, UserModel
from app.services.functions import map_procedure, map_findings, map_polyp, map_transcription

from app.api.transcription_route import StartProcedureRequest

from app.services import functions

from sqlalchemy.exc import IntegrityError

from pwdlib import PasswordHash

import uuid

pwd_hasher = PasswordHash.recommended()
load_dotenv()

ALGORITHM = os.getenv("ALGORITHM")
SECRET_KEY = os.getenv("JWT_KEY")

def test_get_procedure(db_session, client_db, auth_header, test_user):
    
    
    procedure = ProcedureModel(
        user_id = test_user.id,
        patient_name = 'santa claus',
        patient_id = '123',
        endoscopist_id = 1,
        procedure_date = datetime(2025,1,1),
        patient_dob = datetime(1980,1,1),
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        
    )

    db_session.add(procedure)
    db_session.commit()

    response = client_db.get(f"/procedures/{procedure.procedure_id}/full", headers=auth_header)
    

    assert response.status_code == 200

    
    data = response.json()

    assert data['polyps'] == []
    assert data['findings'] == []

def test_get_procedure_with_polyps(db_session, client_db, procedure, auth_header):
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

    response = client_db.get(f"/procedures/{procedure.procedure_id}/full", headers=auth_header)

    data = response.json()

    assert response.status_code == 200
    assert len(data['polyps']) == 1
    assert data['polyps'][0]['size_mm'] == 2.0

def test_get_procedure_not_found(client_db, auth_header): #test the Procedure not found http exception
    res = client_db.get(f"/procedures/99999/full", headers=auth_header)

    assert res.status_code == 404

def test_invalid_procedure_id(client_db, auth_header):
    res = client_db.get("/procedures/abc/full", headers=auth_header) #actually did this error on accident on an earlier test but testing it for real this time as an expected error
    assert res.status_code == 422

def test_polyps_procedure_relationship(client_db, test_user, auth_header, db_session): #making sure that polyps relationship attaches it to the correct procedure
    p1 = ProcedureModel(
        user_id = test_user.id,
        patient_name = 'santa claus',
        patient_id = 'ABC1234',
        endoscopist_id = 1,
        procedure_date = datetime(2025,1,1),
        patient_dob = datetime(1980,1,1),
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        created_at = datetime(2025,1,1)
    )

    p2 = ProcedureModel(
        user_id = test_user.id,
        patient_name = 'papa smurf',
        patient_id = 'DEF1234',
        endoscopist_id = 1,
        procedure_date = datetime(2025,1,1),
        patient_dob = datetime(1980,1,1),
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

    res = client_db.get(f"/procedures/{p2.procedure_id}/full", headers=auth_header)

    data = res.json()

    assert data['polyps'] == []

def test_multiple_polyps(db_session, client_db, procedure, auth_header):
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

    res = client_db.get(f"/procedures/{proc.procedure_id}/full", headers=auth_header)
    data = res.json()

    assert len(data['polyps']) == 2

def test_get_procedure_with_findings(db_session, client_db, procedure, auth_header):
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

    response = client_db.get(f"/procedures/{procedure.procedure_id}/full", headers=auth_header)

    data = response.json()

    assert response.status_code == 200
    assert len(data['findings']) == 1

def test_transcript_not_found(client_db, auth_header):
    res = client_db.get("/transcripts/99999", headers=auth_header)
    assert res.status_code == 404


#test that the start route actually generates a transcript_id
#and then test the start route in more detail since we changed it from simply generating a fake dummy transcript to one
# that holds real data now

def test_start_route(client_db, auth_header, db_session):
    start_request = {
        'patient_name':'bob',
        'patient_dob': date(2020,1,1).isoformat(),
        'patient_nhi': 'ABC1234'
    }
    res = client_db.post("/transcripts/start", headers=auth_header, json=start_request)
    assert res.status_code == 200
    data = res.json()
    assert data['transcript_id'] is not None

    transcript_id = data['transcript_id']

    #check that the database was populated properly with the expected data
    transcript = db_session.get(TranscriptModel, transcript_id)
    
    assert transcript.patient_name == 'bob'
    assert transcript.patient_id == 'ABC1234' #on the front end and pydantic this field is called patient_nhi

def test_start_route_missing_required_field(client_db, auth_header):
    start_request = {
        'patient_name': 'bob',
        'patient_nhi': 'ABC1234'
    }

    res = client_db.post("/transcripts/start", headers=auth_header, json=start_request)

    assert res.status_code == 422 #should fail pydantic validation

def test_start_route_date_incorrect_format(client_db, auth_header):
    start_request = {
        'patient_name': 'bob',
        'patient_dob': '2001-1-1',
        'patient_nhi': 'ABC1234'
    }

    res = client_db.post("/transcripts/start", headers=auth_header, json=start_request)

    assert res.status_code == 422 #pydantic should reject the incorrect data format

def test_start_route_invalid_user(client_db, make_token):

    token = make_token(user_id=9999999)
    start_request = {
        'patient_name':'bob',
        'patient_dob': date(2020,1,1).isoformat(),
        'patient_nhi': 'ABC1234'
    }

    res = client_db.post("/transcripts/start", headers = {"Authorization": f"Bearer {token}"}, json=start_request)

    assert res.status_code == 401 #Unauthorized since the token is not from a user in the database

def test_write_endpoint_links_images_to_procedure(client_db, db_session, auth_header, test_user):
    
    
    fake_transcript_id = uuid.uuid4()

    transcript = TranscriptModel(transcript_id = fake_transcript_id, user_id = test_user.id)
    db_session.add(transcript)
    db_session.commit()

    #create two images associated with the transcript_id = 1 for now
    image1 = Images(
        transcript_id = fake_transcript_id,
        image_path = "path/to/image1.png",
        captured_at = datetime(2025,1,1,10,0,0)

    )

    image2 = Images(
        transcript_id = fake_transcript_id,
        image_path = "path/to/image2.png",
        captured_at = datetime(2025,1,1,10,0,1)
    )

    db_session.add_all([image1, image2])
    db_session.commit()

    #create a colonoscopy report to write to the final endpoint
    colonoscopy_report = ColonoscopyReportFinal(
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0,0).isoformat(),
        procedure_end_time = datetime(2025,1,1,10,6,0).isoformat(),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        polyps = [],
        findings = []
    )

    metadata = ProcedureMetadataFinal(
        patient_NHI = "ABC1234",
        patient_name = "Santa Claus",
        procedure_date = date(2025,1,1).isoformat(),
        endoscopist_id = 1,
        patient_dob = date(1980,1,1).isoformat(),
        indication = 'unknown'
    )

    colonoscopy_report_with_metadata = ColonoscopyReportWithMetadataFinal(
        metadata = metadata,
        report = colonoscopy_report
    )
    response = client_db.post("/write", params = {'transcript_id' : fake_transcript_id} , json = colonoscopy_report_with_metadata.model_dump(mode = "json"), headers=auth_header)

    assert response.status_code == 200

    #need to get the updated procedure id associated with images
    db_session.refresh(image1)
    db_session.refresh(image2)

    procedure_id = response.json()['procedure_id']

    assert image1.procedure_id == procedure_id
    assert image2.procedure_id == procedure_id

def test_pdf_uses_procedure_images_not_transcript_images(client_db, db_session, auth_header, test_user):
    # create two transcripts
    
    transcript_id_1 = uuid.uuid4()
    transcript_id_2 = uuid.uuid4()
    transcript1 = TranscriptModel(transcript_id = transcript_id_1, user_id=test_user.id)
    db_session.add(transcript1)
    db_session.commit()

    transcript2 = TranscriptModel(transcript_id = transcript_id_2, user_id=test_user.id)
    db_session.add(transcript2)
    db_session.commit()

    db_session.refresh(transcript1)
    db_session.refresh(transcript2)

    #create fake images for each transcript and add images to each
    image1 = Images(
        transcript_id = transcript_id_1,
        image_path = "path/to/image1.png",
        captured_at = datetime(2025,1,1,10,0,0)

    )

    image2 = Images(
        transcript_id = transcript_id_2,
        image_path = "path/to/image2.png",
        captured_at = datetime(2025,1,1,10,0,1)
    )

    db_session.add_all([image1, image2])
    db_session.commit()

    
    #create procedure for transcript 1

    #create a colonoscopy report to write to the final endpoint
    colonoscopy_report = ColonoscopyReportFinal(
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0,0).isoformat(),
        procedure_end_time = datetime(2025,1,1,10,6,0).isoformat(),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        polyps = [],
        findings = []
    )

    metadata = ProcedureMetadataFinal(
        patient_NHI = "ABC1234",
        patient_name = "Santa Claus",
        procedure_date = date(2025,1,1).isoformat(),
        endoscopist_id = 1,
        patient_dob = date(1980,1,1).isoformat(),
        indication = 'unknown'
    )

    colonoscopy_report_with_metadata = ColonoscopyReportWithMetadataFinal(
        metadata = metadata,
        report = colonoscopy_report
    )

    #write the colonoscoyp report to the /write endpoint for transcript 1 which generates a procedure_id and links the images to the procedure_id
    response = client_db.post("/write", params = {'transcript_id': transcript_id_1}, json = colonoscopy_report_with_metadata.model_dump(mode = "json"), headers=auth_header)

    assert response.status_code == 200

    #verify PDF only includes images fromt transript 1 and not 2

    procedure_id = response.json()['procedure_id']

    assert image1.procedure_id == procedure_id
    assert image2.procedure_id is None #image2 should not be linked to a procedure_id since we haven't sent transcript with transcript_id = transcript_id_2 to the /write endpoint yet


def test_transcript_retrieval_with_images_sorted_by_timestamp(client_db, db_session, full_transcript, auth_header):

    

    image2 = Images(
        transcript_id = full_transcript.transcript_id,
        image_path = "path/to/image1.png",
        captured_at = datetime(2025,1,1,10,0,0) #timestamp is later

    )

    image1 = Images(
        transcript_id = full_transcript.transcript_id,
        image_path = "path/to/image2.png",
        captured_at = datetime(2025,1,1,10,1,0) #timestamp is earlier
    )

    db_session.add_all([image2, image1]) #adding but out of order by timestamp
    db_session.commit()

    response = client_db.get(f"/transcripts/{full_transcript.transcript_id}/report", headers=auth_header) #retrieving transcript with images

    assert response.status_code == 200

    data = response.json()

    assert len(data['images']) == 2

    #check that the retrieval put them in the proper order by time stamp ascending order
    assert data['images'][0]['image_path'] == "path/to/image1.png"
    assert data['images'][1]['image_path'] == "path/to/image2.png"


def test_get_transcript_with_no_images(client_db, db_session, full_transcript, auth_header):
    


    response = client_db.get(f"/transcripts/{full_transcript.transcript_id}/report", headers=auth_header)

    assert response.status_code == 200

    data = response.json()

    assert len(data['images']) == 0


def test_transcript_retrieval_only_gets_images_for_that_transcript(client_db, db_session, transcript_factory, auth_header):

    transcript1 = transcript_factory()
    transcript2 = transcript_factory()
    

    db_session.add_all([transcript1, transcript2])
    db_session.commit()

    image2 = Images(
        transcript_id = transcript2.transcript_id,
        image_path = "path/to/image2.png",
        captured_at = datetime(2025,1,1,10,0,0) #timestamp is later

    )

    image1 = Images(
        transcript_id = transcript1.transcript_id,
        image_path = "path/to/image1.png",
        captured_at = datetime(2025,1,1,10,1,0) #timestamp is earlier
    )

    db_session.add_all([image2, image1])

    db_session.commit()

    response = client_db.get(f"/transcripts/{transcript2.transcript_id}/report", headers=auth_header)

    assert response.status_code == 200

    images = response.json()['images']
    assert len(images) == 1 #should only be one image

    assert images[0]['image_path'] == "path/to/image2.png"


### need to test draft retrieval endpoint

def test_get_draft_transcript(client_db, db_session, auth_header, full_transcript):
    draft = full_transcript

    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)

    response = client_db.get(f"/transcripts/{draft.transcript_id}/draft", headers=auth_header)

    assert response.status_code == 200
    assert response.json()['status'] == TranscriptStatus.IN_PROGRESS.value

def test_try_to_get_draft_finalized_procedure(client_db, db_session, auth_header, test_user, procedure):
    draft = TranscriptModel(
        user_id = test_user.id,
        status = TranscriptStatus.IN_PROGRESS,
        procedure_id = procedure.procedure_id, #uses the test procedure with procedure_id already assigned, fits the FK relation between transcript and procedure
        polyps = [],
        findings = []
    )

    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)

    response = client_db.get(f"/transcripts/{draft.transcript_id}/draft", headers=auth_header)

    assert response.status_code == 400

def test_draft_not_found(client_db, auth_header):
    transcript_id = uuid.uuid4() #generate a random transcript id
    response = client_db.get(f"/transcripts/{transcript_id}/draft", headers=auth_header)
    assert response.status_code == 404 

def test_get_draft_for_wrong_user(client_db, auth_header, db_session): #actually tests that the user auth prevents one user from seeing transcripts for a different user
    other_user = UserModel(
        username = 'otheruser',
        email = 'otheruser@other.co',
        hashed_password = pwd_hasher.hash('otherpassword')
    )

    db_session.add(other_user)
    db_session.commit()

    transcript = TranscriptModel(
        user_id = other_user.id,
        status = TranscriptStatus.IN_PROGRESS,
        patient_id="ABC1234",
        patient_name="Bob Builder",
        procedure_date=datetime(2025, 1, 1),
        endoscopist_id=1,
        patient_dob=date(1980, 1, 1),
        indication="screening",
        cecum_reached=True,
        cecum_reached_time=datetime(2025, 1, 1, 10, 0),
        procedure_end_time=datetime(2025, 1, 1, 10, 6),
        bbps_right=3,
        bbps_transverse=3,
        bbps_left=3,
        polyps=[],
        findings=[]
    )

    db_session.add(transcript)
    db_session.commit()
    db_session.refresh(transcript)

    #the transcript belongs to "other_user".  now try to get it using the auth_header which has the token for test_user

    response = client_db.get(f"/transcripts/{transcript.transcript_id}/draft", headers=auth_header)

    assert response.status_code == 403

#need a test that also tests trying to get a transcript for the wrong user

def test_get_transcript_with_wrong_user(client_db, auth_header, db_session):
    other_user = UserModel(
        username = 'otheruser',
        email = 'otheruser@other.co',
        hashed_password = pwd_hasher.hash('otherpassword')
    )

    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    transcript = TranscriptModel(
        user_id = other_user.id,
        status = TranscriptStatus.IN_PROGRESS,
        patient_id="ABC1234",
        patient_name="Bob Builder",
        procedure_date=datetime(2025, 1, 1),
        endoscopist_id=1,
        patient_dob=date(1980, 1, 1),
        indication="screening",
        cecum_reached=True,
        cecum_reached_time=datetime(2025, 1, 1, 10, 0),
        procedure_end_time=datetime(2025, 1, 1, 10, 6),
        bbps_right=3,
        bbps_transverse=3,
        bbps_left=3,
        polyps=[],
        findings=[]
    )

    db_session.add(transcript)
    db_session.commit()
    db_session.refresh(transcript)

    response = client_db.get(f"/transcripts/{transcript.transcript_id}/report", headers=auth_header) #same test as above for different endpoint
    assert response.status_code == 403

# test the registration endpoint

def test_new_registration(client_db):
    response = client_db.post("/register", json={
        'username': 'testuser',
        'email': 'testuser@test.com',
        'password': 'testpassword'
    })

    assert response.status_code == 200
    
def test_duplicate_registration_username(client_db, test_user): 
    response = client_db.post("/register", json = {
        'username': 'testuser', #same as test_user
        'email': 'testusernumber2@test.com', #different from test user
        'password':'testpassword'
    })

    assert response.status_code == 409

def test_duplicate_registration_email(client_db, test_user):
    response = client_db.post("/register", json={
        'username': 'differentuser', #different from test_user
        'email': 'testuser@test.com', #same as test_user
        'password': 'testpassword'
    })

    assert response.status_code == 409

#test the login endpoint
def test_login_success(client_db, test_user):
    user_1 = {
        'username_or_email': test_user.username,
        'password': 'testpassword'
    }
    response = client_db.post("/login", json=user_1)

    assert response.status_code == 200

    data = response.json()

    assert 'access_token' in data
    assert data['token_type'] == 'bearer'

    #verify that the token is actually valid

    payload = jwt.decode(data['access_token'], SECRET_KEY, algorithms=ALGORITHM)

    assert payload['sub'] == str(test_user.id)
    assert "exp" in payload

def login_success_with_email(client_db, test_user):
    user_1 = {
        'username_or_email': test_user.email,
        'password': test_user.password
    }

    response = client_db.post("/login", json=user_1)
    assert response.status_code == 200

def test_missing_fields_in_login(client_db, test_user):
    # test for login without required fields.  
    # front end UI will have restrictions on submitting the login without the required fields
    #but we still need backend validation which is tested here
    user_1 = {
        'username_or_email': test_user.username
    }

    response = client_db.post("/login", json=user_1)

    assert response.status_code == 422

def test_login_wrong_password(client_db, test_user):
    user_1 = {
        'username_or_email': test_user.username,
        'password': 'wrong_password'
    }

    response = client_db.post("/login", json=user_1)
    assert response.status_code == 401

def test_nonexistent_user(client_db):
    user_1 = {
        'username_or_email': 'nonexistent_user@example.com',
        'password': 'notapassword'
    }

    response = client_db.post("/login", json=user_1)

    assert response.status_code == 401

#testing uuid as transcript_id

def test_transcript_id_is_uuid(client_db, auth_header):
    #see if using an invalid uuid returns validation error

    res = client_db.post("/transcribe/123", headers=auth_header)

    assert res.status_code == 422 #pydantic should reject the non uuid transcript_id

def test_nonexistent_transcript(client_db, auth_header): #similar to test for draft above.  uuid doesn't exist.  should get 404 file not found
    transcript_id = uuid.uuid4()

    res = client_db.get(f"/transcripts/{transcript_id}/report", headers=auth_header)

    assert res.status_code == 404

### end to end test for the transcript life cycle - 

@pytest.mark.integration
def test_transcript_lifecycle_end_to_end(client_db, auth_header, make_token, test_user):
    token = make_token(test_user.id)
    headers = {"Authorization":f"Bearer {token}"}

    start_result = client_db.post("/transcripts/start", headers=headers, json={
        "patient_name": "santa claus",
        "patient_dob": date(1900,1,1).isoformat(),
        "patient_nhi": "ABC1234"
    })

    assert start_result.status_code == 200

    transcript_id = start_result.json()['transcript_id']

    transcribe_result = client_db.post(f"/transcribe/{transcript_id}",
                                       headers=headers,
                                       files={'file':("transcript.txt", b"some transcript text", "text/plain")},
                                       data = {
                                           "cecum_reached_time" : datetime(2026, 1, 1, 10, 30).isoformat(),
                                           "procedure_end_time" : datetime(2026, 1, 1, 10, 36).isoformat()
                                       })
    assert transcribe_result.status_code == 200

    fetch_result = client_db.get(f"/transcripts/{transcript_id}/draft", headers=headers)
    assert fetch_result.status_code == 200

    draft = fetch_result.json()

    assert draft['patient_name'] == 'santa claus'

