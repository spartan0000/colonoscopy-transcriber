from fpdf import FPDF, XPos, YPos
from io import BytesIO
from datetime import date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from app.models.colonoscopy import PolypFinal, FindingFinal, ColonoscopyReportFinal, ProcedureMetadataFinal, ColonoscopyReportWithMetadataFinal
 
def _calculate_age(dob: date, procedure_date: date) -> str:
    """Calculate patient age from DOB and procedure date in YyMm format."""
    years = procedure_date.year - dob.year
    months = procedure_date.month - dob.month
    
    if months < 0:
        years -= 1
        months += 12
    
    return f"{years}y{months}m"
 
 
def generate_colonoscopy_report_pdf(data: ColonoscopyReportWithMetadataFinal) -> BytesIO:
    """
    Generate a colonoscopy report PDF from structured data.
    
    Args:
        data: ColonoscopyReportWithMetadataFinal object containing metadata and report
        
    Returns:
        BytesIO object containing the PDF bytes, positioned at start for reading
    """
    
    # Calculate patient age from DOB and procedure date
    patient_age = _calculate_age(data.metadata.patient_dob, data.metadata.procedure_date)
    
    pdf = FPDF()
    pdf.add_page()
    
    # Set up fonts
    pdf.set_font("Helvetica", size=11)
    line_height = 6
    section_spacing = 3
    
    # Header: Patient info
    _add_patient_header(pdf, data.metadata, patient_age, line_height, section_spacing)
    
    # Procedure section
    _add_procedure_section(pdf, data.report, line_height, section_spacing)
    
    # Findings section
    _add_findings_section(pdf, data.report, line_height, section_spacing)
    
    # Summary section
    _add_summary_section(pdf, data.report, line_height, section_spacing)
    
    # Convert to bytes
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    
    return pdf_output
 
 
