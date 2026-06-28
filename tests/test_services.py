import pytest 



from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.colonoscopy import ColonoscopyReport, ColonoscopyReportWithMetadata, ProcedureMetadata, Finding

from app.services import functions



def test_finding():
    finding = Finding(
        finding_id = '1',
        description = "test finding",
        location = "ascending_colon",
        biopsy_taken = True
    )

    assert finding.location == 'ascending_colon'

def test_missing_fields():
    finding = Finding(
        description = 'test finding'
    ) 

    assert finding.location == None

    
def test_finding_invalid():
    with pytest.raises(ValueError):
        finding = Finding(
            location = 'invalid_location'
        )

@pytest.mark.asyncio
@patch('app.services.functions.whisper_client.audio.transcriptions.create', new_callable=AsyncMock)
async def test_transcribe_timestamps(mock_whisper):
    mock_whisper.return_value = AsyncMock(
        text = 'full_transcript',
        segments = [
            AsyncMock(start = 0.0, end = 1.0, text = 'segment 1'),
            AsyncMock(start = 1.0, end = 2.0, text = 'segment 2')
        ]

    )

    class FakeUploadFile:
        filename = 'fake_audio.mp3'
        file = None
        content_type = 'audio/mpeg'


    result = await functions.transcribe_get_timestamps(FakeUploadFile())

    assert result['entire_text'] == 'full_transcript'
    assert len(result['segments']) == 2
    assert result['segments'][0]['text'] == 'segment 1'

@pytest.mark.asyncio
@patch('app.services.functions.chat_client.responses.parse', new_callable=AsyncMock)
async def test_extract_json(mock_parse):

    mock_model = ColonoscopyReport(
        polyps = [],
        findings = []
    )

    mock_response = AsyncMock()
    mock_response.output_parsed = mock_model 

    mock_parse.return_value = mock_response

    input_data = {
        'entire_text': 'full transcript',
        'segments': [{'start': 0.0, 'end': 1.0, 'text': 'segment1'}]
    }

    result, status = await functions.extract_json(input_data)

    output = result.model_dump()

    assert isinstance(output, dict)

@pytest.mark.asyncio
async def test_extract_json_2():
    mock_parse = AsyncMock()
    mock_parse.output_parsed = ColonoscopyReport(
        bbps_right = None,
        bbps_transverse = None,
        bbps_left = None,
        polyps = [],
        findings = []
    )

    with patch('app.services.functions.chat_client.responses.parse', return_value=mock_parse):
        result, status = await functions.extract_json({'entire_text': 'x', 'segments': []})
    
    assert result.bbps_right is None

#if chat LLM refuses to transcribe text, returns default model
@pytest.mark.asyncio
async def test_extract_json_llm_refusal():
    mock_response = AsyncMock()
    mock_response.output_parsed = None
    mock_response.output_text = "I'm sorry, I cannot assist with that request."
    with patch('app.services.functions.chat_client.responses.parse', return_value=mock_response):
        result, status = await functions.extract_json({'entire_text': 'x', 'segments':[]})

    
    assert result == functions._empty_report()

# _empty_report in functions.py is the default return which is ColonoscopyReport with empty fields


@pytest.mark.asyncio
async def test_extract_json_exception():
    with patch('app.services.functions.chat_client.responses.parse', side_effect = Exception("API fail")):
        result, status = await functions.extract_json({'entire_text': 'x', 'segments':[]})
    assert result == functions._empty_report()


