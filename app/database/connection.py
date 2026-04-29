import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.database.models import Base
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("PSQL_DATABASE_URL")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

engine = create_engine(DATABASE_URL)
test_engine = create_engine(TEST_DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)
TestSessionLocal = sessionmaker(bind=test_engine)

def init_db():

    Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()