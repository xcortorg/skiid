from typing import Optional, Dict, Union, Any
from pydantic import BaseModel
from discord import Embed
from discord.ui import View

class ScriptType(BaseModel):
    embed: Optional[Embed] = None
    content: Optional[str] = None
    view: Optional[View] = None

    class Config:
        arbitrary_types_allowed = True

