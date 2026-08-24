from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("NEON_DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("NEON_DATABASE_URL no está definida en el .env")

# pool_pre_ping evita el típico error de "conexión cerrada por inactividad"
# que suele pasar con bases de datos serverless como Neon
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
