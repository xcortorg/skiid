import re
import os
import unicodedata
import secrets
import string
import io
import asyncio
from loguru import logger
from discord.ext.commands import (
    Cog,
    CommandError,
    command,
    group,
    has_permissions,
    Greedy,
    BadArgument,
)
from aiohttp import ClientSession
from discord.ext import menus
from discord import Embed, File, Client, Message, Emoji, PartialEmoji, HTTPException
from discord.sticker import GuildSticker, StandardSticker, StickerItem
from .views import StickerStealView, EmojiStealView, confirm
from .views.emoji import read_file
from typing import Optional, Union, List
from lib.patch.context import Context
from lib.managers.aiter import async_iter
from lib.main import MessageLink
from lib.services.Image import remove_background
from lib.worker import offloaded
from .util import image as GetImage
from lib.services.cache import cache


@offloaded
def transparent(filepath: str):
    from transparent import removeBg as tp

    return tp(filepath)


def get_message_stickers(message: Message) -> List[StickerItem]:
    """Returns a list of StickerItem found in a message."""
    stickers = message.stickers
    if len(stickers) == 0:
        raise BadArgument("I was not able to find any stickers in the message!")
    return stickers


@offloaded
def generate(img: bytes):
    import io
    import cairosvg

    kwargs = {"parent_width": 1024, "parent_height": 1024}
    i = io.BytesIO(cairosvg.svg2png(bytestring=img, **kwargs))
    return i.read()


@cache(ttl=1600, key="enlarge:{url}")
async def enlarge(url: str, image: bytes):
    return await generate(image)


URL_REGEX = re.compile(
    r"(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?"
)


def get_urls(message: Message):
    # Returns a list of valid urls from a passed message/context/string
    message = (
        message.content
        if isinstance(message, Message)
        else message.message.content if isinstance(message, Context) else str(message)
    )
    return [x.group(0) for x in re.finditer(URL_REGEX, message)]


class MySource(menus.ListPageSource):
    async def format_page(self, menu, entries):
        if self.get_max_pages() > 1:
            ee = "entries"
        else:
            ee = "entry"
        entries.set_footer(
            text=f"Page {menu.current_page + 1}/{self.get_max_pages()} ({self.get_max_pages()} {ee})"
        )
        return entries


