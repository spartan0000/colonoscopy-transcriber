import pytest
from pydantic import ValidationError
from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportWithMetadata, ProcedureMetadata, Finding, Polyp
from datetime import date

#test the Polyp pydantic model
def test_polyp_minimal():
    polyp = Polyp(
        polyp_id = 1,
        location = 'cecum'
    )

    assert polyp.morphology == None

def test_polyp_full():
    polyp = Polyp(
        polyp_id = 1,
        size_mm = 5.0,
        location = 'ascending_colon',
        morphology = 'sessile',
        resection_method = 'snare',
        resection_complete = True,
        retrieved = True
    )

    assert polyp.size_mm == 5.0
    assert polyp.morphology == 'sessile'

def test_invalid_locatoin():
    with pytest.raises(ValidationError):
        polyp = Polyp(
            polyp_id = 1,
            location = 'weird_location'
        )

def test_invalid_morphology():
    with pytest.raises(ValidationError):
        polyp = Polyp(
            polyp_id = 1,
            location = 'cecum',
            morphology = 'weirdness'
        )

def test_invalid_resection_method():
    with pytest.raises(ValidationError):
        polyp = Polyp(
            polyp_id = 1,
            loation = 'cecum',
            resection_method = 'lasers'
        )

def test_missing_required_field():
    with pytest.raises(ValidationError):
        polyp = Polyp(
            size_mm = 9.0
        )


def test_negative_size():
    
    with pytest.raises(ValidationError):
        p = Polyp(
            polyp_id = 1,
            location = 'transverse_colon',
            size_mm = -3.0
        )

    
#test the Finding pydantic model

def test_finding_valid():
    finding = Finding(
        finding_id = 1,
        description = 'diverticula in the sigmoid colon',
        location = 'sigmoid_colon',
        biopsy_taken = False

    )
    assert finding.biopsy_taken == False


def test_finding_optional_fields():
    finding = Finding()

    assert finding.description == None
    assert finding.location == None

def test_finding_invalid_location():
    with pytest.raises(ValidationError):
        finding = Finding(
            finding_id = 1,
            location = 'face'
        )


#test the ColonoscopyReport pydantic model

def test_valid_empty_report():
    report = ColonoscopyReport(
        cecum_reached = True
    )

    assert report.polyps == []
    assert report.findings == []

def test_report_with_polyps_and_findings():
    r = ColonoscopyReport(
        cecum_reached = True,
        polyps = [
            {'polyp_id': 1,
             'size_mm' : 5.0,
             'location': 'sigmoid_colon',
             },
             
        ],
        findings = [
            {
                'finding_id': 1,
                'description': 'food',
                'location': 'descending_colon',
                'biopsy_taken': False
            }
        ]
    )
    assert len(r.polyps) == 1
    assert len(r.findings) == 1

def test_report_invalid_polyps():
    with pytest.raises(ValidationError):
        r = ColonoscopyReport(
            cecum_reached = True,
            polyps = [
                {
                    'polyp_id': 1,
                    'location': "someplace weird"
                }
            ]
        )
    
#test the metadata model

def test_metadata_valid():
    m = ProcedureMetadata(
        patient_name = "Santa Claus",
        patient_NHI = "ABC1234",
        procedure_date = date.today(),
        endoscopist_id = 1
    )

    assert m.patient_name == "Santa Claus"

def test_metadata_missing_required_field():
    with pytest.raises(ValidationError):
        m = ProcedureMetadata(
            patient_name = "Santa Claus"
        )


#test full report

def test_full_report_valid():
    data = {
        'metadata': {
            'patient_name': "Papa Smurf",
            'patient_NHI': "ABCD1234",
            'procedure_date': date.today(),
            'endoscopist_id': 1
        },
        'report': {
            'cecum_reached': True,
            'withdrawal_time': 500,
            'polyps': [
                {
                    'polyp_id': 1,
                    'size_mm': 5,
                    'location': 'transverse_colon'
                }
            ],
            'findings' : []
        }
    }

@pytest.mark.parametrize("value, expected", [
    ("true", True),
    ("false", False),
    ("True",True),
    ("False", False),
    ("yes", True),
    ("no", False), 
])
def test_boolean_coercion(value, expected):
    r = ColonoscopyReport(
        cecum_reached = value
    )

    assert r.cecum_reached == expected