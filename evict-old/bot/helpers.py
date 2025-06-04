import os
from typing import (Any, Callable, Coroutine, Dict, List, Mapping, Optional,
                    Sequence, Union)

import discord
from bot.ext import PaginatorView
from bot.managers.emojis import Colors, Emojis
from discord import Embed, Interaction, Message, SelectOption, utils
from discord.ext import commands
from discord.ext.commands import Command, Context, Group
from discord.ext.commands.cog import Cog
from discord.ui import Select, View


class EvictContext(Context):
    flags: Dict[str, Any] = {}

    async def getprefix(bot, message):

        if not message.guild:
            return ";"

        check = await bot.db.fetchrow(
            "SELECT * FROM selfprefix WHERE user_id = $1", message.author.id
        )
        if check:
            selfprefix = check["prefix"]

        res = await bot.db.fetchrow(
            "SELECT * FROM prefixes WHERE guild_id = $1", message.guild.id
        )
        if res:
            guildprefix = res["prefix"]

        else:
            guildprefix = ";"

        if not check and res:
            selfprefix = res["prefix"]
        elif not check and not res:
            selfprefix = ";"

        return guildprefix, selfprefix

    def find_role(self, name: str):

        for role in self.guild.roles:

            if role.name == "@everyone":
                continue

            if name.lower() in role.name.lower():
                return role
        return None

    async def success(self, message: str) -> discord.Message:
        return await self.reply(
            embed=discord.Embed(
                color=Colors.color,
                description=f"> {Emojis.approve} {self.author.mention}: {message}",
            )
        )

    async def neutral(self, message: str) -> discord.Message:
        return await self.reply(
            embed=discord.Embed(color=Colors.color, description=f"{message}")
        )

    async def error(self, message: str) -> discord.Message:
        return await self.reply(
            embed=discord.Embed(
                color=Colors.color,
                description=f"> {Emojis.deny} {self.author.mention}: {message}",
            )
        )

    async def warning(self, message: str) -> discord.Message:
        return await self.reply(
            embed=discord.Embed(
                color=Colors.error_color,
                description=f" > {Emojis.warn} {self.author.mention}: {message}",
            )
        )

    async def check(self):
        return await self.message.add_reaction(Emojis.approve)

    async def lastfm_message(self, message: str) -> discord.Message:
        return await self.reply(
            embed=discord.Embed(
                color=Colors.lastfm,
                description=f"> {Emojis.lastfm} {self.author.mention}: {message}",
            )
        )

    async def paginate(
        self,
        contents: List[str],
        title: str = None,
        author: dict = {"name": "", "icon_url": None},
    ):
        iterator = [m for m in utils.as_chunks(contents, 10)]
        embeds = [
            Embed(
                color=Colors.color,
                title=title,
                description="\n".join([f"{f}" for f in m]),
            ).set_author(**author)
            for m in iterator
        ]
        return await self.paginator(embeds)

    async def index(
        self,
        contents: List[str],
        title: str = None,
        author: dict = {"name": "", "icon_url": None},
    ):
        iterator = [m for m in utils.as_chunks(contents, 10)]
        embeds = [
            Embed(
                color=Colors.color,
                title=title,
                description="\n".join(
                    [f"`{(m.index(f)+1)+(iterator.index(m)*10)}.` {f}" for f in m]
                ),
            ).set_author(**author)
            for m in iterator
        ]
        return await self.paginator(embeds)

    async def create_pages(self):
        embeds = []

        i = 0

        for command in self.command.commands:

            commandname = (
                f"{str(command.parent)} {command.name}"
                if str(command.parent) != "None"
                else command.name
            )

            i += 1
            embeds.append(
                discord.Embed(
                    color=Colors.color,
                    title=f"{commandname}",
                    description=command.description,
                )
                .set_author(
                    name=self.author.name,
                    icon_url=self.author.display_avatar.url if not None else "",
                )
                .add_field(
                    name="aliases", value=", ".join(map(str, command.aliases)) or "none"
                )
                .add_field(name="permissions", value=command.brief or "any")
                .add_field(
                    name="usage",
                    value=f"```{commandname} {command.usage if command.usage else ''}```",
                    inline=False,
                )
                .set_footer(
                    text=f"module: {command.cog_name} ・ page {i}/{len(self.command.commands)}",
                    icon_url=self.author.display_avatar.url if not None else "",
                )
            )

        return await self.paginator(embeds)

    async def paginator(self, embeds: List[Union[Embed, str]]) -> Message:

        if len(embeds) == 1:
            return await self.reply(embed=embeds[0])
        view = PaginatorView(self, embeds)
        view.message = await self.reply(embed=embeds[0], view=view)

    async def create_pages(self):
        """Create pages for group commands"""
        return await self.send_help(self.command)

    async def reply(
        self,
        content: Optional[str] = None,
        *,
        embed: Optional[discord.Embed] = None,
        view: Optional[View] = None,
        mention_author: Optional[bool] = False,
        file: Optional[discord.File] = discord.utils.MISSING,
        files: Optional[Sequence[discord.File]] = discord.utils.MISSING,
    ) -> discord.Message:

        reskin = await self.bot.db.fetchrow(
            "SELECT * FROM reskin WHERE user_id = $1 AND toggled = $2",
            self.author.id,
            True,
        )
        if reskin != None and reskin["toggled"]:

            hook = await self.webhook(self.message.channel)

            if view == None:
                return await hook.send(
                    content=content,
                    embed=embed,
                    username=reskin["name"],
                    avatar_url=reskin["avatar"],
                    file=file,
                )

            return await hook.send(
                content=content,
                embed=embed,
                username=reskin["name"],
                avatar_url=reskin["avatar"],
                view=view,
                file=file,
            )
        return await self.send(
            content=content,
            embed=embed,
            reference=self.message,
            view=view,
            mention_author=mention_author,
            file=file,
        )

    async def send(
        self,
        content: Optional[str] = None,
        *,
        embed: Optional[discord.Embed] = None,
        view: Optional[View] = discord.utils.MISSING,
        mention_author: Optional[bool] = False,
        allowed_mentions: discord.AllowedMentions = discord.utils.MISSING,
        reference: Optional[
            Union[discord.Message, discord.MessageReference, discord.PartialMessage]
        ] = None,
        file: Optional[discord.File] = discord.utils.MISSING,
        files: Optional[Sequence[discord.File]] = discord.utils.MISSING,
    ) -> discord.Message:

        reskin = await self.bot.db.fetchrow(
            "SELECT * FROM reskin WHERE user_id = $1 AND toggled = $2",
            self.author.id,
            True,
        )
        if reskin != None and reskin["toggled"]:

            hook = await self.webhook(self.message.channel)
            return await hook.send(
                content=content,
                embed=embed,
                username=reskin["name"],
                avatar_url=reskin["avatar"],
                view=view,
                allowed_mentions=allowed_mentions,
                file=file,
            )

        return await self.channel.send(
            content=content,
            embed=embed,
            view=view,
            allowed_mentions=allowed_mentions,
            reference=reference,
            mention_author=mention_author,
            file=file,
        )

    async def webhook(self, channel) -> discord.Webhook:

        for webhook in await channel.webhooks():

            if webhook.user == self.me:
                return webhook

        return await channel.create_webhook(name="evict")

    async def cmdhelp(self):

        command = self.command
        commandname = (
            f"{str(command.parent)} {command.name}"
            if str(command.parent) != "None"
            else command.name
        )

        embed = discord.Embed(
            color=Colors.color, title=commandname, description=command.description
        )
        embed.set_author(
            name=self.author.name,
            icon_url=self.author.display_avatar.url if not None else "",
        )
        embed.add_field(
            name="aliases", value=", ".join(map(str, command.aliases)) or "none"
        )
        embed.add_field(name="permissions", value=command.brief or "any")
        embed.add_field(
            name="usage",
            value=f"```{commandname} {command.usage if command.usage else ''}```",
            inline=False,
        )
        embed.set_footer(
            text=f"module: {command.cog_name}",
            icon_url=self.author.display_avatar.url if not None else "",
        )

        await self.reply(embed=embed)


