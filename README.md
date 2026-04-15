# 📧 AI Email Response System v3.0 (Multi-User + Modular Architecture)

A fully automated system that reads incoming emails, categorizes them, generates context-aware AI replies, and optionally sends them — with a confidence-based human override.

Now upgraded with:

* ✅ **Frontend + Backend separation**
* ✅ **Multi-user workspace system**
* ✅ **IMAP/SMTP (Hostinger) support**
* ✅ **Modern dashboard UI**

---

# 🚀 Features

| Feature                                 | Status |
| --------------------------------------- | ------ |
| Multi-user workspace system             | ✅      |
| IMAP/SMTP email integration (Hostinger) | ✅      |
| AI reply generation (Groq / LLaMA)      | ✅      |
| Email categorization                    | ✅      |
| Tone control (6 options)                | ✅      |
| Duplicate reply prevention              | ✅      |
| Confidence-based human override         | ✅      |
| Background auto-processing              | ✅      |
| PostgreSQL / SQLite support             | ✅      |
| Modular frontend + backend              | ✅      |
| Modern dashboard UI                     | ✅      |

---

# 🏗️ Project Structure

```bash
Email-Assistant/
│
├── Backend/
│   ├── main.py
│   ├── ai_services.py
│   ├── database.py
│   ├── Imap_service.py
│   ├── config.py
│   ├── email_schema.py
│   ├── .env
│   └── requirements.txt
│
├── Frontend/
│   ├── index.html
│   ├── js/
│   │   ├── app.js
│   │   ├── api.js
│   │   ├── auth.js
│   │   ├── dashboard.js
│   │   └── ui.js
│   └── styles.css
│
├── README.md
```

---

# ⚙️ Setup Instructions

## 1️⃣ Backend Setup

```bash
cd Backend
pip install -r requirements.txt
uvicorn main:app --reload
```

👉 Runs on:

```
http://localhost:8000
```

---

## 2️⃣ Frontend Setup

```bash
cd Frontend
npx live-server
```

👉 Runs on:

```
http://127.0.0.1:8080
```

---

# 🔗 Frontend ↔ Backend Connection

File: `Frontend/js/api.js`

```js
const BASE_URL = "http://localhost:8000";
```

👉 If issue occurs:

```js
const BASE_URL = "http://127.0.0.1:8000";
```

---

# 🧪 Debug Guide (VERY IMPORTANT)

## ✅ 1. Backend Health Check

Open:

```
http://localhost:8000
```

Expected:

```json
{"status": "running"}
```

---

## ✅ 2. API Working?

```
http://localhost:8000/users
```

Expected:

```json
{"users": [...]}
```

---

## ❌ 3. UI Plain / No Styling

### Cause:

Wrong static paths

### Fix `Frontend/index.html`:

```html
<link rel="stylesheet" href="./styles.css">
<script type="module" src="./js/app.js"></script>
```

❌ DO NOT USE:

```html
/static/...
```

---

## ❌ 4. "Failed to fetch" Error

### Causes:

* Backend not running
* Wrong BASE_URL
* Port mismatch

### Fix:

* Start backend
* Check BASE_URL
* Try `127.0.0.1` instead of `localhost`

---

## ❌ 5. Users Not Loading

Check:

* `/users` API working?
* `.env` properly configured?

```env
HOSTINGER_EMAIL=your_email
HOSTINGER_PASSWORD=your_password
```

---

## ❌ 6. JS / CSS Not Loading

Check browser console:

```
Inspect → Console
```

Errors:

```
404 js/app.js
```

👉 Fix paths in `index.html`

---

## ❌ 7. CORS Issue

Already handled in backend:

```python
allow_origins=["*"]
```

---

# ⚡ Quick Run Commands

```bash
# Backend
cd Backend
uvicorn main:app --reload

# Frontend
cd Frontend
npx live-server
```

---

# 📡 API Endpoints

| Method | Endpoint               | Description          |
| ------ | ---------------------- | -------------------- |
| GET    | `/`                    | Health check         |
| POST   | `/generate-reply`      | Generate AI reply    |
| GET    | `/emails/fetch`        | Fetch unread emails  |
| POST   | `/emails/process/{id}` | Process single email |
| POST   | `/emails/auto-process` | Process all emails   |
| POST   | `/emails/approve/{id}` | Approve & send reply |
| GET    | `/dashboard/stats`     | Get stats            |
| GET    | `/dashboard/history`   | Get history          |
| GET    | `/users`               | Get all users        |

---

# 🧠 Email Categories

* complaint
* inquiry
* feedback
* request
* billing
* technical_support
* refund
* other

---

# 🎯 Tone Options

| Tone         | Use Case             |
| ------------ | -------------------- |
| professional | Default business     |
| formal       | Legal / corporate    |
| friendly     | Casual communication |
| apologetic   | Complaints           |
| empathetic   | Emotional cases      |
| concise      | Short replies        |

---

# 🤖 Confidence System

* AI returns `confidence` (0–1)
* Below threshold → `pending_review`
* Above threshold → draft / auto-send

Default:

```
0.75 (75%)
```

---

# ⚙️ Environment Variables

Create `Backend/.env`:

```env
GROQ_API_KEY=your_key
HOSTINGER_EMAIL=your_email
HOSTINGER_PASSWORD=your_password

AUTO_SEND=false
CONFIDENCE_THRESHOLD=0.75
MAX_EMAILS_PER_RUN=10
DEFAULT_TONE=professional
```

---

# 🧠 Architecture

```
Frontend (Live Server / Vercel)
        ↓
API Calls (fetch)
        ↓
FastAPI Backend
        ↓
AI + IMAP + Database
```

---

# 🔥 Common Mistakes

| Mistake             | Fix              |
| ------------------- | ---------------- |
| Using `/static/...` | Use `./` paths   |
| Backend not running | Start uvicorn    |
| Wrong BASE_URL      | Fix API URL      |
| Using file://       | Use live-server  |
| Not refreshing      | Ctrl + Shift + R |

---

# 🚀 Future Improvements

* Deploy frontend → Vercel
* Deploy backend → Railway / Render
* Add authentication system
* Add logging & monitoring
* Add Docker support

---

# 👨‍💻 Author

**Jyotish Kumar**
AI/ML Engineer 🚀

---
