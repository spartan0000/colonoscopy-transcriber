from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum


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
    

    procedure = relationship("Procedure", back_populates="polyps")
    histology = relationship("Histology", back_populates="polyp", uselist=False)

class PathologyType(enum.Enum):
    TUBULAR_ADENOMA = "tubular_adenoma"
    VILLOUS_ADENOMA = "villous_adenoma"
    TUBULOVILLOUS_ADENOMA = "tubulovillous_adenoma"
    SESSILE_SERRATED_ADENOMA = "sessile_serrated_adenoma"
    HYPERPLASTIC_POLYP = "hyperplastic_polyp"
    NORMAL_MUCOSA = "normal_mucosa"
    OTHER = "other"

class DysplasiaGrade(enum.Enum):
    LOW_GRADE = "low_grade"
    HIGH_GRADE = "high_grade"
    NONE = "none"

class Histology(Base):
    __tablename__ = 'histology'

    histology_id = Column(Integer, primary_key = True)
    polyp_id = Column(Integer, ForeignKey('polyps.polyp_id'))
    histology = Column(Enum(PathologyType))
    dysplasia = Column(Enum(DysplasiaGrade))

    polyp = relationship("Polyp", back_populates="histology")

