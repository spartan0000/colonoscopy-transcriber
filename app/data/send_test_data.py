import requests
import asyncio
import os

API_URL = "http://localhost:8000/transcribe"

from pathlib import Path

BASE_PATH = Path(__file__).parent

async def send_test_data(file_path: str):

    with open(file_path, 'rb') as audio_file:
        files = {'audio_file': audio_file}
        response = requests.post(API_URL, files = files)

        if response.status_code == 200:
            print(f'Response: {response.json()}')
        else:
            print(f'Error: {response.status_code} - {response.text}')



if __name__ == "__main__":
    test_file_path = BASE_PATH / 'test_audio_2.mp3'
    asyncio.run(send_test_data(test_file_path))



