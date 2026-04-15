import imaplib
import smtplib
import email
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import List, Optional
from config import IMAP_HOST, IMAP_PORT, SMTP_HOST, SMTP_PORT, HOSTINGER_EMAIL, HOSTINGER_PASSWORD

def _decode_str(value: str) -> str:
    """Decode encoded email header strings (e.g. =?UTF-8?B?...?=)."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


class IMAPService:
    """
    Drop-in replacement for GmailService that uses Hostinger IMAP/SMTP.

    Credentials are read from environment variables:
        HOSTINGER_EMAIL    – aapka Hostinger email address
        HOSTINGER_PASSWORD – uska password

    Ya aap seedha `email_address` aur `password` pass kar sakte hain.
    """

    def __init__(
        self,
        email_address: str = None,
        password: str = None,
    ):
        self.email_address = email_address or HOSTINGER_EMAIL or ""
        self.password = password or HOSTINGER_PASSWORD or ""

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _connect_imap(self) -> imaplib.IMAP4_SSL:
        """Open an authenticated IMAP connection."""
        imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        imap.login(self.email_address, self.password)
        return imap

    def _parse_email(self, raw_bytes: bytes, uid: str) -> Optional[dict]:
        """Parse raw RFC-822 bytes into a dict matching gmail_service format."""
        try:
            msg = email.message_from_bytes(raw_bytes)

            subject = _decode_str(msg.get("Subject", "(no subject)"))
            from_addr = _decode_str(msg.get("From", ""))
            to_addr = _decode_str(msg.get("To", ""))
            date = msg.get("Date", "")
            thread_id = msg.get("Message-ID", uid)  # IMAP has no thread IDs; use Message-ID

            # Extract plain-text body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                        charset = part.get_content_charset() or "utf-8"
                        body = part.get_payload(decode=True).decode(charset, errors="replace")
                        break
            else:
                charset = msg.get_content_charset() or "utf-8"
                body = msg.get_payload(decode=True).decode(charset, errors="replace")

            snippet = body[:200].replace("\n", " ").replace("\r", "")

            return {
                "id": uid,
                "thread_id": thread_id,
                "from": from_addr,
                "to": to_addr,
                "subject": subject,
                "date": date,
                "body": body,
                "snippet": snippet,
            }
        except Exception as e:
            print(f"[IMAPService] Failed to parse email UID {uid}: {e}")
            return None

    # ── Public API (mirrors GmailService) ────────────────────────────────────

    def fetch_unread_emails(
        self,
        user_email: str = None,   # ignored – kept for drop-in compatibility
        db=None,                  # ignored
        max_results: int = 10,
    ) -> List[dict]:
        """Fetch unread emails from INBOX."""
        if not self.email_address or not self.password:
            print("[IMAPService] Credentials missing — returning mock emails.")
            return self._mock_emails()

        try:
            imap = self._connect_imap()
            imap.select("INBOX")

            # Search for UNSEEN (unread) messages
            status, data = imap.search(None, "UNSEEN")
            if status != "OK":
                return []

            uid_list = data[0].split()
            # Take the latest N UIDs
            uids_to_fetch = uid_list[-max_results:]

            emails = []
            for uid in reversed(uids_to_fetch):  # newest first
                uid_str = uid.decode()
                status, msg_data = imap.fetch(uid, "(RFC822)")
                if status != "OK":
                    continue
                raw = msg_data[0][1]
                parsed = self._parse_email(raw, uid_str)
                if parsed:
                    emails.append(parsed)

            imap.logout()
            return emails

        except imaplib.IMAP4.error as e:
            print(f"[IMAPService] IMAP error: {e}")
            return []

    def get_email(
        self,
        user_email: str = None,   # ignored
        db=None,                  # ignored
        email_id: str = None,
        _service=None,            # ignored
    ) -> Optional[dict]:
        """Fetch a single email by UID."""
        if not self.email_address or not self.password:
            return None

        try:
            imap = self._connect_imap()
            imap.select("INBOX")

            status, msg_data = imap.fetch(email_id, "(RFC822)")
            imap.logout()

            if status != "OK":
                return None
            raw = msg_data[0][1]
            return self._parse_email(raw, email_id)

        except imaplib.IMAP4.error as e:
            print(f"[IMAPService] IMAP error fetching {email_id}: {e}")
            return None

    def send_reply(
        self,
        user_email: str = None,   # ignored
        db=None,                  # ignored
        to: str = "",
        subject: str = "",
        body: str = "",
        thread_id: str = None,    # used as In-Reply-To header
    ) -> bool:
        """Send an email via Hostinger SMTP (SSL on port 465)."""
        if not self.email_address or not self.password:
            print(f"[MOCK SMTP SEND] To: {to} | Subject: {subject}")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.email_address
            msg["To"] = to
            msg["Subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"

            # Thread linking
            if thread_id:
                msg["In-Reply-To"] = thread_id
                msg["References"] = thread_id

            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
                smtp.login(self.email_address, self.password)
                smtp.sendmail(self.email_address, to, msg.as_bytes())

            return True

        except smtplib.SMTPException as e:
            print(f"[IMAPService] SMTP send error: {e}")
            return False

    def mark_as_read(
        self,
        user_email: str = None,  # ignored
        db=None,                 # ignored
        email_id: str = None,
    ):
        """Mark a message as \Seen on the IMAP server."""
        if not self.email_address or not self.password:
            return

        try:
            imap = self._connect_imap()
            imap.select("INBOX")
            imap.store(email_id, "+FLAGS", "\\Seen")
            imap.logout()
        except imaplib.IMAP4.error as e:
            print(f"[IMAPService] Could not mark as read: {e}")

    # ── OAuth stubs (not needed for IMAP but kept for interface compatibility) ─

    def get_auth_url(self) -> str:
        return "N/A — IMAP uses email/password, no OAuth needed."

    def handle_callback(self, code: str, db) -> Optional[str]:
        return None

    # ── Mock data (fallback when no credentials) ──────────────────────────────

    def _mock_emails(self) -> List[dict]:
        return [
            {
                "id": "mock_001",
                "thread_id": "<mock-thread-001@hostinger.com>",
                "from": "customer1@example.com",
                "to": "support@yourcompany.com",
                "subject": "Issue with my order #12345",
                "date": "Mon, 13 Apr 2026 10:30:00 +0000",
                "body": "Hi, I placed an order 3 days ago but haven't received any shipping confirmation. Order #12345. Please help!",
                "snippet": "Hi, I placed an order 3 days ago but haven't received any shipping confirmation.",
            }
        ]

# Alias for compatibility if needed
GmailService = IMAPService
