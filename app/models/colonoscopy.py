from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import date

class Polyp(BaseModel):
    polyp_id: str = Field(description = "unique identifier for the polyp in order of appearance")
    size_mm: Optional[float] = Field(description = "size of the polyp in millimeters")
    location: Literal["cecum", "ascending_colon", "hepatic_flexure", "transverse_colon", "splenic_flexure", "descending_colon", "sigmoid_colon", "rectum", "anus", "other"]
    morphology: Optional[str] = Field(description = "morphological classification of the polyp(sessile, pedunculated, flat, etc.)")
    resection_method: Optional[str] = Field(description = "method used to resect the polyp")
    resection_complete: Optional[bool] = Field(description = "whether the polyp resection was complete")
    retrieved: Optional[bool] = Field(description = "whether the polyp was retrieved")

class Finding(BaseModel):
    finding_id: str = Field(description = "unique identifier for the finding in order of appearance")
    description: str = Field(description = "description of the finding")
    location: Optional[Literal["cecum", "ascending_colon", "hepatic_flexure", "transverse_colon", "splenic_flexure", "descending_colon", "sigmoid_colon", "rectum", "anus", "other"]] = Field(description = "location of the finding if applicable")
    biopsy_taken: Optional[bool] = Field(description = "whether a biopsy was taken for this finding")



class ColonoscopyReport(BaseModel):
    cecum_reached: Optional[bool] = Field(description="whether the cecum was reached or not")

    cecum_reached_time: Optional[str] = Field(description="timestamp when the cecum was reached")
    procedure_end_time: Optional[str] = Field(description="timestamp when the procedure ended")
    withdrawal_time: Optional[float] = Field(description="calculated withdrawal time given cecum reached time and procedure end time")
    #need to add other findings such as diveritcula, hemorrhoids, inflammation.
    polyps: List[Polyp]
    findings: List[Finding]


class ProcedureMetadata(BaseModel):
    patient_name: str = Field(description = "name of patient")
    patient_NHI: str = Field(description = "NHI number of patient")
    procedure_date: date 
    endoscopist: str = Field(description = "endoscopist performing the procedure")

class ColonoscopyReportWithMetadata(BaseModel):
    metadata: ProcedureMetadata
    report: ColonoscopyReport

