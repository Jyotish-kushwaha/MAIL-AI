from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
import uvicorn
import asyncio

from ai_services import generate_email_reply, categorize_email

from Imap_service import IMAPService

from email_schema import (
    Email_Request, Email_Response, AutoReplyConfig,
    EmailItem, ProcessingStatus
)
from database import EmailDatabase

app = FastAPI(title="AI Email Response System (Multi-Tenant)", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the static files directory for modular ES architecture
app.mount("/static", StaticFiles(directory="static"), name="static")

db = EmailDatabase()
gmail_service = IMAPService()

# ─── Core Email Routes ────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {"message": "AI Email Response System v3.0 (Multi-User Ready)", "status": "running"}

@app.post("/generate-reply", response_model=Email_Response)
def generate_reply(request: Email_Request):
    """Manually generate a reply for a given email."""
    raw_output = generate_email_reply(request.email_text, request.tone)
    category = categorize_email(request.email_text)
    
    if "error" in raw_output:
        raise HTTPException(status_code=500, detail=raw_output["error"])

    return Email_Response(
        subject=raw_output["subject"],
        body=raw_output["body"],
        category=category,
        tone_used=request.tone,
        confidence=raw_output.get("confidence", 0.9)
    )

# ─── IMAP/Gmail Integration Routes ───────────────────────────────────────────

@app.get("/auth/gmail")
def gmail_auth():
    """Step 1: Get Gmail OAuth2 authorization URL."""
    # Since we're using IMAPService, OAuth is skipped.
    return {"message": "IMAP mode active. No OAuth required. Ensure HOSTINGER_EMAIL & HOSTINGER_PASSWORD are set in .env."}

@app.get("/auth/callback")
def gmail_callback(code: str):
    """Step 2: Handle OAuth2 callback and save credentials."""
    # Since we're using IMAPService, OAuth is skipped.
    return {"message": "IMAP mode active. OAuth callback is not used."}

@app.get("/emails/fetch")
def fetch_emails(user_email: str = Query(None), max_results: int = 10):
    """Fetch recent unread emails from Gmail inbox."""
    if not user_email:
        users = db.get_all_users()
        if not users:
            raise HTTPException(status_code=400, detail="No authorized users found. Provide user_email.")
        user_email = users[0]["email"]

    emails = gmail_service.fetch_unread_emails(user_email, db, max_results)
    return {"user_email": user_email, "emails": emails, "count": len(emails)}

@app.post("/emails/process/{email_id}")
def process_email(email_id: str, config: AutoReplyConfig, user_email: str = Query(None)):
    """Process a specific email: categorize, generate reply, optionally send."""
    if not user_email:
        users = db.get_all_users()
        if not users:
            raise HTTPException(status_code=400, detail="No authorized users found. Provide user_email.")
        user_email = users[0]["email"]

    # Duplicate check
    if db.is_already_replied(email_id, user_email):
        return {"status": "skipped", "reason": "Already replied to this email"}

    # Fetch the email
    email_data = gmail_service.get_email(user_email, db, email_id)
    if not email_data:
        raise HTTPException(status_code=404, detail="Email not found")

    # Categorize
    category = categorize_email(email_data["body"])

    # Generate reply
    reply = generate_email_reply(email_data["body"], config.tone)

    if "error" in reply:
        raise HTTPException(status_code=500, detail=reply["error"])

    # Confidence check — human override
    confidence = reply.get("confidence", 0.9)
    if confidence < config.confidence_threshold:
        db.save_email_record(email_id, user_email, email_data, reply, category, "pending_review")
        return {
            "status": "pending_review",
            "reason": f"Low confidence ({confidence:.0%}). Human review required.",
            "draft": reply,
            "category": category
        }

    # Auto-send if enabled
    if config.auto_send:
        gmail_service.send_reply(
            user_email=user_email,
            db=db,
            to=email_data["from"],
            subject=reply["subject"],
            body=reply["body"],
            thread_id=email_data.get("thread_id")
        )
        db.save_email_record(email_id, user_email, email_data, reply, category, "sent")
        return {"status": "sent", "category": category, "reply": reply}

    # Save as draft
    db.save_email_record(email_id, user_email, email_data, reply, category, "draft")
    return {"status": "draft_saved", "category": category, "reply": reply}

@app.post("/emails/auto-process")
def auto_process_all(config: AutoReplyConfig, background_tasks: BackgroundTasks):
    """Fetch and auto-process all unread emails for ALL users in background."""
    background_tasks.add_task(process_all_emails_task, config)
    return {"message": "Auto-processing started in background for all users.", "status": "running"}

@app.post("/emails/approve/{email_id}")
def approve_and_send(email_id: str):
    """Human override: approve and send a pending-review email."""
    record = db.get_email_record(email_id)
    if not record:
        raise HTTPException(status_code=404, detail="Email record not found")

    user_email = record.get("user_email")
    if not user_email:
        raise HTTPException(status_code=400, detail="Record missing user_email. Cannot send.")

    success = gmail_service.send_reply(
        user_email=user_email,
        db=db,
        to=record["from_address"],
        subject=record["reply_subject"],
        body=record["reply_body"],
        thread_id=record.get("thread_id")
    )
    if success:
        db.update_status(email_id, "sent")
        return {"status": "sent", "message": "Email approved and sent"}
    raise HTTPException(status_code=500, detail="Failed to send email via Gmail API")


# ─── Dashboard & Analytics Routes ────────────────────────────────────────────

@app.get("/dashboard/stats")
def get_stats(user_email: str = Query(None)):
    """Get email processing statistics."""
    return db.get_stats(user_email=user_email)

@app.get("/dashboard/history")
def get_history(user_email: str = Query(None), limit: int = 50, status: str = None, category: str = None):
    """Get email processing history with optional filters."""
    return db.get_history(user_email=user_email, limit=limit, status=status, category=category)

@app.get("/users")
def get_users():
    """Get a list of all currently authenticated users (emails)."""
    users = db.get_all_users()
    return {"users": [u["email"] for u in users]}

@app.get("/dashboard")
def dashboard():
    """Serve the modular HTML dashboard UI."""
    return FileResponse("static/index.html")

# ─── Background Task ──────────────────────────────────────────────────────────

def process_all_emails_task(config: AutoReplyConfig):
    import time
    users = db.get_all_users()
    for user in users:
        user_email = user.get("email")
        if not user_email:
            continue

        try:
            emails = gmail_service.fetch_unread_emails(user_email, db, max_results=config.max_emails_per_run)
            for email in emails:
                if not db.is_already_replied(email["id"], user_email):
                    try:
                        category = categorize_email(email["body"])
                        reply = generate_email_reply(email["body"], config.tone)
                        confidence = reply.get("confidence", 0.9)
                        
                        if confidence >= config.confidence_threshold and config.auto_send:
                            gmail_service.send_reply(
                                user_email=user_email,
                                db=db,
                                to=email["from"],
                                subject=reply["subject"],
                                body=reply["body"],
                                thread_id=email.get("thread_id")
                            )
                            db.save_email_record(email["id"], user_email, email, reply, category, "sent")
                        else:
                            db.save_email_record(email["id"], user_email, email, reply, category, "pending_review")
                    except Exception as e:
                        db.save_email_record(email["id"], user_email, email, {}, "unknown", "error")
                time.sleep(1)  # Rate limiting per email processing
        except Exception as e:
            print(f"Failed processing emails for {user_email}: {e}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Multi-Tenant Server starting!")
    print("Access the dashboard at: http://localhost:8000/dashboard")
    print("="*60 + "\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
