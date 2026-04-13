import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys (prefer env vars over hardcoded values) ─────────────────────────
# Set GROQ_API_KEY in your environment or .env file
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ─── App Settings ─────────────────────────────────────────────────────────────
APP_ENV = os.getenv("APP_ENV", "development")
DEFAULT_TONE = os.getenv("DEFAULT_TONE", "professional")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
AUTO_SEND = os.getenv("AUTO_SEND", "false").lower() == "true"
MAX_EMAILS_PER_RUN = int(os.getenv("MAX_EMAILS_PER_RUN", "10"))
