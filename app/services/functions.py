from openai import OpenAI, AzureOpenAI, AsyncAzureOpenAI
import os

from dotenv import load_dotenv
import asyncio
import json

from pathlib import Path
import yaml
import json


import random
from datetime import date, datetime, timedelta

from fastapi import UploadFile
from io import BytesIO

from sqlalchemy.orm import Session

load_dotenv()

from app.services.clients import chat_client, hnz_client, transcribe_client, whisper_client
from app.models.colonoscopy import ColonoscopyReport, ProcedureMetadata, ColonoscopyReportWithTime, ColonoscopyReportWithMetadata
from app.models.colonoscopy import ColonoscopyReportFinal, ProcedureMetadataFinal, ColonoscopyReportWithMetadataFinal
from app.database.models import ProcedureModel, PolypModel, FindingModel, EndoscopistLookup, PolypLocationLookup


BASE_PATH = Path(__file__).parent.parent
PROMPT_PATH = BASE_PATH / 'prompts'
DATA_PATH = BASE_PATH / 'data'


def load_prompt(prompt_file:str) -> str:
    prompt_path = PROMPT_PATH / prompt_file
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, 'r') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error loading YAML file: {e}")
        system_prompt = f"{config['prompt']['content']}"
        rules = config['prompt'].get('rules')
        if rules:
            rules_text = "\n Rules: \n" + "\n".join(f'- {rule}' for rule in rules)
            system_prompt = f'{system_prompt}\n{rules_text}'
        return system_prompt



#this function likely obsolete given the one below using whisper which will get both the transcription in segments as well as timestamps
#was used for development and testing the extraction of text from audio
async def transcribe_audio(file_path: str) -> str:
    prompt = load_prompt('transcription_prompt.yaml')
    with open(file_path, 'rb') as audio_file:
        transcription = await transcribe_client.audio.transcriptions.create(
            model = 'gpt-4o-transcribe',
            file = audio_file,
            response_format = 'text',
            prompt = prompt
        )
    return transcription


#uses whisper to get transcription with timestamps
async def transcribe_get_timestamps(upload_file: UploadFile) -> dict:
    
    
    timestamps = await whisper_client.audio.transcriptions.create(
        model = 'whisper',
        file = (upload_file.filename, upload_file.file, upload_file.content_type),
        response_format = 'verbose_json',
        timestamp_granularities = ['segment'],

    )

    

        #get rid of unnecessary data like tokens and logprobs
    clean_data = {
        'entire_text':timestamps.text,
        'segments': [
    {
        'start': seg.start,
        'end':seg.end,
        'text': seg.text
    }
        for seg in timestamps.segments
        ]
    }
    return clean_data


def _empty_report() -> ColonoscopyReport:
    return ColonoscopyReport(
                bbps_right = None,
                bbps_transverse = None,
                bbps_left = None,
                polyps = [],
                findings = []
            ) 

#cleaned data (dictionary) then goes into this function to extract polyp data and other endoscopy data in structured format
async def extract_json(user_input: dict) -> dict:
    prompt = load_prompt('extraction_prompt.yaml')
    
    

    transcript_text = f"""
    full text: {user_input['entire_text']}
    segments: {json.dumps(user_input['segments'], indent = 2)}
    """

    try:
        response = await chat_client.responses.parse(
            model = "gpt-5-mini",
            input = [
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': transcript_text}
            ],
            text_format = ColonoscopyReport,
        )


        if type(response.output_parsed) is str or response.output_parsed is None:
            print("LLM failed to return structured output")
            print("RAW:", response.output_text)

            return _empty_report
    
    
        return response.output_parsed
    
    except Exception as e:
        print(f"LLM refusal or parse error: {e}")
        return _empty_report

def add_time_stamps(llm: ColonoscopyReport, cecum_reached_time, procedure_end_time) -> ColonoscopyReportWithTime:
    
    return ColonoscopyReportWithTime(
        cecum_reached = cecum_reached_time is not None,
        cecum_reached_time = cecum_reached_time,
        procedure_end_time = procedure_end_time,
        bbps_right = llm.bbps_right,
        bbps_left = llm.bbps_left,
        bbps_transverse = llm.bbps_transverse,
        polyps = llm.polyps,
        findings = llm.findings,
    )



###function to generate fake metadata for testing purposes. Eventually, will need to source the metadata from primary data source.  

def generate_fake_data(transcribed_report):
    names = ['Bob Marley', 'Ben Franklin', 'Stevie Nicks', 'Santa Claus']
    nhis = ['ABC1234', 'ABC7890', 'XYZ4343', 'LLL1111']
    dobs = [
        date(1945,1,1),
        date(1950,1,1),
        date(1955,1,1),
        date(1920,1,1)
    ]

    metadata = ProcedureMetadata(
        patient_name = random.choice(names),
        patient_NHI = random.choice(nhis),
        procedure_date = date.today() - timedelta(days = random.randint(0,60)),
        patient_dob = random.choice(dobs),
        endoscopist_id = random.randint(1,4)
    )

    full_report = ColonoscopyReportWithMetadata(
        
        metadata = metadata,
        report = transcribed_report
    )
    return full_report

###maping functions to convert from pydantic models to sqlalchemy models for writing to the database.

def map_polyp(polyp):
    return PolypModel(
        
        size_mm = polyp.size_mm,
        location_code = polyp.location,
        morphology = polyp.morphology,
        resection_method = polyp.resection_method,
        resection_complete = polyp.resection_complete,
        retrieved = polyp.retrieved,

    )

def map_findings(finding):
    return FindingModel(
        
        description = finding.description,
        location_code = finding.location,
        biopsy_taken = finding.biopsy_taken
    )

def map_procedure(report, metadata):
    return ProcedureModel(
        patient_id = metadata.patient_NHI,
        patient_name = metadata.patient_name,
        procedure_date = metadata.procedure_date,
        endoscopist_id = metadata.endoscopist_id,
        cecum_reached = report.cecum_reached,
        cecum_reached_time = report.cecum_reached_time,
        procedure_end_time = report.procedure_end_time,
        bbps_right = report.bbps_right,
        bbps_transverse = report.bbps_transverse,
        bbps_left = report.bbps_left,
        
            
    )


def write_transcription_record(db: Session, full_report: ColonoscopyReportWithMetadataFinal):
    metadata = full_report.metadata
    report = full_report.report
    with db.begin():
        
        procedure = map_procedure(report, metadata)
        
        for polyp in report.polyps:
            procedure.polyps.append(map_polyp(polyp))
                
            
        for finding in report.findings:
            procedure.findings.append(map_findings(finding))
                

        db.add(procedure)
        
    db.refresh(procedure)

        

async def final_transcription(upload_file: UploadFile, db: Session):
    clean_data = transcribe_get_timestamps(upload_file)
    output = extract_json(clean_data)
    full_report = generate_fake_data(output)
    write_transcription_record(db = db, full_report = full_report)

    return full_report


#then into this function to generate a final report in PDF
def convert_to_report(data: dict) -> str:
    pass



#testing and development purposes only
test_audio_path = DATA_PATH / 'test_audio_1.m4a'
test_audio_path_2 = DATA_PATH/ 'test_audio_2.mp3'

if __name__ == "__main__":

    with open(test_audio_path_2, 'rb') as f:
        upload_file = UploadFile(filename='test_audio_2.mp3', file=f)

        transcript_with_timestamps = asyncio.run(transcribe_get_timestamps(upload_file))
        json_output = asyncio.run(extract_json(transcript_with_timestamps))

    print(transcript_with_timestamps)
    print(json_output)

