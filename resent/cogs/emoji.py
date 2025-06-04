import asyncio
import io
import re
from dataclasses import dataclass
from io import BytesIO
from itertools import zip_longest
from typing import List, Optional, Union

import aiohttp
import discord
from discord.ext import commands
from utils.permissions import Permissions

IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".gif", ".webp")
STICKER_KB = 512
STICKER_DIM = 320
STICKER_EMOJI = "😶"
MISSING_EMOJIS = "cant find emojis or stickers in that message."
MISSING_REFERENCE = "reply to a message with this command to steal an emoji."
MESSAGE_FAIL = "i couldn't grab that message."
UPLOADED_BY = "uploaded by"
STICKER_DESC = "stolen sticker"
STICKER_FAIL = "failed to upload sticker"
STICKER_SUCCESS = "uploaded sticker"
EMOJI_SUCCESS = "uploaded emoji"
STICKER_SLOTS = "this server doesn't have any more space for stickers."
EMOJI_FAIL = "failed to upload"
EMOJI_SLOTS = "this server doesn't have any more space for emojis."
INVALID_EMOJI = "invalid emoji or emoji ID."
STICKER_TOO_BIG = f"stickers may only be up to {STICKER_KB} KB and {STICKER_DIM}x{STICKER_DIM} pixels."
STICKER_ATTACHMENT = ""


@dataclass(init=True, order=True, frozen=True)
class StolenEmoji:
    animated: bool
    name: str
    id: int

    @property
    def url(self):
        return f"https://cdn.discordapp.com/emojis/{self.id}.{'gif' if self.animated else 'png'}"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, StolenEmoji) and self.id == other.id