def _add_patient_header(pdf: FPDF, metadata: ProcedureMetadataFinal, patient_age: str, line_height: float, section_spacing: float) -> None:
    """Add patient identifying information at top of report."""
    pdf.set_font("Helvetica", size=11)
    
    pdf.cell(0, line_height, f"Date: {metadata.procedure_date.strftime('%d/%m/%Y')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, line_height, f"Name: {metadata.patient_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, line_height, f"NHI: {metadata.patient_NHI}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, line_height, f"Age: {patient_age}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, line_height, f"Indications: {metadata.indication}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(section_spacing)
 
 
def _add_procedure_section(pdf: FPDF, report: ColonoscopyReportFinal, line_height: float, section_spacing: float) -> None:
    """Add procedure details including BBPS scores."""
    pdf.set_font("Helvetica", "B", size=11)
    pdf.cell(0, line_height, "Procedure:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("Helvetica", size=10)
    pdf.ln(section_spacing - 2)
    
    bbps_text = (
        f"After informed consent was obtained, the colonoscope was inserted through the anus and advanced to the cecum. "
        f"The quality of the bowel prep was evaluated using the BBPS (Boston Bowel Preparation Scale) with scores of "
        f"Right Colon = {report.bbps_right}, Transverse Colon = {report.bbps_transverse}, and "
        f"Left Colon = {report.bbps_left}. "
        f"The total BBPS score equals {report.bbps_right + report.bbps_transverse + report.bbps_left}."
    )
    
    _add_wrapped_text(pdf, bbps_text, line_height)
    
    pdf.ln(section_spacing)
 
 
def _add_findings_section(pdf: FPDF, report: ColonoscopyReportFinal, line_height: float, section_spacing: float) -> None:
    """Add findings section, including general findings and polyps."""
    pdf.set_font("Helvetica", "B", size=11)
    pdf.cell(0, line_height, "Findings:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(section_spacing - 2)
    
    # General findings (non-polyp)
    if report.findings:
        pdf.set_font("Helvetica", size=10)
        for finding in report.findings:
            finding_text = _format_finding(finding)
            _add_wrapped_text(pdf, finding_text, line_height)
            pdf.ln(section_spacing - 2)
    
    # Polyp findings
    if report.polyps:
        pdf.set_font("Helvetica", size=10)
        _add_polyp_findings(pdf, report.polyps, line_height, section_spacing)
    
    pdf.ln(section_spacing)
 
 
def _add_polyp_findings(pdf: FPDF, polyps: List[PolypFinal], line_height: float, section_spacing: float) -> None:
    """Format and add polyp findings grouped by location."""
    polyps_by_location = {}
    for polyp in polyps:
        if polyp.location not in polyps_by_location:
            polyps_by_location[polyp.location] = []
        polyps_by_location[polyp.location].append(polyp)
    
    for location, location_polyps in polyps_by_location.items():
        polyp_text = _format_polyp_group(location, location_polyps)
        _add_wrapped_text(pdf, polyp_text, line_height)
        pdf.ln(section_spacing - 2)
 
 
def _add_summary_section(pdf: FPDF, report: ColonoscopyReportFinal, line_height: float, section_spacing: float) -> None:
    """Add summary section at end of report."""
    pdf.set_font("Helvetica", "B", size=11)
    pdf.cell(0, line_height, "Summary:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(section_spacing - 2)
    
    pdf.set_font("Helvetica", size=10)
    
    if report.polyps:
        polyps_by_location = {}
        for polyp in report.polyps:
            if polyp.location not in polyps_by_location:
                polyps_by_location[polyp.location] = []
            polyps_by_location[polyp.location].append(polyp)
        
        for location, location_polyps in polyps_by_location.items():
            summary_text = _format_polyp_summary(location, location_polyps)
            _add_wrapped_text(pdf, f"- {summary_text}", line_height)
            pdf.ln(section_spacing - 2)
    else:
        pdf.cell(0, line_height, "- No polyps identified", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    if report.findings:
        for finding in report.findings:
            if finding.description:
                _add_wrapped_text(pdf, f"- {finding.description}", line_height)
                pdf.ln(section_spacing - 2)
 
 
def _format_finding(finding: FindingFinal) -> str:
    """Format a non-polyp finding as readable text."""
    parts = []
    
    if finding.description:
        parts.append(finding.description)
    
    if finding.location:
        location_formatted = finding.location.replace("_", " ").title()
        parts.append(f"Location: {location_formatted}")
    
    if finding.biopsy_taken is not None:
        biopsy_text = "Biopsy taken" if finding.biopsy_taken else "No biopsy"
        parts.append(biopsy_text)
    
    return ". ".join(parts) + "." if parts else ""
 
 
def _format_polyp_group(location: str, polyps: List[PolypFinal]) -> str:
    """Format a group of polyps at a single location for detailed findings."""
    location_formatted = location.replace("_", " ").title()
    
    if len(polyps) == 1:
        polyp = polyps[0]
        morphology = polyp.morphology if polyp.morphology else "not specified"
        resection = polyp.resection_method if polyp.resection_method else "not specified"
        complete = "complete" if polyp.resection_complete else "incomplete"
        
        return (
            f"A {polyp.size_mm}mm polyp was found in the {location_formatted}. "
            f"The polyp was {morphology}. "
            f"The polyp was removed with {resection}. "
            f"Resection and retrieval was {complete}."
        )
    else:
        sizes = sorted([p.size_mm for p in polyps])
        size_range = f"{min(sizes)}mm to {max(sizes)}mm"
        morphologies = set(p.morphology for p in polyps if p.morphology)
        morphology_str = ", ".join(morphologies) if morphologies else "not specified"
        resections = set(p.resection_method for p in polyps if p.resection_method)
        resection_str = ", ".join(resections) if resections else "not specified"
        all_complete = all(p.resection_complete for p in polyps if p.resection_complete is not None)
        complete = "complete" if all_complete else "incomplete"
        
        return (
            f"{len(polyps)} polyps ranging in size from {size_range} were found in the {location_formatted}. "
            f"The polyps were {morphology_str}. "
            f"The polyps were removed with {resection_str}. "
            f"Resection and retrieval were {complete}."
        )
 
 
def _format_polyp_summary(location: str, polyps: List[PolypFinal]) -> str:
    """Format a brief summary line for a polyp group."""
    location_formatted = location.replace("_", " ").title()
    
    if len(polyps) == 1:
        polyp = polyps[0]
        resection = polyp.resection_method if polyp.resection_method else "unknown method"
        complete_status = "Resection and retrieval complete" if polyp.resection_complete else "Incomplete resection/retrieval"
        
        return (
            f"One {polyp.size_mm}mm polyp was found in the {location_formatted}, "
            f"removed with {resection}. {complete_status}"
        )
    else:
        sizes = sorted([p.size_mm for p in polyps])
        size_range = f"{min(sizes)}mm to {max(sizes)}mm"
        resection = polyps[0].resection_method if polyps[0].resection_method else "unknown method"
        all_complete = all(p.resection_complete for p in polyps if p.resection_complete is not None)
        complete_status = "Resection and retrieval complete" if all_complete else "Incomplete resection/retrieval"
        
        return (
            f"{len(polyps)} polyps {size_range} in size were found in the {location_formatted}, "
            f"removed with {resection}. {complete_status}"
        )
 
 
def _add_wrapped_text(pdf: FPDF, text: str, line_height: float) -> None:
    """Add text with word wrapping."""
    pdf.multi_cell(0, line_height, text)