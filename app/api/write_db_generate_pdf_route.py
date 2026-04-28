from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.database.connection import get_db

from app.services import functions, pdf_generator

from app.models.colonoscopy import ColonoscopyReportFinal, ColonoscopyReportWithMetadataFinal

from sqlalchemy.orm import Session

from pathlib import Path

#logo_path = Path(__file__).parent / "data" / "HNZ_logo.jpg"

from app.logger import logger

from app.config import OUTPUT_DIR, API_BASE

router = APIRouter(tags=['write_db_pdf'])

@router.post("/write")
def write_db_pdf(full_report: ColonoscopyReportWithMetadataFinal, db: Session = Depends(get_db)):

    logger.info(f"Logging to DB: {full_report.model_dump()}")
    #write to the database here once the data returns from the user
    try:
        procedure = functions.write_transcription_record(db=db, full_report = full_report)

        print("LOGGING TO DB COMPLETE")
        print(f"PROCEDURE_ID: {procedure.procedure_id}")

        logger.info(f"Logging to db complete")
        logger.info(f"Procedure ID: {procedure.procedure_id}")
        
    except Exception as e:
        print("DB WRITE FAILED", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to write to database"
        )
    
        logger.error("DB write failed", exc_info=True)
   


    try:
        pdf_bytes = pdf_generator.generate_colonoscopy_report_pdf(full_report)

        filename = f"colonoscopy_report_{full_report.metadata.patient_NHI}.pdf"
        filepath = OUTPUT_DIR/filename

        with open(filepath, 'wb') as f:
            f.write(pdf_bytes.getvalue())


        print(f'Writing PDF to : {filepath}')
        print(f'File exists after write: {filepath.exists()}')

        logger.info(f"PDF generated, written to: {filepath}")
        
        pdf_result = {
            'pdf_url': f'/files/{filename}'
        }

        # return StreamingResponse(
        #     pdf_bytes,
        #     media_type="application/pdf",
        #     headers={"Content-Disposition":f"attachment; filename=colonoscopy_report_{full_report.metadata.patient_NHI}.pdf"}

        # )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
        pdf_result = {
            'pdf_url': None
        }
        logger.error("Failed to generate PDF", exc_info=True)
    
    return {
        'procedure_id': procedure.procedure_id,
        'pdf_url': pdf_result['pdf_url']
    }