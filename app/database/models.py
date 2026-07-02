from sqlalchemy import func, Index, CheckConstraint, UniqueConstraint, Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Text, Enum, Computed
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

import enum
from typing import List, Optional
from datetime import datetime, date

class Base(DeclarativeBase):
    pass

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

class TranscriptStatus(enum.Enum):
    IN_PROGRESS = "in_progress"
    FINALIZED = "finalized"


# class PolypLocation(enum.Enum):
#     CECUM = "cecum"
#     ASCENDING_COLON = "ascending_colon"
#     HEPATIC_FLEXURE = "hepatic_flexure"
#     TRANSVERSE_COLON = "transverse_colon"
#     SPLENIC_FLEXURE = "splenic_flexure"
#     DESCENDING_COLON = "descending_colon"
#     SIGMOID_COLON = "sigmoid_colon"
#     RECTUM = "rectum"
#     ANUS = "anus"
#     OTHER = "other"

# class ResectionMethod(enum.Enum):
#     COLD_SNARE = "cold_snare"
#     HOT_SNARE = "hot_snare"
#     BIOPSY_FORCEPS = "biopsy_forceps"
#     LIFT_AND_RESECT = "lift_and_resect"
#     OTHER = "other"

# class Morphology(enum.Enum):
#     SESSILE = "sessile"
#     PEDUNCULATED = "pedunculated"
#     SEMI_PEDUNCULATED = "semi_pedunculated"
#     FLAT = "flat"
#     OTHER = "other"

###Lookup Tables

class PolypLocationLookup(Base):
    __tablename__ = "polyp_location_lookup"

    location_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    polyps: Mapped[List["PolypModel"]] = relationship("PolypModel", back_populates="location_ref") #this is a one to many relationship with the Polyp table
    findings: Mapped[List["FindingModel"]] = relationship("FindingModel", back_populates="location_ref") #one to many relationship with the Finding table (for non-polyp findings that still have a location)
   
class EndoscopistLookup(Base):
    __tablename__ = "endoscopist_lookup"

    endoscopist_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endoscopist_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    procedures: Mapped[List["ProcedureModel"]] = relationship("ProcedureModel", back_populates="endoscopist_ref") #this is a one to many relationship with the Procedure table

###Main Tables
class ProcedureModel(Base):
    __tablename__ = "procedures"
    __table_args__ = (
        UniqueConstraint("patient_id", "procedure_date", name="uq_patient_procedure_date"),
        CheckConstraint("bbps_right BETWEEN 0 AND 3 OR bbps_right IS NULL", name="check_bbps_right"),
        CheckConstraint("bbps_transverse BETWEEN 0 AND 3 OR bbps_transverse IS NULL", name="check_bbps_transverse"),
        CheckConstraint("bbps_left BETWEEN 0 AND 3 OR bbps_left IS NULL", name="check_bbps_left"),
        CheckConstraint("cecum_reached_time IS NULL OR procedure_end_time >= cecum_reached_time", name="check_time_order"),
        CheckConstraint(
            """
            (
                cecum_reached = false AND cecum_reached_time IS NULL
            )
            OR
            (
                cecum_reached = true AND cecum_reached_time IS NOT NULL
            )    
            """, 
            name = "check_cecum_consistency"
        ),
        Index("idx_proc_patient_date", "patient_id", "procedure_date")
        )
    

    procedure_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(50), nullable=False)
    patient_dob: Mapped[date] = mapped_column(DateTime, nullable = False)
    patient_name: Mapped[str] = mapped_column(String(100), nullable=False) 
    endoscopist_id: Mapped[int] = mapped_column(Integer, ForeignKey("endoscopist_lookup.endoscopist_id"), nullable=False)
    
    procedure_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    indication: Mapped[str] = mapped_column(String(100), nullable = True)
    cecum_reached: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cecum_reached_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    procedure_end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    withdrawal_time: Mapped[float] = mapped_column(Float, Computed(
        """
        CASE
            WHEN cecum_reached_time is NULL THEN NULL
            ELSE EXTRACT(EPOCH FROM (procedure_end_time - cecum_reached_time))/60
        END
        """
    ), nullable=True)

    # The bbps scores are nullable for now.  need to consider when the procedure isn't completed and what to do then.  
    # cannot make them nullable=False since an incomplete procedure won't have all three values
    bbps_right: Mapped[int] = mapped_column(Integer, nullable=True)
    bbps_transverse: Mapped[int] = mapped_column(Integer, nullable=True)
    bbps_left: Mapped[int] = mapped_column(Integer, nullable=True)
    bbps_total: Mapped[int] = mapped_column(Integer, Computed(
        """
        CASE
            WHEN bbps_right is NULL
            OR bbps_transverse is NULL
            or bbps_left is NULL
        THEN NULL
        ELSE bbps_right + bbps_transverse + bbps_left
        END    
        """
    ),
    nullable=True
    )

    entered_by: Mapped[str] = mapped_column(String(100), nullable=True)
    source_system: Mapped[str] = mapped_column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    polyps: Mapped[List["PolypModel"]] = relationship("PolypModel", back_populates="procedure", cascade="all, delete-orphan")
    #specimens: List["Specimen"] = relationship("Specimen", back_populates="procedure", cascade="all, delete-orphan")
    endoscopist_ref: Mapped["EndoscopistLookup"] = relationship("EndoscopistLookup", back_populates="procedures")
    findings: Mapped[List["FindingModel"]] = relationship("FindingModel", back_populates="procedure", cascade="all, delete-orphan")
    

