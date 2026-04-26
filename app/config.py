from pathlib import Path
import os

API_BASE = os.getenv("API_BASE_URL")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "generated_pdfs"
OUTPUT_DIR.mkdir(exist_ok=True)