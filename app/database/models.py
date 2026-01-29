from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Procedure(Base):
    __tablename__ = 'procedures'

    procedure_id = Column(Integer, primary_key=True)
    patient_id = Column(String(50), nullable=False)
    procedure_date = Column(DateTime)
    cecum_reached = Column(Boolean)
    withdrawal_time = Column(Float)

    polyps = relationship("Polyp", back_populates="procedure")

class Polyp(Base):
    __tablename__ = 'polyps'

    polyp_id = Column(Integer, primary_key = True)
    procedure_id = Column(Integer, ForeignKey('procedures.procedure_id'))
    location = Column(String(100))
    size_mm = Column(Float)
    morphology = Column(String(100))
    resection_method = Column(String(100))
    resection_complete = Column(Boolean)
    retrieved = Column(Boolean)
    histology = Column(Text)

    procedure = relationship("Procedure", back_populates='polyps')

    