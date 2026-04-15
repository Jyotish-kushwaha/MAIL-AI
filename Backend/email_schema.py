from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class ToneOption(str, Enum):
    professional = "professional"
    formal = "formal"
    friendly = "friendly"
    apologetic = "apologetic"
    empathetic = "empathetic"
    concise = "concise"


class CategoryOption(str, Enum):
    complaint = "complaint"
    inquiry = "inquiry"
    feedback = "feedback"
    request = "request"
    billing = "billing"
    technical_support = "technical_support"
    refund = "refund"
    other = "other"


class Email_Request(BaseModel):
    email_text: str = Field(..., min_length=10, description="The email content to reply to")
    tone: ToneOption = ToneOption.professional


class Email_Response(BaseModel):
    subject: str
    body: str
    category: Optional[str] = "other"
    tone_used: Optional[str] = "professional"
    confidence: Optional[float] = 0.9


class AutoReplyConfig(BaseModel):
    tone: ToneOption = ToneOption.professional
    auto_send: bool = False
    confidence_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to auto-send (below = pending review)"
    )
    max_emails_per_run: int = Field(default=10, ge=1, le=100)


class EmailItem(BaseModel):
    id: str
    from_address: str
    subject: str
    snippet: str
    category: Optional[str] = None
    status: Optional[str] = None


class ProcessingStatus(BaseModel):
    email_id: str
    status: Literal["sent", "draft", "pending_review", "skipped", "error"]
    message: str
    category: Optional[str] = None
    confidence: Optional[float] = None
