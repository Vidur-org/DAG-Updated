from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message/query")
    stream: bool = Field(default=False, description="Enable streaming response")

class Source(BaseModel):
    title: str
    url: str
    snippet: str

class ChatResponse(BaseModel):
    type: str = Field(..., description="Response type: chat, web_search, or error")
    reply: str = Field(..., description="AI generated response")
    sources: List[Source] = Field(default=[], description="Web search sources")
    quick_answer: Optional[str] = Field(default="", description="Quick answer from search")