import contextlib
import re
import json
from discord import (
    AuditLogAction,
    AuditLogEntry,
)
import copy
import asyncio
import aiohttp
import typing
import unicodedata
from dataclasses import dataclass
from datetime import timedelta, datetime  # type: ignore
from base64 import b64decode  # type: ignore
from io import StringIO
from typing import Optional, Union, Dict, List  # type: ignore
from tool.important.subclasses.parser import Script, EmbedError  # type: ignore
from io import BytesIO
from asyncio import gather, sleep
from discord.ext.commands import (
    Cog,
    bot_has_permissions,
    group as Group,
    has_permissions,
)
from discord import (
    Embed,
    Message,
    TextChannel,  # type: ignore  # noqa: F401
)
from tool.views import EmojiConfirmation, Confirmation  # type: ignore
from tool.aliases import AliasConverter  # type: ignore
from discord.ext.commands.errors import CommandError
from tool.important.database import query_limit  # type: ignore
from discord.errors import HTTPException  # type: ignore
import discord
from discord.ext import commands
from discord.ext.commands.converter import PartialEmojiConverter
from tool.important.subclasses.color import ColorConverter  # type: ignore
from tool.important import Context, is_donator  # type: ignore
from tool.important.subclasses.command import (  # type: ignore
    Member,
    Role,
    Sticker,
    Attachment,
    Image,
    Stickers,
    FakePermissionConverter,
    Argument,
    Emoji,
)
from tuuid import tuuid
from loguru import logger
from pydantic import BaseModel
from loguru import logger as log
from tool.greed import cache
from tool.views import to_style, ButtonRoleView
from tool.worker import lazy, compute_many
from discord.ext.commands.flags import Flag, FlagConverter
from discord.ext.commands import Context as OriginalContext


class AutoresponderFlags(FlagConverter):
    strict: bool = False
    reply: bool = False


class StyleConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        if style := to_style(argument.lower()):
            return style
        raise CommandError("**Style** must be one of `blurple`, `gray`, `green`, `red`")


async def configure_reskin(
    bot: discord.Client, channel: discord.TextChannel, webhooks: dict
):
    if not channel.permissions_for(channel.guild.me).manage_webhooks:
        return False

    if str(channel.id) in webhooks:  # We have to use str() because dicts are stupid
        try:
            await bot.fetch_webhook(webhooks[str(channel.id)])
        except:
            del webhooks[str(channel.id)]
            await cache.delete_many(
                f"reskin:channel:{channel.guild.id}:{channel.id}",
                f"reskin:webhook:{channel.id}",
                f"reskin:guild:channel:{channel.guild.id}:{channel.id}",
            )
        else:
            return True

    try:
        webhook = await asyncio.wait_for(
            channel.create_webhook(name="reskin"),
            timeout=5,
        )
    except:
        return False
    else:
        webhooks[str(channel.id)] = webhook.id
        try:
            await cache.delete(f"reskin:channel:{channel.guild.id}:{channel.id}")
            await cache.set(f"reskin:webhook:{channel.id}", webhook, expire="1h")
            #            await cach.delete(f"reskin:guild:channel:{channel.guild.id}:{channel.id}")
            await cache.set(f"reskin:webhook:{channel.id}", webhook, expire="1h")
        except:
            pass
        return webhook


class EmbedConverter(commands.Converter):
    async def convert(self, ctx: Context, code: str):
        c = code
        c = c.replace("{level}", "")
        logger.info(c)
        try:
            s = Script(c, ctx.author)
            await s.compile()
        except Exception as e:
            raise e
        return code


class GuildSticker(BaseModel):
    name: str
    description: str
    tags: str


if typing.TYPE_CHECKING:
    from tool.greed import Greed  # type: ignore

EMOJI_REGEX = re.compile(
    r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
)

DEFAULT_EMOJIS = re.compile(
    r"[\U0001F300-\U0001F5FF]|[\U0001F600-\U0001F64F]|[\U0001F680-\U0001F6FF]|[\U0001F700-\U0001F77F]|[\U0001F780-\U0001F7FF]|[\U0001F800-\U0001F8FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FA6F]|[\U0001FA70-\U0001FAFF]|[\U00002702-\U000027B0]|[\U000024C2-\U0001F251]|[\U0001F910-\U0001F9C0]|[\U0001F3A0-\U0001F3FF]"
)


@dataclass
class EmojiEntry:
    name: str
    id: int
    url: str
    animated: bool


class Emojis(commands.Converter):
    async def convert(
        self,
        ctx: Context,
        argument: str,
        ref: Optional[bool] = False,
        multiple: Optional[bool] = False,
    ):
        if isinstance(argument, list):
            return argument
        matches = None
        emojis = []
        if ctx.message.reference and ref:
            if ctx.message.reference.cached_message:
                message = ctx.message.reference.cached_message
            else:
                message = await ctx.channel.fetch_message(
                    ctx.message.reference.message_id
                )
            if _matches := EMOJI_REGEX.findall(message.content):
                matches = _matches
            else:
                if len(message.embeds) > 0:
                    _m = EMOJI_REGEX.findall(message.embeds[0].description or "")
                    if _m:
                        matches = _m
                    else:
                        if len(message.embeds[0].fields) > 0:
                            for f in message.embeds[0].fields:
                                if match := EMOJI_REGEX.findall(f.value):
                                    if not multiple:
                                        matches = match
                                        break
                                    else:
                                        string = "".join(
                                            f" {m.value}"
                                            for m in message.embeds[0].fields
                                        )
                                        matches = EMOJI_REGEX.findall(string)
                                        break
        else:
            matches = EMOJI_REGEX.findall(argument)
        for e in matches:
            emojis.append(
                await PartialEmojiConverter().convert(ctx, f"<{e[0]}:{e[1]}:{e[2]}>")
            )
        defaults = DEFAULT_EMOJIS.findall(argument)
        if len(defaults) > 0:
            emojis.extend(defaults)
        return emojis


class ReactionRoleConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        argument = argument.replace("  ", " ")
        message = None
        emoji = None
        role = None
        splitting_char = ""
        if "," in argument:
            splitting_char += ","
        else:
            splitting_char += " "
        if argument.count(splitting_char) == 1:
            emoji, role = argument.split(splitting_char, 1)
        elif argument.count(splitting_char) == 2:
            message, emoji, role = argument.split(splitting_char, 2)
        else:
            raise CommandError("Please include a message, emoji, and role")
        if not message:
            if ctx.message.reference:
                message = ctx.message.reference.jump_url
        if message:
            message = await commands.MessageConverter().convert(ctx, message.strip())
        if not DEFAULT_EMOJIS.findall(emoji):
            emoji = await PartialEmojiConverter().convert(ctx, emoji.strip())
        else:
            emoji = emoji.replace(" ", "")
        role = await Role().convert(ctx, role)
        role = role[0]
        if not role:
            raise CommandError("Missing required argument **Role**")
        if not emoji:
            raise CommandError("Missing required argument **Emoji**")
        if not message:
            raise CommandError("Missing required argument **Message**")
        return {"message": message, "emoji": emoji, "role": role}


def embed_creator(
    text: str,
    num: int = 1980,
    /,
    *,
    title: str = "",
    prefix: str = "",
    suffix: str = "",
    color: int = 0xB1AAD8,
) -> tuple:
    """
    Creates a list of Embed objects, each containing a portion of the input text.

    Parameters:
        text (str): The input text to be divided into portions.
        num (int, optional): The number of characters in each portion. Defaults to 1980.
        title (str, optional): The title of the Embed objects. Defaults to "".
        prefix (str, optional): The prefix to be added to each portion of the text. Defaults to "".
        suffix (str, optional): The suffix to be added to each portion of the text. Defaults to "".
        color (int, optional): The color of the Embed objects. Defaults to 0xb1aad8.

    Returns:
        tuple: A tuple of Embed objects, each containing a portion of the input text.
    """

    return tuple(
        Embed(
            title=title,
            description=prefix + (text[i : i + num]) + suffix,
            color=color if color is not None else 0x2F3136,
        )
        for i in range(0, len(text), num)
    )


def text_creator(
    text: str, num: int = 1980, /, *, prefix: str = "", suffix: str = ""
) -> tuple:
    """
    Generates a tuple of text segments from a given text string, with a specified
    maximum segment length and optional prefix and suffix.

    Parameters:
        text (str): The text string to generate segments from.
        num (int, optional): The maximum length of each segment. Defaults to 1980.
        prefix (str, optional): The prefix to add to each segment. Defaults to "".
        suffix (str, optional): The suffix to add to each segment. Defaults to "".

    Returns:
        tuple: A tuple containing the generated text segments.
    """

    return tuple(
        prefix + (text[i : i + num]) + suffix for i in range(0, len(text), num)
    )


def guild_has_vanity(guild: discord.Guild):
    if guild.vanity_url_code:
        return True
    else:
        return False


TUPLE = ()
SET = ()
DICT = {}


async def get_file_ext(url: str) -> str:
    file_ext1 = url.split("/")[-1].split(".")[1]
    if "?" in file_ext1:
        return file_ext1.split("?")[0]
    else:
        return file_ext1[:3]


async def get_asset(url: str, name: str = None):
    if name is None:
        name = str(tuuid())
    if "discord" not in url:
        url = f"https://proxy.rival.rocks?url={url}"
    ext = await get_file_ext(url)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            logger.info(f"asset {url} got a response of {response.status}")
            binary = await response.read()
    return discord.File(fp=BytesIO(binary), filename=f"{name}.{ext}")


async def get_raw_asset(url: str):
    if "discord" not in url:
        url = f"https://proxy.rival.rocks?url={url}"
    await get_file_ext(url)  # type: ignore
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            logger.info(f"asset {url} got a response of {response.status}")
            binary = await response.read()
    return binary


def multi_replace(text: str, to_replace: Dict[str, str], once: bool = False) -> str:
    """
    Replaces multiple occurrences of substrings in a given text.

    Parameters:
        text (str): The original text in which the replacements will be made.
        to_replace (Dict[str, str]): A dictionary containing the substrings to replace
            as keys and their corresponding replacement strings as values.
        once (bool, optional): If set to True, only the first occurrence of each
            substring will be replaced. Defaults to False.

    Returns:
        str: The modified text after performing the replacements.
    """

    for r1, r2 in to_replace.items():
        if r1 in text:
            if once:
                text = text.replace(str(r1), str(r2), 1)
            else:
                text = text.replace(str(r1), str(r2))

    return text


def is_unicode(emoji: str) -> bool:
    with contextlib.suppress(Exception):
        unicodedata.name(emoji)
        return True

    return False


def check_guild_boost_level():
    async def predicate(ctx: Context) -> bool:
        log.info(ctx.command.qualified_name)
        if ctx.command.qualified_name == "help":
            return True
        if not ctx.author.premium_since and not ctx.author.guild.owner:
            raise CommandError("You need to be a **Booster** to use this command")
        if ctx.guild:
            if ctx.guild.premium_tier >= 2:
                return True
            else:
                raise CommandError(
                    f"This guild is not **level 3 ** boosted\n > (**Current level: ** `{ctx.guild.premium_tier}`)"
                )

    return commands.check(predicate)


def check_br_status():
    async def predicate(ctx: Context) -> bool:
        if ctx.command.qualified_name == "help":
            return True
        if ctx.guild.premium_tier < 2:
            raise CommandError(
                f"This guild is **not ** currently level ** {ctx.guild.premium_tier} ** and must be ** level 2 ** to use this."
            )
        if not await ctx.bot.db.fetchval(
            "SELECT status FROM br_status WHERE guild_id = $1", ctx.guild.id
        ):
            raise CommandError("**Booster roles** are **not** enabled in this guild.")
        if not ctx.author.premium_since and ctx.author.id not in ctx.bot.owner_ids:
            raise CommandError("You need to be a **Booster** to use this command.")
        return True

    return commands.check(predicate)


