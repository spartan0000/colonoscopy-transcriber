from sqlalchemy import func, Index, CheckConstraint, UniqueConstraint, Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum


Base = declarative_base()


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

class PolypLocation(enum.Enum):
    CECUM = "cecum"
    ASCENDING_COLON = "ascending_colon"
    HEPATIC_FLEXURE = "hepatic_flexure"
    TRANSVERSE_COLON = "transverse_colon"
    SPLENIC_FLEXURE = "splenic_flexure"
    DESCENDING_COLON = "descending_colon"
    SIGMOID_COLON = "sigmoid_colon"
    RECTUM = "rectum"
    ANUS = "anus"
    OTHER = "other"

class ResectionMethod(enum.Enum):
    COLD_SNARE = "cold_snare"
    HOT_SNARE = "hot_snare"
    BIOPSY_FORCEPS = "biopsy_forceps"
    LIFT_AND_RESECT = "lift_and_resect"
    OTHER = "other"


class Procedure(Base):
    __tablename__ = "procedures"
    __table_args__ = (
        UniqueConstraint("patient_id", "procedure_date", name="uq_patient_procedure_date"),
        Index("idx_patient_id", "patient_id", "procedure_date")
        )
    

    procedure_id = Column(Integer, primary_key=True)
    patient_id = Column(String(50), nullable=False)
    procedure_date = Column(DateTime(timezone=True), nullable=False)
    cecum_reached = Column(Boolean, nullable=False)
    withdrawal_time = Column(Float, CheckConstraint("withdrawal_time >=0"), nullable = False)

    entered_by = Column(String(100), nullable=False)
    source_system = Column(String(100), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    polyps = relationship("Polyp", back_populates="procedure", cascade="all, delete-orphan")



class Polyp(Base):
    __tablename__ = "polyps"
    __table_args__ = (
        CheckConstraint("size_mm >=0", name="chk_size_mm_non_negative"),
    )

    polyp_id = Column(Integer, primary_key = True)
    procedure_id = Column(Integer, ForeignKey('procedures.procedure_id', ondelete="CASCADE"), nullable=False)
    location = Column(String(100))
    size_mm = Column(Float, nullable=False)
    morphology = Column(String(100))
    resection_method = Column(Enum(ResectionMethod), nullable=False)
    resection_complete = Column(Boolean)
    retrieved = Column(Boolean)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    procedure = relationship("Procedure", back_populates="polyps")
    histology = relationship("Histology", back_populates="polyp", uselist=False, cascade="all, delete-orphan")



class Histology(Base):
    __tablename__ = 'histology'

    histology_id = Column(Integer, primary_key = True)
    polyp_id = Column(Integer, ForeignKey('polyps.polyp_id', ondelete="CASCADE"), nullable=False, unique=True)
    histology = Column(Enum(PathologyType))
    dysplasia = Column(Enum(DysplasiaGrade))

    polyp = relationship("Polyp", back_populates="histology")

