import os

from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SEGUNDOS = 10
INTERVALO_REFRESCO_MS = 15_000
