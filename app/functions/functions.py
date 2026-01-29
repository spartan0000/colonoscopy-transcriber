from openai import OpenAI, AzureOpenAI, AsyncAzureOpenAI
import os

from dotenv import load_dotenv
import asyncio

from pathlib import Path
import yaml
import json

load_dotenv()

from app.functions.clients import chat_client, hnz_client, transcribe_client, whisper_client
from app.models.colonoscopy import ColonoscopyReport

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

async def get_timestamps(file_path: str) -> dict:
    
    with open(file_path, 'rb') as audio_file:
        timestamps = await whisper_client.audio.transcriptions.create(
            model = 'whisper',
            file = audio_file,
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

#cleaned data (dictionary) then goes into this function to extract polyp data and other endoscopy data in structured format
async def extract_json(user_input: dict) -> dict:
    prompt = load_prompt('extraction_prompt.yaml')
    
    transcript_text = f"""
    full text: {user_input['entire_text']}
    segments: {json.dumps(user_input['segments'], indent = 2)}
    """

    response = await chat_client.responses.parse(
        model = "gpt-5-mini",
        input = [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': transcript_text}
        ],
        text_format = ColonoscopyReport,
    )

    output = response.output_parsed.model_dump()
    return output

#then into this function to generate a final report in PDF
def convert_to_report(data: dict) -> str:
    pass



#testing and development purposes only
test_audio_path = DATA_PATH / 'test_audio_1.m4a'
test_audio_path_2 = DATA_PATH/ 'speech_sample.mp3'

if __name__ == "__main__":

    transcript_with_timestamps = asyncio.run(get_timestamps(test_audio_path_2))
    json_output = asyncio.run(extract_json(transcript_with_timestamps))

    print(transcript_with_timestamps)
    print(json_output)

