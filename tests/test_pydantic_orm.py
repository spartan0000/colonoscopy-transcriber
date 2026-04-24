import pytest
from pydantic import ValidationError
from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportWithMetadata, ProcedureMetadata, Finding, Polyp, ColonoscopyReportFinal, ColonoscopyReportWithMetadataFinal, ProcedureMetadataFinal
from app.database.models import ProcedureModel, PolypModel, FindingModel
from app.services.functions import map_polyp, map_findings, map_procedure
from datetime import date, datetime

from sqlalchemy.exc import IntegrityError


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

def test_invalid_location():
    with pytest.raises(ValidationError) as e:
        polyp = Polyp(
            polyp_id = 1,
            location = 'sigmoid'
        )
    assert 'location' in str(e.value)

def test_invalid_morphology():
    with pytest.raises(ValidationError) as e:
        polyp = Polyp(
            polyp_id = 1,
            location = 'cecum',
            morphology = 'weirdness'
        )
    assert 'morphology' in str(e.value)

def test_invalid_resection_method():
    with pytest.raises(ValidationError) as e:
        polyp = Polyp(
            polyp_id = 1,
            location = 'cecum',
            resection_method = 'lasers'
        )
    assert 'resection_method' in str(e.value)

def test_missing_required_field():
    with pytest.raises(ValidationError) as e:
        polyp = Polyp(
            size_mm = 9.0
        )
    assert 'missing' in str(e.value)

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
                    'location': "cecal region"
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
        m = ProcedureMetadataFinal(
            patient_name = "Santa Claus"
        )

def test_bbps():
    r = ColonoscopyReport(
        cecum_reached = True,
        bbps_left = 3,
        bbps_transverse = 2,
        bbps_right = 3,
        
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

    assert r.bbps_left == 3




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

#test that size_mm can be passed as a string and is coerced to a float by pydantic
def test_polyp_size_as_string():
    p = Polyp(
        polyp_id = 1,
        size_mm = "5.0",
        location = 'ascending_colon', 
    )

    assert p.size_mm == 5.0
    assert isinstance(p.size_mm, float)

def test_polyp_size_coercion(): #test to see if int passed to the pydantic model is coerced into a float
    p = Polyp(
        polyp_id = 1,
        size_mm = 5,
        morphology = 'sessile',
        location = 'cecum'
    )

    assert p.size_mm == 5.0



def test_rejects_invalid_input():
    raw = {
        'metadata': {
        'patient_name': 'bob thebuilder',
        'patient_NHI': 'ABC1234',
        'endoscopist_id': 1,
        'procedure_date': datetime(2025,1,1)
    },
    'report': {
        'polyps': [
            {'polyp_id': 1,
             'size_mm': 1.0,
             'location': 'small_bowel'} #invalid location - see if this raises an error
        ]
    }

        }
    
    with pytest.raises(ValidationError) as e:
        ColonoscopyReportWithMetadata(**raw)
    assert 'location' in str(e.value)

def test_partial_llm_output():
    raw = {
        'metadata': {
        'patient_name': 'bob thebuilder',
        'patient_NHI': 'ABC1234',
        'endoscopist_id': 1,
        'procedure_date': datetime(2025,1,1)
    },
    'report': {
        'cecum_reached': True,
        'polyps': [
            {'polyp_id': 1,
             
             'location': 'cecum'} 
        ]
    }

        }
    
    out = ColonoscopyReportWithMetadata(**raw)

    assert out.report.polyps[0].size_mm == None