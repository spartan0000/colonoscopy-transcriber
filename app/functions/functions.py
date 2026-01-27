from openai import OpenAI, AzureOpenAI, AsyncAzureOpenAI
import os

from dotenv import load_dotenv
import asyncio

from pathlib import Path
import yaml

load_dotenv()

from app.functions.clients import chat_client, hnz_client, transcribe_client
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


test_input = """
there's a polyp.  looks like transverse colon.  probably 2mm sessile.  I'll take a snare.  No cautery needed.  Ok, did you get it?  Yes we got it.  Ok great
ok, i'll take the snare again.  this one is also transverse, probably 3mm.  man, this one's tricky.  ok, got it.  did you get it?  Yes we have it.
ok, this one is sigmoid, 3mm.  i'll take the snare again.  ok, did you get it?  Yes we got it.
""" 
test_audio_path = DATA_PATH / 'test_audio_1.m4a'

if __name__ == "__main__":

    result = asyncio.run(extract_json(test_input))
    print(result)