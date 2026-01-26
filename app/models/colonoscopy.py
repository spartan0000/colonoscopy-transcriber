from pydantic import BaseModel
from typing import Optional, List

class Polyp(BaseModel):
    polyp_id: int
    size_mm: Optional[float]
    location: Optional[str]
    morphology: Optional[str]
    resection_method: Optional[str]
    resection_complete: Optional[bool]
    retrieved: Optional[bool]

class ColonoscopyReport(BaseModel):
    polyps: List[Polyp]