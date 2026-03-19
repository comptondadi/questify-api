from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

print("DATABASE_URL:", os.getenv("DATABASE_URL"))
print("JWT Secret:", os.getenv("SECRET_KEY")[:6] + "...")

