from openai import OpenAI, AzureOpenAI, AsyncAzureOpenAI
import os

from dotenv import load_dotenv
import asyncio

from pathlib import Path
import yaml

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

#cleaned data then goes into this function to extract polyp data and other endoscopy data in structured format
async def extract_json(user_input: str) -> dict:
    prompt = load_prompt('extraction_prompt.yaml')
    

    response = await chat_client.responses.parse(
        model = "gpt-5-mini",
        input = [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': user_input}
        ],
        text_format = ColonoscopyReport,
    )

    output = response.output_parsed.model_dump()
    return output

#then into this function to generate a final report in PDF
def convert_to_report(data: dict) -> str:
    pass



test_input = """
there's a polyp.  looks like transverse colon.  probably 2mm sessile.  I'll take a snare.  No cautery needed.  Ok, did you get it?  Yes we got it.  Ok great
ok, i'll take the snare again.  this one is also transverse, probably 3mm.  man, this one's tricky.  ok, got it.  did you get it?  Yes we have it.
ok, this one is sigmoid, 3mm.  i'll take the snare again.  ok, did you get it?  Yes we got it.
""" 
test_audio_path = DATA_PATH / 'test_audio_1.m4a'

if __name__ == "__main__":

    result = asyncio.run(get_timestamps(test_audio_path))
    print(result)