from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Literal
from datetime import date   

class Polyp(BaseModel):
    polyp_id: Optional[int] = Field(default = None, description = "unique identifier for the polyp in order of appearance")
    size_mm: Optional[float] = Field(gt=0,default = None, description = "size of the polyp in millimeters")
    location: Literal["cecum", "ascending_colon", "hepatic_flexure", "transverse_colon", "splenic_flexure", "descending_colon", "sigmoid_colon", "rectum", "anus", "other"]
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
    cecum_reached: Optional[bool] = Field(description="whether the cecum was reached or not")
    @field_validator("cecum_reached", mode = "before")
    def validate_cecum_reached(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v = value.lower()
            if v in ["true", "yes", "1"]:
                return True
            elif v in ["false", "no", "0"]:
                return False
        raise ValueError("cecum_reached must be a boolean or a string representing a boolean value")


    cecum_reached_time: Optional[str] = Field(default = None, description="timestamp when the cecum was reached")
    procedure_end_time: Optional[str] = Field(default = None, description="timestamp when the procedure ended")
    withdrawal_time: Optional[float] = Field(default = None, description="calculated withdrawal time given cecum reached time and procedure end time")
    #need to add other findings such as diveritcula, hemorrhoids, inflammation.
    polyps: List[Polyp] = Field(default_factory = list)
    findings: List[Finding] = Field(default_factory = list)


class ProcedureMetadata(BaseModel):
    patient_name: str = Field(description = "name of patient")
    patient_NHI: str = Field(description = "NHI number of patient")
    procedure_date: date 
    endoscopist_id: int = Field(default = None, description = "endoscopist_id performing the procedure")

class ColonoscopyReportWithMetadata(BaseModel):
    metadata: ProcedureMetadata
    report: ColonoscopyReport

