from openai import OpenAI, AzureOpenAI, AsyncAzureOpenAI
import os

from dotenv import load_dotenv
import asyncio

from pathlib import Path
import yaml

load_dotenv()

from app.functions.clients import chat_client, hnz_client

BASE_PATH = Path(__file__).parent.parent
PROMPT_PATH = BASE_PATH / 'prompts'


def load_prompt() -> str:
    PROMPT_FILE = PROMPT_PATH / 'extraction_prompt.yaml'

    with open(PROMPT_FILE, 'r') as f:
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
    pass


if __name__ == "__main__":
    prompt = load_prompt()
    print(prompt)