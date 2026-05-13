from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    message_count: int


class CachedChatRequest(BaseModel):
    provider: str = Field(..., description="'anthropic' or 'openai'")
    prompt_name: str = Field(..., description="Key from SYSTEM_PROMPTS dict")
    user_message: str = Field(..., min_length=1)


class CachedChatResponse(BaseModel):
    reply: str
    cached_tokens: int
    total_tokens: int
    cache_hit_rate: float
