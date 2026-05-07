from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str | None = None
    conversation_id: str | None = None
    system_prompt: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)


class AgentRunResponse(BaseModel):
    answer: str
    provider: str
    model: str
    usage: dict | None = None
    metadata: dict | None = None
