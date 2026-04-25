import pytest
from pydantic import ValidationError
from app.models.colonoscopy import ColonoscopyReportFinal, ColonoscopyReportWithMetadataFinal, ProcedureMetadataFinal, FindingFinal, PolypFinal

import pathlib

from datetime import datetime, date, timedelta

from app.services.pdf_generator import generate_colonoscopy_report_pdf


def test_pdf_generator(tmp_path):
    raw = {
        'metadata': {
        'patient_name': 'bob thebuilder',
        'patient_NHI': 'ABC1234',
        'patient_dob': date(1940,1,1),
        'endoscopist_id': 1,
        'procedure_date': date(2025,1,1),
        'indication': 'lower gi bleed'
    },
    'report': {
        'cecum_reached': True,
        'cecum_reached_time': datetime.now(),
        'procedure_end_time': datetime.now() - timedelta(minutes=5),
        'withdrawal_time': 5,
        'bbps_right': 3,
        'bbps_transverse': 3,
        'bbps_left': 2,
        'polyps': [
            {'polyp_id': 1,
             'size_mm': 2.0,
             'location': 'cecum'} 
        ]
    }

        }
    
    out = ColonoscopyReportWithMetadataFinal(**raw)

    output_file = tmp_path / "test.pdf"

    buffer = generate_colonoscopy_report_pdf(out)

    with open(output_file, 'wb') as f:
        f.write(buffer.getvalue())

    assert output_file.exists()

     