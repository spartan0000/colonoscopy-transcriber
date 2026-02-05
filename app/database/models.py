from sqlalchemy import func, Index, CheckConstraint, UniqueConstraint, Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum


Base = declarative_base()

###Enums
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

class Morphology(enum.Enum):
    SESSILE = "sessile"
    PEDUNCULATED = "pedunculated"
    SEMI_PEDUNCULATED = "semi_pedunculated"
    FLAT = "flat"
    OTHER = "other"

###Lookup Tables

class PolypLocationLookup(Base):
    __tablename__ = "polyp_location_lookup"

    location_code = Column(String(50), primary_key=True)
    display_name = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    polyps = relationship("Polyp", back_populates="location_ref")

   
class EndoscopistLookup(Base):
    __tablename__ = "endoscopist_lookup"

    endoscopist_id = Column(Integer, primary_key=True)
    endoscopist_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    procedures = relationship("Procedure", back_populates="endoscopist_ref")


###Main Tables
class Procedure(Base):
    __tablename__ = "procedures"
    __table_args__ = (
        UniqueConstraint("patient_id", "procedure_date", name="uq_patient_procedure_date"),
        Index("idx_proc_patient_date", "patient_id", "procedure_date")
        )
    

    procedure_id = Column(Integer, primary_key=True)
    patient_id = Column(String(50), nullable=False)
    endoscopist_id = Column(Integer, ForeignKey("endoscopist_lookup.endoscopist_id"), nullable=False)
    
    procedure_date = Column(DateTime(timezone=True), nullable=False)
    cecum_reached = Column(Boolean, nullable=False)
    withdrawal_time = Column(Float, CheckConstraint("withdrawal_time >=0"), nullable = False)

    entered_by = Column(String(100), nullable=False)
    source_system = Column(String(100), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    polyps = relationship("Polyp", back_populates="procedure", cascade="all, delete-orphan")
    specimens = relationship("Specimen", back_populates="procedure", cascade="all, delete-orphan")
    endoscopist = relationship("EndoscopistLookup", back_populates="procedures")



class Polyp(Base):
    __tablename__ = "polyps"
    __table_args__ = (
        CheckConstraint("size_mm >=0", name="chk_size_mm_non_negative"),
    )

    polyp_id = Column(Integer, primary_key = True)
    specimen_id = Column(Integer, ForeignKey("specimens.specimen_id"), nullable=True)
    procedure_id = Column(Integer, ForeignKey('procedures.procedure_id', ondelete="CASCADE"), nullable=False)
    #location = Column(Enum(PolypLocation), nullable=False)
    location_code = Column(String, ForeignKey("polyp_location_lookup.location_code"), nullable=False)
    size_mm = Column(Float, nullable=False)
    morphology = Column(Enum(Morphology))
    resection_method = Column(Enum(ResectionMethod), nullable=False)
    resection_complete = Column(Boolean)
    retrieved = Column(Boolean)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    procedure = relationship("Procedure", back_populates="polyps")
    location_ref = relationship("PolypLocationLookup", back_populates="polyps")
    histology = relationship("Histology", back_populates="polyp", uselist=False, cascade="all, delete-orphan")




class Histology(Base):
    __tablename__ = 'histology'

    histology_id = Column(Integer, primary_key = True)
    polyp_id = Column(Integer, ForeignKey("polyps.polyp_id", ondelete="CASCADE"), nullable=False, unique=True)
    specimen_id = Column(Integer, ForeignKey("specimen.specimen_id", ondelete="CASCADE"), unique=True)
    histology = Column(Enum(PathologyType))
    dysplasia = Column(Enum(DysplasiaGrade))

    entered_by = Column(String(100), nullable=False)
    source_system = Column(String(100), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    polyp = relationship("Polyp", back_populates="histology")
    specimen = relationship("Specimen", back_populates="histology")


class Specimen(Base):
    __tablename__ = "specimen"
    
    specimen_id = Column(Integer, primary_key=True)
    procedure_id = Column(Integer, ForeignKey("procedures.procedure_id", ondelete="CASCADE"), nullable=False)
    label = Column(String(50), nullable=False)

    histology = relationship("Histology", back_populates="specimen", cascade="all, delete-orphan", uselist=False)
    procedure = relationship("Procedure", back_populates="specimens")