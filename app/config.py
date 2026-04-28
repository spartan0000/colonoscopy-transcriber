from pathlib import Path
import os

import logging

logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

API_BASE = os.getenv("API_BASE_URL")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "generated_pdfs"
OUTPUT_DIR.mkdir(exist_ok=True)