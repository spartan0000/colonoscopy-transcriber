from pydantic import BaseModel, Field
from typing import Optional, List

class Polyp(BaseModel):
    polyp_id: str = Field(description = "unique identifier for the polyp in order of appearance")
    size_mm: Optional[float] = Field(description = "size of the polyp in millimeters")
    location: Optional[str] = Field(description = "location of the polyp in the colon")
    morphology: Optional[str] = Field(description = "morphological classification of the polyp(sessile, pedunculated, flat, etc.)")
    resection_method: Optional[str] = Field(description = "method used to resect the polyp")
    resection_complete: Optional[bool] = Field(description = "whether the polyp resection was complete")
    retrieved: Optional[bool] = Field(description = "whether the polyp was retrieved")

class ColonoscopyReport(BaseModel):
    cecum_reached: Optional[bool] = Field(description="whether the cecum was reached or not")

    cecum_reached_time: Optional[str] = Field(description="timestamp when the cecum was reached")
    procedure_end_time: Optional[str] = Field(description="timestamp when the procedure ended")
    withdrawal_time: Optional[float] = Field(description="calculated withdrawal time given cecum reached time and procedure end time")
    #need to add other findings such as diveritcula, hemorrhoids, inflammation.
    polyps: List[Polyp]