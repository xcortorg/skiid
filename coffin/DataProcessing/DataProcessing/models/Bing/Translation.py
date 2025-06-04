from pydantic import BaseModel


class Translation(BaseModel):
    original: str
    translated: str
    source: str
    target: str
