from pydantic import BaseModel


class Callback(BaseModel):
    code: str
    state: str
