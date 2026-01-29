import sqlalchemy
from sqlalchemy import create_engine
from database.models import Base

DATABASE_URL = "postgresql://colonoscopy_user:colonoscopy_password@localhost:5432/colonoscopy_db"

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

