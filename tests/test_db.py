import pytest 

from datetime import datetime

from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportWithMetadata, ProcedureMetadata
from app.database.models import ProcedureModel, PolypModel, FindingModel, EndoscopistLookup, PolypLocationLookup

from app.services import functions

from sqlalchemy.exc import IntegrityError



def test_end_to_end(db_session):
    #mock LLM outputs
    today = datetime.today()
    mock_transcription = {
        'transcription_result': {
            'entire_text': 'fake transcription text',
            'segments': []
        },
        
    }

    mock_extracted_data = ColonoscopyReport(
        cecum_reached = True,
        withdrawal_time = 500,
        polyps = [
            {
                'polyp_id': 1,
                'size_mm': 5,
                'location': 'sigmoid_colon',
                'morphology': 'sessile',
                'resection_method': 'snare',
                'resection_complete': True,
                'retrieved': True
            },
            {
                'polyp_id': 2,
                'size_mm': 10,
                'location': 'transverse_colon',
                'morphology': 'pedunculated',
                'resection_method': 'biopsy_forceps',
                'resection_complete': False,
                'retrieved': False
            }

        ],

    )

    metadata = ProcedureMetadata(
        patient_name = "Papa Smurf",
        patient_NHI = "ABCD1234",
        procedure_date = today.date(),
        endoscopist_id = 1

    )

    full_report = ColonoscopyReportWithMetadata(
        metadata = metadata,
        report = mock_extracted_data
    )

    #write to db

    functions.write_transcription_record(db_session, full_report)

    procedure = db_session.query(ProcedureModel).filter_by(patient_id = "ABCD1234").first()

    assert procedure is not None
    assert procedure.patient_name == "Papa Smurf"
    assert procedure.endoscopist_id == 1
    assert procedure.cecum_reached == True
    assert procedure.polyps[0].size_mm == 5
    assert procedure.polyps[0].location_code == "sigmoid_colon"

def test_polyp_size_constraint(db_session, procedure):
    
    polyp = PolypModel(
        procedure = procedure,
        location_code = "sigmoid_colon",
        size_mm = -5,
        morphology = "sessile"

    )

    db_session.add(polyp)

    with pytest.raises(IntegrityError):
        db_session.commit()

def test_missing_morphology(db_session, procedure):
    polyp = PolypModel(
        procedure = procedure,
        location_code = "cecum",
        size_mm = 2.0,
        morphology = None
    )
    db_session.add(polyp)

    with pytest.raises(IntegrityError):
        db_session.commit()