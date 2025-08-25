from pydantic import BaseModel


class FeedbackSchema(BaseModel):
    log_id: int
    feedback_text: str


class MCPSchema(BaseModel):
    query: str
    context: dict = {}
    agent_id: int = 1


class RetrieveSchema(BaseModel):
    query: str
