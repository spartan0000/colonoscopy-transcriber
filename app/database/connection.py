import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database.models import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)

def init_db():

    Base.metadata.create_all(engine)



if __name__ == "__main__":
    init_db()