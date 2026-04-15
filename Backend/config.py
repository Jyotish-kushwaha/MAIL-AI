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

# ─── IMAP / SMTP Hostinger Config ─────────────────────────────────────────────
IMAP_HOST = os.getenv("IMAP_HOST", "imap.hostinger.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.hostinger.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

HOSTINGER_EMAIL = os.getenv("HOSTINGER_EMAIL")
HOSTINGER_PASSWORD = os.getenv("HOSTINGER_PASSWORD")
