from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    file_url: Optional[str] = None  # S3 URL if PDF uploaded
    stream: bool = True

class ToolCall(BaseModel):
    tool: str
    status: Literal["started", "completed", "failed"]
    duration_ms: Optional[int] = None
    summary: Optional[str] = None

class Section(BaseModel):
    number: int
    title: str
    content: str

class ChatResponse(BaseModel):
    conversation_id: str
    sections: Optional[List[Section]] = None  # For pre-screening
    answer: Optional[str] = None              # For Q&A
    tool_calls: List[ToolCall] = []
    docx_url: Optional[str] = None
    citations: List[Dict[str, Any]] = []
