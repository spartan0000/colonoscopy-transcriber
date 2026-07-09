from dotenv import load_dotenv
load_dotenv(".env.test")


import pytest
import os
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database.connection import get_db
from app.database.models import Base, ProcedureModel, PolypModel, FindingModel, TranscriptModel, Images, UserModel
from app.main import app

from app.database.seed_lookup_tables import seed_endoscopists, seed_polyp_locations

from unittest.mock import MagicMock
from datetime import datetime, date, timedelta

from fastapi.testclient import TestClient

from pwdlib import PasswordHash

pwd_hasher = PasswordHash.recommended()



TEST_DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASS')}@"
    f"{os.getenv('DB_HOST_TEST')}:5432/test_db"
    

)


test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def engine():
    
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)

    yield test_engine

    Base.metadata.drop_all(test_engine)
    


@pytest.fixture(scope="function")
def db_session():
    """create a new database session for testing then rollback at the end"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session #test runs here

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client_db(db_session):
    """override the get_db dependency to use the testing database session"""

    def override_get_db():
        yield db_session

    from app.database.connection import get_db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client_no_db():
    """client fixture that does not override the db dependency for tests that do not require db writes"""
    def fake_db():
        yield None
    app.dependency_overrides[get_db] = fake_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# @pytest.fixture(scope="session", autouse=True)
# def setup_test_db():
#     """create the test database schema before tests run, drop it after tests are done"""
#     Base.metadata.create_all(test_engine)
#     yield
#     Base.metadata.drop_all(test_engine)


#procedure transcript for tests
@pytest.fixture(scope = "function")
def procedure(db_session, test_user):
    proc = ProcedureModel(
        user_id = test_user.id,
        patient_id = "ABC1234",
        patient_name = "Santa Claus",
        procedure_date = datetime(2025,1,1),
        endoscopist_id = 1,
        patient_dob = datetime(1980,1,1),
        cecum_reached = True,
        cecum_reached_time = datetime(2025,1,1,10,0),
        procedure_end_time = datetime(2025,1,1,10,6),
        bbps_right = 3,
        bbps_transverse = 3,
        bbps_left = 3,
        polyps = [],
        findings = []
        
    )

    db_session.add(proc)
    db_session.commit()
    db_session.refresh(proc)

    return proc

#transcript fixture for tests - basically same as procedure
@pytest.fixture(scope = "function")
def full_transcript(db_session):
    transcript = TranscriptModel(
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
    return transcript

@pytest.fixture(scope = "function")
def transcript_factory(db_session):
    """factory fixture to create transcripts with different attributes for testign"""
    def _make_transcript(**kwargs):
        transcript = TranscriptModel(
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
            findings=[],
            **kwargs
        )
        db_session.add(transcript)
        db_session.commit()
        return transcript
    return _make_transcript


@pytest.fixture(scope = "function", autouse=True)
def seed_lookup(db_session):
    seed_polyp_locations(db_session)
    seed_endoscopists(db_session)

    db_session.commit()

#temporary image path for tests to store images and then roll back

@pytest.fixture(scope="function")
def temp_image(tmp_path):
    image_path = tmp_path / "test_image.png"
    image_path.write_bytes(b"fake_image_data")

    yield image_path

#fake frame for image capture tests
@pytest.fixture(scope="function")
def fake_frame():
    return np.zeros((480,640,3), dtype=np.uint8)

#fake image capture returns True and fake_frame simulating successful image capture
@pytest.fixture(scope="function")
def mock_cap(fake_frame):
    cap = MagicMock()
    cap.read.return_value = (True, fake_frame)
    return cap

#create test user for tests
@pytest.fixture(scope="session")
def test_user(db_session):
    user = UserModel(
        username = "testuser",
        email = "testuser@test.com",
        hashed_password = pwd_hasher.hash("testpassword")
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

#create auth header for tests
@pytest.fixture(scope="session")
def auth_header(client_db, test_user):
    response = client_db.post("/login", json = {
        'username_or_email': 'testuser',
        'password': 'testpassword'
    })

    token = response.json()['access_token']
    return {"Authorization": f"Bearer {token}"}