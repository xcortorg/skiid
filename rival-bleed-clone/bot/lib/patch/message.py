from discord import Message
from typing import Optional, Dict, Any, List

class DiscordMessage(Message):
    def to_dict(self: Message) -> Optional[Dict[str, Any]]:
        