class emoji(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    @staticmethod
    def get_emojis(content: str) -> Optional[List[StolenEmoji]]:
        results = re.findall(r"<(a?):(\w+):(\d{10,20})>", content)
        return [StolenEmoji(*result) for result in results]

    @staticmethod
    def available_emoji_slots(guild: discord.Guild, animated: bool):
        current_emojis = len([em for em in guild.emojis if em.animated == animated])
        return guild.emoji_limit - current_emojis

    async def steal_ctx(
        self, ctx: commands.Context
    ) -> Optional[List[Union[StolenEmoji, discord.StickerItem]]]:
        reference = ctx.message.reference
        if not reference:
            await ctx.send_warning(
                "Reply to a message with this command to steal an emoji, or run ``addemoji``."
            )
            return None
        message = await ctx.channel.fetch_message(reference.message_id)
        if not message:
            await ctx.send_warning("I couldn't fetch that message.")
            return None
        if message.stickers:
            return message.stickers
        if not (emojis := self.get_emojis(message.content)):
            await ctx.send_warning("Can't find emojis or stickers in that message.")
            return None
        return emojis

    @commands.command(
        description="delete an emoji",
        help="emoji",
        usage="[emoji]",
        brief="manage emojis",
        aliases=["delemoji"],
    )
    @Permissions.has_permission(manage_expressions=True)
    async def deleteemoji(self, ctx: commands.Context, emoji: discord.Emoji):
        await emoji.delete()
        await ctx.send_success("Deleted the emoji")

    @commands.command(
        description="add an emoji",
        help="emoji",
        usage="[emoji] <name>",
        brief="manage emojis",
    )
    @Permissions.has_permission(manage_expressions=True)
    async def addemoji(
        self,
        ctx: commands.Context,
        emoji: Union[discord.Emoji, discord.PartialEmoji],
        *,
        name: str = None,
    ):
        if not name:
            name = emoji.name
        try:
            emoji = await ctx.guild.create_custom_emoji(
                image=await emoji.read(), name=name
            )
            await ctx.send_success(f"added emoji `{name}` | {emoji}".capitalize())
        except discord.HTTPException as e:
            return await ctx.send_error(ctx, f"Unable to add the emoji | {e}")

    @commands.command(
        description="add multiple emojis",
        help="emoji",
        usage="[emojis]",
        aliases=["am"],
        brief="manage emojis",
    )
    @Permissions.has_permission(manage_expressions=True)
    async def addmultiple(
        self, ctx: commands.Context, *emoji: Union[discord.Emoji, discord.PartialEmoji]
    ):
        if len(emoji) == 0:
            return await ctx.send_warning("Please provide some emojis to add")
        emojis = []
        await ctx.channel.typing()
        for emo in emoji:
            try:
                emoj = await ctx.guild.create_custom_emoji(
                    image=await emo.read(), name=emo.name
                )
                emojis.append(f"{emoj}")
                await asyncio.sleep(0.5)
            except discord.HTTPException as e:
                return await ctx.send_error(ctx, f"Unable to add the emoji | {e}")

        embed = discord.Embed(color=self.bot.color, title=f"added {len(emoji)} emojis")
        embed.description = "".join(map(str, emojis))
        return await ctx.reply(embed=embed)

    @commands.group(
        invoke_without_command=True,
        help="emoji",
        description="manage server's stickers",
    )
    async def sticker(self, ctx: commands.Context):
        return await ctx.create_pages()

    @sticker.command(
        name="steal",
        help="emoji",
        description="add a sticker",
        aliases=["add"],
        usage="[attach sticker]",
        brief="manage emojis",
    )
    @Permissions.has_permission(manage_expressions=True)
    async def sticker_steal(self, ctx: commands.Context):
        return await ctx.invoke(self.bot.get_command("stealsticker"))

    @sticker.command(
        name="enlarge",
        aliases=["e", "jumbo"],
        help="emoji",
        description="returns a sticker as a file",
        usage="[attach sticker]",
    )
    async def sticker_enlarge(self, ctx: commands.Context):
        if ctx.message.stickers:
            stick = ctx.message.stickers[0]
        else:
            messages = [m async for m in ctx.channel.history(limit=20) if m.stickers]
            if len(messages) == 0:
                return await ctx.send_warning("No sticker found")
            stick = messages[0].stickers[0]
        return await ctx.reply(file=await stick.to_file(filename=f"{stick.name}.png"))

    @sticker.command(
        name="delete",
        help="emoji",
        description="delete a sticker",
        usage="[attach sticker]",
        brief="manage emojis",
    )
    @Permissions.has_permission(manage_expressions=True)
    async def sticker_delete(self, ctx: commands.Context):
        if ctx.message.stickers:
            sticker = ctx.message.stickers[0]
            sticker = await sticker.fetch()
            if sticker.guild.id != ctx.guild.id:
                return await ctx.send_warning("This sticker is not from this server")
            await sticker.delete(reason=f"sticker deleted by {ctx.author}")
            return await ctx.send_success("Deleted the sticker")
        async for message in ctx.channel.history(limit=10):
            if message.stickers:
                sticker = message.stickers[0]
                s = await sticker.fetch()
                if s.guild_id == ctx.guild.id:
                    embed = discord.Embed(
                        color=self.bot.color,
                        description=f"Are you sure you want to delete `{s.name}`?",
                    ).set_image(url=s.url)
                    button1 = discord.ui.Button(emoji="<:check:1208233844751474708>")
                    button2 = discord.ui.Button(emoji="<:stop:1208240063691886642>")

                    async def button1_callback(interaction: discord.Interaction):
                        if ctx.author.id != interaction.user.id:
                            return await self.bot.ext.send_warning(
                                interaction, "You are not the author of this embed"
                            )
                        await s.delete()
                        return await interaction.response.edit_message(
                            embed=discord.Embed(
                                color=self.bot.color,
                                description=f"{self.bot.yes} {interaction.user.mention}: Deleted sticker",
                            ),
                            view=None,
                        )

                    async def button2_callback(interaction: discord.Interaction):
                        if ctx.author.id != interaction.user.id:
                            return await self.bot.ext.send_warning(
                                interaction, "You are not the author of this embed"
                            )
                        return await interaction.response.edit_message(
                            embed=discord.Embed(
                                color=self.bot.color,
                                description=f"{interaction.user.mention}",
                            )
                        )

                    button1.callback = button1_callback
                    button2.callback = button2_callback
                    view = discord.ui.View()
                    view.add_item(button1)
                    view.add_item(button2)
                    return await ctx.reply(embed=embed, view=view)

    @commands.command(
        description="add a sticker",
        help="emoji",
        usage="[attach sticker]",
        brief="manage emojis",
        aliases=["stickersteal", "addsticker", "stickeradd"],
    )
    @Permissions.has_permission(manage_expressions=True)
    async def stealsticker(self, ctx: commands.Context):
        if ctx.message.stickers:
            try:
                url = ctx.message.stickers[0].url
                name = ctx.message.stickers[0].name
                img_data = await self.bot.session.read(url)
                tobytess = BytesIO(img_data)
                file = discord.File(fp=tobytess)
                sticker = await ctx.guild.create_sticker(
                    name=name,
                    description=name,
                    emoji="skull",
                    file=file,
                    reason=f"sticker created by {ctx.author}",
                )
                format = str(sticker.format)
                form = format.replace("StickerFormatType.", "")
                embed = discord.Embed(color=self.bot.color, title="sticker added")
                embed.set_thumbnail(url=url)
                embed.add_field(
                    name="values",
                    value=f"name: `{name}`\nid: `{sticker.id}`\nformat: `{form}`\nlink: [url]({url})",
                )
                return await ctx.reply(embed=embed)
            except Exception as error:
                return await ctx.send_error(
                    ctx, f"Unable to add this sticker - {error}"
                )
        elif not ctx.message.stickers:
            async for message in ctx.channel.history(limit=10):
                if message.stickers:
                    e = discord.Embed(
                        color=self.bot.color, title=message.stickers[0].name
                    ).set_author(
                        name=message.author.name,
                        icon_url=message.author.display_avatar.url,
                    )
                    e.set_image(url=message.stickers[0].url)
                    e.set_footer(text="react below to steal")
                    button1 = discord.ui.Button(
                        label="",
                        style=discord.ButtonStyle.gray,
                        emoji="<:check:1208233844751474708>",
                    )
                    button2 = discord.ui.Button(
                        label="",
                        style=discord.ButtonStyle.gray,
                        emoji="<:stop:1208240063691886642>",
                    )

                    async def button1_callback(interaction: discord.Interaction):
                        if interaction.user != ctx.author:
                            return await self.bot.ext.send_warning(
                                interaction, "you cant use this button", ephemeral=True
                            )
                        try:
                            url = message.stickers[0].url
                            name = message.stickers[0].name
                            img_data = await self.bot.session.read(url)
                            tobytess = BytesIO(img_data)
                            file = discord.File(fp=tobytess)
                            sticker = await ctx.guild.create_sticker(
                                name=name,
                                description=name,
                                emoji="skull",
                                file=file,
                                reason=f"sticker created by {ctx.author}",
                            )
                            format = str(sticker.format)
                            form = format.replace("StickerFormatType.", "")
                            embed = discord.Embed(
                                color=self.bot.color, title="sticker added"
                            )
                            embed.set_thumbnail(url=url)
                            embed.add_field(
                                name="values",
                                value=f"name: `{name}`\nid: `{sticker.id}`\nformat: `{form}`\nlink: [url]({url})",
                            )
                            return await interaction.response.edit_message(
                                embed=embed, view=None
                            )
                        except:
                            embed = discord.Embed(
                                color=self.bot.color,
                                description=f"{self.bot.no} {ctx.author.mention}: unable to add this sticker",
                            )
                            return await interaction.response.edit_message(
                                embed=embed, view=None
                            )

                    button1.callback = button1_callback

                    async def button2_callback(interaction: discord.Interaction):
                        if interaction.user != ctx.author:
                            return await self.bot.ext.send_warning(
                                interaction, "You can't use this button", ephemeral=True
                            )
                        return await interaction.response.edit_message(
                            embed=discord.Embed(
                                color=self.bot.color,
                                description=f"{interaction.user.mention}: Cancelled sticker steal",
                            ),
                            view=None,
                        )

                    button2.callback = button2_callback

                    view = discord.ui.View()
                    view.add_item(button1)
                    view.add_item(button2)
                    return await ctx.reply(embed=e, view=view)

        return await ctx.send_error("No sticker found")

    @commands.command(
        description="returns a list of server's emojis",
        help="emoji",
        aliases=["emojis"],
    )
    async def emojilist(self, ctx: commands.Context):
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for emoji in ctx.guild.emojis:
            mes = f"{mes}`{k}` {emoji} - ({emoji.name})\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    discord.Embed(
                        color=self.bot.color,
                        title=f"emojis in {ctx.guild.name} [{len(ctx.guild.emojis)}]",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        number.append(
            discord.Embed(
                color=self.bot.color,
                title=f"emojis in {ctx.guild.name} [{len(ctx.guild.emojis)}]",
                description=messages[i],
            )
        )
        await ctx.paginator(number)

    @commands.command(
        aliases=["downloademoji", "e", "jumbo"],
        description="gets an image version of your emoji",
        help="emoji",
        usage="[emoji]",
    )
    async def enlarge(
        self, ctx: commands.Context, emoj: Union[discord.PartialEmoji, str]
    ):
        if isinstance(emoj, discord.PartialEmoji):
            return await ctx.reply(
                file=await emoj.to_file(
                    filename=f"{emoj.name}{'.gif' if emoj.animated else '.png'}"
                )
            )
        elif isinstance(emoj, str):
            return await ctx.reply(
                file=discord.File(
                    fp=await self.bot.getbyte(
                        f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{ord(emoj):x}.png"
                    ),
                    filename="emoji.png",
                )
            )

    @commands.command(
        aliases=["ei"], description="show emoji info", help="emoji", usage="[emoji]"
    )
    async def emojiinfo(
        self,
        ctx: commands.Context,
        *,
        emoji: Union[discord.Emoji, discord.PartialEmoji],
    ):
        embed = discord.Embed(
            color=self.bot.color, title=emoji.name, timestamp=emoji.created_at
        ).set_footer(text=f"id: {emoji.id}")
        embed.set_thumbnail(url=emoji.url)
        embed.add_field(name="animated", value=emoji.animated)
        embed.add_field(name="link", value=f"[emoji]({emoji.url})")
        if isinstance(emoji, discord.Emoji):
            embed.add_field(name="guild", value=emoji.guild.name)
            embed.add_field(name="usable", value=emoji.is_usable())
            embed.add_field(name="available", value=emoji.available)
            emo = await emoji.guild.fetch_emoji(emoji.id)
            embed.add_field(name="created by", value=str(emo.user))
        return await ctx.reply(embed=embed)

    @commands.command(
        name="steal",
        description="reply to a message to steal an emoji or sticker",
        help="emoji",
        usage="[emojis]",
        brief="manage expressions",
    )
    @commands.has_permissions(manage_expressions=True)
    async def steal(self, ctx: commands.Context, *names: str):
        if not (emojis := await self.steal_ctx(ctx)):
            return

        if isinstance(emojis[0], discord.StickerItem):
            if len(ctx.guild.stickers) >= ctx.guild.sticker_limit:
                return await ctx.send_warning("there are no more sticker slots.")
            sticker = emojis[0]
            fp = io.BytesIO()
            try:
                await sticker.save(fp)
                await ctx.guild.create_sticker(
                    name=sticker.name,
                    description=STICKER_DESC,
                    emoji=STICKER_EMOJI,
                    file=discord.File(fp),
                    reason=f"uploaded by {ctx.author}",
                )
            except Exception as error:
                return await ctx.send_warning(
                    f"{STICKER_FAIL}, {type(error).__name__}: {error}"
                )
            return await ctx.send_success(f"{STICKER_SUCCESS}: {sticker.name}")

        names = ["".join(re.findall(r"\w+", name)) for name in names]
        names = [name if len(name) >= 2 else None for name in names]
        emojis = list(dict.fromkeys(emojis))

        async with aiohttp.ClientSession() as session:
            for emoji, name in zip_longest(emojis, names):
                if not self.available_emoji_slots(ctx.guild, emoji.animated):
                    return await ctx.send_warning(EMOJI_SLOTS)
                if not emoji:
                    break
                try:
                    async with session.get(emoji.url) as resp:
                        image = io.BytesIO(await resp.read()).read()
                    added = await ctx.guild.create_custom_emoji(
                        name=name or emoji.name,
                        image=image,
                        reason=f"uploaded by {ctx.author}",
                    )
                except Exception as error:
                    return await ctx.send_warning(
                        f"{EMOJI_FAIL} {emoji.name}, {type(error).__name__}: {error}"
                    )
                try:
                    await ctx.message.add_reaction(added)
                except:
                    pass


async def setup(bot) -> None:
    await bot.add_cog(emoji(bot))