class Servers(Cog):
    def __init__(self, bot: "Greed") -> None:
        self.bot = bot
        self.bot.loop.create_task(self.ensure_table())

    async def get_int(self, string: str):
        t = ""
        for s in string:
            try:
                d = int(s)
                t += f"{d}"
            except Exception:
                pass
        return t

    async def get_timeframe(self, timeframe: str):
        import humanfriendly
        from datetime import timedelta

        try:
            converted = humanfriendly.parse_timespan(timeframe)
        except Exception:
            converted = humanfriendly.parse_timespan(
                f"{await self.get_int(timeframe)} hours"
            )
        time = datetime.now() + timedelta(seconds=converted)
        return time

    async def get_emojis(self, string: str) -> Optional[EmojiEntry]:
        data = re.findall(r"<(a?):([a-zA-Z0-9_]+):([0-9]+)>", string)
        if data:
            for _a, emoji_name, emoji_id in data:
                animated = _a == "a"
                animate = False
                if animated:
                    animate = True
                    url = "https://cdn.discordapp.com/emojis/" + emoji_id + ".gif"
                else:
                    url = "https://cdn.discordapp.com/emojis/" + emoji_id + ".png"
                return EmojiEntry(
                    name=emoji_name, url=url, id=emoji_id, animated=animate
                )

    async def update_settings(self, guild_id: int, message: str, enabled: bool):
        """Update the join DM settings in the database."""
        # Check if the guild already has settings
        existing_settings = await self.bot.db.fetch(
            "SELECT * FROM join_dm_settings WHERE guild_id = $1", guild_id
        )

        if existing_settings:
            # Update existing settings
            query = """
            UPDATE join_dm_settings
            SET message = $1, enabled = $2
            WHERE guild_id = $3
            """
            await self.bot.db.execute(query, message, enabled, guild_id)
        else:
            # Insert new settings for the guild
            query = """
            INSERT INTO join_dm_settings (guild_id, message, enabled)
            VALUES ($1, $2, $3)
            """
            await self.bot.db.execute(query, guild_id, message, enabled)

    async def ensure_table(self):
        """Ensure the join_dm_settings table exists and is structured properly."""
        try:
            # Check if the table already exists before trying to create it
            table_check_query = """
            SELECT to_regclass('public.join_dm_settings');
            """
            result = await self.bot.db.fetchval(table_check_query)

            if result is None:
                # Create the join_dm_settings table if it doesn't exist
                create_table_query = """
                CREATE TABLE IF NOT EXISTS join_dm_settings (
                    guild_id BIGINT PRIMARY KEY,
                    message TEXT,
                    enabled BOOLEAN DEFAULT TRUE
                );
                """
                await self.bot.db.execute(create_table_query)

            # Ensure the necessary columns exist (message and enabled)
            alter_table_query = """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'join_dm_settings' AND column_name = 'message') THEN
                    ALTER TABLE join_dm_settings ADD COLUMN message TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'join_dm_settings' AND column_name = 'enabled') THEN
                    ALTER TABLE join_dm_settings ADD COLUMN enabled BOOLEAN DEFAULT TRUE;
                END IF;
            END;
            $$;
            """
            await self.bot.db.execute(alter_table_query)

        except Exception as e:
            print(f"Error ensuring table: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Send the join DM to a member when they join the server, if enabled."""
        # Get the settings for the server
        settings = await self.bot.db.fetch(
            "SELECT * FROM join_dm_settings WHERE guild_id = $1", member.guild.id
        )

        # If no settings are found or DM is disabled, return
        if not settings or not settings.get("enabled"):
            return

        # Get the saved join DM message
        message = settings.get("message", "")
        if message:
            try:
                # Try sending the message to the member
                await member.send(message)
            except Exception as e:
                print(f"Failed to send join DM to {member.name}: {e}")

    @commands.Cog.listener("on_raw_message_delete")
    async def rr_delete(self, message):
        await self.bot.db.execute(
            """DELETE FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3""",
            message.guild_id,
            message.channel_id,
            message.message_id,
        )

    async def check_notification_channel(
        self, ctx: Context, role: Optional[Role] = None
    ):
        data = await self.bot.db.fetchrow(
            """SELECT * FROM notifications WHERE guild_id = $1""", ctx.guild.id
        )
        if not data:
            return False
        role = role or data.get("role_id")
        channels = [
            ctx.guild.get_channel(int(r))
            for r in json.loads(data.channels or "[]")
            if ctx.guild.get_channel(int(r))
        ]
        if not channels:
            return False
        if isinstance(role, int):
            role = ctx.guild.get_role(role)
        if not role:
            return False
        if channels and role:
            for c in channels:
                if role not in c.overwrites:
                    await c.set_permissions(
                        role,
                        overwrite=discord.PermissionOverwrite(view_channel=False),
                        reason="notifications channel setup",
                    )
            return True

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        if message.mention_everyone:
            data = await self.bot.db.fetchrow(
                """SELECT channels, message FROM notifications WHERE guild_id = $1""",
                message.guild.id,
            )
            if data:
                if data.channels:
                    channels = (
                        data.channels
                        if isinstance(data.channels, list)
                        else [data.channels]
                    )
                    if message.channel.id in channels:
                        return await self.bot.send_embed(
                            destination=message.channel,
                            code=data.message,
                            user=message.author,
                        )
                else:
                    logger.error("No channels found in the database.")

    @commands.group(
        name="levels",
        brief="setup level roles and autoboard",
        invoke_without_command=True,
        aliases=["lvls"],
    )
    async def levels(self, ctx: Context):
        return await ctx.send_help()

    async def assign_level_role(self, ctx: Context, role: Role, level: int):
        xp_task = self.bot.levels.get_xp(level)
        xp = await xp_task.compute()
        rows = await self.bot.db.fetch(
            """SELECT user_id FROM text_levels WHERE guild_id = $1 AND xp >= $2""",
            ctx.guild.id,
            xp,
        )
        for row in rows:
            if member := ctx.guild.get_member(row.user_id):
                await member.add_roles(role, reason="Level Role")

    @levels.command(
        name="channel",
        brief="set a channel for level award messages",
        example=",levels channel #txt",
        usage=",levels channel <channel>",
    )
    @commands.has_permissions(manage_guild=True)
    async def levels_channel(self, ctx: Context, *, channel: TextChannel):
        data = json.loads(
            await self.bot.db.fetchval(
                """SELECT award_message FROM text_level_settings WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or "{}"
        )
        data["channel_id"] = channel.id
        await self.bot.db.execute(
            """INSERT INTO text_level_settings (guild_id, award_message) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET award_message = excluded.award_message""",
            ctx.guild.id,
            json.dumps(data),
        )
        return await ctx.success(
            f"**Messages for leveling** will now be sent to {channel.mention}"
        )

    @levels.command(name="enable", brief="enable leveling")
    @commands.has_permissions(manage_guild=True)
    async def levels_enable(self, ctx: Context):
        await self.bot.db.execute(
            """INSERT INTO text_level_settings (guild_id) VALUES($1) ON CONFLICT(guild_id) DO NOTHING""",
            ctx.guild.id,
        )
        return await ctx.success("successfully enabled leveling")

    @levels.command(name="disable", brief="disable leveling")
    @commands.has_permissions(manage_guild=True)
    async def levels_disable(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM text_level_settings WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("successfully disabled leveling")

    @levels.group(
        name="message",
        brief="set a message for leveling up",
        example=",levels message {embed}{description: congrats {user.mention} for hitting level {level}}",
        usage=",levels message <message>",
        invoke_without_command=True,
        aliases=["msg", "m"],
    )
    @commands.has_permissions(manage_guild=True)
    async def levels_message(self, ctx: Context, *, message: EmbedConverter):
        data = json.loads(
            await self.bot.db.fetchval(
                """SELECT award_message FROM text_level_settings WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or "{}"
        )
        data["message"] = message
        await self.bot.db.execute(
            """INSERT INTO text_level_settings (guild_id, award_message) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET award_message = excluded.award_message""",
            ctx.guild.id,
            json.dumps(data),
        )
        return await ctx.success(
            "The **award message** for leveling has been **applied**"
        )

    @levels_message.command(
        name="test",
        brief="test your level up message",
        aliases=["debug", "t", "try", "view"],
    )
    @commands.has_permissions(manage_guild=True)
    async def levels_message_test(self, ctx: Context):
        data = await self.bot.db.fetchval(
            """SELECT award_message FROM text_level_settings WHERE guild_id = $1""",
            ctx.guild.id,
        )
        if not data:
            return await ctx.fail("You **have not** created a **level message**")
        data = json.loads(data)
        if not data.get("channel_id"):
            return await ctx.fail("You **have not** created a **level channel**")
        if not data.get("message"):
            return await ctx.fail("You **have not** created a **level message**")
        self.bot.dispatch("text_level_up", ctx.guild, ctx.author, 1)
        return await ctx.success("Your created **level message** has been sent")

    @levels_message.command(
        name="reset", brief="reset your level message configuration", aliases=["clear"]
    )
    @commands.has_permissions(manage_guild=True)
    async def levels_message_reset(self, ctx: Context):
        try:
            await self.bot.db.execute(
                """UPDATE text_level_settings SET award_message = NULL WHERE guild_id = $1""",
                ctx.guild.id,
            )
        except Exception:
            pass
        return await ctx.success("Your **level message** has been **cleared**")

    @levels.group(
        name="role",
        brief="add level roles to be awarded",
        usage=",levels role <level> <role>",
        example=",levels role 5 level-5",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_guild=True)
    async def levels_role(self, ctx: Context, level: int, *, role: Role):
        role = role[0]
        data = json.loads(
            await self.bot.db.fetchval(
                """SELECT roles FROM text_level_settings WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or "[]"
        )
        if [level, role.id] not in data:
            data.append([level, role.id])
            await self.bot.db.execute(
                """INSERT INTO text_level_settings (guild_id, roles) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET roles = excluded.roles""",
                ctx.guild.id,
                json.dumps(data),
            )
            await self.assign_level_role(ctx, role, level)
        return await ctx.success(
            f"{role.mention} will now be **given to users** who reach **level {level}**"
        )

    @levels_role.command(
        name="remove",
        brief="remove a level role",
        usage=",levels role remove <level> <role>",
        example=",levels role remove 5 level-5",
        aliases=["r", "rem", "del", "delete"],
    )
    @commands.has_permissions(manage_guild=True)
    async def levels_role_remove(self, ctx: Context, level: int):
        data = json.loads(
            await self.bot.db.fetchval(
                """SELECT roles FROM text_level_settings WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or "[]"
        )
        new = []
        for d in data:
            if d[0] != level:
                new.append(d)
        
        await self.bot.db.execute(
            """INSERT INTO text_level_settings (guild_id, roles) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET roles = excluded.roles""",
            ctx.guild.id,
            json.dumps(new),
        )
        return await ctx.success(
            f"All **reward roles has been cleared** for **level {level}**"
        )

    @levels.command(
        name="list", brief="show all level rewards", aliases=["show", "l", "ls", "s"]
    )
    @commands.has_permissions(manage_guild=True)
    async def levels_list(self, ctx: Context):
        rows = []
        data = json.loads(
            await self.bot.db.fetchval(
                """SELECT roles FROM text_level_settings WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or "[]"
        )
        ii = 0
        for i, d in enumerate(data, start=1):
            role = ctx.guild.get_role(d[1])
            if not role:
                ii += 1
                continue
            level = d[0]
            rows.append(f"`{i - ii}` {role.mention} - `{level}`")
        if len(rows) == 0:
            return await ctx.fail("You have **not set any reward levels**")
        embed = Embed(color=self.bot.color, title="Level Rewards")
        return await self.bot.dummy_paginator(ctx, embed, rows)

    @levels.command(name="setup", brief="setup leveling")
    @commands.has_permissions(manage_guild=True)
    async def levels_setup(self, ctx: Context):
        await self.bot.db.execute(
            """INSERT INTO text_level_settings (guild_id) VALUES($1) ON CONFLICT(guild_id) DO NOTHING""",
            ctx.guild.id,
        )
        return await ctx.success("**Leveling** has been **enabled**")

    @commands.group(
        name="notifications",
        aliases=["notis", "noti", "notification"],
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_guild=True)
    async def notification(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @notification.command(
        name="reset", aliases=["clear"], brief="clear your notification channel setup"
    )
    @commands.has_permissions(manage_guild=True)
    async def notification_reset(self, ctx: Context):
        data = await self.bot.db.fetchrow(
            """SELECT channels, role_id FROM notifications WHERE guild_id = $1""",
            ctx.guild.id,
        )
        if data:
            role = ctx.guild.get_role(data.role_id)
        else:
            return await ctx.fail("there is no current notification channel setup")

        if role:
            await role.delete(reason=f"notification channel reset by {str(ctx.author)}")
        await self.bot.db.execute(
            """DELETE FROM notifications WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("successfully cleared notification channels")

    @notification.group(name="channel", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def notification_channel(self, ctx: Context):
        return await ctx.send_help()

    @notification_channel.command(
        name="add", brief="Set a channel for notifications to be optionally disabled"
    )
    @commands.has_permissions(manage_guild=True)
    async def notification_channel_add(self, ctx: Context, *, channel: TextChannel):
        data = await self.bot.db.fetchrow(
            """SELECT channels, role_id FROM notifications WHERE guild_id = $1""",
            ctx.guild.id,
        )
        if data:
            new_data = json.loads(data.channels) if data.channels else []
            role = ctx.guild.get_role(data.role_id)
        else:
            new_data = []
            role = None

        new_data.append(channel.id)
        await self.bot.db.execute(
            """INSERT INTO notifications (guild_id, channels) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET channels = excluded.channels""",
            ctx.guild.id,
            json.dumps(new_data),
        )
        await self.check_notification_channel(ctx)
        return await ctx.success(
            f"**Added** {channel.mention} as a notification channel"
        )

    @notification_channel.command(
        name="remove", brief="Remove a channel for notifications"
    )
    @commands.has_permissions(manage_guild=True)
    async def notification_channel_remove(self, ctx: Context, *, channel: TextChannel):
        data = await self.bot.db.fetchrow(
            """SELECT channels, role_id FROM notifications WHERE guild_id = $1""",
            ctx.guild.id,
        )
        if data and data.channels:
            new_data = json.loads(data.channels)
            role = ctx.guild.get_role(data.role_id)
        else:
            return await ctx.fail("there are no notifications channel setup")

        if role:
            await channel.set_permissions(
                role,
                overwrite=None,
                reason="Disabled notifications role for this channel",
            )
        new_data.remove(channel.id)
        await self.bot.db.execute(
            """INSERT INTO notifications (guild_id, channels) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET channels = excluded.channels""",
            ctx.guild.id,
            json.dumps(new_data),
        )
        await self.check_notification_channel(ctx)
        return await ctx.success(
            f"**Removed** {channel.mention} from being a notification channel"
        )

    @notification_channel.command(
        name="list", brief="List all channels notifications option has been enabled for"
    )
    @commands.has_permissions(manage_guild=True)
    async def notification_channel_list(self, ctx: Context):
        embed = discord.Embed(color=self.bot.color, title="Notification Channels")
        data = await self.bot.db.fetchval(
            """SELECT channels FROM notifications WHERE guild_id = $1""", ctx.guild.id
        )
        if not data:
            return await ctx.fail("**Notification channels** are **not** setup")

        channels = json.loads(data) if data else []
        channels = [
            ctx.guild.get_channel(d) for d in channels if ctx.guild.get_channel(d)
        ]
        rows = [
            f"`{i}` {channel.mention}" for i, channel in enumerate(channels, start=1)
        ]
        return await self.bot.dummy_paginator(ctx, embed, rows)

    @notification.command(
        name="setup",
        brief="Create a role to be used to disable @everyone mentions for a channel",
    )
    @commands.has_permissions(manage_guild=True)
    async def notification_setup(self, ctx: Context):
        role = await ctx.guild.create_role(
            name="no-pings", reason=f"notifications setup used by {str(ctx.author)}"
        )
        await self.bot.db.execute(
            """INSERT INTO notifications (guild_id, role_id) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id""",
            ctx.guild.id,
            role.id,
        )
        await self.check_notification_channel(ctx, role)
        return await ctx.success(f"**Notification role** has been **created**")

    @notification.command(
        name="responder",
        brief="set a responder message when an @everyone is sent into a notification channel",
        example=",notifications responder ,dis to disable pings",
    )
    @commands.has_permissions(manage_guild=True)
    async def notification_responder(self, ctx: Context, *, embed_code: str):
        await self.bot.db.execute(
            """INSERT INTO notifications (guild_id, message) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET message = excluded.message""",
            ctx.guild.id,
            embed_code,
        )
        return await ctx.success(f"**Response message** has been set")

    @notification.command(
        name="command",
        brief="enable or disable the ping disable command",
        example=",notifications command true",
    )
    @commands.has_permissions(manage_guild=True)
    async def notification_command(self, ctx: Context, state: bool):
        await self.bot.db.execute(
            """INSERT INTO notifications (guild_id, command) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET command = excluded.command""",
            ctx.guild.id,
            state,
        )
        state_message = "Enabled" if state else "Disabled"
        return await ctx.success(
            f"**{state_message}** the &&notifications disable** command"
        )

    @commands.command(
        name="disable", aliases=["dis"], brief="disable pings for a channel"
    )
    async def disable(self, ctx: Context):
        data = await self.bot.db.fetchrow(
            """SELECT * FROM notifications WHERE guild_id = $1""", ctx.guild.id
        )
        if not data:
            return await ctx.fail("**Notification** haven't been setup yet")
        role = ctx.guild.get_role(data.role_id)
        if not role:
            return await ctx.fail("**Notification role** has **not** been created")
        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
            state = False
        else:
            await ctx.author.add_roles(role)
            state = True
        msg = "**Disabled**" if state else "**Enabled**"
        return await ctx.success(f"{msg} notifications")

    @commands.group(
        name="paginator",
        invoke_without_command=True,
        aliases=["pag"],
        brief="Set up multi page embeds for your server",
        example=",paginator {embed_code}",
    )
    async def paginator(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @paginator.command(
        name="add",
        aliases=["create", "c", "a"],
        brief="make a paginator from a list of embed code objects",
        usage=",paginator add <name> <embeds>",
        example=",paginator add hello {embed}$v{description: sup}{embed}$v{description: welcome}",
    )
    @commands.has_permissions(manage_messages=True)
    async def paginator_add(self, ctx: Context, *, arg: Argument):
        name = arg.first
        embeds = arg.second
        return await self.bot.paginators.create(ctx, name, embeds)

    @paginator.command(
        name="remove",
        aliases=["rem", "r", "del", "d", "delete"],
        brief="delete an existing paginator",
        usage=",paginator remove <name>",
        example=",paginator remove hello",
    )
    @commands.has_permissions(manage_messages=True)
    async def paginator_remove(self, ctx: Context, *, name: str):
        return await self.bot.paginators.delete(ctx, name)

    @paginator.command(
        name="list", brief="list all paginators setup", example=",paginator list"
    )
    @commands.has_permissions(manage_messages=True)
    async def paginator_list(self, ctx: Context):
        return await self.bot.paginators.list(ctx)

    @paginator.command(
        name="clear", brief="Remove all existing paginators", example=",paginator clear"
    )
    @commands.has_permissions(manage_messages=True)
    async def paginator_clear(self, ctx: Context):
        await asyncio.gather(
            *[
                self.bot.db.execute(
                    """DELETE FROM paginator WHERE guild_id = $1""", ctx.guild.id
                ),
                ctx.success("reset all paginators"),
            ]
        )

    @commands.group(
        name="alias",
        invoke_without_command=True,
        brief="view alias sub commands",
        example=",alias",
    )
    async def alias(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @alias.command(
        name="add",
        aliases=["create", "a", "c"],
        brief="add an alias for a command",
        example=",alias add ban, byebye",
    )
    @commands.has_permissions(manage_guild=True)
    async def alias_add(self, ctx: Context, *, data: AliasConverter):
        self.bot.alias_kwargs = ctx.kwargs
        await self.bot.db.execute(
            "INSERT INTO aliases (guild_id, command_name, alias) VALUES ($1,$2,$3) ON CONFLICT(guild_id, alias) DO NOTHING",
            ctx.guild.id,
            data.command.qualified_name,
            data.alias,
        )
        return await ctx.success(
            f"**Added** `{data.alias}` as an **alias** for `{data.command.qualified_name}`"
        )

    @alias.command(
        name="remove",
        aliases=["delete", "r", "rem", "del", "d"],
        brief="remove an alias from a command",
        example=",alias remove ban",
    )
    @commands.has_permissions(manage_guild=True)
    async def alias_remove(self, ctx: Context, *, alias: str):
        await self.bot.db.execute(
            "DELETE FROM aliases WHERE guild_id = $1 AND alias = $2",
            ctx.guild.id,
            alias,
        )
        return await ctx.success(f"**Removed** `{alias}` custom alias")

    @alias.command(
        name="list", brief="show all your current command aliases", example="alias list"
    )
    @commands.has_permissions(manage_guild=True)
    async def alias_list(self, ctx: Context):
        data = await self.bot.db.fetch(
            """SELECT command_name, alias FROM aliases WHERE guild_id = $1""",
            ctx.guild.id,
        )
        rows = []
        for i, row in enumerate(data, start=1):
            rows.append(f"`{i}` **{row['command_name']}** - {row['alias']}")
        if len(rows) == 0:
            return await ctx.fail("no **aliases** found")
        else:
            return await self.bot.dummy_paginator(
                ctx, Embed(title="Aliases", color=self.bot.color), rows
            )

    # @Group(
    #     name="autopfp",
    #     brief="configure auto profile pictures for the server",
    #     example=",autopfp",
    # )
    # async def pfpchannel(self, ctx: Context):
    #     if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
    #         return
    #     return await ctx.send_help(ctx.command)

    # @pfpchannel.command(
    #     name="setup",
    #     aliases=["add"],
    #     brief="set a channel to send profile pictures to",
    #     example=",autopfp setup #pfps",
    # )
    # @commands.has_permissions(manage_guild=True)
    # async def pfpchannel_set(self, ctx: Context, *, channel: TextChannel):
    #     await self.bot.db.execute(
    #         """INSERT INTO pfps (guild_id,channel_id) VALUES($1,$2) ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id""",
    #         ctx.guild.id,
    #         channel.id,
    #     )
    #     return await ctx.success(f"**Autopfp channel** was set to {channel.mention}")

    # @pfpchannel.command(
    #     name="reset",
    #     aliases=["clear", "remove"],
    #     brief="remove the channel set to send profile pictures",
    #     example=",autopfp reset",
    # )
    # @commands.has_permissions(manage_guild=True)
    # async def pfpchannel_reset(self, ctx: Context):
    #     await self.bot.db.execute(
    #         """DELETE FROM pfps WHERE guild_id = $1""", ctx.guild.id
    #     )
    #     return await ctx.success("Autopfp channel was **removed**")

    @Group(
        name="settings",
        aliases=["setting"],
        brief="Settings for your server",
        example=",settings",
    )
    async def settings(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command)

    @settings.command(
        name="transcribe",
        brief="enable or disable auto transcribing messages",
        example=",settings transcribe true",
        usage=",settings transcribe <state>",
    )
    @has_permissions(manage_guild=True)
    async def settings_transcribe(self, ctx: Context, state: bool):
        if not state:
            query = """DELETE FROM auto_transcribe WHERE guild_id = $1"""
            message = "successfully **DISABLED** auto transcribe"
        else:
            query = """INSERT INTO auto_transcribe (guild_id) VALUES($1) ON CONFLICT(guild_id) DO NOTHING"""
            message = "successfully **ENABLED** auto transcribe"
        await self.bot.db.execute(query, ctx.guild.id)
        return await ctx.success(message)

    #
    #    @settings.group(name="reskin", invoke_without_command=True)
    #    @bot_has_permissions(manage_guild=True)
    #    @has_permissions(manage_guild=True)
    #    async def settings_reskin(self, ctx: Context):
    #        return await ctx.send_help(ctx.command)

    # @settings_reskin.group(name = "server", invoke_without_command = True)
    # @bot_has_permissions(manage_guild=True)
    # @has_permissions(manage_guild=True)
    # async def settings_reskin_server(self, ctx: Context):
    #     return await ctx.send_help(ctx.command)

    #    @settings_reskin.command(
    #        name="name",
    #        aliases=["username"],
    #        brief="set the reskin username for the guild",
    #        usage=",settings reskin name <name>",
    #       example=",settings reskin name dyno",
    #  )
    # @bot_has_permissions(manage_guild=True)
    #    @has_permissions(manage_guild=True)
    #    async def settings_reskin_server_name(self, ctx: Context, *, name: str):
    #       data = await self.bot.db.fetchval(
    #            """SELECT webhooks FROM reskin.server WHERE guild_id = $1""", ctx.guild.id
    #        )
    #        if data:
    #            wh = await self.bot.do_webhooks(ctx.channel, data, name=name)
    #        else:
    #            wh = await self.bot.do_webhooks(ctx.channel, None, name=name)
    #        await self.bot.db.execute(
    #            """INSERT INTO reskin.server (guild_id, username, avatar, webhooks) VALUES($1, $2, $3, $4) ON CONFLICT(guild_id) DO UPDATE SET username = excluded.username""",
    #            ctx.guild.id,
    #            name,
    #            None,
    #            wh,
    #        )
    #       return await ctx.success("Your **reskin setting** has been **applied**")
    #
    #    @settings_reskin.command(
    #        name="avatar",
    #        brief="set the avatar for the guild reskin",
    #        usage=",settings reskin avatar <url/attachment>",
    #        example=",settings reskin avatar https://cdn.discord.com/123.png",
    #    )
    #    @bot_has_permissions(manage_guild=True)
    #    @has_permissions(manage_guild=True)
    #    async def settings_reskin_server_avatar(
    #        self, ctx: Context, url: Optional[str] = None
    #    ):
    #        avatar = None
    ##        data = await self.bot.db.fetchval(
    #            """SELECT webhooks FROM reskin.server WHERE guild_id = $1""", ctx.guild.id
    #        )
    #        if not url:
    #            if len(ctx.message.attachments) > 0:
    #                url = ctx.message.attachments[0].url
    #                avatar = await ctx.message.attachments[0].read()
    #            elif ctx.message.reference:
    #                message = await self.bot.get_reference(ctx.message)
    #                if not message:
    #                    return await ctx.fail("**Message does not have a file**")
    ##                if len(message.attachments) > 0:
    #                    url = message.attachments[0].url
    #                    avatar = await message.attachments[0].read()
    #        else:
    #            async with aiohttp.ClientSession() as session:
    #                async with session.get(url) as resp:
    #                    avatar = await resp.read()
    #        wh = await self.bot.do_webhooks(ctx.channel, data, avatar=avatar)
    #        await self.bot.db.execute(
    #            """INSERT INTO reskin.server (guild_id, username, avatar, webhooks) VALUES($1, $2, $3, $4) ON CONFLICT(guild_id) DO UPDATE SET avatar = excluded.avatar, webhooks = excluded.webhooks""",
    #            ctx.guild.id,
    #            None,
    #            url,
    #            wh,
    #        )
    #        if not avatar:
    #            return await ctx.success("**Reskin avatar** has been **reset**")
    #        return await ctx.success(
    #            f"**Reskin avatar** was set to [**this file**]({url})"
    #        )
    #
    #    @settings_reskin.command(name="reset", brief="reset your server's reskin setup")
    #    @bot_has_permissions(manage_guild=True)
    #    @has_permissions(manage_guild=True)
    #    async def settings_reskin_server_reset(self, ctx: Context):
    ##        data = await self.bot.db.fetchval(
    #            """SELECT webhooks FROM reskin.server WHERE guild_id = $1""", ctx.guild.id
    #        )
    #        if data:
    #            wh = json.loads(data)
    #            for w in wh:
    #                try:
    #                    _ = discord.Webhook.from_url(w[1], client=self.bot)
    #                    await _.delete(reason=f"Reskin Setup Reset by {str(ctx.author)}")
    #                except Exception:
    #                    pass
    #        await self.bot.db.execute(
    #            """DELETE FROM reskin.server WHERE guild_id = $1""", ctx.guild.id
    #        )
    #        return await ctx.success("**Reset** your **server reskin**")
    #
    #    # @settings_reskin.group(name = "self", aliases = ["user"], brief = "setup your own personal reskin config", invoke_without_command = True)
    # async def settings_reskin_self(self, ctx: Context):
    #     return await ctx.send_help(ctx.command)

    # @settings_reskin_self.command(name = "name", aliases = ["username"], brief = "set the reskin username for yourself", usage = ",settings reskin self name <name>", example = ",settings reskin self name dyno")
    # @bot_has_permissions(manage_guild=True)
    # @has_permissions(manage_guild=True)
    # async def settings_reskin_self_name(self, ctx: Context, *, name: str):
    #     data = await self.bot.db.fetchval("""SELECT webhooks FROM reskin.main WHERE user_id = $1""", ctx.author.id)
    #     if data:
    #         wh = await self.bot.do_webhooks(ctx.channel, data, name=name)
    #     else:
    #         wh = await self.bot.do_webhooks(ctx.channel, None, name = name)
    #     await self.bot.db.execute("""INSERT INTO reskin.main (user_id, username, avatar, webhooks) VALUES($1, $2, $3, $4) ON CONFLICT(user_id) DO UPDATE SET username = excluded.username""", ctx.author.id, name, None, wh)
    #     return await ctx.success("successfully setup reskin for yourself")

    # @settings_reskin_self.command(name = "avatar", brief = "set the avatar for your reskin", usage = ",settings reskin self avatar <url/attachment>", example = ",settings reskin self avatar https://cdn.discord.com/123.png")
    # @bot_has_permissions(manage_guild=True)
    # @has_permissions(manage_guild=True)
    # async def settings_reskin_self_avatar(self, ctx: Context, url: Optional[str] = None):
    #     avatar = None
    #     data = await self.bot.db.fetchval("""SELECT webhooks FROM reskin.main WHERE user_id = $1""", ctx.author.id)
    #     if not url:
    #         if len(ctx.message.attachments) > 0:
    #             url = ctx.message.attachments[0].url
    #             avatar = await ctx.message.attachments[0].read()
    #         elif ctx.message.reference:
    #             message = await self.bot.get_reference(ctx.message)
    #             if not message: return await ctx.fail("Could not get that message reference")
    #             if len(message.attachments) > 0:
    #                 url = message.attachments[0].url
    #                 avatar = await message.attachments[0].read()
    #     else:
    #         async with aiohttp.ClientSession() as session:
    #             async with session.get(url) as resp:
    #                 avatar = await resp.read()
    #     wh = await self.bot.do_webhooks(ctx.channel, data, avatar = avatar)
    #     await self.bot.db.execute("""INSERT INTO reskin.main (user_id, username, avatar, webhooks) VALUES($1, $2, $3, $4) ON CONFLICT(user_id) DO UPDATE SET avatar = excluded.avatar, webhooks = excluded.webhooks""", ctx.author.id, None, url, wh)
    #     if not avatar:
    #         return await ctx.success("set the reskin personal avatar to None")
    #     return await ctx.success(f"set the reskin personal avatar to [**This URL**]({url})")

    # @settings_reskin_self.command(name = "reset", brief = "reset your reskin setup")
    # @bot_has_permissions(manage_guild=True)
    # @has_permissions(manage_guild=True)
    # async def settings_reskin_self_reset(self, ctx: Context):
    #     data = await self.bot.fetchval("""SELECT webhooks FROM reskin.main WHERE user_id = $1""", ctx.author.id)
    #     if data:
    #         wh = json.loads(data)
    #         for w in wh:
    #             _ = discord.Webhook.from_url(w[1])
    #             await _.delete(reason = "Reskin Setup Reset by {str(ctx.author)}")
    #     await self.bot.db.execute("""DELETE FROM reskin.main WHERE user_id = $1""", ctx.author.id)
    #     return await ctx.success("reset your reskin personal setup")

    @settings.group(name="context", invoke_without_command=True)
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @settings_context.command(name="clear", brief="reset all of your context settings")
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_reset(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM context WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("reset your **context settings**")

    @settings_context.group(
        name="success",
        brief="change the success color",
        example=",settings context success #303135",
        usage=",settings context success {color}",
        invoke_without_command=True,
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_success(self, ctx: Context, *, color: ColorConverter):
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, success_color) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET success_color = excluded.success_color""",
            ctx.guild.id,
            str(color),
        )
        return await ctx.success(
            f"successfully set your **success color** to {str(color)}"
        )

    @settings_context_success.command(
        name="emoji",
        brief="change the success emoji",
        example=",settings context success emoji <:hi:1231421421412>",
        usage=",settings context success emoji {emoji}",
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_success_emoji(self, ctx: Context, *, emoji: Emojis):
        emoji = emoji[0]
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, success_emoji) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET success_emoji = excluded.success_emoji""",
            ctx.guild.id,
            str(emoji),
        )
        return await ctx.success(
            f"successfully set your **success emoji** to {str(emoji)}"
        )

    @settings_context.group(
        name="fail",
        brief="change the fail color",
        example=",settings context fail #303135",
        usage=",settings context fail {color}",
        invoke_without_command=True,
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_fail(self, ctx: Context, *, color: ColorConverter):
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, fail_color) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET fail_color = excluded.fail_color""",
            ctx.guild.id,
            str(color),
        )
        return await ctx.success(
            f"successfully set your **fail color** to {str(color)}"
        )

    @settings_context_fail.command(
        name="emoji",
        brief="change the fail emoji",
        example=",settings fail emoji <:hi:1231421421412>",
        usage=",settings fail emoji {emoji}",
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_fail_emoji(self, ctx: Context, *, emoji: Emojis):
        emoji = emoji[0]
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, fail_emoji) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET fail_emoji = excluded.fail_emoji""",
            ctx.guild.id,
            str(emoji),
        )
        return await ctx.success(
            f"successfully set your **fail emoji** to {str(emoji)}"
        )

    @settings_context.group(
        name="warning",
        brief="change the warning color",
        example=",settings contextwarning #303135",
        usage=",settings contextwarning {color}",
        invoke_without_command=True,
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_warning(self, ctx: Context, *, color: ColorConverter):
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, warning_color) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET warning_color = excluded.warning_color""",
            ctx.guild.id,
            str(color),
        )
        return await ctx.success(
            f"successfully set your **warning color** to {str(color)}"
        )

    @settings_context_warning.command(
        name="emoji",
        brief="change the warning emoji",
        example=",settings contextwarning emoji <:hi:1231421421412>",
        usage=",settings contextwarning emoji {emoji}",
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_warning_emoji(self, ctx: Context, *, emoji: Emojis):
        emoji = emoji[0]
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, warning_emoji) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET warning_emoji = excluded.warning_emoji""",
            ctx.guild.id,
            str(emoji),
        )
        return await ctx.success(
            f"successfully set your **warning emoji** to {str(emoji)}"
        )

    async def get_attachments(self, ctx: Context):
        if reference := ctx.message.reference:
            msg = await self.bot.fetch_message(ctx.channel, reference.message_id)
            if len(msg.attachments) > 0:
                return await msg.attachments[0].read()
        if len(ctx.message.attachments) > 0:
            return await ctx.message.attachments[0].read()
        return None

    @settings.group(
        name="system",
        aliases=["sys"],
        brief="Settings for system related commands",
        example=",settings system",
        invoke_without_command=True,
    )
    async def system(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @system.command(
        name="boost",
        brief="Toggle the servers boost system message",
        example=",settings system boost true",
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def system_boost(
        self, ctx: Context, *, channel: discord.abc.GuildChannel = None
    ):
        if channel is None:
            await ctx.guild.edit(
                system_channel_flags=discord.SystemChannelFlags(
                    premium_subscriptions=False,
                    join_notifications=ctx.guild.system_channel_flags.join_notifications,
                )
            )
        else:
            await ctx.guild.edit(
                system_channel=channel,
                system_channel_flags=discord.SystemChannelFlags(
                    premium_subscriptions=True,
                    join_notifications=ctx.guild.system_channel_flags.join_notifications,
                ),
            )
        state = (
            "enabled"
            if ctx.guild.system_channel_flags.premium_subscriptions
            else "disabled"
        )
        return await ctx.success(f"**System Boost messages** set to {state}")

    @system.command(
        name="welcome",
        brief="toggle the welcome system message",
        example=",settings system welcome true",
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def system_welcome(
        self, ctx: Context, *, channel: discord.abc.GuildChannel = None
    ):
        if channel is None:
            await ctx.guild.edit(
                system_channel_flags=discord.SystemChannelFlags(
                    join_notifications=False,
                    premium_subscriptions=ctx.guild.system_channel_flags.premium_subscriptions,
                )
            )
        else:
            await ctx.guild.edit(
                system_channel=channel,
                system_channel_flags=discord.SystemChannelFlags(
                    join_notifications=True,
                    premium_subscriptions=ctx.guild.system_channel_flags.premium_subscriptions,
                ),
            )
        state = (
            "enabled"
            if ctx.guild.system_channel_flags.join_notifications
            else "disabled"
        )
        return await ctx.success(f"**System welcome message** set to {state}")

    @system.command(
        name="sticker",
        aliases=("stickers",),
        brief="auto reply to the welcome system message",
        example=",settings system sticker true",
    )
    @has_permissions(manage_guild=True)
    @bot_has_permissions(manage_guild=True)
    async def system_sticker(self, ctx: Context, state: bool):
        if state is True:
            await self.bot.db.execute(
                """INSERT INTO system_messages (guild_id) VALUES($1)""", ctx.guild.id
            )
        else:
            await self.bot.db.execute(
                """DELETE FROM system_messages WHERE guild_id = $1""", ctx.guild.id
            )
        return await ctx.success(f"**System sticker message reply** set to {state}")

    @settings.command(
        name="banner",
        brief="Apply an image as the guild banner",
        example=",settings system banner {image}",
    )
    @has_permissions(manage_guild=True)
    @bot_has_permissions(manage_guild=True)
    async def set_banner(self, ctx: Context, *, image: Image = None):
        if image is None:
            if image := await self.get_attachments(ctx):
                image = image
            else:
                return await ctx.fail("no image provided")
        await ctx.guild.edit(
            banner=image, reason=f"Banner updated by {str(ctx.author)}"
        )
        return await ctx.success("**Updated** the servers banner")

    @settings.command(
        name="splash",
        brief="Apply an image as the guild splash",
        example=",settings system splash {image}",
    )
    @has_permissions(manage_guild=True)
    @bot_has_permissions(manage_guild=True)
    async def set_splash(self, ctx: Context, *, image: Image = None):
        if image is None:
            if image := await self.get_attachments(ctx):
                image = image
            else:
                return await ctx.fail("no image provided")
        await ctx.guild.edit(
            splash=image, reason=f"splash updated by {str(ctx.author)}"
        )
        return await ctx.success("*Updated** the server splash")

    @settings.command(
        name="icon",
        aliases=["pfp", "av", "avatar"],
        brief="Apply an image as the guild icon",
        example=",settings system icon {image}",
    )
    @has_permissions(manage_guild=True)
    @bot_has_permissions(manage_guild=True)
    async def set_avatar(self, ctx: Context, *, image: Image = None):
        if image is None:
            if image := await self.get_attachments(ctx):
                image = image
            else:
                return await ctx.fail("no image provided")
        await ctx.guild.edit(icon=image, reason=f"banner updated by {str(ctx.author)}")
        return await ctx.success("**Updated** the server icon")

    @settings.command(
        name="description",
        brief="Apply a message as the guild description",
        aliases=["desc"],
        example=",settings system description this is the best server",
    )
    @has_permissions(manage_guild=True)
    @bot_has_permissions(manage_guild=True)
    async def set_description(self, ctx: Context, *, text: str):
        await ctx.guild.edit(
            description=text, reason=f"description updated by {str(ctx.author)}"
        )
        return await ctx.success("**Updated** the server description")

    @Group(
        name="sticker",
        brief="Manage the servers stickers",
        example=",sticker",
        invoke_without_command=True,
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker(self: "Servers", ctx: Context):
        return await ctx.send_help(ctx.command.qualified_name)

    def rerun(self, image_bytes: bytes, size=(120, 120), max_size_kb=512):
        from PIL import Image, ImageSequence

        with BytesIO(image_bytes) as input_buffer:
            with Image.open(input_buffer) as im:
                frames = [
                    frame.copy()
                    for i, frame in enumerate(ImageSequence.Iterator(im))
                    if i % 3 == 0
                ]  # Skip every other frame
                resized_frames = [frame.resize(size, Image.LANCZOS) for frame in frames]

                output_buffer = BytesIO()
                quality = 90  # Start with high quality
                resized_frames[0].save(
                    output_buffer,
                    format="GIF",
                    save_all=True,
                    append_images=resized_frames[1:],
                    loop=0,
                    optimize=True,
                    quality=quality,
                )

                while output_buffer.tell() > max_size_kb * 1024:
                    output_buffer = BytesIO()
                    quality -= 10
                    if quality < 10:
                        raise ValueError(
                            "Cannot compress the image to the required size."
                        )
                    resized_frames[0].save(
                        output_buffer,
                        format="GIF",
                        save_all=True,
                        append_images=resized_frames[1:],
                        loop=0,
                        optimize=True,
                        quality=quality,
                    )

                output_buffer.seek(0)
                return output_buffer.read()

    async def convert_sticker(self, img_url: str, svg: bool = False) -> discord.File:  # type: ignore
        from tools import thread  # type: ignore
        from PIL import Image, ImageSequence
        from wand.image import Image as IMG
        from tool.worker import offloaded

        @thread
        def convert_gif(
            image_bytes: bytes,
            gif: Optional[bool] = False,
            size=(320, 320),
            max_size_kb=512,
        ):
            from PIL import Image, ImageSequence
            from wand.image import Image as IMG
            from io import BytesIO

            if gif is True:
                with BytesIO(image_bytes) as input_buffer:
                    with Image.open(input_buffer) as im:
                        frames = [
                            frame.copy()
                            for i, frame in enumerate(ImageSequence.Iterator(im))
                            if i % 3 == 0
                        ]  # Skip every other frame
                        resized_frames = [
                            frame.resize(size, Image.LANCZOS) for frame in frames
                        ]

                        output_buffer = BytesIO()
                        quality = 90  # Start with high quality
                        resized_frames[0].save(
                            output_buffer,
                            format="GIF",
                            save_all=True,
                            append_images=resized_frames[1:],
                            loop=0,
                            optimize=True,
                            quality=quality,
                        )

                        while output_buffer.tell() > max_size_kb * 1024:
                            output_buffer = BytesIO()
                            quality -= 10
                            if quality < 10:
                                try:
                                    return self.rerun(image_bytes)
                                except Exception:
                                    raise ValueError(
                                        "Cannot compress the image to the required size."
                                    )
                            resized_frames[0].save(
                                output_buffer,
                                format="GIF",
                                save_all=True,
                                append_images=resized_frames[1:],
                                loop=0,
                                optimize=True,
                                quality=quality,
                            )

                        output_buffer.seek(0)
                        return output_buffer.read()
            else:
                with IMG(blob=image_bytes) as i:  #
                    i.coalesce()
                    i.optimize_layers()
                    i.compression_quality = 100
                    png_bytes = i.make_blob(format="apng" if i.animation else "png")
                    return png_bytes

        if ".gif" in img_url:
            conversion = await convert_gif(await get_raw_asset(img_url), True)
            filename = "meow.gif"
        else:
            conversion = await convert_gif(await get_raw_asset(img_url))
            filename = "meow.png"

        return discord.File(fp=BytesIO(conversion), filename=filename)

    @sticker.command(
        name="add",
        aliases=("create",),
        example=",sticker add (reply to sticker)",
        brief="Add a sticker recently posted in chat to the server",
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker_add(self: "Servers", ctx: Context, *, name: str):
        """
        Create a new sticker
        """
        if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
            return await ctx.fail("This server exceeds the **sticker limit**.")

        if len(name) < 2 or len(name) > 30:
            return await ctx.fail(
                "Name must be between between **2** and **30 characters**"
            )

        try:
            image = await Stickers.search(ctx)
        except Exception:
            image = None
        if not image:
            image = await Attachment.search(ctx)
            logger.info(f"getting asset from {image}")
            if image is None:
                return await ctx.fail("No image provided")
        a = await get_raw_asset(image)
        ext = await get_file_ext(image)
        #        await ctx.send(files=[a])
        try:
            sticker = await ctx.guild.create_sticker(
                name=name,
                description="...",
                file=discord.File(fp=BytesIO(a), filename=f"{name}.{ext}"),
                reason=f"{self.bot.user.name.title()} Utilities [{ctx.author}]",
                emoji="??",
            )
        except Exception:  # type: ignore
            message = await ctx.normal(
                "please wait while I attempt to compress this asset"
            )
            embed = message.embeds[0]
            try:
                file = await self.convert_sticker(image)
                sticker = await ctx.guild.create_sticker(
                    name=name,
                    description="...",
                    file=file,
                    reason=f"{self.bot.user.name.title()} Utilities [{ctx.author}]",
                    emoji="??",
                )
                embed.description = (
                    f"**Created** the sticker [**{sticker.name}**]({sticker.url})"
                )
            except Exception:  # type: ignore
                embed.description = "**Failed** to create the sticker with the attachment provided due to it being to large"

            return await message.edit(embed=embed)
        return await ctx.success(
            f"**Created** the sticker [**{sticker.name}**]({sticker.url})"
        )

    @sticker.command(
        name="remove",
        aliases=("delete",),
        usage="<sticker>",
        example=",sticker delete dumb_sticker",
        brief="Delete a sticker from the server",
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker_remove(self: "Servers", ctx: Context, *, sticker: Sticker):
        """
        Delete an existing sticker
        """
        await sticker.delete(
            reason=f"{self.bot.user.name.title()} Utilities [{ctx.author}]"
        )
        return await ctx.fail("**Deleted** that sticker")

    @sticker.command(
        name="rename",
        aliases=("name",),
        usage="<sticker>",
        example=",sticker rename dumb_sticker, new_name,",
        brief="Rename a sticker in the server",
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker_rename(
        self: "Servers", ctx: Context, sticker: Sticker, *, name: str
    ):
        """
        Rename an existing sticker
        """
        if len(name) < 2 or len(name) > 30:
            return await ctx.fail("Name must be between **2** and **30 characters**")
        await sticker.edit(
            name=name, reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]"
        )

        return await ctx.fail(f"**Renamed** that sticker to: **{name}**")

    @sticker.command(
        name="clean",
        aliases=["strip", "cleanse"],
        brief="Remove any vanity links or .gg/ URLs from all sticker names",
        example=",sticker clean",
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker_clean(self: "Servers", ctx: Context):
        if not ctx.guild.stickers:
            return await ctx.fail("This server has no stickers to clean")

        cleaned = []
        skipped = []
        failed = []

        async def clean_sticker(sticker):
            try:
                if ".gg/" not in sticker.name:
                    skipped.append(sticker)
                    return None

                name = sticker.name.split(".gg/")[0]

                if len(name.strip()) < 2:
                    skipped.append(sticker)
                    return None

                cleaned_sticker = await sticker.edit(
                    name=name.strip(),
                    reason=f"Cleaned vanity URLs by {str(ctx.author)}",
                )
                cleaned.append(cleaned_sticker)
                return cleaned_sticker

            except Exception as e:
                logger.error(f"Failed to clean sticker {sticker.name}: {str(e)}")
                failed.append(sticker)
                return None

        await gather(*(clean_sticker(s) for s in ctx.guild.stickers))

        embed = discord.Embed(
            title="Sticker Cleanup Results",
            color=self.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Summary",
            value=f"✅ Cleaned: {len(cleaned)}\n↪️ Skipped: {len(skipped)}\n❌ Failed: {len(failed)}",
            inline=False,
        )

        if cleaned:
            cleaned_names = "\n".join(f"• {s.name}" for s in cleaned[:10])
            if len(cleaned) > 10:
                cleaned_names += f"\n+ {len(cleaned)-10} more..."
            embed.add_field(name="Cleaned Stickers", value=cleaned_names, inline=False)

        if failed:
            failed_names = "\n".join(f"• {s.name}" for s in failed[:5])
            if len(failed) > 5:
                failed_names += f"\n+ {len(failed)-5} more..."
            embed.add_field(name="Failed Stickers", value=failed_names, inline=False)

        await ctx.send(embed=embed)

    @sticker.command(
        name="tag",
        brief="Add your vanity link to every sticker name",
        example=",sticker tag",
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker_tag(self: "Servers", ctx: Context):
        if guild_has_vanity(ctx.guild) is not True:
            return await ctx.fail("this guild doesn't have a vanity")
        if not ctx.guild.stickers:
            return await ctx.fail("There aren't any **stickers** in this server.")

        async def tag_sticker(sticker):
            if f".gg/{ctx.guild.vanity_url_code}" in sticker.name:
                return

            return await sticker.edit(
                name=sticker.name[: 30 - len(f" .gg/{ctx.guild.vanity_url_code}")]
                + f" .gg/{ctx.guild.vanity_url_code}".strip(),
                reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]",
            )

        tagged = [await tag_sticker(s) for s in ctx.guild.stickers]

        return await ctx.success(f"**Tagged** `{len(tagged)}` stickers")

    @Group(
        name="premiumrole",
        aliases=["pr", "boosterreward"],
        brief="Premium role settings for when users boost",
        example=",premiumrole",
    )
    @commands.has_permissions(manage_guild=True)
    async def premiumrole(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @premiumrole.command(
        name="add",
        aliases=["give", "set"],
        brief="set a role for all boosters to be given",
        example=",premiumrole add pic",
    )
    @commands.has_permissions(manage_guild=True)
    async def premiumrole_add(self, ctx: Context, role: Role):
        role = role[0]
        await self.bot.db.execute(
            """INSERT INTO premiumrole (guild_id, role_id) VALUES ($1, $2) ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id""",
            ctx.guild.id,
            role.id,
        )
        return await ctx.success(f"**Boosters** will now be given {role.mention}")

    @premiumrole.command(
        name="remove",
        aliases=["r"],
        brief="remove the booster role",
        example=",premiumrole remove pic",
    )
    @commands.has_permissions(manage_guild=True)
    async def premiumrole_remove(self, ctx: Context, role: Role):  # type: ignore
        await self.bot.db.execute(
            """DELETE FROM premiumrole WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("**Removed** the **booster role**")

    @premiumrole.command(
        name="list",
        aliases=["status"],
        brief="Check which role is set as a premium reward role",
        example=",premiumrole list",
    )
    @commands.has_permissions(manage_guild=True)
    async def premiumrole_status(self, ctx: Context):
        if role_id := await self.bot.db.fetchval(
            """SELECT role_id FROM premiumrole WHERE guild_id = $1""", ctx.guild.id
        ):
            return await ctx.success(
                f"**Reward for boosting** is set to {ctx.guild.get_role(role_id).mention}"
            )
        else:
            return await ctx.fail("**Premiumrole** is **not** set")

    @commands.Cog.listener("on_guild_emojis_update")
    async def emoji_ratelimit(self, guild, before, after):
        if not guild.me.guild_permissions.view_audit_log:
            return
        if len(before) != len(after):
            async for audit in guild.audit_logs(
                action=discord.AuditLogAction.emoji_create,
                limit=1,
                after=discord.utils.utcnow() - timedelta(seconds=1),
            ):
                if audit.user.id == self.bot.user.id:
                    return
            await self.bot.glory_cache.ratelimited(f"emojis:{guild.id}", 49, 60 * 60)

    @Group(
        name="emoji",
        usage="<sub command>",
        example="removeduplicates",
        invoke_without_command=True,
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji(self: "Servers", ctx: Context):
        """
        Manage the server emojis
        """

        return await ctx.send_help(ctx.command.qualified_name)

    @emoji.command(
        name="steal", brief="steal the most recently used emoji", example=",emoji steal"
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_steal(self, ctx: Context):
        try:
            emoji = None
            i = 0
            if ctx.message.reference:
                emoji = await Emojis().convert(ctx, "", True)
                emoji = emoji[0]
            else:

                async for message in ctx.channel.history(limit=200):
                    i += 1
                    if await Emojis().convert(ctx, message.content):  # type: ignore
                        try:
                            emoj = await self.get_emojis(message.content)
                            try:
                                if get_emoji := self.bot.get_emoji(int(emoj.id)):
                                    if get_emoji.guild.id != ctx.guild.id:
                                        emoji = emoj
                                        break
                                    else:
                                        continue
                                else:
                                    emoji = emoj
                                    break
                            except Exception:  # type: ignore
                                emoji = emoj
                        except Exception:  # type: ignore
                            emoji = await self.get_emojis(message.content)
                            if emoji:
                                break
            if emoji is None:
                return await ctx.fail(f"no **emojis** found in the last {i} messages")
            embed = discord.Embed(color=self.bot.color).add_field(
                name="Emoji ID", value=emoji.id, inline=True
            )
            if get_emoji := self.bot.get_emoji(int(emoji.id)):
                embed.add_field(name="Guild", value=get_emoji.guild.name, inline=True)
            embed.add_field(
                name="Image URL",
                value=f"[**Click here to open the image**]({emoji.url})",
                inline=False,
            )
            embed.set_image(url=emoji.url)
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
            embed.title = emoji.name
            message = await ctx.send(embed=embed)
            view = EmojiConfirmation(message, emoji, ctx.author)
            await message.edit(view=view)
            await view.wait()
        except Exception as e:
            if ctx.author.name == "aiohttp":
                raise e
            else:
                return await ctx.fail("No stealable emojis detected")

    @emoji.command(
        name="add",
        aliases=("create",),
        example=",emoji add [emojis]",
        brief="Add multiple emojis to the server",
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_addmultiple(
        self: "Servers",
        ctx: Context,
        *,
        emojis: Optional[Emojis] = None,
    ):
        """
        Create multiple emojis
        """
        if ctx.message.reference and not emojis:
            emojis = await Emojis().convert(ctx, "", True, True)
        else:
            if not emojis:
                return await ctx.fail("Please provide **Emojis**")
        if len(ctx.guild.emojis) >= ctx.guild.emoji_limit:
            return await ctx.fail("**Server exceeds** the **emoji limit**.")
        if not emojis:
            return await ctx.fail("No **Emojis** were found")

        created_emojis = []  # List to hold created emojis
        log.info(emojis)
        msg = None
        remaining = ctx.guild.emoji_limit - len(ctx.guild.emojis)
        e = (
            emojis[:remaining] if isinstance(emojis, list) else [emojis]
        )  # Handle single emoji case
        log.info(f"{e} {remaining}")
        for emoji in e:
            await sleep(0.001)
            if (
                await self.bot.glory_cache.ratelimited(
                    f"emojis:{ctx.guild.id}", 49, 60 * 60
                )
                != 0
            ):  # type: ignore
                raise CommandError("Emoji adding is ratelimited for this guild")
            new_emoji = await ctx.guild.create_custom_emoji(
                name=emoji.name,
                image=await emoji.read(),
                reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]",
            )
            created_emojis.append(new_emoji)

        if not created_emojis:
            return await ctx.fail("**No emojis** could be added")

        created_emoji_str = " ".join(
            str(emoji) for emoji in created_emojis
        )  # Concatenate created emojis

        if len(created_emojis) != len(e):
            return await ctx.success(f"**Could only create** {created_emoji_str}")
        if msg is not None:
            return await msg.edit(
                embed=discord.Embed(
                    color=self.bot.color, description=f"**Created** {created_emoji_str}"
                )
            )
        return await ctx.success(f"**Created** {created_emoji_str}")

    @emoji.command(
        name="image",
        aliases=("fromfile",),
        example=",emoji add :sad_bear:",
        brief="Add an emoji to the guild",
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_add(
        self: "Servers",
        ctx: Context,
        *,
        name: Optional[Union[discord.PartialEmoji, str, discord.Emoji]] = "lol",
    ):
        """
        Create a new emoji
        """
        logger.info(f"got type {type(name)}")
        if sum(ctx.guild.emojis) >= ctx.guild.emoji_limit:
            return await ctx.fail("**Server exceeds** the **emoji limit**")

        if not isinstance(name, discord.PartialEmoji) and not isinstance(
            name, discord.PartialEmoji
        ):
            if len(name) < 2 or len(name) > 30:
                return await ctx.fail(
                    "Please provide a **valid** name between 2 and 30 characters."
                )
            if not (image := await Attachment.search(ctx)):
                return await ctx.fail("There are **no recently sent images**")
        else:
            image = await name.read()
            name = name.name
        if isinstance(image, str):
            image = await Attachment.search(ctx)
            async with aiohttp.ClientSession() as session:
                async with session.get(image) as response:
                    content_type = response.headers.get("Content-Type")
                    if content_type != "image/gif":
                        count = ctx.static_emoji_count
                    else:
                        count = ctx.animated_emoji_count
                    image = await response.read()
            name = name
        try:
            if (
                await self.bot.glory_cache.ratelimited(
                    f"emojis:{ctx.guild.id}", 49, 60 * 60
                )
                != 0
            ):  # type: ignore
                raise CommandError("Emoji adding is ratelimited for this guild")
            emoji = await ctx.guild.create_custom_emoji(
                name=name,
                image=image,
                reason=f"{self.bot.user.name.title()} Utilities[{str(ctx.author)}]",
            )

        except HTTPException as error:
            if "(error code: 30008)" in str(error):
                return await ctx.fail("**Server** doesn't have enough **emoji slots**")
            # if ctx.author.name == "aiohttp":
            #     raise error
            if "(error code: 50045)" in str(error):
                return await ctx.fail("The **Image** you sent was to large")
            if ctx.author.name == "aiohttp":
                raise error
            return await ctx.fail("Please provide a **valid** image.")

        return await ctx.success(
            f"**Created** the emoji [**{emoji.name}**]({emoji.url})"
        )

    @emoji.command(
        name="remove",
        aliases=("delete",),
        example=",emoji remove [emoji]",
        brief="Remove an emoji from the server",
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_remove(
        self: "Servers", ctx: Context, *, emoji: Union[discord.Emoji, str]
    ):
        """Remove an emoji from the server"""

        if isinstance(emoji, str) or (
            isinstance(emoji, discord.Emoji) and emoji.guild_id != ctx.guild.id
        ):
            return await ctx.fail("That emoji cannot be deleted from this server")

        await emoji.delete(
            reason=f"{self.bot.user.name.title()} Utilities [{ctx.author}]"
        )
        return await ctx.success("**Deleted** that emoji")

    @emoji.command(
        name="rename",
        aliases=("name",),
        example=",emoji rename :sad: megasad",
        brief="Rename an emoji",
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_rename(self: "Servers", ctx: Context, emoji: Emoji, *, name: str):

        if len(name) < 2 or len(name) > 30:
            return await ctx.fail("Name must be between **2** and **30 characters**")

        await emoji.edit(
            name=name, reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]"
        )

        return await ctx.success(f"Renamed** that emoji to: **{name}**")

    @emoji.command(
        name="removeduplicates",
        brief="Remove all emojis that has a duplicate",
        example=",emoji removeduplicates",
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_removeduplicates(self: "Servers", ctx: Context):

        if not ctx.guild.emojis:
            return await ctx.fail("There are **no emojis**")

        duplicates = set()
        seen = set()
        emojis_bytes = await gather(*(emoji.read() for emoji in ctx.guild.emojis))

        for emoji, emoji_bytes in zip(ctx.guild.emojis, emojis_bytes):
            if emoji_bytes in seen:
                duplicates.add(emoji)

            else:
                seen.add(emoji_bytes)

        removed = await gather(
            *(
                duplicate.delete(
                    reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]: Duplicate emoji"
                )
                for duplicate in duplicates
            )
        )

        return await ctx.success(f"**Removed** `{len(removed)}` duplicated emojis")

    @Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.me.guild_permissions.manage_messages:
            if data := await self.bot.db.fetchrow(
                "SELECT * FROM welcome WHERE guild_id = $1", member.guild.id
            ):
                channel = self.bot.get_channel(data["channel_id"])
                message = data["message"]
                if channel:
                    try:
                        await self.bot.send_embed(channel, message, user=member)
                    except EmbedError as e:
                        await channel.send(f"fix your welcome message: {e}")

    @Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if data := await self.bot.db.fetchrow(
            "SELECT * FROM leave WHERE guild_id = $1", member.guild.id
        ):
            channel = self.bot.get_channel(data["channel_id"])
            message = data["message"]
            if channel:
                await self.bot.send_embed(channel, message, user=member)

    @commands.command(
        name="embed",
        aliases=["ce", "createembed"],
        example=",embed {embed_code}",
        brief="Create an embed using an embed code",
    )
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx: Context, *, code: str):
        from tool.rival import EmbedException  # type: ignore

        try:
            await self.bot.send_embed(ctx.channel, code, user=ctx.author)
        except EmbedException as e:
            raise e
            return await ctx.fail(e)
        except Exception as e:
            raise e

    @commands.group(
        name="selfprefix",
        invoke_without_command=True,
        brief="Set a self prefix thats unique to you to use for the bot",
        example=",selfprefix !",
    )
    async def selfprefix(self, ctx: Context, prefix: str = None):
        if prefix and len(prefix) > 3:
            return await ctx.fail("Prefix **cannot** be longer than `2` **characters**")
        if not prefix:
            return await ctx.fail("Please provide a **prefix**")
        await self.bot.db.execute(
            "INSERT INTO selfprefix (prefix, user_id) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET prefix = $1",
            prefix,
            ctx.author.id,
        )
        self.bot.cache.self_prefixes[ctx.author.id] = prefix
        await ctx.success(f"**Selfprefix** has been changed to `{prefix}`")

    @selfprefix.command(
        name="remove",
        aliases=["reset"],
        brief="Reset the self prefix you have previously set",
        example=",selfprefix remove",
    )
    @is_donator()
    async def selfprefix_remove(self, ctx: Context):
        await self.bot.db.execute(
            "DELETE FROM selfprefix WHERE user_id = $1", ctx.author.id
        )
        try:
            self.bot.cache.self_prefixes.pop(ctx.author.id)
        except Exception:
            pass
        await ctx.success("**Removed** your **Selfprefix**")

    @commands.group(
        name="prefix",
        invoke_without_command=True,
        brief="Set a prefix for the bot to respond to in the guild",
        example=",prefix ;",
    )
    @commands.has_permissions(manage_guild=True)
    async def prefix(self, ctx: Context, prefix: str = None):
        if prefix is not None and len(prefix) > 2:
            await ctx.fail("Prefix **cannot** be longer than **2 characters**")
            return
        await self.bot.db.execute(
            "INSERT INTO prefixes (prefix, guild_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET prefix = EXCLUDED.prefix",
            prefix,
            ctx.guild.id,
        )
        self.bot.cache.prefixes[ctx.guild.id] = prefix
        invite_link = await ctx.channel.create_invite()
        await ctx.success(
            f"[**Guild Prefix**]({invite_link}) has been **changed** to `{prefix}`"
        )

    @prefix.command(
        name="remove",
        aliases=["reset"],
        brief="Remove the custom guild prefix from the bot",
        example=",prefix remove",
    )
    @commands.has_permissions(manage_guild=True)
    async def prefix_remove(self, ctx: Context):
        invite_link = await ctx.channel.create_invite()
        await self.bot.db.execute(
            "DELETE FROM prefixes WHERE guild_id = $1", ctx.guild.id
        )
        try:
            self.bot.prefix.pop(ctx.guild.id)
        except Exception:
            pass
        await ctx.fail(
            f"[**Guild Prefix**]({invite_link}) **removed**, mention the bot for the [**Global Prefix**]({invite_link})"
        )

    @commands.group(
        name="fakepermissions",
        aliases=["fakepermission", "fp", "fakeperms"],
        invoke_without_command=True,
        brief="Fake Permissions for roles to be used through the bot",
        example=",fakepermissions",
    )
    async def fakepermissions(self, ctx: Context):
        # show all permissions that can be used as fake permissions
        permissions = [
            "create_instant_invite",
            "kick_members",
            "ban_members",
            "administrator",
            "manage_channels",
            "manage_guild",
            "add_reactions",
            "view_audit_log",
            "priority_speaker",
            "stream",
            "read_messages",
            "manage_members",
            "send_messages",
            "send_tts_messages",
            "manage_messages",
            "embed_links",
            "attach_files",
            "read_message_history",
            "mention_everyone",
            "external_emojis",
            "view_guild_insights",
            "connect",
            "speak",
            "mute_members",
            "deafen_members",
            "move_members",
            "use_voice_activation",
            "change_nickname",
            "manage_nicknames",
            "manage_roles",
            "manage_webhooks",
            "manage_expressions",
            "use_application_commands",
            "request_to_speak",
            "manage_events",
            "manage_threads",
            "create_public_threads",
            "create_private_threads",
            "external_stickers",
            "send_messages_in_threads",
            "use_embedded_activities",
            "moderate_members",
            "use_soundboard",
            "create_expressions",
            "use_external_sounds",
            "send_voice_messages",
        ]
        return await ctx.normal(
            f"**Available Permissions**\n```{', '.join(permissions)}```"
        )

    async def handle_fakeperm_addition(
        self, guild: discord.Guild, role: discord.Role, perms: Union[str, List[str]]
    ):
        if isinstance(perms, list):
            p = ",".join(p for p in perms)
        else:
            p = perms
        if current_perms := await self.bot.db.fetchval(
            """SELECT perms FROM fakeperms WHERE guild_id = $1 AND role_id = $2""",
            guild.id,
            role.id,
        ):
            perm = f"{current_perms},{p}"
        else:
            perm = p
        await self.bot.db.execute(
            """INSERT INTO fakeperms (guild_id, role_id, perms) VALUES($1, $2, $3) ON CONFLICT(guild_id, role_id) DO UPDATE SET perms = excluded.perms""",
            guild.id,
            role.id,
            perm,
        )
        return True

    @fakepermissions.command(
        name="add",
        brief="Add a fake permission to a role",
        example=",fakepermission add @members, manage guild",
    )
    @commands.has_permissions(guild_owner=True)
    async def fakepermissions_add(
        self, ctx: Context, *, entry: FakePermissionConverter
    ):
        await self.handle_fakeperm_addition(ctx.guild, entry.role[0], entry.permissions)
        return await ctx.success(
            f"**Added** `{entry.permissions}` **permissions to** {entry.role[0].mention}"
        )

    @fakepermissions.command(
        name="remove",
        brief="remove fake permissions from a role",
        example=",fakepermission remove @member",
    )
    @commands.has_permissions(guild_owner=True)
    async def fakepermissions_remove(self, ctx: Context, *, role: discord.Role):
        fake_perms = await self.bot.db.fetchrow(
            """SELECT * FROM fakeperms WHERE guild_id = $1 AND role_id = $2""",
            ctx.guild.id,
            role.id,
        )
        if not fake_perms:
            return await ctx.fail(f"**No fake permissions** are set for {role.mention}")

        await self.bot.db.execute(
            """DELETE FROM fakeperms WHERE guild_id = $1 AND role_id = $2""",
            ctx.guild.id,
            role.id,
        )
        return await ctx.success(f"**Revoked fake permissions from** {role.mention}")

    @fakepermissions.command(
        name="clear", brief="clear all fake permissions", example="fakpermissions clear"
    )
    @commands.has_permissions(guild_owner=True)
    async def fakepermissions_clear(self, ctx: Context):
        fake_perms = await self.bot.db.fetchrow(
            """SELECT * FROM fakeperms WHERE guild_id = $1""", ctx.guild.id
        )
        if not fake_perms:
            return await ctx.fail("**No roles** have any **fake permissions** set")
        await self.bot.db.execute(
            """DELETE FROM fakeperms WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("**Revoked all fake permissions** from **all roles**")

    @fakepermissions.command(
        name="list",
        brief="show all fake permission entries",
        example=",fakepermissions list",
    )
    @commands.has_permissions(guild_owner=True)
    async def fakepermissions_list(self, ctx: Context):
        rows = []
        i = 0
        for role_id, perms in await self.bot.db.fetch(
            """SELECT role_id, perms FROM fakeperms WHERE guild_id = $1""", ctx.guild.id
        ):
            if role := ctx.guild.get_role(int(role_id)):
                i += 1
                rows.append(f"`{i}` {role.mention} - `{perms}`")
        if len(rows) == 0:
            return await ctx.fail("**No fake permissions** found for any roles")
        return await self.bot.dummy_paginator(
            ctx, Embed(title="Fake Permissions", color=self.bot.color), rows
        )

    # welcome message

    @commands.hybrid_group(
        name="welcome",
        aliases=["welc"],
        invoke_without_command=True,
        with_app_command=True,
        brief="Welcome configurations for the server",
        example=",welcome",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome(self, ctx: Context) -> discord.Message:
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @welcome.command(
        name="setup",
        aliases=["make", "create"],
        brief="setup welcome settings",
        example=",welcome setup",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_create(self, ctx: Context) -> discord.Message:
        if await self.bot.db.fetchrow(
            "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail(
                "**Welcome settings** have **already been configured** for this server"
            )

        await self.bot.db.execute(
            "INSERT INTO welcome (guild_id, channel_id, message) VALUES ($1, $2, $3)",
            ctx.guild.id,
            ctx.channel.id,
            "welcome {user}",
        )
        self.bot.cache.welcome[ctx.guild.id] = {
            "channel": ctx.channel.id,
            "message": "welcome {user}",
        }
        await ctx.success("**Configured the welcome** for this server")

    @welcome.command(
        name="channel",
        aliases=["chan"],
        brief="Set the welcome channel",
        example=",welcome channel #welcomechannel",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_channel(
        self, ctx: Context, channel: discord.TextChannel
    ) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"Welcome settings have **not** been configured yet. Use `{ctx.prefix}welcome setup` first"
            )
        if self.bot.cache.welcome.get(ctx.guild.id):
            self.bot.cache.welcome[ctx.guild.id]["channel"] = channel.id
        else:
            self.bot.cache.welcome[ctx.guild.id] = {"channel": channel.id}
        await self.bot.db.execute(
            "UPDATE welcome SET channel_id = $1 WHERE guild_id = $2",
            channel.id,
            ctx.guild.id,
        )
        await ctx.success(f"**Welcome channel** has been **set** to {channel.mention}")

    @welcome.command(
        name="reset",
        aliases=["remove", "delete", "off"],
        brief="Clear welcome settings",
        example=",welcome reset",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_delete(self, ctx: Context) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"Welcome settings have **not** been configured yet. Use `{ctx.prefix}welcome setup` first"
            )
        self.bot.cache.welcome.pop(ctx.guild.id)
        await self.bot.db.execute(
            "DELETE FROM welcome WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.success("**Deleted the welcome** for this server")

    @welcome.command(
        name="view",
        brief="View your current welcome embed code",
        example=",welcome view",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_view(self, ctx: Context):
        if not (
            data := await self.bot.db.fetchrow(
                "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"Welcome settings have **not** been configured yet. Use `{ctx.prefix}welcome setup` first"
            )
        return await ctx.send(f"```{data['message']}```")

    @welcome.command(
        name="message",
        aliases=["msg"],
        brief="Set the welcome message",
        example=",welcome message wsp {user}",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_message(self, ctx: Context, *, message: str) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"Welcome settings have **not** been configured yet. Use `{ctx.prefix}welcome setup` first"
            )
        await self.bot.send_embed(ctx.channel, message, user=ctx.author)
        self.bot.cache.welcome[ctx.guild.id]["message"] = message
        await self.bot.db.execute(
            "UPDATE welcome SET message = $1 WHERE guild_id = $2",
            message,
            ctx.guild.id,
        )
        await ctx.success(f"Welcome message has been **set** to `{message}`.")

    @welcome.command(
        name="test",
        aliases=["trial"],
        brief="Test the welcome message",
        example=",welcome test",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_test(self, ctx: Context) -> discord.Reaction:
        self.bot.dispatch("member_join", ctx.author)
        await ctx.success("**Welcome message** was sent")

    @commands.group(
        name="leave",
        aliases=["goodbye"],
        invoke_without_command=True,
        brief="Manage leave messages for when a user leaves the guild",
        example=",leave",
    )
    @commands.has_permissions(manage_channels=True)
    async def leave(self, ctx: Context) -> discord.Message:
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @leave.command(
        name="channel",
        aliases=["chan"],
        brief="Set the leave channel",
        example=",leave channel #goodbye",
    )
    @commands.has_permissions(manage_channels=True)
    async def leave_channel(
        self, ctx: Context, channel: discord.TextChannel
    ) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"**Leave settings** have **not** been configured yet. Use `{ctx.prefix}leave setup` first"
            )

        await self.bot.db.execute(
            "UPDATE leave SET channel_id = $1 WHERE guild_id = $2",
            channel.id,
            ctx.guild.id,
        )
        self.bot.cache.leave[ctx.guild.id]["channel"] = channel.id
        await ctx.success(f"Leave channel has been **set** to {channel.mention}.")

    @leave.command(name="view", brief="view your current leave embed code")
    @commands.has_permissions(manage_channels=True)
    async def leave_view(self, ctx: Context):
        if not (
            data := await self.bot.db.fetchrow(
                "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"**Leave settings** have **not** been configured yet. Use `{ctx.prefix}leave setup` first"
            )
        return await ctx.send(f"```{data['message']}```")

    @leave.command(
        name="setup",
        aliases=["enable", "on"],
        brief="Configure leave settings",
        example=",leave setup",
    )
    @commands.has_permissions(manage_channels=True)
    async def leave_create(self, ctx: Context) -> discord.Message:
        if await self.bot.db.fetchrow(
            "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail(
                "**Leave settings** have **already** been configured for this server"
            )

        await self.bot.db.execute(
            "INSERT INTO leave (guild_id, channel_id, message) VALUES ($1, $2, $3)",
            ctx.guild.id,
            ctx.channel.id,
            "leave {user}",
        )
        self.bot.cache.leave[ctx.guild.id] = {
            "channel": ctx.channel.id,
            "message": "leave {user}",
        }
        await ctx.success("**Leave settings** have **been configured** for this server")

    @leave.command(
        name="reset",
        aliases=["remove", "delete"],
        brief="Clear leave settings",
        example=",leave reset",
    )
    @commands.has_permissions(manage_channels=True)
    async def leave_delete(self, ctx: Context) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"**Leave settings** have **not** been configured yet. Use `{ctx.prefix}leave setup` first"
            )

        await self.bot.db.execute("DELETE FROM leave WHERE guild_id = $1", ctx.guild.id)
        self.bot.cache.leave.pop(ctx.guild.id)
        await ctx.success("**Deleted** the leave settings")

    @leave.command(
        name="message",
        aliases=["msg"],
        brief="Set the leave message",
        example=",leave message {embed_code}",
    )
    async def leave_message(self, ctx: Context, *, message: str) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"**Leave settings** have **not** been configured yet. Use `{ctx.prefix}leave setup` first"
            )
        await self.bot.send_embed(ctx.channel, message, user=ctx.author)
        self.bot.cache.leave[ctx.guild.id]["message"] = message
        await self.bot.db.execute(
            "UPDATE leave SET message = $1 WHERE guild_id = $2",
            message,
            ctx.guild.id,
        )
        await ctx.success(f"**Leave message** has been **set** to `{message}`")

    @leave.command(
        name="test",
        aliases=["trial"],
        brief="Test the leave message",
        example=",leave test",
    )
    @commands.has_permissions(manage_channels=True)
    async def leave_test(self, ctx: Context) -> discord.Reaction:
        self.bot.dispatch("member_remove", ctx.author)
        await ctx.success("**Leave message** has been sent")

    # boosters enable/disable and customization options for boosters in guilds.

    @commands.group(
        name="boosterroles",
        aliases=["br", "boosterrole"],
        brief="Commands for setting up and using booster roles in your guild",
        example=",boosterroles",
    )
    async def br(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        if not (
            role_id := await self.bot.db.fetchval(
                "SELECT role_id FROM br WHERE role_id = $1", role.id
            )
        ):
            return

        await self.bot.db.execute("DELETE FROM br WHERE role_id = $1", role_id)

    @commands.Cog.listener("on_member_remove")
    async def br_deletion(self, member: discord.Member):
        if role_id := await self.bot.db.fetchval(
            """SELECT role_id FROM br WHERE guild_id = $1 AND user_id = $2""",
            member.guild.id,
            member.id,
        ):
            if role := member.guild.get_role(role_id):
                await role.delete(reason="boost role auto cleanup")

    @br.command(
        name="setup",
        aliases=("enable",),
        brief="Allow users to create their own role after boosting the guild",
        example=",boosterroles enable",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    @check_guild_boost_level()
    async def br_enable(self, ctx: Context) -> discord.Message:
        if await self.bot.db.fetchval(
            "SELECT status FROM br_status WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail(
                "**Booster roles** are already **enabled** in this guild"
            )

        await self.bot.db.execute(
            "INSERT INTO br_status (guild_id, status) VALUES ($1, $2)",
            ctx.guild.id,
            True,
        )
        return await ctx.success("**Enabled booster roles** for this guild")

    @br.command(
        name="disable",
        aliases=("reset",),
        brief="Disable booster roles in the guild",
        example=",boosterroles disable",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def br_disable(self, ctx: Context) -> discord.Message:
        if not await self.bot.db.fetchval(
            "SELECT status FROM br_status WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail(
                "**Booster roles** are already **disabled** in this guild"
            )

        await self.bot.db.execute(
            "DELETE FROM br_status WHERE guild_id = $1", ctx.guild.id
        )
        return await ctx.success("**Disabled booster roles** for this guild")

    async def cleanup_boostroles(self, ctx: Context):
        for r in await self.bot.db.fetch(
            """SELECT role_id FROM br WHERE guild_id = $1""", ctx.guild.id
        ):
            if role := ctx.guild.get_role(r):
                try:
                    await role.delete(reason="boost role cleanup")
                except Exception:
                    await self.bot.db.execute(
                        """DELETE FROM br WHERE guild_id = $1 AND role_id = $2""",
                        ctx.guild.id,
                        r,
                    )
        await self.bot.db.execute(
            """DELETE FROM br WHERE guild_id = $1""", ctx.guild.id
        )
        return True

    async def edit_position(self, ctx: Context, role: discord.Role):
        if base := await self.bot.db.fetchval(
            """SELECT role_id FROM br_base WHERE guild_id = $1""", ctx.guild.id
        ):
            if base_role := ctx.guild.get_role(base):
                # Get all booster roles for this guild
                booster_roles = await self.bot.db.fetch(
                    """SELECT role_id FROM br WHERE guild_id = $1""", ctx.guild.id
                )
                
                # Filter out deleted roles and sort by current position
                valid_roles = []
                for r_id in booster_roles:
                    if r := ctx.guild.get_role(r_id):
                        valid_roles.append(r)
                
                # Sort roles by current position (highest to lowest)
                valid_roles.sort(key=lambda x: x.position, reverse=True)
                
                # Position the target role just below the base role
                await role.edit(position=base_role.position - 1)
                
                # Position other booster roles below the target role
                for i, r in enumerate(valid_roles):
                    if r.id != role.id:  # Skip the role we just positioned
                        try:
                            await r.edit(position=base_role.position - (i + 2))
                        except discord.HTTPException:
                            continue
            else:
                return await ctx.fail(
                    f"**Base role** must have been **deleted**: `{base}`"
                )
        else:
            return await ctx.fail("**No base role** set for this guild")

    async def bulk_edit_boostroles(self, ctx: Context):
        for r in await self.bot.db.fetch(
            """SELECT role_id FROM br WHERE guild_id = $1""", ctx.guild.id
        ):
            if role := ctx.guild.get_role(r):
                await self.edit_position(ctx, role)

    @br.command(
        name="base",
        aliases=["baserole"],
        brief="Set a base role for booster roles to be created under",
        example=",boosterroles base @members",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def br_base(self, ctx: Context, *, role: Role = None):
        if role is None:
            await self.bot.db.execute(
                """DELETE FROM br_status WHERE guild_id = $1""", ctx.guild.id
            )
            await self.bot.db.execute(
                """DELETE FROM br_base WHERE guild_id = $1""", ctx.guild.id
            )
            await self.cleanup_boostroles(ctx)
            return await ctx.success("disabled `boost roles` and cleaned up the roles")
        else:
            role = role[0]
            if role.position >= ctx.guild.me.top_role.position:
                return await ctx.fail(
                    "**Base role** is **higher** then my **top role**"
                )
            if not await self.bot.db.fetch(
                """SELECT * FROM br_status WHERE guild_id = $1""", ctx.guild.id
            ):
                await self.bot.db.execute(
                    """INSERT INTO br_status (guild_id, status) VALUES($1,$2)""",
                    ctx.guild.id,
                    True,
                )
            await self.bot.db.execute(
                """INSERT INTO br_base (guild_id, role_id) VALUES($1,$2) ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id""",
                ctx.guild.id,
                role.id,
            )
            roles = await self.bot.db.fetch(
                """SELECT role_id FROM br WHERE guild_id = $1""", ctx.guild.id
            )
            if roles:
                msg = await ctx.success(
                    "changing all boost role positions... this may take a while..."
                )
                for rr in roles:
                    if ctx.guild.get_role(rr):  # type: ignore
                        await role.edit(position=role.position - 1)
                await msg.edit(
                    embed=discord.Embed(
                        description=f"**Base role** set to <@&{role.id}>",
                        color=self.bot.color,
                    )
                )
            else:
                return await ctx.success(f"**Base role** set to {role.mention}")

    @br.command(
        "sync",
        brief="Sync all existing booster roles to the correct position based on the base role",
        example=",boosterroles sync",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def br_sync(self, ctx: Context) -> discord.Message:
        if not await self.bot.db.fetchval(
            """SELECT role_id FROM br_base WHERE guild_id = $1""", ctx.guild.id
        ):
            return await ctx.fail("**No base role** set for this guild. Set one with `,br base @role` first")

        roles = await self.bot.db.fetch(
            """SELECT role_id FROM br WHERE guild_id = $1""", ctx.guild.id
        )
        if not roles:
            return await ctx.fail("No booster roles found to sync")

        msg = await ctx.success("Syncing all booster roles... this may take a while...")
        synced = 0
        failed = 0

        # Get all valid booster roles
        valid_roles = []
        for role_id in roles:
            if role := ctx.guild.get_role(role_id):
                valid_roles.append(role)

        if not valid_roles:
            return await msg.edit(
                embed=discord.Embed(
                    description="No valid booster roles found to sync",
                    color=self.bot.color,
                )
            )

        # Sort roles by current position (highest to lowest)
        valid_roles.sort(key=lambda x: x.position, reverse=True)

        # Get base role
        base_role_id = await self.bot.db.fetchval(
            """SELECT role_id FROM br_base WHERE guild_id = $1""", ctx.guild.id
        )
        base_role = ctx.guild.get_role(base_role_id)

        for i, role in enumerate(valid_roles):
            try:
                await role.edit(position=base_role.position - (i + 1))
                synced += 1
            except discord.HTTPException:
                failed += 1
                continue

        await msg.edit(
            embed=discord.Embed(
                description=f"**Synced** {synced} booster roles{f' ({failed} failed)' if failed > 0 else ''}",
                color=self.bot.color,
            )
        )

    

    @br.command(
        "share",
        aliases=("give",),
        brief="Share your booster role with another user or remove it if they already have it",
        example=",boosterroles share @sudosql",
    )
    @commands.bot_has_permissions(administrator=True)
    @check_br_status()
    async def br_share(self, ctx: Context, *, member: discord.Member):
        if data := await self.bot.db.fetchval(
            """SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2""",
            ctx.author.id,
            ctx.guild.id,
        ):
            if role := ctx.guild.get_role(data):
                if role in member.roles:
                    await member.remove_roles(role)
                    action = "removed from"
                else:
                    await member.add_roles(role)
                    action = "shared with"
            else:
                return await ctx.fail("your booster role **doesn't exist**")
        else:
            return await ctx.fail("your booster role **doesn't exist**")

        return await ctx.success(
            f"**Booster role** has been **{action}** {member.mention}"
        )

    @br.command(
        "create",
        aliases=("make",),
        brief="Create a custom booster role for boosting the guild",
        example=",boosterroles create topG",
    )
    @check_br_status()
    @commands.bot_has_permissions(administrator=True)
    async def br_create(
        self, ctx: Context, *, name: str, color: int = 3447003
    ) -> discord.Message:
        author: discord.Member = typing.cast(discord.Member, ctx.author)
        rolename = f"{name}"
        exists = await self.bot.db.fetchval(
            "SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2",
            author.id,
            ctx.guild.id,
        )
        if exists:
            return await ctx.fail("You already have a **booster role** in this guild")

        # Remove the icon parameter from create_role
        role = await ctx.guild.create_role(name=rolename, color=discord.Color(color))
        if base := await self.bot.db.fetchval(
            """SELECT role_id FROM br_base WHERE guild_id = $1""", ctx.guild.id
        ):
            if base_role := ctx.guild.get_role(base):
                await role.edit(position=base_role.position - 1)
        await author.add_roles(role, reason="BoosterRole")
        await self.bot.db.execute(
            "INSERT INTO br (user_id, role_id, guild_id) VALUES ($1, $2, $3)",
            author.id,
            role.id,
            ctx.guild.id,
        )
        return await ctx.success(
            f"**Created** your own **booster role**: {role.mention} with the color `{hex(typing.cast(int, color))}`"
        )

    @br.command(
        "delete",
        aliases=("remove", "del", "rm"),
        brief="Remove your custom booster role from the guild",
        example=",boosterroles remove",
    )
    @commands.bot_has_permissions(administrator=True)
    @check_br_status()
    async def br_delete(self, ctx: Context) -> Optional[discord.Message]:
        author: discord.Member = typing.cast(discord.Member, ctx.author)
        if not (
            role := await self.bot.db.fetchval(
                "SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2",
                author.id,
                ctx.guild.id,
            )
        ):
            return await ctx.fail(
                "You **do not** have a **booster role** in this guild"
            )

        role = ctx.guild.get_role(int(role))
        if role:
            await role.delete(reason="BoosterRole")
            await self.bot.db.execute(
                "DELETE FROM br WHERE user_id = $1 AND guild_id = $2",
                author.id,
                ctx.guild.id,
            )
            return await ctx.success("**Deleted** your **booster role** in this guild")

    @br.command(
        "rename",
        aliases=("name",),
        brief="Rename your custom booster role in this guild",
        example=",boosterroles rename littleG",
    )
    @commands.bot_has_permissions(administrator=True)
    @check_br_status()
    async def br_rename(self, ctx: Context, name: str) -> Optional[discord.Message]:
        author: discord.Member = typing.cast(discord.Member, ctx.author)
        if not (
            role := await self.bot.db.fetchval(
                "SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2",
                author.id,
                ctx.guild.id,
            )
        ):
            return await ctx.fail(
                "You **do not** have a **booster role** in this guild"
            )

        role = ctx.guild.get_role(int(role))
        if role:
            await role.edit(
                name=f"{name}",
                reason="BoosterRole",
            )
            return await ctx.success(
                f"**Renamed** your **booster role** to {role.mention}"
            )

    @br.command(
        "color",
        aliases=("colour",),
        brief="Change the color or recolor your custom booster role in this guild",
        example=",boosterroles color #2b2d31",
    )
    @commands.bot_has_permissions(administrator=True)
    @check_br_status()
    async def br_color(
        self, ctx: Context, *, color: ColorConverter
    ) -> Optional[discord.Message]:
        author: discord.Member = typing.cast(discord.Member, ctx.author)
        if not (
            role := await self.bot.db.fetchval(
                "SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2",
                author.id,
                ctx.guild.id,
            )
        ):
            return await ctx.fail(
                "You **do not** have a **booster role** in this guild"
            )

        role = ctx.guild.get_role(int(role))
        if role:
            await role.edit(color=color, reason="BoosterRole")
            return await ctx.success(
                f"**Changed** your **booster role's color** to `{color}`"
            )

    async def get_icon(
        self, url: Optional[Union[discord.Emoji, discord.PartialEmoji, str]] = None
    ):
        if url is None:
            return None
        if isinstance(url, discord.Emoji):
            return await url.read()
        elif isinstance(url, discord.PartialEmoji):
            return await url.read()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.read()
            return data

    @br.command(
        "icon",
        aliases=("icn",),
        brief="Set or Change the current icon you have set for your custom booster role in this guild",
        example=",boosterroles icon :blunt:",
    )
    @commands.bot_has_permissions(administrator=True)
    @check_br_status()
    async def br_icon(
        self,
        ctx,
        *,
        icon: Optional[Union[discord.Emoji, discord.PartialEmoji, str]] = None,
    ) -> discord.Message:
        if isinstance(icon, str):
            if not icon.startswith("https://"):
                return await ctx.fail("that is not a valid URL")
        author = ctx.author
        if not (
            role := await self.bot.db.fetchval(
                "SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2",
                author.id,
                ctx.guild.id,
            )
        ):
            return await ctx.fail(
                "You **do not** have a **booster role** in this guild"
            )
        role = ctx.guild.get_role(role)
        icon = await self.get_icon(icon)
        if icon is None:
            if not role.display_icon:
                return await ctx.fail(
                    "Your **booster role** does not have an **icon** set"
                )
        await role.edit(display_icon=icon, reason="BoosterRole")
        if icon:
            return await ctx.success("**Booster role icon changed**")
        else:
            return await ctx.success(
                "**Booster roles icon** has been **reset** for this guild"
            )

    @br.command(
        "list",
        aliases=("all",),
        brief="List all the booster roles in this guild",
        example=",boosterroles list",
    )
    @commands.has_permissions(manage_guild=True)
    async def br_list(self, ctx: Context):
        rows = []
        data = await self.bot.db.fetch(
            """SELECT user_id, role_id FROM br WHERE guild_id = $1""", ctx.guild.id
        )
        if not data:
            return await ctx.fail("No booster roles found in this guild.")

        for i, record in enumerate(data, start=1):
            user = ctx.guild.get_member(record["user_id"])
            role = ctx.guild.get_role(record["role_id"])
            if user and role:
                rows.append(f"`{i}` {role.mention} - Owned by {user.mention}")
            elif role:
                rows.append(f"`{i}` {role.mention} - Owner not found")
            else:
                rows.append(f"`{i}` Role not found - User ID: {record['user_id']}")

        embed = discord.Embed(
            title=f"Booster Roles in {ctx.guild.name}",
            color=self.bot.color,
        )
        await self.bot.dummy_paginator(ctx, embed, rows, 10, "booster role")

    @br.command(
        "include",
        aliases=("bypass",),
        brief="Include a user in the booster role list",
        example=",boosterroles include @role @user",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def br_include(self, ctx: Context, role: Role, user: discord.Member):
        """
        Include a user in the booster role list by associating them with a specific role.
        """
        role = role[0]
        if not ctx.guild.get_role(role.id):
            return await ctx.fail("The specified role does not exist in this guild.")

        if await self.bot.db.fetchval(
            """SELECT role_id FROM br WHERE role_id = $1 AND guild_id = $2""",
            role.id,
            ctx.guild.id,
        ):
            return await ctx.fail("This role is already associated with a booster.")

        await self.bot.db.execute(
            """INSERT INTO br (user_id, role_id, guild_id) VALUES ($1, $2, $3)""",
            user.id,
            role.id,
            ctx.guild.id,
        )
        return await ctx.success(
            f"**Included** {user.mention} as the owner of the booster role {role.mention}."
        )


    # Autorole setup for guilds.

    @commands.group(
        name="autorole",
        aliases=["arole"],
        example=",autorole",
        brief="Configure autorole settings through the bot",
    )
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(administrator=True)
    async def autorole(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command.qualified_name)

    @autorole.command(
        name="add",
        aliases=["set"],
        brief="Add an autorole or autoroles",
        example=",autorole add @member",
    )
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(administrator=True)
    @query_limit("autorole", 3)
    async def autorole_add(self, ctx: commands.Context, *, roles: Role):
        if not roles:
            return await ctx.fail("No valid roles were mentioned.")
        await self.bot.db.fetch(  # type: ignore
            "SELECT COUNT(*) FROM autorole WHERE guild_id = $1",
            ctx.guild.id,
        )
        for role in roles:
            if not await self.bot.db.fetch(
                "SELECT * FROM autorole WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            ):
                await self.bot.db.execute(
                    "INSERT INTO autorole (guild_id, role_id) VALUES ($1, $2)",
                    ctx.guild.id,
                    role.id,
                )
        data = await self.bot.db.fetch(
            """SELECT role_id FROM autorole WHERE guild_id = $1""", ctx.guild.id
        )
        self.bot.cache.autorole[ctx.guild.id] = [_data.role_id for _data in data]
        added_roles = [f"<@&{role.id}>" for role in roles]
        await ctx.success(
            f"**Autorole** will give {', '.join(added_roles)} to **users on join**"
        )

    @autorole.command(
        name="remove",
        aliases=["delete"],
        brief="Remove an autorole or autoroles",
        example=",autorole remove member",
    )
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(administrator=True)
    async def autorole_remove(self, ctx: commands.Context, *, roles: Role):
        for role in roles:
            if not await self.bot.db.fetch(
                "SELECT * FROM autorole WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            ):
                return await ctx.fail(
                    f"`{role.name}` is **not** set as an **autorole**"
                )
            await self.bot.db.execute(
                "DELETE FROM autorole WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            )
        data = await self.bot.db.fetch(
            """SELECT role_id FROM autorole WHERE guild_id = $1""", ctx.guild.id
        )
        self.bot.cache.autorole[ctx.guild.id] = [_data.role_id for _data in data]
        return await ctx.success(
            f"**Removed** {', '.join([f'<@&{x.id}>' for x in roles])} from the **autoroles list**"
        )

    @autorole.command(name="list", brief="list all autoroles", example=",autorole list")
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(administrator=True)
    async def autorole_list(self, ctx: commands.Context):
        guild = ctx.guild
        embed = discord.Embed(title=f"{guild.name} Autoroles", color=self.bot.color)
        embed.set_author(
            name=guild.name, icon_url=guild.icon.url if guild.icon else None
        )
        if data := await self.bot.db.fetch(
            "SELECT * FROM autorole WHERE guild_id = $1",
            ctx.guild.id,
        ):
            roles = []
            for i, x in enumerate(data):
                if role := guild.get_role(x["role_id"]):
                    roles.append(f"``{i+1}.`` {role.mention}")
                else:
                    # Delete the invalid role from database
                    await self.bot.db.execute(
                        "DELETE FROM autorole WHERE guild_id = $1 AND role_id = $2",
                        ctx.guild.id,
                        x["role_id"],
                    )
                    roles.append(
                        f"``{i+1}.`` Role `{x['role_id']}` was deleted or no longer exists"
                    )

            if roles:
                embed.description = "\n".join(roles)
            else:
                embed.description = "No valid autoroles found"
        else:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: There are **no autoroles** set",
                color=0x2D2B31,
            )
        await ctx.send(embed=embed)

    async def add_react(
        self,
        ctx: Context,
        _type: str,
        react: Union[discord.Emoji, discord.PartialEmoji, str],
    ):
        emoji = react  # ((b64encode(str(reaction).encode()).decode() if isinstance(b64encode(str(reaction).encode()), bytes) else b64encode(str(reaction).encode()) if not is_unicode(reaction) else reaction ) if not is_unicode(reaction) else reaction,)
        if not self.bot.cache.autoreacts.get(ctx.guild.id):
            self.bot.cache.autoreacts[ctx.guild.id] = {}
        if not self.bot.cache.autoreacts[ctx.guild.id].get(_type):
            self.bot.cache.autoreacts[ctx.guild.id][_type] = []
        self.bot.cache.autoreacts[ctx.guild.id][_type].append(emoji)
        return True

    @commands.group(
        name="autoreact",
        aliases=(
            "reaction",
            "autoreaction",
            "autoreactions",
        ),
        brief="Configure the autoreactions for the guild",
        example=",autoreact",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact(self: "Servers", ctx: Context):
        """
        Set up automatic reactions to messages that match a trigger
        """

        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @autoreact.group(
        name="add",
        brief="Automatically react to phrases said",
        example=",autoreact add com :skull:",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_add(self: "Servers", ctx: Context, *, args: Argument):
        """
        Add a reaction to a trigger
        """
        trigger = args.first
        reactions = args.second
        reactions = await Emojis().convert(ctx, reactions)
        for reaction in reactions:
            reaction = str(reaction)
            if reaction in tuple(
                record.reaction
                for record in await self.bot.db.fetch(
                    "SELECT reaction FROM autoreact WHERE guild_id = $1 AND keyword = $2",
                    ctx.guild.id,
                    trigger,
                )
            ):
                return await ctx.fail(
                    "**That auto-reply event** reaction already exists"
                )

            if (
                await self.bot.db.fetchval(
                    "SELECT COUNT(*) FROM autoreact WHERE guild_id = $1 AND keyword = $2;",
                    ctx.guild.id,
                    trigger,
                )
                > 15
            ):
                return await ctx.fail("**Too many reactions** set for that event")

            if len(trigger) > 32:
                return await ctx.fail("Provide a trigger **under 32 characters**")
            if self.bot.cache.autoreacts.get(ctx.guild.id):
                if self.bot.cache.autoreacts[ctx.guild.id].get(trigger):
                    self.bot.cache.autoreacts[ctx.guild.id][trigger].append(reaction)
                else:
                    self.bot.cache.autoreacts[ctx.guild.id][trigger] = [reaction]
            else:
                self.bot.cache.autoreacts[ctx.guild.id] = {trigger: [reaction]}

            await self.bot.db.execute(
                "INSERT INTO autoreact (guild_id, keyword, reaction) VALUES ($1, $2, $3);",
                ctx.guild.id,
                trigger,
                reaction,
            )
        reaction_str = " ".join(str(m) for m in reactions)
        return await ctx.success(
            f"**Created** {reaction_str} as a reaction for `{trigger}`"
        )

    @autoreact_add.command(
        name="images",
        brief="Automatically react to images sent",
        example=",autoreact add images :sob:",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_add_images(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Add a reaction for images
        """

        if reaction is None:
            return await ctx.fail("**Emoji could not** be found")
        reaction = str(reaction)
        if reaction in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "images",
            )
        ):
            return await ctx.fail(
                "**That auto-reaction** for images **already exists**"
            )

        if (
            await self.bot.db.fetchval(
                "SELECT COUNT(*) FROM autoreact_event WHERE guild_id = $1 AND event = $2;",
                ctx.guild.id,
                "images",
            )
            > 15
        ):
            return await ctx.fail("**Too many reactions** for that event exists")
        if self.bot.cache.autoreacts.get(ctx.guild.id):
            if self.bot.cache.autoreacts[ctx.guild.id].get("images"):
                if isinstance(self.bot.cache.autoreacts[ctx.guild.id]["images"], str):
                    self.bot.cache.autoreacts[ctx.guild.id]["images"] = [
                        self.bot.cache.autoreacts[ctx.guild.id]["images"]
                    ]
                self.bot.cache.autoreacts[ctx.guild.id]["images"].append(reaction)
            else:
                self.bot.cache.autoreacts[ctx.guild.id]["images"] = reaction
        else:
            self.bot.cache.autoreacts[ctx.guild.id] = {"images": reaction}

        await self.bot.db.execute(
            "INSERT INTO autoreact_event (guild_id, event, reaction) VALUES ($1, $2, $3);",
            ctx.guild.id,
            "images",
            reaction,
        )

        return await ctx.success(f"**Created** {reaction} as a **reaction for images**")

    @autoreact_add.command(
        name="spoilers",
        brief="Automatically react to spoiler images",
        example=",autoreact add spoilers :shh:",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_add_spoilers(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Add a reaction for spoilers
        """

        if reaction is None:
            return await ctx.fail("**Emoji** does not exist")
        reaction = str(reaction)
        if reaction in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "spoilers",
            )
        ):
            return await ctx.fail(
                "**That auto-reaction** for spoilers **already exists**"
            )

        if (
            await self.bot.db.fetchval(
                "SELECT COUNT(*) FROM autoreact_event WHERE guild_id = $1 AND event = $2;",
                ctx.guild.id,
                "spoilers",
            )
            > 15
        ):
            return await ctx.fail("**Too many reactions** for that event exists")
        if self.bot.cache.autoreacts.get(ctx.guild.id):
            if self.bot.cache.autoreacts[ctx.guild.id].get("spoilers"):
                self.bot.cache.autoreacts[ctx.guild.id]["spoilers"].append(reaction)
            else:
                self.bot.cache.autoreacts[ctx.guild.id]["spoilers"] = [reaction]
        else:
            self.bot.cache.autoreacts[ctx.guild.id] = {"spoilers": [reaction]}

        await self.bot.db.execute(
            "INSERT INTO autoreact_event (guild_id, event, reaction) VALUES ($1, $2, $3);",
            ctx.guild.id,
            "spoilers",
            reaction,
        )

        return await ctx.success(
            f"**Created** {reaction} as a **reaction for spoilers**"
        )

    @autoreact_add.command(
        name="emojis",
        brief="Automatically react to emojis sent",
        example=",autoreaction add emojis :wave:",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_add_emojis(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Add a reaction for emojis
        """

        if reaction is None:
            return await ctx.fail("**Emoji** could not be found")
        reaction = str(reaction)
        if reaction in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "emojis",
            )
        ):
            return await ctx.fail("That is already an **auto-reaction** for emojis.")

        if (
            await self.bot.db.fetchval(
                "SELECT COUNT(*) FROM autoreact_event WHERE guild_id = $1 AND event = $2;",
                ctx.guild.id,
                "emojis",
            )
            > 15
        ):
            return await ctx.fail("**Too many reactions** for that event exists")
        if self.bot.cache.autoreacts.get(ctx.guild.id):
            if self.bot.cache.autoreacts[ctx.guild.id].get("emojis"):
                self.bot.cache.autoreacts[ctx.guild.id]["emojis"].append(reaction)
            else:
                self.bot.cache.autoreacts[ctx.guild.id]["emojis"] = [reaction]
        else:
            self.bot.cache.autoreacts[ctx.guild.id] = {"emojis": [reaction]}

        await self.bot.db.execute(
            "INSERT INTO autoreact_event (guild_id, event, reaction) VALUES ($1, $2, $3);",
            ctx.guild.id,
            "emojis",
            reaction,
        )

        return await ctx.success(f"**Created** {reaction} as a **reaction for emojis**")

    @autoreact_add.command(
        name="stickers",
        brief="Automatically react to stickers sent",
        example=",autoreact add stickers :zzz:",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_add_stickers(
        self: "Servers", ctx: Context, reaction: Optional[Emoji]
    ):
        """
        Add a reaction for stickers
        """
        if not reaction:
            await self.bot.db.exuecute(
                """DELETE FROM autoreact_event WHERE guild_id = $1 AND event = $2""",
                ctx.guild.id,
                "stickers",
            )
            self.bot.cache.autoreacts[ctx.guild.id].pop("stickers", None)
            return await ctx.success(
                "successfully **cleared** all sticker auto reactions"
            )
        reaction = str(reaction)
        if reaction is None:
            return await ctx.fail("**Emoji** could **not** be found")

        if reaction in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "stickers",
            )
        ):
            return await ctx.fail("That is already an **auto-reaction** for stickers")

        if (
            await self.bot.db.fetchval(
                "SELECT COUNT(*) FROM autoreact_event WHERE guild_id = $1 AND event = $2;",
                ctx.guild.id,
                "stickers",
            )
            > 15
        ):
            return await ctx.fail("**Too many reactions** for that event exist")
        if self.bot.cache.autoreacts.get(ctx.guild.id):
            if self.bot.cache.autoreacts[ctx.guild.id].get("stickers"):
                self.bot.cache.autoreacts[ctx.guild.id]["stickers"].append(reaction)
            else:
                self.bot.cache.autoreacts[ctx.guild.id]["stickers"] = [reaction]
        else:
            self.bot.cache.autoreacts[ctx.guild.id] = {"stickers": [reaction]}

        await self.bot.db.execute(
            "INSERT INTO autoreact_event (guild_id, event, reaction) VALUES ($1, $2, $3);",
            ctx.guild.id,
            "stickers",
            reaction,
        )

        return await ctx.success(
            f"**Created** {reaction} as a **reaction for stickers**"
        )

    @autoreact.group(
        name="remove",
        brief="Remove the autoreaction for phrases said",
        example=",reaction remove com",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_remove(
        self: "Servers", ctx: Context, trigger: str, reaction: Optional[Emoji] = None
    ):
        """
        Remove a reaction from an auto-react trigger
        """

        if reaction is not None:
            reaction = str(reaction)
            if reaction not in tuple(
                record.reaction
                for record in await self.bot.db.fetch(
                    "SELECT reaction FROM autoreact WHERE guild_id = $1 AND keyword = $2",
                    ctx.guild.id,
                    trigger,
                )
            ):
                return await ctx.fail("**Auto-reaction** does not exist")

            await self.bot.db.execute(
                "DELETE FROM autoreact WHERE keyword = $1 AND reaction = $2;",
                trigger,
                reaction,
            )
            try:
                self.bot.cache.autoreacts[ctx.guild.id][trigger].remove(reaction)
            except Exception:
                try:
                    self.bot.cache.autoreacts[ctx.guild.id][trigger].remove(
                        str(reaction)
                    )
                except Exception:
                    pass

        else:
            await self.bot.db.execute(
                """DELETE FROM autoreact WHERE keyword = $1 AND guild_id = $2""",
                trigger,
                ctx.guild.id,
            )
            try:
                self.bot.cache.autoreacts[ctx.guild.id].pop(trigger)
            except Exception:
                pass

        return await ctx.success("**Removed** that **auto-reaction**")

    @autoreact_remove.command(
        name="images",
        brief="Remove autoreactions for images sent",
        example=",autoreaction remove images",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_remove_images(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Remove a reaction for images
        """
        reaction = str(reaction)
        if reaction not in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "images",
            )
        ):
            return await ctx.fail("**Auto-reaction** does not exist")

        await self.bot.db.execute(
            "DELETE FROM autoreact_event WHERE guild_id = $1 AND event = $2 AND reaction = $3;",
            ctx.guild.id,
            "images",
            reaction,
        )
        try:
            self.bot.cache.autoreacts[ctx.guild.id]["images"].remove(reaction)
        except Exception:
            pass

        return await ctx.success("**Removed** that **auto-reaction**")

    @autoreact_remove.command(
        name="spoilers",
        brief="Remove autoreactions for spoilers sent",
        example=",autoreaction remove spoilers",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_remove_spoilers(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Remove a reaction for spoilers
        """
        reaction = str(reaction)
        if reaction not in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "spoilers",
            )
        ):
            return await ctx.fail("**Auto-reaction** does not exist")

        await self.bot.db.execute(
            "DELETE FROM autoreact_event WHERE guild_id = $1 AND event = $2 AND reaction = $3;",
            ctx.guild.id,
            "spoilers",
            reaction,
        )
        try:
            self.bot.cache.autoreacts[ctx.guild.id]["spoilers"].remove(reaction)
        except Exception:
            pass

        return await ctx.success("**Removed** that **auto-reaction**")

    @autoreact_remove.command(
        name="emojis",
        brief="Remove autoreactions for emojis sent",
        example=",autoreaction remove emojis",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_remove_emojis(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Remove a reaction for emojis
        """
        reaction = str(reaction)
        if reaction not in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "emojis",
            )
        ):
            return await ctx.fail("**Auto-reaction** does not exist")

        await self.bot.db.execute(
            "DELETE FROM autoreact_event WHERE guild_id = $1 AND event = $2 AND reaction = $3;",
            ctx.guild.id,
            "emojis",
            reaction,
        )
        try:
            self.bot.cache.autoreacts[ctx.guild.id]["emojis"].remove(reaction)
        except Exception:
            pass

        return await ctx.success("**Removed** that **auto-reaction**")

    @autoreact_remove.command(
        name="stickers",
        usage="Remove autoreactions for stickers sent",
        example=",autoreaction remove stickers",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_remove_stickers(self: "Servers", ctx: Context, reaction: Emoji):
        reaction = str(reaction)
        if reaction not in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "stickers",
            )
        ):
            return await ctx.fail("**Auto-reaction** does not exist")
        try:
            self.bot.cache.autoreacts[ctx.guild.id]["stickers"].remove(reaction)
        except Exception:
            pass
        await self.bot.db.execute(
            "DELETE FROM autoreact_event WHERE guild_id = $1 AND event = $2 AND reaction = $3;",
            ctx.guild.id,
            "stickers",
            reaction,
        )

        return await ctx.success("**Removed** that **auto-reaction**")

    @autoreact.command(
        name="clear",
        brief="remove all autoreactions from the guild",
        example="autoreaction clear",
    )
    async def autoreact_clear(
        self: "Servers", ctx: Context, type: Optional[str] = None
    ):
        if not await self.bot.db.fetch(
            "SELECT * FROM autoreact WHERE guild_id = $1", ctx.guild.id
        ) and not await self.bot.db.fetch(
            "SELECT * FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Auto-reaction triggers** do not exist")

        if type is not None:
            if type.lower() not in ("images", "spoilers", "emojis", "stickers"):
                return await ctx.fail("**Auto-reaction event** does not exist")

            if not await self.bot.db.fetch(
                "SELECT * FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
            ):
                return await ctx.fail("**Auto-reaction event** does not exist")

            if not await self.bot.db.fetch(
                "SELECT * FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                type.lower(),
            ):
                return await ctx.fail("**Auto-reaction event** does not exist")
            try:
                self.bot.cache.autoreacts.pop(ctx.guild.id)
            except Exception:
                pass
            await self.bot.db.execute(
                "DELETE FROM autoreact_event WHERE guild_id = $1 AND event = $2;",
                ctx.guild.id,
                type.lower(),
            )

            return await ctx.success(
                "**Cleared** every **auto-reaction** for that event"
            )

        if await self.bot.db.fetch(
            "SELECT * FROM autoreact WHERE guild_id = $1", ctx.guild.id
        ):
            await self.bot.db.execute(
                "DELETE FROM autoreact WHERE guild_id = $1;", ctx.guild.id
            )

        if await self.bot.db.fetch(
            "SELECT * FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
        ):
            await self.bot.db.execute(
                "DELETE FROM autoreact_event WHERE guild_id = $1;", ctx.guild.id
            )
        try:
            self.bot.cache.autoreacts.pop(ctx.guild.id)
        except Exception:
            pass
        return await ctx.success("**Cleared** every **auto-reaction trigger**")

    @autoreact.command(
        name="removeall",
        aliases=("deleteall",),
        example=",autoreact removeall",
        brief="Remove and reset every auto reaction trigger",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_removeall(self: "Servers", ctx: Context, trigger: str):
        if trigger not in tuple(
            record.keyword
            for record in await self.bot.db.fetch(
                "SELECT keyword FROM autoreact WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail("**Auto-reaction trigger** does not exist")

        await self.bot.db.execute(
            "DELETE FROM autoreact WHERE guild_id = $1 AND keyword = $2;",
            ctx.guild.id,
            trigger,
        )
        try:
            self.bot.cache.autoreacts.pop(ctx.guild.id)
        except Exception:
            pass

        return await ctx.success("**Cleared** every **auto-reaction** for that trigger")

    @autoreact.command(
        name="list",
        brief="View all autoreactions currenctly set for phrases",
        example=",autoreaction list",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_list(self: "Servers", ctx: Context):
        """
        View every auto-reaction trigger
        """

        if not await self.bot.db.fetch(
            "SELECT * FROM autoreact WHERE guild_id = $1", ctx.guild.id
        ):
            if not await self.bot.db.fetch(
                "SELECT * FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
            ):
                return await ctx.fail("**Auto-reaction triggers** does not exist")

        text = []
        keywords_covered = []
        events = {}
        for record in await self.bot.db.fetch(
            "SELECT event, reaction FROM autoreact_event WHERE guild_id = $1",
            ctx.guild.id,
        ):
            if record.event in events:
                events[record.event].append(record.reaction)
            else:
                events[record.event] = [record.reaction]

        for record in await self.bot.db.fetch(
            "SELECT keyword, reaction FROM autoreact WHERE guild_id = $1", ctx.guild.id
        ):
            if record.keyword in keywords_covered:
                continue

            reactions = tuple(
                record.reaction
                for record in await self.bot.db.fetch(
                    "SELECT reaction FROM autoreact WHERE guild_id = $1 AND keyword = $2",
                    ctx.guild.id,
                    record.keyword,
                )
            )

            text.append(
                f"**{record.keyword}** - Reactions: {', '.join((str(reaction)) for reaction in reactions)}"
            )
            logger.info(text)
            keywords_covered.append(record.keyword)
        for k, v in events.items():
            text.append(
                f"**{k}** - Reactions: {', '.join((str(reaction)) for reaction in v)}"
            )
        return await self.bot.dummy_paginator(
            ctx, discord.Embed(title="Auto Reactions", color=self.bot.color), text
        )
        return await ctx.paginate(  # type: ignore
            embed_creator(
                text.getvalue(),
                1980,
                color=self.bot.color,
                title=f"Auto-Reaction Triggers in '{ctx.guild.name}'",
            )
        )

    # @autoreact.command(name="extras", aliases=("listextras", "events", "listevents"), brief='list all autoreactions set for extras (ex. images)', example=',autoreactions extras')
    ##@commands.has_permissions(manage_emojis=True)
    async def autoreact_listextras(self: "Servers", ctx: Context):
        """
        View every auto-reaction event trigger
        """

        if not await self.bot.db.fetch(
            "SELECT * FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Auto-reaction event triggers** does not exist")

        text = StringIO()
        events_covered = []

        for record in await self.bot.db.fetch(
            "SELECT event FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
        ):
            if record.event in events_covered:
                continue

            reactions = tuple(
                record.reaction
                for record in await self.bot.db.fetch(
                    "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                    ctx.guild.id,
                    record.event,
                )
            )

            text.write(
                f"**{record.event}** - Reactions: {', '.join((b64decode(reaction.encode()).decode() if len(tuple(reaction)) > 1 else reaction) for reaction in reactions)}"
            )
            events_covered.append(record.event)

        return await ctx.paginate(
            embed_creator(
                text.getvalue(),
                1980,
                color=self.bot.color,
                title=f"{ctx.guild.name} Auto-Reactions",
            )
        )

    @commands.group(
        name="reskin",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_guild=True)
    async def reskin(self, ctx: Context):
        """Customize the bot's appearance"""
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command.qualified_name)

    @reskin.command(
        name="setup",
        aliases=["webhooks", "enable"],
    )
    @commands.has_permissions(manage_guild=True)
    async def reskin_setup(self, ctx: Context):
        """Set up the reskin webhooks"""
        table = "reskin"
        configuration = await self.bot.db.fetch_config(ctx.guild.id, table) or {}
        configuration["status"] = True
        webhooks = configuration.get("webhooks", {})

        async with ctx.typing():
            tasks = list()
            for channel in ctx.guild.text_channels:
                if any(
                    ext in channel.name.lower()
                    for ext in ("ticket", "log", "discrim", "bleed")
                ) or (
                    channel.category
                    and any(
                        ext in channel.category.name.lower()
                        for ext in (
                            "tickets",
                            "logs",
                            "jail",
                            "pfps",
                            "pfp",
                            "icons",
                            "icon",
                            "banners",
                            "banner",
                        )
                    )
                ):
                    continue

                tasks.append(configure_reskin(self.bot, channel, webhooks))

            gathered = await asyncio.gather(*tasks)
            created = [webhook for webhook in gathered if webhook]

        configuration["webhooks"] = webhooks
        await self.bot.db.update_config(ctx.guild.id, table, configuration)

        if not created:
            return await ctx.fail(
                "No **webhooks** were created"
                + (
                    str(gathered)
                    if ctx.author.id in self.bot.owner_ids and any(gathered)
                    else ""
                ),
            )

        await ctx.success(f"The **reskin webhooks** have been set across all channels")

    @reskin.command(
        name="disable",
    )
    @commands.has_permissions(manage_guild=True)
    async def reskin_disable(self, ctx: Context):
        """Disable the reskin webhooks"""
        table = "reskin"

        configuration = await self.bot.db.fetch_config(ctx.guild.id, table) or {}
        if not configuration.get("status"):
            return await ctx.fail("Reskin webhooks are already **disabled**")

        configuration["status"] = False
        await self.bot.db.update_config(ctx.guild.id, "reskin", configuration)
        await ctx.success("Disabled **reskin** across the server")

    @reskin.command(
        name="name",
        usage="```Swift\nSyntax: !reskin name <name>\nExample: !reskin name blame```",
        brief="name",
        aliases=["username"],
    )
    async def reskin_name(self, ctx: Context, *, username: str):
        """Change your personal reskin username"""

        premium = await self.bot.db.fetchrow(
            "SELECT user_id FROM donators WHERE user_id = $1", ctx.author.id
        )
        if not premium:
            return await ctx.fail(
                "**Premium** is required to use this command join [/greedbot](https://discord.gg/greedbot) to learn more"
            )
        table = "reskin"
        configuration = await self.bot.db.fetch_config(ctx.guild.id, table) or {}
        if not configuration.get("status"):
            return await ctx.fail(
                f"Reskin webhooks are **disabled**\n> Use `{ctx.prefix}reskin setup` to set them up",
            )

        if len(username) > 32:
            raise CommandError("Your name can't be longer than **32 characters**")

        if table == "reskin":
            await self.bot.db.execute(
                "INSERT INTO reskin (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET username = $2",
                ctx.author.id,
                username,
            )

        await ctx.success(f"Changed your **reskin username** to **{username}**")

    @reskin.command(
        name="delete",
        aliases=["remove", "del", "r", "d"],
        description="remove your reskin configuration",
    )
    async def reskin_delete(self, ctx: Context):
        await self.bot.db.execute(
            f"""DELETE FROM reskin WHERE user_id = $1""", ctx.author.id
        )
        return await ctx.success(f"successfully **deleted** your reskin configuration")

    @reskin.command(
        name="avatar",
        usage="```Swift\nSyntax: !reskin avatar <image>\nExample: !reskin avatar https://greed./greed.png```",
        brief="image",
        aliases=["icon", "av"],
    )
    async def reskin_avatar(self, ctx: Context, *, image: str = None):
        """Change your personal reskin avatar"""

        premium = await self.bot.db.fetchrow(
            "SELECT user_id FROM donators WHERE user_id = $1", ctx.author.id
        )
        if not premium:
            return await ctx.fail("**Premium** is required to use this command")

        if image != None:
            if "-guild" in image:
                table = "guild_reskin"
                image = image.replace("-guild", "")
            else:
                table = "reskin"
        else:
            table = "reskin"
        if image is None:
            if len(ctx.message.attachments) == 0:
                raise discord.ext.commands.errors.CommandError(f"No Image provided")
            image = ctx.message.attachments[0].url
        configuration = await self.bot.db.fetch_config(ctx.guild.id, table) or {}
        if not configuration.get("status"):
            return await ctx.fail(
                f"Reskin webhooks are **disabled**\n> Use `{ctx.prefix}reskin setup` to set them up",
            )
        if table == "reskin":
            await self.bot.db.execute(
                "INSERT INTO reskin (user_id, avatar_url) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET avatar_url = $2",
                ctx.author.id,
                image,
            )
        else:
            await self.bot.db.execute(
                """INSERT INTO guild_reskin (guild_id, avatar_url) VALUES($1,$2) ON CONFLICT(guild_id) DO UPDATE SET avatar_url = excluded.avatar_url""",
                ctx.guild.id,
                image,
            )

        await ctx.success(f"Changed your **reskin avatar** to [**image**]({image})")

    @commands.group(
        name="reactionrole",
        aliases=["reactionroles", "rr", "reactrole"],
        example=",reactionrole",
        brief="Configure reaction role settings",
    )
    @commands.has_permissions(manage_roles=True)
    async def reactionrole(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @reactionrole.command(
        name="add",
        aliases=["a", "create", "c"],
        brief="Add a reaction role to a message",
        example=",autoreaction add [message] [emoji] [roles]",
    )
    async def reactionrole_add(
        self, ctx: Context, *, message_emoji_role: ReactionRoleConverter
    ):
        emoji = str(message_emoji_role["emoji"])
        message = message_emoji_role["message"]
        role = message_emoji_role["role"]

        try:
            await message.add_reaction(emoji)
        except discord.HTTPException as e:
            if e.code == 10014:
                return await ctx.fail(
                    "Invalid emoji provided. Please use a valid emoji."
                )
            raise

        if await self.bot.db.fetch(
            """SELECT * FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4 AND role_id = $5""",
            ctx.guild.id,
            message.channel.id,
            message.id,
            emoji,
            role.id,
        ):
            await self.bot.db.execute(
                """DELETE FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4 AND role_id = $5""",
                ctx.guild.id,
                message.channel.id,
                message.id,
                emoji,
                role.id,
            )
        await self.bot.db.execute(
            """INSERT INTO reactionrole (guild_id,channel_id,message_id,emoji,role_id,message_url) VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(guild_id,channel_id,message_id,emoji,role_id) DO UPDATE SET role_id = excluded.role_id""",
            ctx.guild.id,
            message.channel.id,
            message.id,
            emoji,
            role.id,
            message.jump_url,
        )

        return await ctx.success("**Reaction role** has been **added to that message**")

    def get_emoji(self, emoji: str):
        try:
            emoji = emoji
            return emoji
        except Exception:
            return emoji

    @reactionrole.command(
        name="remove",
        aliases=["delete", "del", "rem", "r", "d"],
        brief="Remove a reaction role from a message",
        example=",reactionrole remove [message_id] [emoji]",
    )
    async def reactionrole_remove(
        self,
        ctx: Context,
        message: discord.Message,
        emoji: Union[discord.Emoji, discord.PartialEmoji, str],
    ):
        if isinstance(emoji, (discord.Emoji, discord.PartialEmoji)):
            emoji = str(emoji)
        else:
            emoji = emoji
        await self.bot.db.execute(
            """DELETE FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4""",
            ctx.guild.id,
            message.channel.id,
            message.id,
            emoji,
        )
        return await ctx.success("**Removed** the **reaction role**")

    @reactionrole.command(
        name="clear",
        brief="Clear all reaction roles from a message",
        example=",reactionrole clear",
    )
    async def reactionrole_clear(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM reactionrole WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("**Cleared** all **reaction roles** if any exist")

    @reactionrole.command(
        name="list",
        brief="View a list of all reaction roles set to messages",
        example=",reactionrole list",
    )
    async def reactionrole_list(self, ctx: Context):
        rows = []
        i = 0
        for (
            channel_id,
            message_id,  # type: ignore
            emoji,
            role_id,
            message_url,
        ) in await self.bot.db.fetch(
            """SELECT channel_id,message_id,emoji,role_id,message_url FROM reactionrole WHERE guild_id = $1""",
            ctx.guild.id,
        ):
            if ctx.guild.get_channel(channel_id):  # type: ignore
                emoji = self.get_emoji(str(emoji))
                if role := ctx.guild.get_role(role_id):
                    i += 1
                    rows.append(
                        f"`{i}.` [Message]({message_url}) - {emoji} - {role.mention}"
                    )
        embed = discord.Embed(
            title=f"{ctx.guild.name}'s reaction roles",
            url=self.bot.domain,
            color=self.bot.color,
        )
        if len(rows) == 0:
            return await ctx.fail("**No reaction roles found**")
        return await self.bot.dummy_paginator(ctx, embed, rows, 10, "reaction role")

    @commands.group(
        "autoresponder",
        aliases=["ar", "autoresponse"],
        example=",autoresponder",
        brief="Configure auto responses for your server",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_messages=True)
    async def autoresponder(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command.qualified_name)

    @autoresponder.command(
        name="add",
        aliases=["a", "create"],
        brief="Add an automatic response to given phrase",
        example=",autoresponder add com, you're a troll --strict --reply",
    )
    @commands.has_permissions(manage_messages=True)
    async def autoresponder_add(self, ctx: Context, *, arg: Argument):
        # if "," not in arg: return await ctx.fail('use a comma to split the trigger and response')

        trigger = arg.first
        response = arg.second
        
        # Initialize flags with default values
        strict_flag = False
        reply_flag = False
        original_response = response
        
        if '--' in response:
            try:
                # Split the response from potential flags
                response_parts = response.split('--', 1)
                response = response_parts[0].strip()
                
                # Parse the flags
                flag_part = response_parts[1].strip()
                
                # Simple parsing for flags without values
                if "strict" in flag_part:
                    strict_flag = True
                if "reply" in flag_part:
                    reply_flag = True
                
                logger.info(f"Parsed flags: strict={strict_flag}, reply={reply_flag}")
            except Exception as e:
                # If flag parsing fails, assume it's part of the response
                logger.error(f"Flag parsing error: {e}")
                response = original_response
        
        if ctx.guild.id in self.bot.cache.autoresponders:
            if trigger in self.bot.cache.autoresponders[ctx.guild.id]:
                self.bot.cache.autoresponders[ctx.guild.id][trigger] = {
                    "response": response,
                    "strict": strict_flag,
                    "reply": reply_flag
                }
            else:
                self.bot.cache.autoresponders[ctx.guild.id][trigger] = {
                    "response": response,
                    "strict": strict_flag,
                    "reply": reply_flag
                }
        else:
            self.bot.cache.autoresponders[ctx.guild.id] = {
                trigger: {
                    "response": response,
                    "strict": strict_flag,
                    "reply": reply_flag
                }
            }
            
        await self.bot.db.execute(
            """INSERT INTO autoresponder (guild_id, trig, response, strict, reply) 
               VALUES($1, $2, $3, $4, $5) 
               ON CONFLICT (guild_id, trig) 
               DO UPDATE SET response = excluded.response, 
                            strict = excluded.strict,
                            reply = excluded.reply""",
            ctx.guild.id,
            trigger,
            response,
            strict_flag,
            reply_flag
        )
        
        flag_info = []
        if strict_flag:
            flag_info.append("strict matching")
        if reply_flag:
            flag_info.append("with reply")
            
        flag_text = f" ({', '.join(flag_info)})" if flag_info else ""
        await ctx.success(f"**Auto-responder** ``{trigger}``{flag_text} applied")

    @autoresponder.command(
        name="remove",
        aliases=["del", "d", "r", "rem"],
        brief="Remove an automatic response from a given phrase",
        example=",autoresponder remove hi",
    )
    @commands.has_permissions(manage_messages=True)
    async def autoresponder_remove(self, ctx: Context, *, trigger: str):
        if ctx.guild.id not in self.bot.cache.autoresponders:
            return await ctx.fail("**Auto-Response** has not been **setup**")
        if trigger not in self.bot.cache.autoresponders[ctx.guild.id]:
            return await ctx.fail(
                f"**No auto-responder** found with trigger **{trigger}**"
            )
        await self.bot.db.execute(
            """DELETE FROM autoresponder WHERE guild_id = $1 AND trig = $2""",
            ctx.guild.id,
            trigger,
        )
        self.bot.cache.autoresponders[ctx.guild.id].pop(trigger)
        return await ctx.success(
            f"**Auto-responder** with the trigger ``{trigger}`` **Removed**"
        )

    @autoresponder.command(
        name="clear",
        aliases=["cl"],
        brief="Clear all the current auto responders",
        example=",autoresponder clear",
    )
    @commands.has_permissions(manage_messages=True)
    async def autoresponder_clear(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM autoresponder WHERE guild_id = $1""", ctx.guild.id
        )
        try:
            self.bot.cache.autoresponders.pop(ctx.guild.id)
        except Exception:
            pass
        return await ctx.success("**Cleared** all **auto-responders**")

    @autoresponder.command(
        name="list",
        aliases=["l", "show"],
        brief="Show a list of all current auto responses",
        example=",autoresponder list",
    )
    @commands.has_permissions(manage_messages=True)
    async def autoresponder_list(self, ctx: Context):
        rows = []
        for trig, response, strict, reply in await self.bot.db.fetch(
            """SELECT trig, response, strict, reply FROM autoresponder WHERE guild_id = $1""",
            ctx.guild.id,
        ):
            flag_info = []
            if strict:
                flag_info.append("strict")
            if reply:
                flag_info.append("reply")
                
            flag_text = f" [{', '.join(flag_info)}]" if flag_info else ""
            rows.append(f"`{trig}`{flag_text} - `{response}`")
            
        if len(rows) > 0:
            embed = discord.Embed(
                title=f"{ctx.guild.name}'s auto-responders",
                url=self.bot.domain,
                color=self.bot.color,
            )
            await self.bot.dummy_paginator(ctx, embed, rows, 10, "autoresponder")
        else:
            return await ctx.fail("**Server** has no **auto-responders setup**")

    @commands.group(
        name="boost",
        aliases=["bm", "boostmessage"],
        brief="Configure boost messages for the server",
        example=",boost",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg(self, ctx: Context):
        if ctx.subcommand_passed is not None:
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @boostmsg.command(
        name="setup",
        aliases=(
            "on",
            "enable",
        ),
        brief="Enable boost messages for the guild",
        example=",boost setup",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_enable(self, ctx: Context) -> discord.Message:
        if await self.bot.db.fetchrow(
            "SELECT * FROM guild.boost WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Boost messages** are already **enabled**")

        await self.bot.db.execute(
            "INSERT INTO guild.boost (guild_id, channel_id, message) VALUES ($1, $2, $3)",
            ctx.guild.id,
            ctx.channel.id,
            "Thank you for boosting the server, {user.mention}!",
        )
        return await ctx.success("**Enabled** boost messages")

    @boostmsg.command(
        name="reset",
        aliases=(
            "off",
            "disable",
        ),
        brief="Disable boost messages for the guild",
        example=",boost reset",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_disable(self, ctx: Context) -> discord.Message:
        if not await self.bot.db.fetchrow(
            "SELECT * FROM guild.boost WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Boost messages** are already **disabled**")

        await self.bot.db.execute(
            "DELETE FROM guild.boost WHERE guild_id = $1", ctx.guild.id
        )
        return await ctx.success("**Disabled** boost messages")

    @boostmsg.command(
        name="channel",
        aliases=("chan",),
        brief="Assign a channel for boost messages to be sent",
        example=",boost channel #boostchannel",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_channel(
        self, ctx: Context, channel: discord.TextChannel
    ) -> discord.Message:
        if not await self.bot.db.fetchrow(
            "SELECT * FROM guild.boost WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Boost messages** are not **enabled**")

        await self.bot.db.execute(
            "UPDATE guild.boost SET channel_id = $1 WHERE guild_id = $2",
            channel.id,
            ctx.guild.id,
        )
        return await ctx.success(f"**Boost message channel** set to {channel.mention}")

    @boostmsg.command(
        name="message",
        aliases=("msg",),
        brief="Set the message to be sent when someone boosts the guild",
        example=",boost message [code]",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_message(self, ctx: Context, *, message: str) -> discord.Message:
        if not await self.bot.db.fetchrow(
            "SELECT * FROM guild.boost WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Boost messages** are not **enabled**")
        await self.bot.send_embed(ctx.channel, message, user=ctx.author)
        await self.bot.db.execute(
            "UPDATE guild.boost SET message = $1 WHERE guild_id = $2",
            message,
            ctx.guild.id,
        )
        return await ctx.success(f"**Boost message** set to ``{message}``")

    @boostmsg.command(
        name="view",
        brief="View the current boost message embed code",
        example=",boost view",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchrow(
                "SELECT message FROM guild.boost WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail("**Boost messages** are not **enabled**")
        return await ctx.success(f"```{message}```")

    @boostmsg.command(
        name="test", brief="Test the set boost message", example=",boost test"
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_test(self, ctx: Context):
        if not (
            data := await self.bot.db.fetchrow(
                "SELECT * FROM guild.boost WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail("**Boost messages** are not **enabled**")

        channel = self.bot.get_channel(data["channel_id"])
        if not channel:
            return await ctx.fail("Boost message channel not found")

        await self.bot.send_embed(channel, data["message"], user=ctx.author)
        return await ctx.success("**Boost message** was sent")

    @commands.group(name="thread", invoke_without_command=True)
    async def _thread(self, ctx):
        return await ctx.send_help(ctx.command.qualified_name)

    @_thread.command(
        name="lock", brief="Locks a thread", example=",thread lock #channel"
    )
    @commands.has_permissions(manage_threads=True)
    async def thread_lock(self, ctx, thread: Optional[discord.Thread] = None):
        if not thread:
            thread = ctx.channel
        if not isinstance(thread, discord.Thread):
            return await ctx.fail("> This channel is not a thread!")

        await thread.edit(
            locked=True,
            archived=True,
            reason=f"Thread locked by moderator {ctx.author.name}",
        )
        return await ctx.success(f"Successfully locked {thread.name}")

    @_thread.command(
        name="unlock", brief="Unlocks a thread", example=",thread unlock #channel"
    )
    @commands.has_permissions(manage_threads=True)
    async def thread_unlock(self, ctx, thread: Optional[discord.Thread] = None):
        if not thread:
            thread = ctx.channel
        if not isinstance(thread, discord.Thread):
            return await ctx.fail("> This channel is not a thread!")

        await thread.edit(
            locked=False,
            archived=False,
            reason=f"Thread unlocked by moderator {ctx.author.name}",
        )
        return await ctx.success(f"Successfully unlocked {thread.name}")

    @_thread.command(
        name="remove",
        brief="Remove a member from the thread",
        example=",thread remove #thread @member",
    )
    @commands.has_permissions(manage_threads=True)
    async def thread_remove(
        self,
        ctx,
        thread: Optional[discord.Thread] = None,
        member: discord.Member = None,
    ):
        if not thread:
            thread = ctx.channel
        if not isinstance(thread, discord.Thread):
            return await ctx.fail("> This channel is not a thread!")

        if not member:
            return await ctx.fail("> Please specify a member to remove!")

        try:
            await thread.fetch_member(member.id)
        except discord.NotFound:
            return await ctx.fail(f"{member.mention} is not in this thread!")

        await thread.remove_user(member)
        return await ctx.success(
            f"Successfully removed {member.mention} from {thread.name}"
        )

    @_thread.command(
        name="add",
        brief="Add a member to the thread",
        example=",thread add #thread @member",
    )
    @commands.has_permissions(manage_threads=True)
    async def thread_add(
        self,
        ctx,
        thread: Optional[discord.Thread] = None,
        member: discord.Member = None,
    ):
        if not thread:
            thread = ctx.channel
        if not isinstance(thread, discord.Thread):
            return await ctx.fail("> This channel is not a thread!")

        if not member:
            return await ctx.fail("> Please specify a member to add!")

        if await thread.fetch_member(member.id):
            return await ctx.fail(f"{member.mention} is already in this thread!")

        await thread.add_user(member)
        return await ctx.success(
            f"Successfully added {member.mention} to {thread.name}"
        )

    @commands.group(
        name="counter",
        invoke_without_command=True,
        brief="Manage and track counting channels.",
    )
    async def counter(self, ctx):
        """Base command for the counter."""
        return await ctx.send_help(ctx.command.qualified_name)

    @counter.command(name="enable", brief="Enable the counter in a specific channel.")
    @has_permissions(manage_channels=True)
    async def counter_enable(self, ctx, channel: discord.TextChannel):
        """Enable the counter in a specific channel."""
        # Check if the channel is already enabled
        row = await self.bot.db.fetchrow(
            "SELECT current_count FROM counter_channels WHERE channel_id = $1",
            channel.id,
        )

        if row:
            await ctx.warning(f"{channel.mention} is already enabled for the counter.")
            return

        # Add the channel to the database with an initial count of 1
        await self.bot.db.execute(
            "INSERT INTO counter_channels (channel_id, current_count) VALUES ($1, $2)",
            channel.id,
            1,
        )
        await ctx.success(f"Counter enabled in {channel.mention}!")

        # Send the first message
        first_message = await channel.send("1")
        await first_message.add_reaction("✅")

    @counter.command(name="disable", brief="Disabel the counter in a specific channel.")
    @has_permissions(manage_channels=True)
    async def counter_disable(self, ctx, channel: discord.TextChannel):
        """Disable the counter in a specific channel."""
        row = await self.bot.db.fetchrow(
            "SELECT current_count FROM counter_channels WHERE channel_id = $1",
            channel.id,
        )

        if not row:
            await ctx.warning(f"{channel.mention} is not an active counter channel.")
            return

        # Remove the channel from the database
        await self.bot.db.execute(
            "DELETE FROM counter_channels WHERE channel_id = $1", channel.id
        )
        await ctx.success(f"Counter disabled in {channel.mention}.")

    @commands.group(
        name="pingonjoin",
        aliases=["poj"],
        brief="Toggle ping on join",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_guild=True)
    async def pingonjoin(self, ctx: Context):
        return await ctx.send_help(ctx.command.qualified_name)

    @pingonjoin.command(name="enable", aliases=["on"], brief="Enable ping on join")
    @commands.has_permissions(manage_guild=True)
    async def pingonjoin_enable(
        self, ctx: Context, channel: discord.TextChannel, threshold: int = None
    ):
        threshold = threshold or 1
        await self.bot.db.execute(
            """
            INSERT INTO pingonjoin (guild_id, channel_id, threshold) 
            VALUES ($1, $2, $3)
              ON CONFLICT (guild_id) 
              DO UPDATE SET channel_id = excluded.channel_id, threshold = excluded.threshold
            """,
            ctx.guild.id,
            channel.id,
            threshold,
        )
        return await ctx.success(
            f"**Ping on join** enabled in {channel.mention} with a threshold of {threshold}"
        )

    @pingonjoin.command(
        name="message",
        aliases=["msg"],
    )
    @commands.has_permissions(manage_guild=True)
    async def pingonjoin_message(self, ctx: Context, *, message: EmbedConverter):
        await self.bot.db.execute(
            "UPDATE pingonjoin SET message = $1 WHERE guild_id = $2",
            message,
            ctx.guild.id,
        )
        return await ctx.success(f"**Ping on join** message set to {message}")

    @pingonjoin.command(
        name="disable", aliases=["off", "reset"], brief="Resets ping on join module"
    )
    @commands.has_permissions(manage_guild=True)
    async def pingonjoin_disable(self, ctx: Context):
        await self.bot.db.execute(
            "DELETE FROM pingonjoin WHERE guild_id = $1", ctx.guild.id
        )
        return await ctx.success("**Ping on join** has been disabled")

    @commands.group(
        name="buttonrole",
        aliases=["buttonroles"],
        brief="No Description Provided",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @buttonrole.command(
        name="remove",
        brief="Remove a button role from a message",
        example=",buttonrole remove discord.channels/... 3",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_remove(self, ctx: Context, message: Message, index: int):
        entries = await self.bot.db.fetch(
            """SELECT index FROM button_roles WHERE message_id = $1 ORDER BY index ASC"""
        )
        if index > len(entries):
            index = len(index)
        await self.bot.db.execute(
            """DELETE FROM button_roles WHERE message_id = $1 AND index = $2""",
            message.id,
            entries[index - 1].index,
        )
        view = ButtonRoleView(self.bot, ctx.guild.id, message.id)
        await view.prepare()
        await message.edit(view=view)
        return await ctx.success(
            f"successfully removed that button from the button roles on [this message]({message.jump_url})"
        )

    @buttonrole.command(name="reset", brief="Clears every button role from guild")
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_reset(self, ctx: Context):
        for row in await self.bot.db.fetch(
            """SELECT message_id, channel_id FROM button_roles WHERE guild_id = $1""",
            ctx.guild.id,
        ):
            channel = ctx.guild.get_channel(row.channel_id)
            if not channel:
                continue
            try:
                message = await channel.fetch_message(row.message_id)
            except Exception:
                continue
            await message.edit(view=None)
        await self.bot.db.execute(
            """DELETE FROM button_roles WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("successfully cleared all button roles")

    @buttonrole.command(
        name="removeall",
        brief="Removes all button roles from a message",
        example=",buttonrole removeall discord.com/channels/...",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_removeall(self, ctx: Context, message: Message):
        await message.edit(view=None)
        await self.bot.db.execute(
            """DELETE FROM button_roles WHERE message_id = $1""", message.id
        )
        return await ctx.success(
            f"successfully removed all button roles from [this message]({message.jump_url})"
        )

    @buttonrole.command(name="list", brief="View a list of every button role")
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_list(self, ctx: Context):
        rows = []
        embed = Embed(color=self.bot.color, title="Button roles").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        i = 0
        for row in await self.bot.db.fetch(
            """SELECT message_id, channel_id, role_id FROM button_roles WHERE guild_id = $1 ORDER BY index ASC""",
            ctx.guild.id,
        ):
            if not (channel := ctx.guild.get_channel(row.channel_id)):
                asyncio.ensure_future(
                    self.bot.db.execute(
                        """DELETE FROM button_roles WHERE channel_id = $1 AND guild_id = $2""",
                        row.channel_id,
                        ctx.guild.id,
                    )
                )
                continue
            try:
                message = await channel.fetch_message(row.message_id)
            except Exception:
                asyncio.ensure_future(
                    self.bot.db.execute(
                        """DELETE FROM button_roles WHERE message_id = $1 AND guild_id = $2""",
                        row.message_id,
                        ctx.guild.id,
                    )
                )
                continue
            if not (role := ctx.guild.get_role(row.role_id)):
                asyncio.ensure_future(
                    self.bot.db.execute(
                        """DELETE FROM button_roles WHERE role_id = $1 AND guild_id = $2""",
                        row.role_id,
                        ctx.guild.id,
                    )
                )
                continue
            i += 1
            rows.append(f"`{i}` {role.mention} - [message]({message.jump_url})")
        return await ctx.paginate(embed, rows, 10, "button role", "button roles")

    @buttonrole.command(name="add", brief="add a button role", example="")
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_add(
        self,
        ctx: Context,
        message: Message,
        role: Role,
        style: StyleConverter,
        emoji: Optional[PartialEmojiConverter] = None,
        label: Optional[str] = None,
    ):
        if not message.author.id == self.bot.user.id:
            raise CommandError("That is not a message that I created")
        if not emoji and not label:
            raise CommandError("either an emoji or label must be provided")
        indexes = await self.bot.db.fetch(
            """SELECT index FROM button_roles WHERE message_id = $1 ORDER BY index ASC""",
            message.id,
        )
        try:
            index = indexes[-1].index + 1
        except Exception:
            index = 1
        if label is not None and len(label) > 100:
            raise CommandError("label must be 100 characters or less")
        await self.bot.db.execute(
            """INSERT INTO button_roles (guild_id, message_id, channel_id, role_id, style, emoji, label, index) VALUES($1, $2, $3, $4, $5, $6, $7, $8)""",
            ctx.guild.id,
            message.id,
            message.channel.id,
            role.id,
            style,
            emoji,
            label,
            index,
        )
        view = ButtonRoleView(self.bot, ctx.guild.id, message.id)
        await view.prepare()
        await message.edit(view=view)
        return await ctx.success(f"Successfully added button role for {role.mention} to [this message]({message.jump_url})")

    @commands.group(
        name="rolelock",
        brief="Manage role locks.",
        invoke_without_command=True,
        usage=",rolelock [subcommand]",
    )
    async def rolelock(self, ctx):
        """RoleLock management commands."""
        return await ctx.send_help(ctx.command.qualified_name)

    @rolelock.command(
        name="add",
        brief="Add role locks for locker roles.",
        usage=",rolelock add <@locker_role> <@locked_role>, <@locked_role>, ...",
    )
    @commands.has_permissions(manage_guild=True)
    async def add(self, ctx, locker: discord.Role, *locked_roles: str):
        """
        Add one or multiple role locks to allow a locker role to grant certain locked roles.
        Example: ,rolelock add @staff @mod, @admin
        """
        if not locked_roles:
            return await ctx.send_help(ctx.command.qualified_name)

        locked_role_ids = []
        for locked_role in locked_roles:
            try:
                locked_role_obj = await commands.RoleConverter().convert(
                    ctx, locked_role.strip()
                )
                locked_role_ids.append(locked_role_obj.id)
            except commands.RoleNotFound:
                await ctx.send(
                    f"Could not find role: `{locked_role.strip()}`. Skipping."
                )

        success_roles = []
        for locked_role_id in locked_role_ids:
            await self.bot.db.execute(
                "INSERT INTO rolelock (guild_id, locker_role, locked_role) VALUES ($1, $2, $3)",
                ctx.guild.id,
                locker.id,
                locked_role_id,
            )
            success_roles.append(locked_role_id)

        if success_roles:
            success_names = ", ".join(f"<@&{role_id}>" for role_id in success_roles)
            await ctx.send(
                f"{locker.mention} can now grant the following roles: {success_names}."
            )
        else:
            await ctx.send("No valid locked roles were provided.")

    @rolelock.command(
        name="remove",
        brief="Remove a role lock.",
        usage=",rolelock remove <@locker_role>",
    )
    @commands.has_permissions(manage_guild=True)
    async def remove(self, ctx, locker: discord.Role):
        """Remove a role lock by specifying the locker role."""
        await self.bot.db.execute(
            "DELETE FROM rolelock WHERE guild_id = $1 AND locker_role = $2",
            ctx.guild.id,
            locker.id,
        )
        await ctx.send(f"All locks related to {locker.mention} have been removed.")

    @rolelock.command(name="list", brief="List all role locks.", usage=",rolelock list")
    @commands.has_permissions(manage_guild=True)
    async def list(self, ctx):
        """List all role locks set in the guild."""
        rows = await self.bot.db.fetch(
            "SELECT locker_role, locked_role FROM rolelock WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not rows:
            await ctx.send("No role locks have been set in this server.")
        else:
            description = "\n".join(
                f"<@&{locker}> can grant <@&{locked}>" for locker, locked in rows
            )
            await ctx.send(f"RoleLocks in this server:\n{description}")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Listen for role updates and handle locked role enforcement."""
        if before.roles == after.roles:
            return

        added_roles = [role for role in after.roles if role not in before.roles]

        for role in added_roles:
            cache_key = f"rolelock:{after.guild.id}:{after.id}:{role.id}"
            
            if await self.bot.glory_cache.get(cache_key):
                continue
                
            rows = await self.bot.db.fetch(
                "SELECT locker_role, locked_role, authorized_user_ids FROM rolelock WHERE guild_id = $1 AND locked_role = $2",
                after.guild.id,
                role.id,
            )

            if rows:
                locker_role_id = rows[0]["locker_role"]
                locked_role_id = rows[0]["locked_role"]
                authorized_user_ids = (
                    rows[0]["authorized_user_ids"].split(",")
                    if rows[0]["authorized_user_ids"]
                    else []
                )

                if role.id == locked_role_id:
                    has_locker_role = locker_role_id in [r.id for r in after.roles]

                    assigner_id = None
                    async for entry in after.guild.audit_logs(
                        limit=5, action=discord.AuditLogAction.member_role_update
                    ):
                        if entry.target.id == after.id and role in entry.changes.after:
                            assigner_id = entry.user.id
                            break

                    if not (
                        has_locker_role
                        or (assigner_id and str(assigner_id) in authorized_user_ids)
                    ):
                        try:
                            await self.bot.glory_cache.set(cache_key, 1, 30)
                            
                            await after.remove_roles(
                                role,
                                reason="RoleLock Enforcement: Unauthorized role assignment.",
                            )
                            print(
                                f"Removed {role.name} from {after.name}. Unauthorized role assignment."
                            )
                        except discord.Forbidden:
                            print(
                                f"Failed to remove {role.name} from {after.name}. Permissions issue."
                            )
                        except Exception as e:
                            print(
                                f"Unexpected error removing role from {after.name}: {e}"
                            )
                    else:
                        print(
                            f"Role {role.name} added to {after.name} by an authorized user or locker role."
                        )

                # Handle authorized users if the locker role is added
                elif (
                    role.id == locker_role_id
                    and str(after.id) not in authorized_user_ids
                ):
                    authorized_user_ids.append(str(after.id))
                    updated_ids = ",".join(authorized_user_ids)
                    await self.bot.db.execute(
                        "UPDATE rolelock SET authorized_user_ids = $1 WHERE guild_id = $2 AND locked_role = $3",
                        updated_ids,
                        after.guild.id,
                        locked_role_id,
                    )
                    print(
                        f"User {after.name} added to authorized users for locked role {locked_role_id}."
                    )

    @commands.command(
        name="drag",
        brief="Drag a member to your voicechannel",
        example=",drag @shittour",
        aliases=["d"],
    )
    @commands.has_permissions(move_members=True, manage_channels=True)
    async def drag(self, ctx: Context, member: discord.Member):
        if not ctx.author.voice:
            return await ctx.send("You must be in a voice channel to use this command.")
        if not member.voice:
            return await ctx.send("The user must be in a voice channel to drag them.")
        await member.move_to(ctx.author.voice.channel)
        await ctx.success(f"Dragged {member.mention} to your voice channel.")

    @commands.command(
        name="clearinvites", brief="Clear all server invites", example=",clearinvites"
    )
    @commands.has_permissions(manage_guild=True)
    async def clearinvites(self, ctx: Context):
        invites = await ctx.guild.invites()
        if not invites:
            return await ctx.fail("No invites found in this server")

        await ctx.confirm("Are you sure you want to delete all invites?")
        async with ctx.typing():
            deleted = 0
            for invite in invites:
                try:
                    await invite.delete(reason=f"Cleared by {str(ctx.author)}")
                    deleted += 1
                except:
                    continue
            return await ctx.success(f"Successfully cleared `{deleted}` invites")

    @commands.command(
        name="unbanall", brief="Unbans every member in the guild", example=",unbanall"
    )
    @commands.has_permissions(ban_members=True)
    async def unbanall(self, ctx: Context):
        if (
            ctx.author.id not in self.bot.owner_ids
            and ctx.author.id != ctx.guild.owner_id
        ):
            return await ctx.fail("You must be the server owner to use this command")

        await ctx.confirm("Are you sure you want to unban everyone?")

        bans = [entry async for entry in ctx.guild.bans()]
        if not bans:
            return await ctx.fail("There are no banned users in this server")

        @lazy(pure=False, batch_size=100)
        async def unban_batch(guild, users, author):
            results = []
            for user in users:
                try:
                    await guild.unban(user, reason=f"Mass unban by {str(author)}")
                    results.append(True)
                except:
                    results.append(False)
            return results

        async with ctx.typing():
            batch_size = 100
            batches = [
                bans[i : i + batch_size] for i in range(0, len(bans), batch_size)
            ]

            unban_tasks = [
                unban_batch(
                    ctx.guild, [ban_entry.user for ban_entry in batch], ctx.author
                )
                for batch in batches
            ]

            batch_results = await compute_many(*unban_tasks)

            unbanned = sum(
                sum(1 for result in batch if result) for batch in batch_results
            )

            return await ctx.success(
                f"Successfully unbanned `{unbanned}` out of `{len(bans)}` users"
            )

    @commands.group(
        name="antiselfreact", aliases=["antisr"], brief="Anti-Self-React feature"
    )
    @commands.has_permissions(manage_messages=True)
    async def antisr(self, ctx: Context):
        """Base command group for the Anti-Self-React feature."""
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command.qualified_name)

    @antisr.command(
        name="enable", aliases=["on"], brief="Enable Anti-Self-React in the guild"
    )
    @commands.has_permissions(manage_messages=True)
    async def enable(self, ctx: Context):
        """Enable Anti-Self-React in the guild."""
        await self.bot.db.execute(
            "INSERT INTO antisr_guilds (guild_id) VALUES ($1) ON CONFLICT(guild_id) DO NOTHING;",
            ctx.guild.id,
        )
        await ctx.success("AntiSelfReact has been enabled in this server.")

    @antisr.command(
        name="disable", aliases=["off"], brief="Disable Anti-Self-React in the guild"
    )
    @commands.has_permissions(manage_messages=True)
    async def disable(self, ctx: Context):
        """Disable Anti-Self-React in the guild."""
        await self.bot.db.execute(
            "DELETE FROM antisr_guilds WHERE guild_id = $1;", ctx.guild.id
        )
        await ctx.success("AntiSelfReact has been disabled in this server.")

    @antisr.command(
        name="add", aliases=["include"], brief="Add a user to the Anti-Self-React list"
    )
    @commands.has_permissions(manage_messages=True)
    async def add(self, ctx: Context, user: discord.Member):
        """Add a user to the Anti-Self-React list."""
        await self.bot.db.execute(
            "INSERT INTO antisr_users (guild_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING;",
            ctx.guild.id,
            user.id,
        )
        await ctx.success(f"{user.mention} has been added to the AntiSelfReact list.")

    @antisr.command(
        name="remove",
        aliases=["exclude"],
        brief="Remove a user from the Anti-Self-React list",
    )
    @commands.has_permissions(manage_messages=True)
    async def remove(self, ctx: Context, user: discord.Member):
        """Remove a user from the Anti-Self-React list."""
        await self.bot.db.execute(
            "DELETE FROM antisr_users WHERE guild_id = $1 AND user_id = $2;",
            ctx.guild.id,
            user.id,
        )
        await ctx.success(
            f"{user.mention} has been removed from the AntiSelfReact list."
        )

    @antisr.command(name="ignore", aliases=["skip"], brief="Ignore a user or role")
    @commands.has_permissions(manage_messages=True)
    async def ignore(self, ctx: Context, target: discord.Object):
        """Ignore a user or role from Anti-Self-React."""
        is_role = isinstance(target, discord.Role)
        await self.bot.db.execute(
            "INSERT INTO antisr_ignores (guild_id, target_id, is_role) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING;",
            ctx.guild.id,
            target.id,
            is_role,
        )
        await ctx.success(
            f"{'Role' if is_role else 'User'} {target.id} has been ignored."
        )

    @antisr.command(
        name="unignore", aliases=["unskip"], brief="Unignore a user or role"
    )
    @commands.has_permissions(manage_messages=True)
    async def unignore(
        self, ctx: Context, target: Union[discord.Role, discord.Member, discord.User]
    ):
        """Unignore a user or role from Anti-Self-React."""
        is_role = isinstance(target, discord.Role)
        await self.bot.db.execute(
            "DELETE FROM antisr_ignores WHERE guild_id = $1 AND target_id = $2 AND is_role = $3;",
            ctx.guild.id,
            target.id,
            is_role,
        )
        await ctx.success(
            f"{'Role' if is_role else 'User'} {target.id} is no longer ignored."
        )

    @commands.Cog.listener("on_raw_reaction_add")
    async def antireact(self, payload: discord.RawReactionActionEvent):
        """Handle reaction events and enforce Anti-Self-React."""
        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        if not await self.bot.db.fetchrow(
            "SELECT 1 FROM antisr_guilds WHERE guild_id = $1;", guild.id
        ):
            return

        try:
            member = guild.get_member(payload.user_id) or await guild.fetch_member(
                payload.user_id
            )
        except discord.NotFound:
            return
        except discord.HTTPException as e:
            logger.error(f"Member fetch failed: {e}")
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return
        except discord.HTTPException as e:
            logger.error(f"Message fetch failed: {e}")
            return

        if message.author.id != member.id:
            return

        role_ids = [role.id for role in member.roles]
        exempt = await self.bot.db.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 FROM antisr_ignores
                WHERE guild_id = $1
                AND (
                    (target_id = $2 AND NOT is_role) OR
                    (target_id = ANY($3::BIGINT[]) AND is_role)
                )
            )
            """,
            guild.id,
            member.id,
            role_ids,
        )

        if exempt:
            return

        if not await self.bot.db.fetchrow(
            "SELECT 1 FROM antisr_users WHERE guild_id = $1 AND user_id = $2;",
            guild.id,
            member.id,
        ):
            return

        try:
            await message.remove_reaction(payload.emoji, member)
        except discord.Forbidden:
            logger.warning(f"Missing reaction manage permissions in {guild.id}")
        except discord.HTTPException as e:
            logger.error(f"Reaction removal failed: {e}")

        try:
            await member.kick(reason="Anti-Self-React: Reacted to own message")
            logger.info(f"Kicked {member} ({member.id}) in {guild} for self-reacting")
        except discord.Forbidden:
            logger.warning(f"Missing kick permissions in {guild.id}")
        except discord.HTTPException as e:
            logger.error(f"Kick failed: {e}")
        else:
            await self.bot.db.execute(
                "DELETE FROM antisr_users WHERE guild_id = $1 AND user_id = $2;",
                guild.id,
                member.id,
            )


async def setup(bot: "Greed") -> None:
    await bot.add_cog(Servers(bot))
