import requests
import asyncio
import os

API_URL = "http://127.0.0.1:8000/transcribe"
DB_TEST_URL = "http://127.0.0.1:8000/test_db"

from pathlib import Path

BASE_PATH = Path(__file__).parent

def send_test_data(file_path: str):

    with open(file_path, 'rb') as f:
        files = {'file': (str(file_path), f, "audio/mpeg")}
        response = requests.post(API_URL, files = files)

        if response.status_code == 200:
            print(f'Response: {response.json()}')
        else:
            print(f'Error: {response.status_code} - {response.text}')



if __name__ == "__main__":
    #tests the transcribe endpoint
    #test_file_path = BASE_PATH / 'test_audio_2.mp3'
    #send_test_data(test_file_path)


    #used only for testing database connection
    response = requests.post(DB_TEST_URL)
    print(response.status_code)
    print(response.json())