class PolypModel(Base):
    __tablename__ = "polyps"
    __table_args__ = (
        CheckConstraint("size_mm >=0", name="chk_size_mm_non_negative"),
    )

    
    ###need to decide which of these are really nullable and which are not and make sure it matches the pydantic model.###


    polyp_id: Mapped[int] = mapped_column(Integer, primary_key = True)
    #specimen_id: Mapped[int] = mapped_column(Integer, ForeignKey("specimens.specimen_id"), nullable=True)
    procedure_id: Mapped[int] = mapped_column(Integer, ForeignKey('procedures.procedure_id', ondelete="CASCADE"), nullable=False)
    #location = Column(Enum(PolypLocation), nullable=False) #not needed due to line below which uses a look up table instead of enum
    location_code: Mapped[str] = mapped_column(String(50), ForeignKey("polyp_location_lookup.location_code"), nullable=False)
    size_mm: Mapped[float] = mapped_column(Float, nullable=False)
    morphology: Mapped[str] = mapped_column(String(50))
    resection_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resection_complete: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    retrieved: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    procedure: Mapped["ProcedureModel"] = relationship("ProcedureModel", back_populates="polyps")
    location_ref: Mapped["PolypLocationLookup"] = relationship("PolypLocationLookup", back_populates="polyps")
    #histology: Optional["Histology"] = relationship("Histology", back_populates="polyp", uselist=False, cascade="all, delete-orphan")


class FindingModel(Base):
    __tablename__ = 'finding'

    finding_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    procedure_id: Mapped[int] = mapped_column(Integer, ForeignKey('procedures.procedure_id', ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location_code: Mapped[str] = mapped_column(String(50), ForeignKey("polyp_location_lookup.location_code"), nullable=True)

    biopsy_taken: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    procedure: Mapped["ProcedureModel"] = relationship("ProcedureModel", back_populates="findings")
    location_ref: Mapped["PolypLocationLookup"] = relationship("PolypLocationLookup", back_populates="findings") #using the polyp location lookup table for both polyps and other findings (somewhat confusing though)


#need table to manage state so that we can track progress of an unfinished report so that user can retrieve and finish it later
#this TranscriptModel is a temporary holding table for the report data before it is finalized and written to Procedures, Polyps, Findings.
class TranscriptModel(Base):
    __tablename__ = "transcripts"

    transcript_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    procedure_id: Mapped[int] = mapped_column(Integer, ForeignKey("procedures.procedure_id", ondelete="CASCADE"), nullable=True) #nullable true since we want to allow creation of a transcript before we have all the procedure details, we can update the transcript later with the procedure_id once we have it.
    patient_id: Mapped[str] = mapped_column(String(50), nullable=False)
    patient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    endoscopist_id: Mapped[int] = mapped_column(Integer, nullable=False)
    patient_dob: Mapped[date] = mapped_column(DateTime, nullable=False)
    procedure_date: Mapped[datetime] = mapped_column(DateTime())
    indication: Mapped[str] = mapped_column(String(100), nullable = True)
    cecum_reached: Mapped[bool] = mapped_column(Boolean, nullable=False)
    #changed the times to nullable = True, can enforce that they exist at the "finalize" application layer and not here in the database
    cecum_reached_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    procedure_end_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    #withdrawal time is a computed colun in the procedures table so we store the cecum reached time and procedure end time here
    bbps_right: Mapped[int] = mapped_column(Integer, nullable=True)
    bbps_transverse: Mapped[int] = mapped_column(Integer, nullable=True)
    bbps_left: Mapped[int] = mapped_column(Integer, nullable=True)
    #bbps total is a computed column in the procedures table so we store the individual segment scores here for now, total computed when report finalized
    polyps: Mapped[List] = mapped_column(JSONB, nullable=False)
    findings: Mapped[List] = mapped_column(JSONB, nullable=False)
    status: Mapped[TranscriptStatus] = mapped_column(Enum(TranscriptStatus), default=TranscriptStatus.IN_PROGRESS, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

class Images(Base):
    __tablename__ = 'images'

    image_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transcript_id: Mapped[int] = mapped_column(Integer, ForeignKey("transcripts.transcript_id", ondelete = "CASCADE"), nullable=False)
    image_path: Mapped[str] = mapped_column(String(200), nullable = False)
    anatomic_location: Mapped[str] = mapped_column(String(200))
    #this is whether the image was auto labelled or manually labelled for use later on
    label_source: Mapped[str] = mapped_column(String(100))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default = func.now(), nullable=False)

    
    
# class Histology(Base):
#     __tablename__ = 'histology'

#     histology_id = Column(Integer, primary_key = True)
#     polyp_id = Column(Integer, ForeignKey("polyps.polyp_id", ondelete="CASCADE"), nullable=False, unique=True)
#     specimen_id = Column(Integer, ForeignKey("specimen.specimen_id", ondelete="CASCADE"), unique=True)
#     histology = Column(Enum(PathologyType))
#     dysplasia = Column(Enum(DysplasiaGrade))

#     entered_by = Column(String(100), nullable=False)
#     source_system = Column(String(100), nullable=False)

#     created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

#     polyp: "Polyp" = relationship("Polyp", back_populates="histology")
#     specimen: "Specimen" = relationship("Specimen", back_populates="histology")


# class Specimen(Base):
#     __tablename__ = "specimen"
    
#     specimen_id = Column(Integer, primary_key=True)
#     procedure_id = Column(Integer, ForeignKey("procedures.procedure_id", ondelete="CASCADE"), nullable=False)
#     label = Column(String(50), nullable=False)

#     histology: "Histology" = relationship("Histology", back_populates="specimen", cascade="all, delete-orphan", uselist=False)
#     procedure: "Procedure" = relationship("Procedure", back_populates="specimens")