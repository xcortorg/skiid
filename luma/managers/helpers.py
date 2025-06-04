import asyncio
import io
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import colorgram
import discord
from discord.ext import commands
from discord_paginator import Paginator
from PIL import Image
from pydantic import BaseModel

from .persistent.views import ConfirmView

if TYPE_CHECKING:
    from .bot import Luma


class Reskin(BaseModel):
    username: str
    avatar_url: str


class Context(commands.Context):
    bot: "Luma"

    def find_role(self: "Context", name: str):
        return next((r for r in self.guild.roles[1:] if name in r.name), None)

    async def has_reskin(self: "Context") -> Optional[Reskin]:
        if not self.guild:
            return None

        check = await self.bot.db.fetchrow(
            "SELECT * FROM reskin WHERE user_id = $1", self.author.id
        )
        if not check:
            return None

        reskin = {
            "username": check.username or self.guild.me.name,
            "avatar_url": check.avatar_url or self.guild.me.display_avatar.url,
        }
        return Reskin(**reskin)

    async def send(self: "Context", *args, **kwargs) -> discord.Message:

        if self.interaction:
            try:
                await self.interaction.response.send_message(*args, **kwargs)
                return await self.interaction.original_response()
            except:
                return await self.interaction.followup.send(*args, **kwargs)

        if patch := kwargs.pop("patch", None):
            kwargs.pop("reference", None)

            if args:
                kwargs["content"] = args[0]

            return await patch.edit(**kwargs)
        else:

            reskin = await self.has_reskin()
            if not reskin:
                return await super().send(*args, **kwargs)
            else:
                try:
                    webhook = next(
                        (
                            w
                            for w in await self.channel.webhooks()
                            if w.user.id == self.bot.user.id
                        ),
                    )
                except StopIteration:
                    webhook = await self.channel.create_webhook(
                        name=f"{self.bot.user.name} - reskin"
                    )

                kwargs.update(
                    {
                        "username": reskin.username,
                        "avatar_url": reskin.avatar_url,
                        "wait": True,
                    }
                )
                kwargs.pop("delete_after", None)
                return await webhook.send(*args, **kwargs)

    async def reply(self: "Context", *args, **kwargs) -> discord.Message:
        if await self.has_reskin():
            return await self.send(*args, **kwargs)
        else:
            return await super().reply(*args, **kwargs)

    async def confirm(self: "Context", message: str) -> discord.Message:
        embed = discord.Embed(
            color=0x8AFF9A,
            description=f"<:check:1263809876132626452> {self.author.mention}: {message}",
        )
        return await self.reply(embed=embed)

    async def warn(self: "Context", message: str) -> discord.Message:
        embed = discord.Embed(
            color=0xFFC56E,
            description=f"<:warn:1263810465780465664> {self.author.mention}: {message}",
        )
        return await self.reply(embed=embed)

    async def error(self: "Context", message: str) -> discord.Message:
        embed = discord.Embed(
            color=0xFF6464, description=f":x: {self.author.mention}: {message}"
        )
        return await self.reply(embed=embed)

    async def confirm_view(self: "Context", message: str, button1, button2):
        embed = discord.Embed(color=self.bot.color, description=message)
        view = ConfirmView(self.author.id, button1, button2)
        await self.send(embed=embed, view=view)

    async def get_attachment(self: "Context"):
        if self.message.attachments:
            return self.message.attachments[0]
        if self.message.reference:
            if self.message.reference.resolved.attachments:
                return self.message.reference.resolved.attachments[0]

        mes = [m async for m in self.channel.history(limit=10) if m.attachments]
        if len(mes) > 0:
            return mes[0].attachments[0]

        return None

    async def dominant(self: "Context", url: Union[discord.Asset, str]) -> int:

        if isinstance(url, discord.Asset):
            url = url.read()

        img = Image.open(io.BytesIO(await url))
        img.thumbnail((32, 32))

        color = colorgram.extract(img, 1)
        return discord.Color.from_rgb(*list(color[0].rgb)).value

    async def paginator(
        self: "Context", embeds: List[Union[discord.Embed, str]]
    ) -> discord.Message:

        if len(embeds) == 1:
            if isinstance(embeds[0], discord.Embed):
                return await self.reply(embed=embeds[0])
            if isinstance(embeds[0], str):
                return await self.reply(embed=embeds[0])

        paginator = Paginator(self, embeds)
        paginator.add_button("prev", emoji="<:left:1076415738493018112>")
        paginator.add_button("delete", emoji="<:stop:1076415715449516083>")
        paginator.add_button("next", emoji="<:right:1076415697510477856>")
        await paginator.start()

    async def paginate(self: "Context", contents: List[str], title: str = None):
        items = [m for m in discord.utils.as_chunks(contents, 10)]
        embeds = [
            discord.Embed(
                color=self.bot.color,
                title=title,
                description=f"\n".join(
                    [f"`{(m.index(f)+1)+(items.index(m)*10)}`. {f}" for f in m]
                ),
            )
            for m in items
        ]

        return await self.paginator(embeds)


