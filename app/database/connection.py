import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.database.models import Base
import os

from dotenv import load_dotenv

load_dotenv()


# print("DB_USER =", os.getenv("DB_USER"))
# print("DB_PASS =", os.getenv("DB_PASS"))
# print("DB_HOST =", os.getenv("DB_HOST"))
# print("DB_NAME =", os.getenv("DB_NAME"))

for var in ["DB_USER", "DB_PASS", "DB_HOST_TEST", "DB_HOST_PROD", "DB_NAME"]:
    if not os.getenv(var):
        raise ValueError(f"{var} is not set")

DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASS')}@"
    f"{os.getenv('DB_HOST_PROD')}:5432/"
    f"{os.getenv('DB_NAME')}"

)
TEST_DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASS')}@"
    f"{os.getenv('DB_HOST_TEST')}:5432/test_db"
    

)

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