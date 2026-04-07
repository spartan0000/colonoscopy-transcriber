import pytest
from pydantic import ValidationError
from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportWithMetadata, ProcedureMetadata, Finding, Polyp


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