class Cache:
    def __init__(self):
        self.inventory: Dict[str, Any] = {}

    async def expire(self: "Cache", key: str, time: int):
        await asyncio.sleep(time)
        self.delete(key)

    async def add(self: "Cache", key: str, obj: Any, time: Optional[int] = None) -> Any:
        if self.get(key):
            self.inventory[key].append(key)
        else:
            self.inventory[key] = obj

            if time:
                await self.expire(key, time)

        return obj

    def get(self: "Cache", key: str) -> Any:
        return self.inventory.get(key)

    def delete(self: "Cache", key: str):
        return self.inventory.pop(key, None)


class LumaHelp(commands.HelpCommand):
    context: "Context"

    def __init__(self: "LumaHelp", **options):
        super().__init__(
            command_attrs={"aliases": ["h", "cmds", "commands"], "hidden": True},
            **options,
        )

    async def send_group_help(self: "LumaHelp", group: commands.Group):
        embeds = []
        i = 0
        bot = self.context.bot
        for command in group.commands:
            i += 1
            aliases = list(
                map(
                    lambda a: a.alias,
                    await self.context.bot.db.fetch(
                        "SELECT alias FROM aliases WHERE guild_id = $1 AND command = $2",
                        self.context.guild.id,
                        command.qualified_name,
                    ),
                )
            )
            aliases.extend(command.aliases)

            embeds.append(
                discord.Embed(
                    color=bot.color,
                    description=f"```{self.context.clean_prefix}{command.qualified_name} {' '.join([f'[{k}]' if v.required else f'<{k}>' for k, v in command.clean_params.items()])}\n{command.usage or ''}```\n{command.help}",
                )
                .set_author(name=bot.user.name, icon_url=bot.user.display_avatar.url)
                .set_footer(
                    text=f"Module: {command.cog_name} {f'• Aliases: {', '.join(map(lambda a: a, aliases))}' if aliases else ''} • Page: {i}/{len(group.commands)}"
                )
            )

        await self.context.paginator(embeds)

    async def send_command_help(self: "LumaHelp", command: commands.Command):
        aliases = (
            list(
                map(
                    lambda a: a.alias,
                    await self.context.bot.db.fetch(
                        "SELECT alias FROM aliases WHERE guild_id = $1 AND command = $2",
                        self.context.guild.id,
                        command.qualified_name,
                    ),
                )
            )
            or []
        )
        aliases.extend(command.aliases)

        embed = (
            discord.Embed(
                color=self.context.bot.color,
                description=f"```{self.context.clean_prefix}{command.qualified_name} {' '.join([f'[{k}]' if v.required else f'<{k}>' for k, v in command.clean_params.items()])}```\n{command.help}",
            )
            .set_author(
                name=self.context.author.name,
                icon_url=self.context.author.display_avatar.url,
            )
            .set_footer(
                text=f"Module: {command.cog_name} {f'• Aliases: {', '.join(map(lambda a: a, aliases))}' if aliases else ''}"
            )
        )
        await self.context.reply(embed=embed)

    async def send_bot_help(self, _):
        cogs = sorted(
            (
                cog
                for cog in self.context.bot.cogs.values()
                if cog.get_commands()
                and not cog.qualified_name in ["Jishaku", "Developer"]
            ),
            key=lambda c: c.qualified_name,
        )
        embeds = []
        embeds.append(
            discord.Embed(
                color=self.context.bot.color,
                description="Feature-rich, customizable & multi-purpose bot",
            ).set_author(
                name=self.context.author.name,
                icon_url=self.context.author.display_avatar.url,
            )
        )
        for cog in cogs:
            embeds.append(
                discord.Embed(
                    color=self.context.bot.color,
                    title=f"{cog.qualified_name} Commands",
                    description=f"**{', '.join(cmd.qualified_name + ('*' if isinstance(cmd, commands.Group) else '') for cmd in cog.get_commands())}**",
                )
                .set_author(
                    name=self.context.author.name,
                    icon_url=self.context.author.display_avatar.url,
                )
                .set_footer(text=f"{len(tuple(cog.walk_commands()))} commands")
            )
        return await self.context.paginator(embeds)
