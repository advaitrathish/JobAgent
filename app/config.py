
import os
from pathlib import Path

from dotenv import load_dotenv


# Project directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from the project root
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(ENV_FILE)


# FreeLLMAPI configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "auto").strip() or "auto"


# Application directories
DATA_DIR = PROJECT_ROOT / "data"
RESUME_DIR = PROJECT_ROOT / "resumes"
LOG_DIR = PROJECT_ROOT / "logs"


# Application settings
APP_NAME = "JobAgent"
TIMEZONE = "Asia/Kolkata"

# Safety settings
REQUIRE_APPROVAL_BEFORE_SENDING = True