class HelpCommand(commands.HelpCommand):
    def __init__(self, **kwargs):
        self.ec_color = 0xCCCCFF
        super().__init__(**kwargs)

    def create_main_help_embed(self, ctx):
        embed = Embed(
            color=0xCCCCFF,
            title="Evict Command Menu",
            description="```\n"
            "[ ] = optional, < > = required\n"
            "Sub commands are indicated by an asterisk(*).\n```",
        )
        embed.add_field(
            name="Useful Links 🔗 ",
            value="**[Support](https://discord.gg/evict)**  • "
            "**[Website](https://evict.cc)**  • "
            "**[Invite](https://discord.com/oauth2/authorize?client_id=1203514684326805524&permissions=8&integration_type=0&scope=bot)**",
            inline=False,
        )

        return embed

    async def send_bot_help(
        self, mapping: Mapping[Cog | None, List[Command[Any, Callable[..., Any], Any]]]
    ) -> Coroutine[Any, Any, None]:

        bot = self.context.bot
        embed = self.create_main_help_embed(self.context)

        embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.set_footer(
            text="Select a category from the dropdown menu below"
        )  # Fixed footer

        # Log details about the cogs and their commands
        for cog in mapping.keys():
            cog_name = cog.qualified_name if cog else "No Category"
            print(f"Cog Name: {cog_name}, Commands: {len(mapping[cog])}")

        # Create a list of categories for the dropdown menu, excluding specific categories
        categories = [
            cog.qualified_name if cog else "No Category"
            for cog in mapping.keys()
            if cog
            and cog.qualified_name
            not in [
                "owner",
                "Jishaku",
                "Members",
                "api",
                "auth",
                "Messages",
                "Bot",
                "listeners",
                "task",
                "reacts",
                "Cog",
            ]
        ]

        # Log the resulting categories
        print("Categories after filtering:", categories)

        # Handle case where no categories are found
        if not categories:
            categories.append("General")  # Provide a default category if none are found

        # Ensure the number of categories does not exceed 25
        categories = categories[:25]

        # Create the Select menu
        select = Select(
            placeholder="Choose a category...",
            options=[
                SelectOption(label=category, value=category, description="")
                for category in categories
            ],
        )

        async def select_callback(interaction: Interaction):
            selected_category = interaction.data["values"][0]
            selected_cog = next(
                (
                    cog
                    for cog in mapping.keys()
                    if (cog and cog.qualified_name == selected_category)
                    or (not cog and selected_category == "No Category")
                ),
                None,
            )

            if selected_cog is not None:
                commands = mapping[selected_cog]
                command_list = ", ".join(
                    [
                        (
                            f"{command.name}*"
                            if isinstance(command, Group)
                            else f"{command.name}"
                        )
                        for command in commands
                    ]
                )
            else:
                command_list = "No commands available"

            embed = Embed(
                color=0x7291DF,
                title=f"Category: {selected_category}",
                description=f"**```\n{command_list}\n```**",
            )
            embed.set_author(
                name="Evict Command Menu", icon_url=bot.user.display_avatar.url
            )
            embed.set_footer(
                text=(
                    f"{len(commands)} command{'s' if len(commands) != 1 else ''}"
                    if selected_cog
                    else "No commands"
                )
            )

            await interaction.response.edit_message(embed=embed, view=view)

        select.callback = select_callback

        # Create a View and add the Select menu to it
        view = View()
        view.add_item(select)

        await self.context.reply(embed=embed, view=view)

    def get_desc(self, c: Command | Group) -> str:
        if c.help != None:
            return c.help.capitalize()
        return "no description"

    async def send_command_help(self, command: commands.Command):

        commandname = (
            f"{str(command.parent)} {command.name}"
            if str(command.parent) != "None"
            else command.name
        )

        embed = discord.Embed(
            color=self.ec_color, title=commandname, description=command.description
        )
        embed.set_author(
            name=self.context.author.name,
            icon_url=self.context.author.display_avatar.url if not None else "",
        )
        embed.add_field(
            name="aliases", value=", ".join(map(str, command.aliases)) or "none"
        )
        embed.add_field(name="permissions", value=command.brief or "any")
        embed.add_field(
            name="usage",
            value=f"```{commandname} {command.usage if command.usage else ''}```",
            inline=False,
        )
        embed.set_footer(
            text=f"module: {command.cog_name}",
            icon_url=self.context.author.display_avatar.url if not None else "",
        )

        await self.context.reply(embed=embed)

    async def send_group_help(self, group: commands.Group):

        ctx = self.context
        embeds = []
        i = 0

        for command in group.commands:
            commandname = (
                f"{str(command.parent)} {command.name}"
                if str(command.parent) != "None"
                else command.name
            )
            i += 1

            embeds.append(
                discord.Embed(
                    color=self.ec_color,
                    title=f"{commandname}",
                    description=command.description,
                )
                .set_author(
                    name=ctx.author.name,
                    icon_url=ctx.author.display_avatar.url if not None else "",
                )
                .add_field(
                    name="aliases", value=", ".join(map(str, command.aliases)) or "none"
                )
                .add_field(name="permissions", value=command.brief or "any")
                .add_field(
                    name="usage",
                    value=f"```{commandname} {command.usage if command.usage else ''}```",
                    inline=False,
                )
                .set_footer(
                    text=f"module: {command.cog_name} ・ page {i}/{len(group.commands)}",
                    icon_url=ctx.author.display_avatar.url if not None else "",
                )
            )

        return await self.context.paginator(embeds)


class StartUp:

    async def startup(bot):
        await bot.wait_until_ready()

    async def loadcogs(self):

        for file in os.listdir("./events"):
            if file.endswith(".py"):
                try:
                    await self.load_extension(f"events.{file[:-3]}")
                    print(f"Loaded plugin {file[:-3]}".lower())
                except Exception as e:
                    print("failed to load %s %s".lower(), file[:-3], e)

        for fil in os.listdir("./cogs"):
            if fil.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{fil[:-3]}")
                    print(f"Loaded plugin {fil[:-3]}".lower())
                except Exception as e:
                    print("failed to load %s %s".lower(), fil[:-3], e)
