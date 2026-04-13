# AI Email Response System v2.0

A fully automated system that reads incoming Gmail emails, categorizes them, generates context-aware AI replies, and optionally sends them — with a confidence-based human override.

---

## Features

| Feature | Status |
|---------|--------|
| Gmail OAuth2 integration | ✅ |
| AI reply generation (Groq/LLaMA) | ✅ |
| Email categorization | ✅ |
| Tone control (6 options) | ✅ |
| Duplicate reply prevention | ✅ |
| Confidence-based human override | ✅ |
| Background auto-processing | ✅ |
| SQLite history & analytics | ✅ |
| Web dashboard UI | ✅ |

---

## Project Structure

```
email_ai_system/
├── main.py                    # FastAPI app + all routes
├── config.py                  # API keys & settings
├── requirements.txt           # Dependencies
│
├── services/
│   ├── ai_services.py         # Groq LLM: reply generation + categorization
│   └── gmail_service.py       # Gmail API: fetch, send, OAuth2
│
├── schemas/
│   └── email_schema.py        # Pydantic models
│
├── utils/
│   └── database.py            # SQLite: history, deduplication, stats
│
└── templates/
    └── dashboard.html         # Full-featured web dashboard
```

---

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
AUTO_SEND=false
CONFIDENCE_THRESHOLD=0.75
MAX_EMAILS_PER_RUN=10
DEFAULT_TONE=professional
```

### 3. Set Up Gmail API

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Enable the **Gmail API**
4. Go to **APIs & Services → Credentials**
5. Create **OAuth 2.0 Client ID** (type: Web application)
6. Add redirect URI: `http://localhost:8000/auth/callback`
7. Download the credentials as `credentials.json`
8. Place `credentials.json` in the project root

### 4. Run the Server

```bash
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Authenticate Gmail

Visit: `http://localhost:8000/auth/gmail`

This returns an auth URL. Open it in your browser, authorize access, and the token is saved automatically.

---

## Usage

### Dashboard
Open `http://localhost:8000/dashboard` for the full web UI.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/generate-reply` | Manually generate a reply |
| GET | `/auth/gmail` | Get Gmail OAuth URL |
| GET | `/auth/callback` | OAuth callback handler |
| GET | `/emails/fetch` | Fetch unread emails |
| POST | `/emails/process/{id}` | Process a single email |
| POST | `/emails/auto-process` | Auto-process all unread |
| POST | `/emails/approve/{id}` | Approve a pending-review email |
| GET | `/dashboard/stats` | Get processing statistics |
| GET | `/dashboard/history` | Get email history |

### Manual Reply Example

```bash
curl -X POST http://localhost:8000/generate-reply \
  -H "Content-Type: application/json" \
  -d '{
    "email_text": "I placed an order 3 days ago and have not received confirmation.",
    "tone": "apologetic"
  }'
```

### Auto-Process Configuration

```bash
curl -X POST http://localhost:8000/emails/auto-process \
  -H "Content-Type: application/json" \
  -d '{
    "tone": "professional",
    "auto_send": false,
    "confidence_threshold": 0.75,
    "max_emails_per_run": 10
  }'
```

---

## Email Categories

The AI automatically classifies emails into:
- `complaint` — Unhappy customers, negative experiences
- `inquiry` — Questions, information requests
- `feedback` — Reviews, suggestions
- `request` — Feature or service requests
- `billing` — Payment, invoice, subscription issues
- `technical_support` — Bug reports, usage help
- `refund` — Refund/return demands
- `other` — Everything else

---

## Tone Options

| Tone | Best For |
|------|----------|
| `professional` | General business correspondence |
| `formal` | Legal, enterprise, official contexts |
| `friendly` | Consumer brands, casual SaaS |
| `apologetic` | Complaints, service failures |
| `empathetic` | Emotional or distressed customers |
| `concise` | Quick acknowledgements |

---

## Confidence & Human Override

The AI returns a `confidence` score (0.0–1.0) with each reply.

- **Above threshold** → auto-send (if enabled) or save as draft
- **Below threshold** → saved as `pending_review` for human approval

Use `POST /emails/approve/{id}` to approve and send pending emails.

Default threshold: **75%**

---

## Notes

- Without `credentials.json`, the system uses **mock emails** for testing
- The SQLite database (`email_history.db`) is created automatically
- Email processing is **idempotent** — already-replied emails are skipped
