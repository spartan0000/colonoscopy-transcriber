import pytest
import os


from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database.connection import get_db
from app.database.models import Base, ProcedureModel, PolypModel, FindingModel
from app.main import app

from app.database.seed_lookup_tables import seed_endoscopists, seed_polyp_locations

from dotenv import load_dotenv

from datetime import datetime

from fastapi.testclient import TestClient

load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=test_engine)



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

    

    from app.database.connection import get_db
    app.dependency_overrides[get_db] = lambda: db_session
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

@pytest.fixture(scope = "function")
def procedure(db_session):
    proc = ProcedureModel(
        patient_id = "ABC1234",
        patient_name = "Santa Claus",
        procedure_date = datetime(2025,1,1),
        endoscopist_id = 1,
        cecum_reached = True,
        withdrawal_time = 100
    )

    db_session.add(proc)
    db_session.commit()

    return proc

@pytest.fixture(scope = "function")
def seed_lookup(db_session):
    seed_polyp_locations(db_session)
    seed_endoscopists(db_session)

    db_session.commit()