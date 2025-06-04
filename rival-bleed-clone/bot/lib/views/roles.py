import discord
import re
from typing import Optional

STYLE_MAPPING = {
    "primary": {"aliases": ["prim", "p", "blue", "purple", "blurple"], "value": discord.ButtonStyle.primary},
    "secondary": {"aliases": ["second", "sec", "s", "grey", "gray", "g"], "value": discord.ButtonStyle.secondary},
    "success": {"aliases": ["good", "green"], "value": discord.ButtonStyle.success},
    "danger": {"aliases": ["bad", "red"], "value": discord.ButtonStyle.danger}
}

def to_style(value: str) -> Optional[discord.ButtonStyle]:
    if match := STYLE_MAPPING.get(value.lower()):
        return match[value]
    for val in STYLE_MAPPING.values():
        if value.lower() in val["aliases"]:
            return val["value"]
    return None


class ButtonRole(discord.ui.DynamicItem[discord.ui.Button], template=r"button:role:(?P<guild_id>[0-9]+):(?P<role_id>[0-9]+):(?P<message_id>[0-9]+)"):
    def __init__(self, guild_id: int, role_id: int, message_id: int, emoji: Optional[str] = None, label: Optional[str] = None, style: Optional[discord.ButtonStyle] = discord.ButtonStyle.primary):
        super().__init__(discord.ui.Button(label=label, style=style, emoji=emoji, custom_id=f"button:role:{guild_id}:{role_id}:{message_id}"))
        self.guild_id = guild_id
        self.role_id = role_id
        self.message_id = message_id
        self.emoji = emoji
        self.label = label
        self.style = style

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):  # type: ignore
        kwargs = {"guild_id": int(match["guild_id"]), "role_id": int(match["role_id"]), "message_id": int(match["message_id"])}
        return cls(**kwargs)

    async def assign_role(self, interaction: discord.Interaction, role: discord.Role):
        try:
            await interaction.user.add_roles(role, reason = "Button Role")
        except Exception:
            return await interaction.fail(f"i couldn't assign {role.mention} to you")
        return await interaction.success(f"successfully gave you {role.mention}")

    async def remove_role(self, interaction: discord.Interaction, role: discord.Role):
        try:
            await interaction.user.remove_roles(role, reason = "Button Role")
        except Exception:
            return await interaction.fail(f"i couldn't assign {role.mention} to you")
        return await interaction.success(f"successfully gave you {role.mention}")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        role = guild.get_role(self.role_id)
        if not role:
            return
        if not role.is_assignable():
            return
        if role.is_dangerous():
            return
        if role not in interaction.user.roles:
            return await self.assign_role(interaction, role)
        else:
            return await self.remove_role(interaction, role)

class ButtonRoleView(discord.ui.View):
    def __init__(self, bot: discord.Client, guild_id: int, message_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.message_id = message_id

    async def prepare(self):
        data = await self.bot.db.fetch("""SELECT * FROM button_roles WHERE guild_id = $1 AND message_id = $2 ORDER BY index DESC""", self.guild_id, self.message_id)
        for entry in data:
            kwargs = {"guild_id": self.guild_id, "role_id": entry.role_id, "message_id": entry.message_id, "emoji": entry.emoji, "label": entry.label, "style": to_style(entry.style)}
            self.add_item(ButtonRole(**kwargs))
        self.bot.add_view(self, message_id = self.message_id)


async def get_index(self, message: discord.Message) -> dict:
    data = {}
    i = 0
    for row in message.components:
        for child in row.children:
            i += 1
            data[i] = child
    return data
