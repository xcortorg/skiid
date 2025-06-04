import io
import os
import re
import zipfile
import asyncio
import discord
import aiohttp
import datetime
import functools
import validators
import unicodedata

from io import BytesIO
from PIL import Image, ImageSequence
from collections import defaultdict
from typing import List, Tuple, Union
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

from discord import Embed, Emoji, File, PartialEmoji, HTTPException, NotFound
from discord.errors import HTTPException
from discord.ext.commands import BadArgument, Cog, bot_has_guild_permissions, command, group, has_guild_permissions

from modules.styles import colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.misc.views import DownloadAsset

def generate(img):
    drawing = svg2rlg(BytesIO(img))
    png_data = renderPM.drawToString(drawing, fmt='PNG')
    return io.BytesIO(png_data)

class Emoji(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Emoji commands"
        self.locks = defaultdict(asyncio.Lock)

    async def emoji_bucket(self, ctx: EvelinaContext, emoj: PartialEmoji):
        """Avoid emoji adding rate limit"""
        if not await self.bot.cache.get("emojis"):
            await self.bot.cache.set("emojis", {ctx.guild.id: []})
        emojis: dict = await self.bot.cache.get("emojis")
        if not emojis.get(ctx.guild.id):
            emojis[ctx.guild.id] = []
        guild_emojis: List[Tuple[PartialEmoji, datetime.datetime]] = emojis[ctx.guild.id]
        guild_emojis.append(tuple([emoj, datetime.datetime.now()]))
        for g in guild_emojis:
            if (datetime.datetime.now() - g[1]).total_seconds() > 3600:
                guild_emojis.remove(g)
        emojis.update({ctx.guild.id: guild_emojis})
        await self.bot.cache.set("emojis", emojis)
        if len(guild_emojis) > 29:
            raise BadArgument(f"Guild got rate limited for adding emojis. Try again **in the next hour**")
        return False
    
    async def get_sticker(self, ctx: EvelinaContext):
        """Retrieves the first sticker found in the message, reply, or channel history."""
        if ctx.message.stickers:
            return ctx.message.stickers[0]
        if ctx.message.reference:
            ref_message = ctx.message.reference.resolved
            if ref_message and ref_message.stickers:
                return ref_message.stickers[0]
        async for message in ctx.channel.history(limit=50):
            if message.stickers:
                return message.stickers[0]
        raise BadArgument("Sticker not found. Please provide a message containing a sticker or reply to one.")

    @group(name="emoji", invoke_without_command=True, case_insensitive=True)
    async def emoji(self, ctx: EvelinaContext):
        """Manage the server's emojis"""
        return await ctx.create_pages()

    @command(name="steal", aliases=["add"], brief="manage expressions", usage="steal 🦮 mommy")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def steal(self, ctx: EvelinaContext, emoji: PartialEmoji = None, *, name: str = None):
        """Steal an emoji from another server"""
        return await self.emoji_steal(ctx, emoji=emoji, name=name)

    @emoji.command(name="add", brief="manage expressions", usage="emoji add mommy")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def emoji_add(self, ctx: EvelinaContext, name: str):
        """Add an emoji to the server"""
        reference_attachments = []
        if ctx.message.reference and ctx.message.reference.resolved:
            reference_attachments = ctx.message.reference.resolved.attachments
        if not ctx.message.attachments and not reference_attachments:
            return await ctx.send_warning("Please attach an image to use as a sticker.")
        attachments = ctx.message.attachments or reference_attachments
        attachment = attachments[0]
        if not attachment.content_type.startswith('image/'):
            return await ctx.send_warning("Attached file must be an image.")
        image_bytes = await attachment.read()
        is_animated = attachment.content_type == 'image/gif'
        if is_animated and len([e for e in ctx.guild.emojis if e.animated]) >= ctx.guild.emoji_limit:
            return await ctx.send_warning("This server cannot have new animated emojis anymore")
        elif not is_animated and len([e for e in ctx.guild.emojis if not e.animated]) >= ctx.guild.emoji_limit:
            return await ctx.send_warning("This server cannot have new static emojis anymore")
        if name is not None and len(name) > 32:
            return await ctx.send_warning("Emoji name is too long")
        try:
            emoji = await ctx.guild.create_custom_emoji(
                name=name,
                image=image_bytes,
                reason=f"Emoji added by {ctx.author}"
            )
            await ctx.send_success(f"Added {emoji} as **[{emoji.name}]({emoji.url})**")
        except HTTPException as e:
            await ctx.send_warning(f"An error occurred while trying to add the emoji\n```{e}```")

    @emoji.command(name="steal", brief="manage expressions", usage="emoji steal 🦮 mommy")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def emoji_steal(self, ctx: EvelinaContext, emoji: PartialEmoji = None, *, name: str = None):
        """Steal an emoji from another server"""
        async def download_image(url):
            return await self.bot.session.get_bytes(url) 
        async def create_emoji(image_bytes, emoji_name):
            try:
                return await ctx.guild.create_custom_emoji(name=emoji_name, image=image_bytes, reason=f"Emoji added by {ctx.author}")
            except HTTPException as e:
                await ctx.send_warning(f"Error creating emoji: {e}")
                return None
        if ctx.message.reference:
            try:
                ref_message = await ctx.fetch_message(ctx.message.reference.message_id)
                emojis = re.findall(r'<a?:(\w+):(\d+)>', ref_message.content)
                if emojis:
                    emoji_name, emoji_id = emojis[0]
                    emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if ref_message.content.startswith('<a') else 'png'}"
                    image_bytes = await download_image(emoji_url)
                    if await self.emoji_bucket(ctx, emoji_url):
                        return
                    emoji_created = await create_emoji(image_bytes, emoji_name)
                    if emoji_created:
                        await ctx.send_success(f"Added {emoji_created} as **[{emoji_name}]({emoji_url})**")
            except HTTPException:
                await ctx.send_warning(f"You have reached the emoji limit for this server")
        elif emoji:
            if validators.url(str(emoji)):
                try:
                    image_bytes = await download_image(str(emoji))
                    if await self.emoji_bucket(ctx, str(emoji)):
                        return
                    emoji_created = await create_emoji(image_bytes, name or "new_emoji")
                    if emoji_created:
                        await ctx.send_success(f"Added {emoji_created} as **[{name or 'new_emoji'}]({emoji_created.url})**")
                except HTTPException:
                    await ctx.send_warning(f"You have reached the emoji limit for this server")
            else:
                match = re.match(r'<a?:(\w+):(\d+)>', str(emoji))
                if match:
                    emoji_name, emoji_id = match.groups()
                    emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if str(emoji).startswith('<a') else 'png'}"
                    try:
                        image_bytes = await download_image(emoji_url)
                        if await self.emoji_bucket(ctx, emoji_url):
                            return
                        emoji_created = await create_emoji(image_bytes, name or emoji_name)
                        if emoji_created:
                            await ctx.send_success(f"Added {emoji_created} as **[{name or emoji_name}]({emoji_url})**")
                    except HTTPException:
                        await ctx.send_warning(f"You have reached the emoji limit for this server")
                else:
                    await ctx.send_warning("Invalid emoji provided")
        else:
            return await ctx.create_pages()

    @emoji.command(name="remove", aliases=["delete", "del"], brief="manage expressions", usage="emoji remove 🦮")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def emoji_remove(self, ctx: EvelinaContext, *, emoji: Emoji):
        """Remove an emoji from the server"""
        await emoji.delete(reason=f"Emoji deleted by {ctx.author}")
        return await ctx.send_success("Deleted the emoji")
    
    @emoji.command(name="rename", brief="manage expressions", usage="emoji rename 🦮 mommy")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def emoji_rename(self, ctx: EvelinaContext, emoji: Emoji, *, name: str):
        """Rename an emoji"""
        if len(name) > 32:
            return await ctx.send_warning("Emoji name is too long")
        if not re.fullmatch(r"[a-zA-Z0-9_]+", name):
            return await ctx.send_warning("Invalid emoji name. Only alphanumeric characters and underscores are allowed.")
        await emoji.edit(name=name, reason=f"Emoji renamed by {ctx.author}")
        return await ctx.send_success(f"Renamed the emoji ({emoji}) to **{name}**")

    @emoji.command(name="list")
    async def emoji_list(self, ctx: EvelinaContext):
        """Returns a list of emojis in this server"""
        if len(ctx.guild.emojis) == 0:
            return await ctx.send_warning("No emojis found for this server")
        await ctx.paginate([f"{emoji} - {emoji.name} (`{emoji.id}`)" for emoji in ctx.guild.emojis], f"Emojis ({len(ctx.guild.emojis)})", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @emoji.command(name="info", usage="emoji info 🦮")
    async def emoji_info(self, ctx: EvelinaContext, *, emoji: Union[Emoji, PartialEmoji]):
        """Information about an emoji"""
        if emoji.animated:
            emoji_state = "a"
        else:
            emoji_state = ""
        embed = Embed(color=colors.NEUTRAL, title=emoji.name, url=emoji.url)
        embed.set_thumbnail(url=emoji.url)
        embed.add_field(name="Created", value=f"<t:{int(emoji.created_at.timestamp())}:f>", inline=True)
        embed.add_field(name="Markdown", value=f"```<{emoji_state}:{emoji.name}:{emoji.id}>```", inline=False)
        view = DownloadAsset(ctx, emoji)
        view.message = await ctx.reply(embed=embed, view=view)

    @emoji.command(name="enlarge", aliases=["download", "e", "jumbo"], usage="emoji enlarge 🦮")
    async def emoji_enlarge(self, ctx: EvelinaContext, *, emoji: Union[PartialEmoji, str]):
        """Gets an image version of your emoji"""
        return await ctx.invoke(self.bot.get_command("enlarge"), emoji=emoji)

    @emoji.command(name="search", usage="emoji search mommy")
    async def emoji_search(self, ctx: EvelinaContext, *, query: str):
        """Search emojis based by query"""
        emojis = [f"{e} `{e.id}` - {e.name}" for e in self.bot.emojis if query in e.name]
        if not emojis:
            return await ctx.send_warning("No emojis found")
        return await ctx.paginate(emojis, f"Emojis containing {query} ({len(emojis)})")

    @emoji.command(name="zip", brief="manage expressions")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def emoji_zip(self, ctx: EvelinaContext):
        """Send a zip file of all emojis in the server"""
        async with self.locks[ctx.guild.id]:
            async with ctx.typing():
                buff = BytesIO()
                with zipfile.ZipFile(buff, "w") as zip:
                    added_files = set()
                    for emoji in ctx.guild.emojis:
                        file_extension = "gif" if emoji.animated else "png"
                        base_name = emoji.name
                        file_name = f"{base_name}.{file_extension}"
                        counter = 1
                        while file_name in added_files:
                            file_name = f"{base_name}_{counter}.{file_extension}"
                            counter += 1
                        added_files.add(file_name)
                        zip.writestr(file_name, data=await emoji.read())
                buff.seek(0)
                await ctx.send(file=File(buff, filename=f"emojis-{ctx.guild.name}.zip"))

    @emoji.command(name="addmulti", aliases=["am"], brief="manage expressions", usage="emoji addmulti 🦮 🧢")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def emoji_addmulti(self, ctx: EvelinaContext, *emojis: PartialEmoji):
        """Add multiple emojis at the same time"""
        if len(emojis) == 0:
            return await ctx.send_help(ctx.command)
        if len(emojis) > 30:
            raise BadArgument("Do not add more than 10 emojis at once")
        try:
            async with self.locks[ctx.channel.id]:
                mes = await ctx.reply(embed=Embed(color=colors.NEUTRAL, description=f"{ctx.author.mention}: Adding **{len(emojis)}** emojis..."))
                emoji_list = []
                for emo in emojis:
                    if await self.emoji_bucket(ctx, emo):
                        if len(emoji_list) > 0:
                            return await mes.edit(embed=Embed(color=colors.NEUTRAL, title=f"Added {len(emojis)} emojis", description="".join(emoji_list)))
                    emoj = await ctx.guild.create_custom_emoji(name=emo.name, image=await emo.read(), reason=f"Emoji created by {ctx.author}")
                    emoji_list.append(f"{emoj}")
                return await mes.edit(
                    embed=Embed(color=colors.NEUTRAL, title=f"Added {len(emojis)} emojis", description="".join(emoji_list)))
        except HTTPException:
            await ctx.send_warning(f"You have reached the emoji limit for this server")

    @command(name="enlarge", aliases=["e", "jumbo"])
    async def enlarge(self, ctx: EvelinaContext, emoji: Union[PartialEmoji, str]):
        """Get an image version of an emoji"""
        if isinstance(emoji, PartialEmoji):
            return await ctx.reply(file=await emoji.to_file(filename=f"{emoji.name}{'.gif' if emoji.animated else '.png'}"))
        elif isinstance(emoji, str):
            convert = False
            if emoji[0] == "<":
                try:
                    name = emoji.split(":")[1]
                except IndexError:
                    return await ctx.send_warning("This is **not** an emoji")
                emoji_name = emoji.split(":")[2][:-1]
                if emoji.split(":")[0] == "<a":
                    url = f"https://cdn.discordapp.com/emojis/{emoji_name}.gif"
                    name += ".gif"
                else:
                    url = f"https://cdn.discordapp.com/emojis/{emoji_name}.png"
                    name += ".png"
            else:
                chars = []
                name = []
                for char in emoji:
                    chars.append(hex(ord(char))[2:])
                    try:
                        name.append(unicodedata.name(char))
                    except ValueError:
                        name.append("none")
                name = "_".join(name) + ".png"
                if len(chars) == 2 and "fe0f" in chars:
                    chars.remove("fe0f")
                if "20e3" in chars:
                    chars.remove("fe0f")
                url = "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/" + "-".join(chars) + ".svg"
                convert = True
            try:
                img, status = await self.bot.session.get_bytes(url, return_status=True)
                if status != 200:
                    return await ctx.send_warning(f"[This is **not** an emoji]({url})")
            except aiohttp.ClientError as e:
                return await ctx.send_warning(f"Error fetching image: {e}")
            if convert:
                task = functools.partial(generate, img)
                task = self.bot.loop.run_in_executor(None, task)
                try:
                    img = await asyncio.wait_for(task, timeout=15)
                except asyncio.TimeoutError:
                    return await ctx.send_warning("Image Creation **Timed Out**")
            else:
                img = io.BytesIO(img)
            await ctx.send(file=discord.File(img, name))

    @emoji.command(name="sticker", brief="manage expressions", usage="emoji sticker 🦮 mommy")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def emoji_sticker(self, ctx: EvelinaContext, emoji: Emoji, name: str):
        """Convert a custom emoji to a sticker"""
        if len(ctx.guild.stickers) >= ctx.guild.sticker_limit:
            return await ctx.send_warning("This server cannot have new stickers anymore")
        if name is not None and len(name) > 32:
            return await ctx.send_warning("Sticker name is too long")
        try:
            emoji_data, status = await self.bot.session.get_bytes(str(emoji.url), return_status=True)
            if status != 200:
                await ctx.send_warning(f"Failed to fetch emoji image.")
                return
            if emoji.animated:
                sticker_filename = "data/images/tmp/sticker.png"
                with open(sticker_filename, 'wb') as f:
                    f.write(emoji_data)
                sticker_file = discord.File(fp=sticker_filename, filename="sticker.png")
            else:
                img = Image.open(BytesIO(emoji_data)).convert("RGBA")
                img = img.resize((512, 512), Image.Resampling.LANCZOS)
                with BytesIO() as image_binary:
                    img.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    sticker_file = discord.File(fp=image_binary, filename="sticker.png")
            sticker = await ctx.guild.create_sticker(
                name=name,
                description=name,
                emoji="🖼️",
                file=sticker_file,
                reason=f"Sticker created by {ctx.author}"
            )
            await ctx.send_success(f"Added [**sticker**]({sticker.url}) with the name **{name}**")
        except HTTPException:
            await ctx.send_warning(f"An error occurred while creating the sticker")

    @group(invoke_without_command=True, case_insensitive=True)
    async def sticker(self, ctx: EvelinaContext):
        """Manage server's stickers"""
        return await ctx.create_pages()

    @sticker.command(name="add", brief="manage expressions", usage="sticker add mommy")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def sticker_add(self, ctx: EvelinaContext, name: str):
        """Add a sticker with an image attachment"""
        if len(ctx.guild.stickers) >= ctx.guild.sticker_limit:
            return await ctx.send_warning("This server cannot have new stickers anymore")
        if name is not None and len(name) > 32:
            return await ctx.send_warning("Sticker name is too long")
        reference_attachments = []
        if ctx.message.reference and ctx.message.reference.resolved:
            reference_attachments = ctx.message.reference.resolved.attachments
        if not ctx.message.attachments and not reference_attachments:
            return await ctx.send_warning("Please attach an image to use as a sticker.")
        attachments = ctx.message.attachments or reference_attachments
        attachment = attachments[0]
        if not attachment.content_type.startswith('image/'):
            return await ctx.send_warning("Attached file must be an image.")
        image_bytes = await attachment.read()
        img = Image.open(BytesIO(image_bytes)).convert("RGBA")
        img = img.resize((512, 512), Image.Resampling.LANCZOS)
        with BytesIO() as image_binary:
            img.save(image_binary, 'PNG')
            image_binary.seek(0)
            file = File(fp=image_binary, filename="sticker.png")
        try:
            sticker = await ctx.guild.create_sticker(
                name=name,
                description=name, 
                emoji="🖼️",
                file=file,
                reason=f"Sticker created by {ctx.author}"
            )
            await ctx.send_success(f"Added [**sticker**]({sticker.url}) with the name **{name}**")
        except HTTPException as e:
            await ctx.send_warning(f"An error occurred while adding the sticker:\n ```{e}```")

    @sticker.command(name="steal", brief="manage expressions", usage="sticker steal mommy")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def sticker_steal(self, ctx: EvelinaContext, *, name: str = None):
        """Steal a sticker from another server"""
        if len(ctx.guild.stickers) >= ctx.guild.sticker_limit:
            return await ctx.send_warning("This server cannot have new stickers anymore")
        if name is not None and len(name) > 32:
            return await ctx.send_warning("Sticker name is too long")
        try:
            sticker = await self.get_sticker(ctx)
            if sticker is None:
                return await ctx.send_warning("Could not retrieve sticker")
            sticker_data = await sticker.read()
            if not sticker_data:
                return await ctx.send_warning("Sticker data is empty or unreadable")
            if name is None:
                name = sticker.name
            file = File(fp=BytesIO(sticker_data), filename=f"{name}.png")
            stick = await ctx.guild.create_sticker(
                name=name, 
                description=name, 
                emoji="🖼️",
                file=file, 
                reason=f"sticker created by {ctx.author}"
            )
            return await ctx.send_success(f"Added [**sticker**]({stick.url}) with the name **{name}**")
        except NotFound:
            await ctx.send_warning("Could not find the sticker asset")
        except Exception:
            await ctx.send_warning("An error occurred while adding the sticker")

    @sticker.command(name="rename", brief="manage expressions", usage="sticker rename mommy")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def sticker_rename(self, ctx: EvelinaContext, *, name: str):
        """Rename a sticker"""
        if len(name) > 32:
            return await ctx.send_warning("Sticker name is too long")
        try:
            sticker = await ctx.get_sticker()
            if sticker is None:
                return await ctx.send_warning("Sticker not found. Please provide a valid sticker")
            full_sticker = await sticker.fetch()
            if full_sticker.guild.id != ctx.guild.id:
                return await ctx.send_warning("This sticker is not from this server")
            await full_sticker.edit(name=name, reason=f"Sticker renamed by {ctx.author}")
            return await ctx.send_success(f"Renamed the sticker ({sticker}) to **{name}**")
        except HTTPException:
            await ctx.send_warning("An error occurred while renaming the sticker")

    @sticker.command(name="enlarge", aliases=["e", "jumbo"])
    async def sticker_enlarge(self, ctx: EvelinaContext):
        """Returns a sticker as a file"""
        try:
            stick = await ctx.get_sticker()
            if not stick:
                await ctx.send_warning("Sticker not found or accessible.")
                return
            if stick.format.name == "apng":
                sticker_file = await stick.to_file(filename=f"{stick.name}.apng")
            else:
                sticker_file = await stick.to_file(filename=f"{stick.name}.png")
            await ctx.reply(file=sticker_file)
        except NotFound:
            await ctx.send_warning(f"Could not find the sticker asset")

    @sticker.command(name="delete", brief="manage expressions")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def sticker_delete(self, ctx: EvelinaContext, *, name: str = None):
        """Delete a sticker"""
        try:
            if name is not None:
                sticker = discord.utils.get(ctx.guild.stickers, name=name)
                if not sticker:
                    return await ctx.send_warning(f"Could not find a sticker with the name `{name}`")
                if sticker.guild.id != ctx.guild.id:
                    return await ctx.send_warning("This sticker is not from this server")
                await sticker.delete(reason=f"Sticker deleted by {ctx.author}")
                return await ctx.send_success(f"Deleted the sticker **{sticker.name}**")
            else:
                sticker = await ctx.get_sticker()
                if sticker is None:
                    return await ctx.send_warning("Sticker not found. Please provide a valid sticker")
                full_sticker = await sticker.fetch()
                if full_sticker.guild.id != ctx.guild.id:
                    return await ctx.send_warning("This sticker is not from this server")
                await full_sticker.delete(reason=f"Sticker deleted by {ctx.author}")
                return await ctx.send_success(f"Deleted the sticker **{full_sticker.name}**")
        except discord.NotFound:
            return await ctx.send_warning("Sticker not found. It may have already been deleted")
        except AttributeError as e:
            return await ctx.send_warning("Failed to fetch sticker details. The sticker might not exist")
        except discord.Forbidden:
            return await ctx.send_warning("Bot lacks the permission to delete this sticker")
        except Exception as e:
            return await ctx.send_warning(f"An error occurred: {str(e)}")

    @sticker.command(name="zip", brief="manage expressions")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def sticker_zip(self, ctx: EvelinaContext):
        """Send a zip file containing the server's stickers"""
        async with self.locks[ctx.guild.id]:
            async with ctx.typing():
                buff = BytesIO()
                with zipfile.ZipFile(buff, "w") as zip:
                    for sticker in ctx.guild.stickers:
                        zip.writestr(f"{sticker.name}.png", data=await sticker.read())
            buff.seek(0)
            await ctx.send(file=File(buff, filename=f"stickers-{ctx.guild.name}.zip"))

    @sticker.command(name="tag", brief="manage expressions")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def sticker_tag(self, ctx: EvelinaContext):
        """Add your server's vanity URL to the end of sticker names"""
        if not ctx.guild.vanity_url:
            return await ctx.send_warning(f"There is no **vanity url** set")
        current_vanity = f"gg/{ctx.guild.vanity_url_code}"
        message = await ctx.send_loading(f"Adding or updating **{current_vanity}** to `{len(ctx.guild.stickers)}` stickers...")
        for sticker in ctx.guild.stickers:
            name_parts = sticker.name.split(" | ")
            name_parts = [part.split(" gg/")[0].split(" .gg/")[0].rstrip() for part in name_parts if "gg/" not in part and ".gg/" not in part]
            new_name = " | ".join(name_parts).strip()
            new_name = f"{new_name} | {current_vanity}"
            try:
                await sticker.edit(name=new_name)
                await asyncio.sleep(1.5)
            except:
                pass
        try:
            await message.delete()
        except Exception:
            pass
        await ctx.send_success(f"Updated stickers with **{current_vanity}** in server stickers")
    
    @sticker.command(name="emoji", brief="manage expressions", usage="sticker emoji mommy")
    @has_guild_permissions(manage_expressions=True)
    @bot_has_guild_permissions(manage_expressions=True)
    async def sticker_emoji(self, ctx: EvelinaContext, *, name: str = None):
        """Convert a sticker to a custom emoji and optionally attach it to a message"""
        if name is not None and len(name) > 32:
            return await ctx.send_warning("Emoji name is too long")
        try:
            sticker = await self.get_sticker(ctx)
            if sticker is None:
                return await ctx.send_warning("Could not retrieve sticker")
            sticker_data = await sticker.read()
            if not sticker_data:
                return await ctx.send_warning("Sticker data is empty or unreadable")
            if name is None:
                name = sticker.name
            if sticker.format == discord.StickerFormatType.apng:
                img = Image.open(BytesIO(sticker_data))
                frames = []
                for frame in ImageSequence.Iterator(img):
                    frame = frame.convert("RGBA").resize((128, 128), Image.Resampling.LANCZOS)
                    frames.append(frame)
                with BytesIO() as image_binary:
                    frames[0].save(
                        image_binary,
                        format="GIF",
                        save_all=True,
                        append_images=frames[1:],
                        loop=0,
                        duration=img.info['duration']
                    )
                    image_binary.seek(0)
                    emoji_file = discord.File(fp=image_binary, filename=f"{name}.gif")
            else:
                img = Image.open(BytesIO(sticker_data)).convert("RGBA")
                img = img.resize((128, 128), Image.Resampling.LANCZOS)
                with BytesIO() as image_binary:
                    img.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    emoji_file = discord.File(fp=image_binary, filename=f"{name}.png")
            emoji = await ctx.guild.create_custom_emoji(
                name=name,
                image=emoji_file.fp.read(),
                reason=f"Emoji created by {ctx.author}"
            )
            await ctx.send_success(f"Added {emoji} as **[{emoji.name}]({emoji.url})**")
        except Exception:
            await ctx.send_warning(f"An error occurred while creating the emoji")

async def setup(bot: Evelina):
    await bot.add_cog(Emoji(bot))