from pydantic import BaseModel


class SuggestionsOut(BaseModel):
    topic: str
    suggestions: list[str]
