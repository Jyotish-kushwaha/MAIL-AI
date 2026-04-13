from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
import json
import re
from config import GROQ_API_KEY

client = None
if GROQ_API_KEY:
    try:
        client = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            api_key=GROQ_API_KEY
        )
    except Exception as e:
        print(f"Warning: Failed to initialize ChatGroq: {e}")
else:
    print("Warning: GROQ_API_KEY is not set. AI services will not be available.")


# ─── Email Reply Template ─────────────────────────────────────────────────────

REPLY_TEMPLATE = """
You are a professional customer support assistant.

Generate a high-quality email reply. Respond ONLY with valid JSON — no preamble, no markdown.

Email received:
\"\"\"{email_text}\"\"\"

Requested tone: {tone}

Available tones: professional, formal, friendly, apologetic, empathetic, concise

Output format (STRICT JSON ONLY):
{{
    "subject": "Short relevant subject line (Re: original topic)",
    "body": "Full email reply with greeting, acknowledgement, solution, and polite closing",
    "confidence": 0.0 to 1.0 (how confident you are this reply is appropriate)
}}

Guidelines:
- Start with a warm greeting (Dear [Customer], Hello, etc.)
- Acknowledge the customer's issue or request specifically
- Provide a clear, helpful response or solution
- Offer further assistance
- End with a professional closing (Best regards, Sincerely, etc.)
- Match the {tone} tone throughout
- confidence should be lower if the email is ambiguous, threatening, or requires human judgment
"""

# ─── Categorization Template ──────────────────────────────────────────────────

CATEGORY_TEMPLATE = """
Categorize this customer email into exactly ONE of these categories:
complaint, inquiry, feedback, request, billing, technical_support, refund, other

Email:
\"\"\"{email_text}\"\"\"

Respond with ONLY the category word, nothing else.
"""

reply_prompt = PromptTemplate(
    input_variables=["email_text", "tone"],
    template=REPLY_TEMPLATE
)

category_prompt = PromptTemplate(
    input_variables=["email_text"],
    template=CATEGORY_TEMPLATE
)


def generate_email_reply(email_text: str, tone: str = "professional") -> dict:
    """Generate an AI reply for the given email."""
    if not client:
        return {
            "error": "GROQ_API_KEY is missing. AI reply generation is disabled.",
            "subject": "Re: Your Message",
            "body": "Thank you for contacting us. A team member will follow up shortly.",
            "confidence": 0.0
        }
        
    prompt = reply_prompt.format(email_text=email_text, tone=tone)
    response = client.invoke(prompt)
    
    try:
        # Strip any accidental markdown fences
        content = response.content.strip()
        content = re.sub(r"^```json\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        result = json.loads(content)
        
        # Ensure confidence is present and valid
        if "confidence" not in result:
            result["confidence"] = 0.85
        result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
        return result
    except (json.JSONDecodeError, ValueError):
        return {
            "error": "Failed to parse AI response",
            "raw": response.content,
            "subject": "Re: Your Message",
            "body": "Thank you for contacting us. A team member will follow up shortly.",
            "confidence": 0.3
        }


def categorize_email(email_text: str) -> str:
    """Categorize the email into a predefined category."""
    if not client:
        return "other"
        
    prompt = category_prompt.format(email_text=email_text)
    response = client.invoke(prompt)
    
    valid_categories = {
        "complaint", "inquiry", "feedback", "request",
        "billing", "technical_support", "refund", "other"
    }
    
    category = response.content.strip().lower()
    return category if category in valid_categories else "other"