class Asset(Cog):
    def __init__(self, bot: Client):
        self.bot = bot
        self.EMOJI_REGEX = re.compile(
            r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
        )
        self.locked: List[int] = []

    async def clense(self, text):
        regex = r"(discord\.)?([\w\-\.\/])*(\.[a-zA-Z]{2,3}\/?)[^\s\b\n|]*[^.,;:\?\!\@\^\$ -].[a-zA-Z]"
        results = re.findall(regex, text)
        ee = text.split()
        for d in ee:
            if "/" in d or ".gg" in d:
                ee.remove(d)
        name = " ".join(g for g in ee)
        if len(name) > 30:
            amt = len(name) - 30
            name = name[0 : len(name) - amt - 1]
        return name

    async def clense_names(self, vanity, text):
        regex = r"(discord\.)?([\w\-\.\/])*(\.[a-zA-Z]{2,3}\/?)[^\s\b\n|]*[^.,;:\?\!\@\^\$ -].[a-zA-Z]"
        results = re.findall(regex, text)
        ee = text.split()
        async for d in aiter(ee):
            if "/" in d or ".gg" in d:
                ee.remove(d)
        name = " ".join(g for g in (ee))
        van = f" .gg/{vanity}"
        if len(name) + len(van) > 30:
            amt = len(van) + len(name) - 30
            name = name[0 : len(name) - amt]
        return name

    async def format_stickers(self, ctx):
        i = 0
        async for sticker in aiter(ctx.guild.stickers):
            if f".gg/{ctx.guild.vanity_url_code}" not in sticker.name:
                name = await self.clense_names(ctx.guild.vanity_url_code, sticker.name)
                await asyncio.sleep(3)
                await sticker.edit(
                    name=f"{name} .gg/{ctx.guild.vanity_url_code}",
                    reason=f"stickers reformatted by {str(ctx.author)}",
                )
                i += 1
        return i

    async def multi_sticker_steal(self, ctx):
        l = []
        urls = []
        if not ctx.author.nick:
            author_name = str(ctx.author)
        else:
            author_name = ctx.author.display_name
        async for message in ctx.channel.history(limit=100):
            if message.stickers:
                for s in message.stickers:
                    ee = self.bot.get_sticker(int(s.id))
                    dic = {}
                    dic["name"] = await self.clense(s.name)
                    dic["url"] = s.url
                    dic["id"] = s.id
                    try:
                        if ee:
                            if ee.guild.id != ctx.guild.id:
                                l.append(dic)
                        else:
                            l.append(dic)
                    except:
                        l.append(dic)
        if l:
            if len(l) <= 1:
                dic = l[0]
                return [False, dic]
        else:
            return None
        embeds = []
        async for i, e in async_iter(enumerate(l, start=0)):
            bb = l[i]
            eee = self.bot.get_sticker(int(bb["id"]))
            try:
                if eee:
                    guild = eee.guild.name
                else:
                    guild = "Unknown"
            except:
                guild = "Unknown"

            embeds.append(
                Embed(title=bb["name"], color=0xD6BCD0)
                .add_field(name="Emoji ID", value=f"`{bb['id']}`", inline=True)
                .add_field(name="Guild", value=guild, inline=True)
                .add_field(name="Image URL", value=f"[Here]({bb['url']})", inline=False)
                .set_author(name=author_name, icon_url=ctx.author.display_avatar)
                .set_image(url=bb["url"])
            )
        return [True, embeds, l]

    async def multi_emoji_steal(self, ctx):
        l = []
        urls = []
        if not ctx.author.nick:
            author_name = str(ctx.author)
        else:
            author_name = ctx.author.display_name
        async for message in ctx.channel.history(limit=100):
            data = re.findall(r"<(a?):([a-zA-Z0-9\_]+):([0-9]+)>", message.content)
            if data:
                for _a, emoji_name, emoji_id in data:
                    # if len(data) > 1:
                    dic = {}
                    url = (
                        f"https://cdn.discordapp.com/emojis/{emoji_id}.gif"
                        if _a
                        else f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
                    )
                    if url not in urls:
                        urls.append(
                            f"https://cdn.discordapp.com/emojis/{emoji_id}.gif"
                            if _a
                            else f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
                        )
                        dic["name"] = emoji_name
                        dic["id"] = emoji_id
                        ee = self.bot.get_emoji(int(emoji_id))
                        dic["url"] = (
                            f"https://cdn.discordapp.com/emojis/{emoji_id}.gif"
                            if _a
                            else f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
                        )
                        try:
                            if ee:
                                if ee.guild.id != ctx.guild.id:
                                    l.append(dic)
                            else:
                                l.append(dic)
                        except:
                            l.append(dic)
        if l:
            if len(l) <= 1:
                dic = l[0]
                return [False, dic]
        else:
            return None
        embeds = []
        async for i, e in async_iter(enumerate(l, start=0)):
            bb = l[i]
            eee = self.bot.get_emoji(int(bb["id"]))
            try:
                if eee:
                    guild = eee.guild.name
                else:
                    guild = "Unknown"
            except:
                guild = "Unknown"

            embeds.append(
                Embed(title=bb["name"], color=0xD6BCD0)
                .add_field(name="Emoji ID", value=f"`{bb['id']}`", inline=True)
                .add_field(name="Guild", value=guild, inline=True)
                .add_field(name="Image URL", value=f"[Here]({bb['url']})", inline=False)
                .set_author(name=author_name, icon_url=ctx.author.display_avatar)
                .set_image(url=bb["url"])
            )
        return [True, embeds, l]

    @command(name="steal", description="View the most recent emote used")
    @has_permissions(manage_emojis=True)
    async def steal(self, ctx: Context, *, message_link: Optional[str] = None):
        if message_link is not None:
            emojis = ""
            message_link = MessageLink.from_url(message_link)
            message = await message_link.fetch_message()
            data = self.EMOJI_REGEX.findall(message.content)
            for _a, emoji_name, emoji_id in data:
                animated = _a == "a"
                if animated:
                    url = "https://cdn.discordapp.com/emojis/" + emoji_id + ".gif"
                else:
                    url = "https://cdn.discordapp.com/emojis/" + emoji_id + ".png"
                f = await GetImage.download(url)
                img = await read_file(f)
                emote = await ctx.guild.create_custom_emoji(name=emoji_name, image=img)
                emojis += f"{str(emote)}"
            return await ctx.success(
                f"successfully **stole** the following **emojis** {emojis}"
            )
        else:
            try:
                emojis = await self.multi_emoji_steal(ctx=ctx)
                if not emojis:
                    return await ctx.fail("no **emoji** to steal")
                if emojis[0] == False:
                    emname = emojis[1].get("name")
                    emurl = emojis[1].get("url")
                    emid = emojis[1].get("id")
                else:
                    emotes = emojis[1]
                    formatter = MySource(emotes, per_page=1)
                    menu = EmojiStealView(self.bot, formatter, emojis[-1])
                    return await menu.start(ctx)
            except Exception as e:
                return await ctx.reply(
                    embed=Embed(
                        color=0xD6BCD0,
                        description=f"{self.bot.config['emojis']['warning']} {ctx.author.mention}: **no grabbable previously sent emoji detected**",
                    )
                )
        if emid:
            try:
                message = await ctx.send(
                    embed=Embed(title=emname, color=0xD6BCD0)
                    .add_field(name=f"Emoji ID", value=f"`{emid}`")
                    .add_field(name="Image URL", value=f"[Here]({emurl})")
                    .set_author(
                        name=ctx.author.display_name, icon_url=ctx.author.display_avatar
                    )
                    .set_image(url=emurl)
                    .set_footer(text="Page 1/1 (1 entry)")
                )
            except:
                return await ctx.reply(
                    embed=Embed(
                        color=self.bot.color,
                        description=f"{self.bot.config['emojis']['warning']} {ctx.author.mention}: **no grabbable previously sent emoji detected**",
                    )
                )
            confirmed: bool = await confirm(self, ctx, message)
            if confirmed:
                # response=requests.get(emurl)
                # img = response.content
                f = await GetImage.download(emurl)
                img = await read_file(f)
                emote = await ctx.guild.create_custom_emoji(name=emname, image=img)
                await message.edit(
                    view=None,
                    embed=Embed(
                        description=f"{self.bot.config['emojis']['success']} **added emoji:** {emote}",
                        color=self.bot.color,
                    ),
                )
                GetImage.remove(f)
            else:
                await message.edit(
                    view=None,
                    embed=Embed(
                        description=f"{self.bot.config['emojis']['fail']} **cancelled emoji steal**",
                        color=self.bot.color,
                    ),
                )

    @command(
        name="addmultiple",
        description="adds passed emojis from emotes/urls with names (max of 10)",
        aliases=["addemojis", "addemoji", "addemotes", "emotesadd"],
        example=",addmultiple link smile",
    )
    @has_permissions(manage_emojis=True)
    async def addmultiple(self, ctx: Context, *, emoji=None, name=None):
        if not len(ctx.message.attachments) and emoji == name == None:
            return await ctx.send_help(ctx.command)
        # Let's find out if we have an attachment, emoji, or a url
        # Check attachments first - as they'll have priority
        if len(ctx.message.attachments):
            name = emoji
            emoji = " ".join([x.url for x in ctx.message.attachments])
            if name:  # Add the name separated by a space
                emoji += " " + name
        # Now we split the emoji string, and walk it, looking for urls, emojis, and names
        emojis_to_add = []
        last_name = []
        for x in emoji.split():
            # Check for a url
            urls = get_urls(x)
            if len(urls):
                url = (urls[0], os.path.basename(urls[0]).split(".")[0])
            else:
                # Check for an emoji
                url = self._get_emoji_url(x)
                if not url:
                    # Gotta be a part of the name - add it
                    last_name.append(x)
                    continue
            if len(emojis_to_add) and last_name:
                # Update the previous name if need be
                emojis_to_add[-1][1] = "".join(
                    [z for z in "_".join(last_name) if z.isalnum() or z == "_"]
                )
            # We have a valid url or emoji here - let's make sure it's unique
            if not url[0] in [x[0] for x in emojis_to_add]:
                emojis_to_add.append([url[0], url[1]])
            # Reset last_name
            last_name = []
        if len(emojis_to_add) and last_name:
            # Update the final name if need be
            emojis_to_add[-1][1] = "".join(
                [z for z in "_".join(last_name) if z.isalnum() or z == "_"]
            )
        if not emojis_to_add:
            return await ctx.send_help(ctx.command)
        # Now we have a list of emojis and names
        added_emojis = []
        allowed = (
            len(emojis_to_add)
            if len(emojis_to_add) <= self.max_emojis
            else self.max_emojis
        )
        omitted = (
            " ({} omitted, beyond the limit of {})".format(
                len(emojis_to_add) - self.max_emojis, self.max_emojis
            )
            if len(emojis_to_add) > self.max_emojis
            else ""
        )
        message = await ctx.send(
            embed=Embed(
                color=self.bot.color,
                description=f"{self.bot.config['emojis']['success']} {ctx.author.mention}: "
                + "Adding {} emoji{}{}...".format(
                    allowed, "" if allowed == 1 else "s", omitted
                ),
            )
        )
        for emoji_to_add in emojis_to_add[: self.max_emojis]:
            # Let's try to download it
            emoji, e_name = emoji_to_add  # Expand into the parts
            f = await GetImage.download(emoji)
            if not f:
                logger.info(f"Could not download emoji - {f}")
                continue
            # Open the image file
            image = await read_file(f)
            # Clean up
            GetImage.remove(f)
            if not e_name.replace("_", ""):
                continue
            # Create the emoji and save it
            try:
                new_emoji = await ctx.guild.create_custom_emoji(
                    name=e_name,
                    image=image,
                    roles=None,
                    reason="Added by {}#{}".format(
                        ctx.author.name, ctx.author.discriminator
                    ),
                )
            except:
                continue
            added_emojis.append(new_emoji)
        msg = "Created {} of {} emoji{}{}.".format(
            len(added_emojis), allowed, "" if allowed == 1 else "s", omitted
        )
        if len(added_emojis):
            msg += "\n\n"
            emoji_text = [
                "{} - `:{}:`".format(self._get_emoji_mention(x), x.name)
                for x in added_emojis
            ]
            msg += "\n".join(emoji_text)
        await message.edit(
            embed=Embed(
                color=self.bot.color,
                description=f"{self.bot.config['emojis']['success']} {ctx.author.mention}: "
                + msg,
            )
        )

    @command(
        name="deleteemojis",
        aliases=["delemojis", "delemoji", "deleteemoji"],
        description="delete emojis from the guild (Max of 10)",
        example=",deleteemojis :sup: :rofl: :haha:",
    )
    @has_permissions(manage_emojis=True)
    async def deleteemojis(self, ctx: Context, emojis: Greedy[Emoji]):
        if len(emojis) > 10:
            raise CommandError("maximum of **10** emojis")
        e = []
        num = 0
        failed = 0
        for emoji in emojis:
            if emoji in list(ctx.guild.emojis):
                e.append(emoji.name)
                num += 1
                await emoji.delete()
            else:
                failed += 1
                pass
        if e:
            if failed == 0:
                embed = Embed(
                    description=f"{self.bot.config['emojis']['success']} {ctx.author.mention}: **deleted emojis:** \n"
                    + "\n".join(emojis for emojis in emojis),
                    color=self.bot.color,
                )
                await ctx.reply(embed=embed)
            else:
                embed = Embed(
                    description=f"{self.bot.config['emojis']['success']} {ctx.author.mention}: "
                    + "**deleted %s emojis, but failed to delete %S**" % (num, failed),
                    color=self.bot.color,
                )
                await ctx.reply(embed=embed)
        else:
            embed = Embed(
                description=f"{self.bot.config['emojis']['fail']} {ctx.author.mention}: could not find those emojis",
                color=self.bot.color,
            )
            await ctx.reply(embed=embed)

    async def eetnlarge(
        self,
        ctx: Context,
        message: Union[Message, Emoji, PartialEmoji] = None,
    ):
        if message:
            if isinstance(message, Emoji):
                emojii = message
                url = str(emojii.url)
                name = emojii.name
                embed = Embed(title=self.bot.user.name, color=self.bot.color).set_image(
                    url=url
                )
                embed.add_field(name=name, value=f"`{emojii.id}`")
                return await ctx.send(embed=embed)

            if isinstance(message, PartialEmoji):
                emojii = message
                url = str(emojii.url)
                name = emojii.name
                embed = Embed(title=self.bot.user.name, color=self.bot.color).set_image(
                    url=url
                )
                embed.add_field(name=name, value=f"`{emojii.id}`")
                return await ctx.send(embed=embed)

            if isinstance(message, Message):
                try:
                    if message.referenced:
                        message = message
                    msg = await ctx.fetch_message(message.id)
                    text = msg.content
                    data = re.findall(r"<(a?):([a-zA-Z0-9\_]+):([0-9]+)>", text)
                    for _a, emoji_name, emoji_id in data:
                        animated = _a == "a"
                        if animated:
                            url = (
                                "https://cdn.discordapp.com/emojis/" + emoji_id + ".gif"
                            )
                        else:
                            url = (
                                "https://cdn.discordapp.com/emojis/" + emoji_id + ".png"
                            )
                        emoteurl = url
                        name = emoji_name
                    # response=requests.get(emoteurl)
                    # img=response.content
                    # img=await GetImage.download(emoteurl)
                    await ctx.send(
                        embed=Embed(
                            title=name,
                            description=f"`{emoji_id}`",
                            color=self.bot.color,
                        ).set_image(url=emoteurl)
                    )
                    # return GetImage.remove(img)
                except:
                    raise CommandError("Invalid Message ID")
                emb = Embed(
                    color=self.bot.color,
                    description=f"No emoji to enlarge, you can also use a message ID by doing {ctx.prefix}enlarge <messageid>\n alternatively do {ctx.prefix}enlarge <emoji>",
                )
                return await ctx.send(embed=emb, delete_after=15)
        try:
            emojis = await self.emoji_find(ctx=ctx)
            emname = emojis.get("name")
            emurl = emojis.get("url")
            emid = emojis.get("id")
        except AttributeError:
            return await ctx.reply(
                embed=Embed(
                    color=self.bot.color,
                    description=f"{self.bot.config['emojis']['fail']} {ctx.author.mention}: **no grabbable previously sent emoji detected**",
                )
            )
        try:
            message = await ctx.send(
                embed=Embed(title=self.bot.user.name, color=self.bot.color)
                .add_field(name=f"{emname}", value=f"```{emid}```")
                .set_image(url=emurl)
            )
        except:
            return await ctx.reply(
                embed=Embed(
                    color=self.bot.color,
                    description=f"{self.bot.config['emojis']['fail']} {ctx.author.mention}: **no grabbable previously sent emoji detected**",
                )
            )

    @command(
        name="editemoji",
        aliases=["editemote"],
        description="rename an emoji",
        example=",editemoji :sup: meow",
    )
    @has_permissions(manage_emojis=True)
    async def editemoji(self, ctx: Context, emoji: Emoji, name: str):
        if len(name) > 20:
            raise CommandError("name must be 20 characters or less")
        if emoji in list(ctx.guild.emojis):
            await emoji.edit(name=name)
            return await ctx.success(f"renamed {emoji} to **{name}**")
        else:
            raise CommandError("could not find that emoji in this **guild**")

    @group(
        name="emoji",
        aliases=["emojis", "emote", "emotes"],
        description="manage server custom emojis",
        invoke_without_command=True,
    )
    async def emoji(self, ctx: Context):
        return await ctx.send_help()

    @emoji.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="view the emojis in the server",
    )
    async def emoji_list(self, ctx: Context) -> Message:
        """
        View all emotes in the server
        """

        if not ctx.guild.emojis:
            return await ctx.fail("No **emotes** found")

        return await ctx.paginate(
            Embed(
                title="List of emotes",
            ),
            [f"{emote} [{emote.name}]({emote.url})" for emote in ctx.guild.emojis],
        )

    @emoji.command(
        name="add",
        aliases=["create", "c", "a"],
        description="create emoji(s)",
        example=",emoji add link smile",
    )
    @has_permissions(manage_emojis=True)
    async def emoji_add(self, ctx: Context, *, emoji=None, name=None):
        return await self.addmultiple(ctx=ctx, emoji=emoji, name=name)

    @emoji.command(
        name="delete",
        aliases=["del", "d", "remove", "rem", "r"],
        description="delete emoji(s)",
        example=",emoji delete :smile1: :smile2:",
    )
    @has_permissions(manage_emojis=True)
    async def emoji_delete(self, ctx: Context, emojis: Greedy[Emoji]):
        return await self.deletemultiple(ctx=ctx, emojis=emojis)

    @emoji.command(
        name="edit",
        aliases=["rename"],
        description="rename an emoji",
        example=",emoji edit :smile: sup",
    )
    @has_permissions(manage_emojis=True)
    async def emoji_edit(self, ctx: Context, emoji: Emoji, name: str):
        return await self.editemoji(ctx=ctx, emoji=emoji, name=name)

    @emoji.command(
        name="enlarge",
        aliases=["big", "bigemoji", "e"],
        description="enlarge an emoji and return an image from it",
        example=",emoji enlarge :sup:",
    )
    async def emoji_enlarge(self, ctx: Context, emoji: Optional[str] = None):
        if emoji is None:
            return await self.eetnlarge(ctx, ctx.message.reference)
        convert = False
        if emoji[0] == "<":
            # custom Emoji
            try:
                name = emoji.split(":")[1]
            except IndexError:
                raise CommandError("that isn't an emoji")
            emoji_name = emoji.split(":")[2][:-1]
            if emoji.split(":")[0] == "<a":
                # animated custom emoji
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
                    # Sometimes occurs when the unicodedata library cannot
                    # resolve the name, however the image still exists
                    name.append("none")
            name = "_".join(name) + ".png"
            if len(chars) == 2 and "fe0f" in chars:
                # remove variation-selector-16 so that the appropriate url can be built without it
                chars.remove("fe0f")
            if "20e3" in chars:
                # COMBINING ENCLOSING KEYCAP doesn't want to play nice either
                chars.remove("fe0f")
            url = "https://twemoji.maxcdn.com/2/svg/" + "-".join(chars) + ".svg"
            convert = True
        async with self.session.get(url) as resp:
            if resp.status != 200:
                raise CommandError("that isn't an emoji")
            img = await resp.read()
        img = await enlarge(url, img)
        return await ctx.send(file=File(img, name))

    @group(
        name="sticker",
        aliases=["stickers"],
        description="manage guild stickers",
        invoke_without_command=True,
    )
    async def sticker(self, ctx: Context):
        return await ctx.send_help()

    @sticker.command(
        name="add",
        aliases=["create", "c", "a"],
        description="create sticker(s)",
        example=",sticker add link smile",
    )
    @has_permissions(manage_emojis=True)
    async def sticker_add(
        self, ctx: Context, message: Union[Message, str], *, name: Optional[str] = None
    ):
        if len(ctx.guild.stickers) >= ctx.guild.sticker_limit:
            raise CommandError("guild sticker limit reached")
        if ctx.message.attachments:
            if not message:
                message = "".join(
                    (secrets.choice(string.ascii_letters) for i in range(6))
                )
            try:
                img = await GetImage.download(ctx.message.attachments[0].url)
                added_sticker: GuildSticker = await ctx.guild.create_sticker(
                    name=message,
                    description="sticker",
                    emoji="🥛",
                    file=File(img),
                    reason=f"{ctx.author} added sticker",
                )
                return await ctx.success(
                    f"added sticker named [{message}]({ctx.message.attachments[0].url})"
                )
            except Exception:
                raise CommandError("image too large")
        if ctx.message.reference:
            message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        if isinstance(message, str):
            if message.startswith("https://"):
                try:
                    await self.validate_content(message)
                    refcode = "".join(
                        (secrets.choice(string.ascii_letters) for i in range(6))
                    )
                    name = name or f"rivalsticker{refcode}"
                    added_sticker: GuildSticker = await ctx.guild.create_sticker(
                        name=name,
                        description="sticker",
                        emoji="🥛",
                        file=File(img),
                        reason=f"Stolen by {ctx.author.name}#{ctx.author.discriminator}",
                    )
                    return await ctx.success(
                        f"added sticker named [{name}]({ctx.message.attachments[0].url})"
                    )
                except Exception:
                    raise CommandError("discord returned a malformed exception")

            else:
                raise CommandError("make sure its a gif, jpeg, or png file URL")
            message = message or ctx.message
        sticker_items = get_message_stickers(message)
        sticker_item = sticker_items[0]
        sticker = await sticker_item.fetch()
        if isinstance(sticker, StandardSticker):
            raise BadArgument(
                "Specified sticker is already in-built. It'd be dumb to add it again."
            )
        b = io.BytesIO(await sticker.read())
        try:
            # Returns bad request, possible problem with the library, henceforth, the command is disabled
            added_sticker: GuildSticker = await ctx.guild.create_sticker(
                name=sticker.name,
                description="sticker",
                emoji="🥛",
                file=File(b),
                reason=f"Stolen by {ctx.author.name}#{ctx.author.discriminator}",
            )
            b.close()
        except HTTPException as exc:
            if exc.code == 30039:
                raise CommandError("guild stickers have reached the guild limit")
            raise exc
        else:
            return await ctx.success(
                f"sticker [{added_sticker.name}]({added_sticker.url}) has been added!",
            )

    @sticker.command(
        name="delete",
        aliases=["del", "d", "remove", "rem", "r"],
        description="delete a guild sticker",
    )
    @has_permissions(manage_emojis=True)
    async def sticker_delete(self, ctx: Context, message: Optional[Message] = None):
        if ctx.message.reference:
            message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        message = message or ctx.message

        sticker_items = get_message_stickers(message)
        sticker_item = sticker_items[0]

        sticker = await sticker_item.fetch()
        name = sticker.name
        if sticker.guild == ctx.guild:
            await sticker.delete()
            return await ctx.success(f"successfully deleted {name}")
        else:
            raise CommandError("sticker not found in guild stickers")

    @sticker.command(
        name="clense",
        aliases=["clean", "cl"],
        description="cleans sticker names and adds vanity to them",
    )
    @has_permissions(manage_emojis=True)
    async def sticker_clense(self, ctx: Context):
        if not ctx.guild.vanity_url_code:
            raise CommandError("guild has no vanity url")
        if ctx.guild.id in self.locked:
            raise CommandError("there is currently a clensing going on...")
        self.locked.append(ctx.guild.id)
        message = await ctx.normal(f"reformatting stickers, this may take a while...")
        amount: int = await self.format_stickers(ctx)
        try:
            self.locked.remove(ctx.guild.id)
        except Exception:
            pass
        return await message.edit(
            embed=await ctx.success(
                f"successfully cleaned **{amount}** stickers", return_embed=True
            )
        )

    @sticker.command(
        name="steal",
        aliases=["take"],
        description="steal the most recently sent stickers",
    )
    @has_permissions(manage_emojis=True)
    async def sticker_steal(
        self,
        ctx: Context,
        message: Optional[Union[Message, str]] = None,
        name: Optional[str] = None,
    ):
        if len(ctx.guild.stickers) >= ctx.guild.sticker_limit:
            raise CommandError("guild sticker limit reached")
        if not message:
            if reference := ctx.message.reference:
                message = await ctx.channel.fetch_message(reference.message_id)
        if isinstance(message, str):
            try:
                async with ClientSession() as session:
                    async with session.request("HEAD", message) as resp:
                        if int(resp.headers.get("Content-Length", 5)) > 52428800:
                            raise CommandError("Content Length Too Large")

                    async with session.get(message) as response:
                        img = io.BytesIO(await response.read())
                refcode = "".join(
                    (secrets.choice(string.ascii_letters) for i in range(6))
                )
                name = name or f"rivalsticker{refcode}"
                added_sticker: GuildSticker = await ctx.guild.create_sticker(
                    name=name,
                    description="sticker",
                    emoji="🥛",
                    file=File(img),
                    reason=f"Stolen by {ctx.author.name}#{ctx.author.discriminator}",
                )
                return await ctx.success(
                    f"sticker [{added_sticker.name}]({added_sticker.url}) has been added",
                )
            except Exception:
                raise CommandError("discord returned a malformed response")

        elif isinstance(message, Message):
            message = message or ctx.message
            sticker_items = get_message_stickers(message)
            sticker_item = sticker_items[0]
            sticker = await sticker_item.fetch()
            if isinstance(sticker, StandardSticker):
                raise BadArgument(
                    "Specified sticker is already in-built. It'd be dumb to add it again."
                )
            b = io.BytesIO(await sticker.read())
            try:
                added_sticker: GuildSticker = await ctx.guild.create_sticker(
                    name=sticker.name,
                    description="sticker",
                    emoji="🥛",
                    file=File(b),
                    reason=f"Stolen by {ctx.author.name}#{ctx.author.discriminator}",
                )
                b.close()
                return await ctx.success(
                    f"successfully stole [**{sticker.name}**]({sticker.url})"
                )
            except Exception:
                raise CommandError(
                    f"No sticker sent in this [message]({message.jump_url})"
                )
        else:
            try:
                stickers = await self.multi_sticker_steal(ctx=ctx)
                if not stickers:
                    raise CommandError("no **Sticker** to steal")
                if stickers[0] == False:
                    emname = stickers[1].get("name")
                    emurl = stickers[1].get("url")
                    emid = stickers[1].get("id")
                else:
                    emotes = stickers[1]
                    formatter = MySource(emotes, per_page=1)
                    menu = StickerStealView(self.bot, formatter, stickers[-1])
                    return await menu.start(ctx)
            except Exception:
                raise CommandError(f"no grabbable previously sent **sticker** detected")

    @command(
        name="transparent",
        description="Remove background from an image",
        example=",transparent https://...",
    )
    async def transparent(self, ctx: Context, url: Optional[str] = None):
        if url is None:
            if ctx.message.attachments:
                url = ctx.message.attachments[0].url
            elif ctx.message.reference:
                if resolved := ctx.message.reference.cached_message:
                    if resolved.message.attachments:
                        url = resolved.message.attachments[0].url
                else:
                    channel = self.bot.get_channel(ctx.message.reference.channel_id)
                    if (
                        resolved := await channel.fetch_message(
                            ctx.message.reference.message_id
                        )
                    ) and resolved.attachments:
                        url = resolved.attachments[0].url
        if not url:
            raise CommandError("please provide either a URL, Attachment or Message")
        # f = await GetImage.download(url)
        f = await self.bot.get_image(url)
        output = await remove_background(f)  # await transparent(f)
        return await ctx.reply(file=File(output))
