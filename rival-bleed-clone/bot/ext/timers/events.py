from discord.ext.commands import (
    Cog,
    Context,
    command,
    group,
    CommandError,
    has_permissions,
)
from discord import Client, Embed, File, Member, User, Guild


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot
