from pydantic import BaseModel


class TranslationResponse(BaseModel):
    original: str
    translated: str
    source: str
    target: str
