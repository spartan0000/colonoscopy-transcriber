from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Literal
from datetime import date, datetime  

#draft versions for data returned from transcription endpoint for user validation - intermediate state before final version persisted to database

class Polyp(BaseModel):
    polyp_id: Optional[int] = Field(default = None, description = "unique identifier for the polyp in order of appearance")
    size_mm: Optional[float] = Field(ge=0, default = None, description = "size of the polyp in millimeters")
    location: Literal["cecum", "ascending_colon", "hepatic_flexure", "transverse_colon", "splenic_flexure", "descending_colon", "sigmoid_colon", "rectum", "anus", "other"] = Field(default=None)
    morphology: Literal["sessile", "pedunculated", "semi_pedunculated", "flat", "other"] = Field(default = None, description = "morphological classification of the polyp(sessile, pedunculated, flat, etc.)")
    resection_method: Literal["snare", "cold_snare", "hot_snare", "biopsy_forceps", "lift_and_resect", "other"] = Field(default = None, description = "method used to resect the polyp")
    resection_complete: Optional[bool] = Field(default = None, description = "whether the polyp resection was complete")
    retrieved: Optional[bool] = Field(default = None, description = "whether the polyp was retrieved")

class Finding(BaseModel):
    finding_id: Optional[int] = Field(default = None, description = "unique identifier for the finding in order of appearance")
    description: Optional[str] = Field(default = None, description = "description of the finding")
    location: Optional[Literal["cecum", "ascending_colon", "hepatic_flexure", "transverse_colon", "splenic_flexure", "descending_colon", "sigmoid_colon", "rectum", "anus", "other"]] = Field(default = None, description = "location of the finding if applicable")
    biopsy_taken: Optional[bool] = Field(default = None, description = "whether a biopsy was taken for this finding")

class ColonoscopyReport(BaseModel):
    
    cecum_reached: Optional[bool] = Field(default=None, description="whether the cecum was reached or not")
    @field_validator("cecum_reached", mode = "before")
    def validate_cecum_reached(cls, value):
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str): 
            v = value.lower()
            if v in ["true", "yes", "1"]:
                return True
            elif v in ["false", "no", "0"]:
                return False
        return None


    cecum_reached_time: Optional[datetime] = Field(default = None, description="timestamp when the cecum was reached")
    procedure_end_time: Optional[datetime] = Field(default = None, description="timestamp when the procedure ended")
    withdrawal_time: Optional[float] = Field(default = None, description="calculated withdrawal time given cecum reached time and procedure end time")
    bbps_right: Optional[int] = Field(default = None, ge=0, le=3, description="boston bowel prep score for the right colon")
    bbps_transverse: Optional[int] = Field(default = None, ge=0, le=3, description="boston bowel prep score for the transverse colon")
    bbps_left: Optional[int] = Field(default = None, ge=0, le=3, description="boston bowel prep score for the left colon")
    
    #need to add other findings such as diveritcula, hemorrhoids, inflammation.
    polyps: List[Polyp] = Field(default_factory = list)
    findings: List[Finding] = Field(default_factory = list)


class ProcedureMetadata(BaseModel):
    patient_name: Optional[str] = Field(default = None, description = "name of patient")
    patient_NHI: Optional[str] = Field(default = None, description = "NHI number of patient")
    procedure_date: Optional[date] = Field(default = None, description="date of procedure") 
    endoscopist_id: Optional[int] = Field(default = None, description = "endoscopist_id performing the procedure")



#need second set of validation models that are more strict for the final submission endpoint
#need to decide which of these fields are actually required.  too strict, app can crash.  not strict enough, app allows useless information.

class PolypFinal(BaseModel):
    polyp_id: int = Field(..., description = "unique identifier for the polyp in order of appearance")
    size_mm: float = Field(..., ge=0, description = "size of the polyp in millimeters")
    location: Literal["cecum", "ascending_colon", "hepatic_flexure", "transverse_colon", "splenic_flexure", "descending_colon", "sigmoid_colon", "rectum", "anus", "other"]
    morphology: Literal["sessile", "pedunculated", "semi_pedunculated", "flat", "other"] = Field(default = None, description = "morphological classification of the polyp(sessile, pedunculated, flat, etc.)")
    resection_method: Literal["snare", "cold_snare", "hot_snare", "biopsy_forceps", "lift_and_resect", "other"] = Field(default = None, description = "method used to resect the polyp")
    resection_complete: Optional[bool] = Field(default = None, description = "whether the polyp resection was complete")
    retrieved: Optional[bool] = Field(default = None, description = "whether the polyp was retrieved")

class FindingFinal(BaseModel):
    finding_id: int = Field(..., description = "unique identifier for the finding in order of appearance")
    description: Optional[str] = Field(default = None, description = "description of the finding")
    location: Optional[Literal["cecum", "ascending_colon", "hepatic_flexure", "transverse_colon", "splenic_flexure", "descending_colon", "sigmoid_colon", "rectum", "anus", "other"]] = Field(default = None, description = "location of the finding if applicable")
    biopsy_taken: Optional[bool] = Field(default = None, description = "whether a biopsy was taken for this finding")

class ColonoscopyReportFinal(BaseModel):
    cecum_reached: bool = Field(..., description="whether the cecum was reached or not")
    @field_validator("cecum_reached", mode = "before")
    def validate_cecum_reached(cls, value):
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str): 
            v = value.lower()
            if v in ["true", "yes", "1"]:
                return True
            elif v in ["false", "no", "0"]:
                return False
        return None


    cecum_reached_time: datetime = Field(..., description="timestamp when the cecum was reached")
    procedure_end_time: datetime = Field(..., description="timestamp when the procedure ended")
    withdrawal_time: float = Field(..., description="calculated withdrawal time given cecum reached time and procedure end time")
    bbps_right: int = Field(..., ge=0, le=3, description="boston bowel prep score for the right colon")
    bbps_transverse: int = Field(..., ge=0, le=3, description="boston bowel prep score for the transverse colon")
    bbps_left: int = Field(..., ge=0, le=3, description="boston bowel prep score for the left colon")
    
    #need to add other findings such as diveritcula, hemorrhoids, inflammation.
    polyps: List[PolypFinal] = Field(default_factory = list)
    findings: List[FindingFinal] = Field(default_factory = list) 

class ProcedureMetadataFinal(BaseModel):
    patient_name: str = Field(..., description = "name of patient")
    patient_NHI: str = Field(..., description = "NHI number of patient")
    patient_dob: date
    procedure_date: date 
    indication: str = Field(..., description="text input for the indication for the procedure") #this could eventually be a very long list or enum of indications
    endoscopist_id: int = Field(..., description = "endoscopist_id performing the procedure")

class ColonoscopyReportWithMetadata(BaseModel):
    
    metadata: ProcedureMetadata
    report: ColonoscopyReport

class ColonoscopyReportWithMetadataFinal(BaseModel):

    metadata: ProcedureMetadataFinal
    report: ColonoscopyReportFinal

 