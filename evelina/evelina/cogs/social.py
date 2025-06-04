import asyncio
import uuid
import asyncio
import aiohttp
import discord
import datetime
import dateutil.parser

from urllib.parse import unquote

from discord import Embed, Interaction, ButtonStyle, TextStyle
from discord.ui import Button, button, View, Modal, TextInput
from discord.ext.commands import Cog, group, command, cooldown, BucketType

from modules import config
from modules.styles import emojis, colors, icons
from modules.helpers import EvelinaContext
from modules.evelinabot import Evelina
from modules.predicates import nsfw_channel
from modules.misc.views import GunsInfoView

class ClashOfClansVerifyModal(Modal):
    def __init__(self, bot: Evelina, data: dict):
        super().__init__(title="Enter Verification Code")
        self.token = TextInput(label="API Token", placeholder="Enter your API token", style=TextStyle.short, required=True)
        self.add_item(self.token)
        self.bot = bot
        self.data = data

    async def on_submit(self, interaction: Interaction):
        token = self.token.value
        if not token:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You need to provide a verification code")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        payload = {"token": token}
        tag = self.data['tag'][1:]
        data = await self.bot.session.post_json(f"https://api.clashofclans.com/v1/players/%23{tag}/verifytoken", headers={"Authorization": f"Bearer {config.CLASHOFCLANS}"}, params=payload)
        if data['status'] == "invalid":
            embed = Embed(color=colors.WARNING, description=f"{emojis.DENY} {interaction.user.mention}: Invalid verification code")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        elif data['status'] == "ok":
            await interaction.client.db.execute("INSERT INTO clashofclans (user_id, tag) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET tag = $2", interaction.user.id, tag)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Successfully verified your Clash of Clans account")
            return await interaction.response.edit_message(embed=embed, view=None)
        else:
            embed = Embed(color=colors.WARNING, description=f"{emojis.DENY} {interaction.user.mention}: An error occurred while verifying your Clash of Clans account")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

class ClashOfClansVerifyView(View):
    def __init__(self, bot: Evelina, data: dict, author_id: int):
        super().__init__()
        self.bot = bot
        self.data = data
        self.author_id = author_id

    @button(label="Verification", style=ButtonStyle.blurple)
    async def verification(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("You are not the author of this embed", ephemeral=True)
        return await interaction.response.send_modal(ClashOfClansVerifyModal(self.bot, self.data))

class Social(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        
    @command(aliases=["git"], usage="github nike")
    async def github(self, ctx: EvelinaContext, username: str):
        """Gets profile information on the given Github user"""
        data = await self.bot.session.get_json(f"https://api.evelina.bot/github/user?username={username}&key=X3pZmLq82VnHYTd6Cr9eAw")
        if 'message' in data:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
        embed = (
            discord.Embed(color=colors.NEUTRAL, title = f"{data['display'] if data['display'] else ''} (@{data['username']})", description=data['bio'], url=f"https://github.com/{data['username']}/", timestamp=dateutil.parser.parse(data['created']))
            .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            .set_thumbnail(url=data['avatar'])
            .add_field(name="Followers", value=f"{data['followers']}")
            .add_field(name="Following", value=f"{data['following']}")
            .add_field(name="Repos", value=f"{data['repos']}")
            .set_footer(text="Created on", icon_url=icons.GITHUB)
        )
        await ctx.send(embed=embed)

    @command(aliases=["snap"], usage="snapchat nike")
    async def snapchat(self, ctx: EvelinaContext, username: str):
        """Get bitmoji and QR scan code for user"""
        data = await self.bot.session.get_json("https://api.evelina.bot/snapchat/user", params={"username": username, "key": "8F6qVxN55aoODT0FRh16pydP"})
        if 'message' in data:
            return await ctx.send(f"Couldn't get information about **{username}**")
        embed = (
            discord.Embed(
                color=colors.SNAPCHAT,
                title=f"{data['display_name']} (@{data['username']})",
                url=data['url'],
                description=data.get('bio', 'No bio available')
            )
            .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            .set_thumbnail(url=data['avatar'])
            .set_footer(text="Snapchat", icon_url=icons.SNAPCHAT)
        )
        button = discord.ui.Button(label="Snapcode")
        async def button_callback(interaction: discord.Interaction):
            e = discord.Embed(color=0xFFFF00)
            e.set_image(url=data['snapcode'])
            await interaction.response.send_message(embed=e, ephemeral=True)
        button.callback = button_callback
        view = discord.ui.View()
        view.add_item(button)
        await ctx.send(embed=embed, view=view)

    @command(usage="roblox nike")
    async def roblox(self, ctx: EvelinaContext, username: str):
        """Gets profile information on the given Roblox user"""
        data = await self.bot.session.get_json(f"https://api.evelina.bot/roblox/user?username={username}&key=X3pZmLq82VnHYTd6Cr9eAw")
        if 'message' in data:
            await ctx.send_warning(f"Couldn't get information about **{username}**")
            return
        data["bio"] = data["bio"].replace("\\n", "\n")
        data["created_at"] = datetime.datetime.fromtimestamp(data["created_at"])
        embed = (
            discord.Embed(color=colors.NEUTRAL, title=f"{data['display_name']} (@{data['username']}){' ' + emojis.ROBLOX_CHECKMARK if data['verified'] else ''}{' 🔒' if data['banned'] else ''}", url=data['url'] if data['url'] else None, description=data['bio'])
            .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            .set_thumbnail(url=data['avatar_url'] if data['avatar_url'] else None)
            .add_field(name="Created", value=f"<t:{int(data['created_at'].timestamp())}:f>", inline=False)
            .add_field(name="Friends", value=f"{data['friends']:,}", inline=True)
            .add_field(name="Followers", value=f"{data['followers']:,}", inline=True)
            .add_field(name="Following", value=f"{data['followings']:,}", inline=True)
            .set_footer(text=f"Roblox", icon_url=icons.ROBLOX)
        )
        await ctx.send(embed=embed)

    @command(aliases=["ca"], usage="cashapp nike")
    async def cashapp(self, ctx: EvelinaContext, cashtag: str):
        """Retrieve simple CashApp profile information"""
        response, status = await self.bot.session.get_text(f"https://cash.app/${cashtag}", return_status=True)
        if status == 404:
            return await ctx.send_warning("Cashapp profile not found")
        if status != 200:
            return await ctx.send_warning("There was a problem getting the user's CashApp profile")
        qr_url = f"https://cash.app/qr/${cashtag}?size=288&margin=0"
        qr = await self.bot.getbyte(qr_url)
        await ctx.send(f"<https://cash.app/${cashtag}>", file=discord.File(qr, filename="cashapp_qr.png"))

    @command(aliases=["guns"], usage="gunsinfo b")
    async def gunsinfo(self, ctx: EvelinaContext, *, username: str = None):
        """Gets profile information on the given Guns.lol user"""
        if username is None:
            check = await self.bot.db.fetchrow("SELECT * FROM guns WHERE user_id = $1", ctx.author.id)
            if check:
                uid = check['uid']
                data = await self.bot.session.get_json("https://api.evelina.bot/guns/uid", params={"id": uid, "key": config.EVELINA})
                username = data.get("username")
            else:
                return await ctx.send_help(ctx.command)
        data = await self.bot.session.get_json("https://api.evelina.bot/guns/user", params={"username": username, "key": config.EVELINA})
        if 'message' in data:
            return await ctx.send_warning(f"Couldn't get information about Guns user **{username}**")
        display_name = data["config"].get("display_name", "Unknown")
        username = data.get("username", "Unknown")
        description = data["config"].get("description", "No description provided")
        discord_id = f"> Owned by <@{data['discord']['id']}>" if "discord" in data else ''
        page_views = data["config"].get("page_views", "Unknown")
        uid_value = data.get("uid", "Unknown")
        account_created = data.get("account_created", "Unknown")
        alias = data.get("alias", None)
        avatar_url = data["config"].get("avatar", None)
        if avatar_url == "":
            discord_avatars = data["discord"]['avatar'] if "discord" in data else []
            if len(discord_avatars) > 0:
                avatar_url = discord_avatars[0]
            else:
                avatar_url = None
        background_url = data["config"].get("url", None)
        audio_url = data["config"].get("audio", None)
        custom_cursor = data["config"].get("custom_cursor", None)
        user_badges = data["config"].get("user_badges", [])
        badge_emojis = {
            "bughunter": emojis.GUNS_BUGHUNTER,
            "donor": emojis.GUNS_DONOR,
            "imagehost_access": emojis.GUNS_IMAGEHOST_ACCESS,
            "og": emojis.GUNS_OG,
            "premium": emojis.GUNS_PREMIUM,
            "server_booster": emojis.GUNS_SERVER_BOOSTER,
            "staff": emojis.GUNS_STAFF,
            "verified": emojis.GUNS_VERIFIED,
            "christmas_2024": emojis.GUNS_CHRISTMAS_2024,
            "winner": emojis.GUNS_WINNER,
            "second": emojis.GUNS_SECOND,
            "third": emojis.GUNS_THIRD
        }
        if user_badges:
            if isinstance(user_badges[0], dict):
                enabled_badges = [badge['name'] for badge in user_badges if badge.get('enabled', False)]
            elif isinstance(user_badges[0], str):
                enabled_badges = user_badges
            else:
                enabled_badges = []
            badges = ' '.join([badge_emojis.get(badge, '') for badge in enabled_badges if isinstance(badge, str) and badge in badge_emojis])
        else:
            badges = None
        embed = (
            discord.Embed(
                color=colors.NEUTRAL,
                title=f"{display_name} (@{username})",
                description=f"{f'{badges}' if badges else ''}\n{description}\n{discord_id}",
                url=f"https://guns.lol/{username}"
            )
            .add_field(name="Account Creation", value=f"<t:{account_created}:R>")
            .set_footer(text=f"Views: {page_views:,} ● UID {uid_value:,}", icon_url=icons.GUNS)
        )
        if alias:
            embed.add_field(name="Alias", value=alias)
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
            embed.add_field(name="Avatar", value=f"[Click here]({avatar_url})")
        if background_url:
            embed.set_image(url=background_url)
            embed.add_field(name="Background", value=f"[Click here]({background_url})")
        if custom_cursor:
            embed.add_field(name="Cursor", value=f"[Click here]({custom_cursor})")
        if audio_url:
            if isinstance(audio_url, str):
                embed.add_field(name="Audio", value=f"[Click here]({audio_url})")
            elif isinstance(audio_url, list):
                selected_audios = [audio for audio in audio_url]
                if selected_audios:
                    audio_field_value = ", ".join([f"[{audio['title']}]({audio['url']})" for i, audio in enumerate(selected_audios)])
                    embed.add_field(name="Audio", value=audio_field_value, inline=False)
        view = GunsInfoView(self.bot, data)
        await ctx.send(embed=embed, view=view)

    @command(aliases=["gunsuid"], usage="gunsinfouid 28")
    async def gunsinfouid(self, ctx: EvelinaContext, *, uid: str = None):
        """Gets profile information on the given Guns.lol UID"""
        if uid is None:
            check = await self.bot.db.fetchrow("SELECT * FROM guns WHERE user_id = $1", ctx.author.id)
            if check:
                uid = check['uid']
            else:
                return await ctx.send_help(ctx.command)
        data = await self.bot.session.get_json("https://api.evelina.bot/guns/uid", params={"id": uid, "key": config.EVELINA})
        if 'message' in data:
            return await ctx.send_warning(f"Couldn't get information about Guns UID **{uid}**")
        display_name = data["config"].get("display_name", "Unknown")
        username = data.get("username", "Unknown")
        description = data["config"].get("description", "No description provided")
        discord_id = f"> Owned by <@{data['discord']['id']}>" if "discord" in data else ''
        page_views = data["config"].get("page_views", "Unknown")
        uid_value = data.get("uid", "Unknown")
        account_created = data.get("account_created", "Unknown")
        alias = data.get("alias", None)
        avatar_url = data["config"].get("avatar", None)
        if avatar_url == "":
            discord_avatars = data["discord"]['avatar'] if "discord" in data else []
            if len(discord_avatars) > 0:
                avatar_url = discord_avatars[0]
            else:
                avatar_url = None
        background_url = data["config"].get("url", None)
        audio_url = data["config"].get("audio", None)
        custom_cursor = data["config"].get("custom_cursor", None)
        user_badges = data["config"].get("user_badges", [])
        badge_emojis = {
            "bughunter": emojis.GUNS_BUGHUNTER,
            "donor": emojis.GUNS_DONOR,
            "imagehost_access": emojis.GUNS_IMAGEHOST_ACCESS,
            "og": emojis.GUNS_OG,
            "premium": emojis.GUNS_PREMIUM,
            "server_booster": emojis.GUNS_SERVER_BOOSTER,
            "staff": emojis.GUNS_STAFF,
            "verified": emojis.GUNS_VERIFIED,
            "christmas_2024": emojis.GUNS_CHRISTMAS_2024,
            "winner": emojis.GUNS_WINNER,
            "second": emojis.GUNS_SECOND,
            "third": emojis.GUNS_THIRD
        }
        if user_badges:
            if isinstance(user_badges[0], dict):
                enabled_badges = [badge['name'] for badge in user_badges if badge.get('enabled', False)]
            elif isinstance(user_badges[0], str):
                enabled_badges = user_badges
            else:
                enabled_badges = []
            badges = ' '.join([badge_emojis.get(badge, '') for badge in enabled_badges if isinstance(badge, str) and badge in badge_emojis])
        else:
            badges = None
        embed = (
            discord.Embed(
                color=colors.NEUTRAL,
                title=f"{display_name} (@{username})",
                description=f"{f'{badges}' if badges else ''}\n{description}\n{discord_id}",
                url=f"https://guns.lol/{username}"
            )
            .add_field(name="Account Creation", value=f"<t:{account_created}:R>")
            .set_footer(text=f"Views: {page_views:,} ● UID {uid_value:,}", icon_url=icons.GUNS)
        )
        if alias:
            embed.add_field(name="Alias", value=alias)
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
            embed.add_field(name="Avatar", value=f"[Click here]({avatar_url})")
        if background_url:
            embed.set_image(url=background_url)
            embed.add_field(name="Background", value=f"[Click here]({background_url})")
        if custom_cursor:
            embed.add_field(name="Cursor", value=f"[Click here]({custom_cursor})")
        if audio_url:
            if isinstance(audio_url, str):
                embed.add_field(name="Audio", value=f"[Click here]({audio_url})")
            elif isinstance(audio_url, list):
                selected_audios = [audio for audio in audio_url]
                if selected_audios:
                    audio_field_value = ", ".join([f"[{audio['title']}]({audio['url']})" for i, audio in enumerate(selected_audios)])
                    embed.add_field(name="Audio", value=audio_field_value, inline=False)
        view = GunsInfoView(self.bot, data)
        await ctx.send(embed=embed, view=view)
    
    @command(usage="gunslink 28")
    async def gunslink(self, ctx: EvelinaContext, uid: int):
        """Connect your Discord account to Guns.lol"""
        data = await self.bot.session.get_json("https://api.evelina.bot/guns/uid", params={"id": uid, "key": config.EVELINA})
        if 'message' in data:
            return await ctx.send_warning(f"Given guns.lol account does not exist")
        if 'discord' not in data:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {ctx.author.mention}: You have to link your discord account to your guns.lol account first")
            embed.set_image(url=f"https://images.guns.lol/4sLQa.png")
            return await ctx.send(embed=embed)
        if int(data['discord']['id']) != int(ctx.author.id):
            return await ctx.send_warning("You can only link your own guns.lol account")
        check = await self.bot.db.fetchrow("SELECT * FROM guns WHERE user_id = $1", ctx.author.id)
        if check:
            if int(check['uid']) != uid:
                old_uid_data = await self.bot.session.get_json("https://api.evelina.bot/guns/uid", params={"id": check['uid'], "key": config.EVELINA})
                if 'discord' in old_uid_data and int(old_uid_data['discord']['id']) == int(ctx.author.id):
                    await self.bot.db.execute("UPDATE guns SET uid = $1 WHERE user_id = $2", uid, ctx.author.id)
                    await ctx.send_success(f"Successfully updated your linked guns.lol account to [**{data['username']}**](https://guns.lol/{data['username']})")
                else:
                    await self.bot.db.execute("DELETE FROM guns WHERE user_id = $1", ctx.author.id)
                    if int(data['discord']['id']) == int(ctx.author.id):
                        await self.bot.db.execute("INSERT INTO guns (user_id, uid) VALUES ($1, $2)", ctx.author.id, uid)
                        await ctx.send_success(f"Successfully linked the new guns.lol account [**{data['username']}**](https://guns.lol/{data['username']})")
                    else:
                        await ctx.send_warning("You can only link your own guns.lol account")
            else:
                await ctx.send_warning(f"You have already linked this guns.lol account to [**{data['username']}**](https://guns.lol/{data['username']})")
        else:
            await self.bot.db.execute("INSERT INTO guns (user_id, uid) VALUES ($1, $2)", ctx.author.id, uid)
            await ctx.send_success(f"Successfully linked your guns.lol account to [**{data['username']}**](https://guns.lol/{data['username']})")

    @command()
    async def gunslist(self, ctx: EvelinaContext):
        """List all linked guns.lol accounts"""
        data = await self.bot.db.fetch("SELECT * FROM guns ORDER BY uid ASC")
        if not data:
            return await ctx.send_warning("No guns.lol accounts linked")
        async def fetch_user_data(entry):
            user_data = await self.bot.session.get_json("https://api.evelina.bot/guns/uid", params={"id": entry['uid'], "key": config.EVELINA})
            if 'message' in user_data:
                return None
            return f"[**{user_data['username']}**](https://guns.lol/{user_data['username']}) (`{entry['uid']}`) - <@{entry['user_id']}>"
        tasks = [fetch_user_data(entry) for entry in data]
        results = await asyncio.gather(*tasks)
        content = [result for result in results if result is not None] 
        if not content:
            return await ctx.send_warning("No valid guns.lol accounts found.")
        await ctx.paginate(content, "Linked guns.lol accounts", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command(aliases=["snapstory"], usage="snapchatstory nike")
    async def snapchatstory(self, ctx: EvelinaContext, username: str):
        """Gets all current stories for the given Snapchat user"""
        try:
            async with ctx.typing():
                data = await self.bot.session.get_json("https://api.evelina.bot/snapchat/story", params={"username": username.lower(), "key": config.EVELINA})
            story_urls = data.get("stories", {}).get("urls", [])
            story_times = data.get("stories", {}).get("times", [])
            author = data.get("author", {}).get("username", "unknown")
            if not story_urls or not story_times:
                return await ctx.send_warning(f"Couldn't get stories from **{username}** - no stories found.")
            if len(story_urls) != len(story_times):
                return await ctx.send_warning(f"Couldn't get stories from **{username}** - mismatch between story URLs and times.")
            semaphore = asyncio.Semaphore(5)
            tasks = [
                self.process_snapchat_story(self.bot.session._session, url, timestamp_str, author, index, len(story_urls), semaphore)
                for index, (url, timestamp_str) in enumerate(zip(story_urls, story_times))
            ]
            uploaded_urls = await asyncio.gather(*tasks)
            uploaded_urls = [msg for msg in uploaded_urls if msg]
            if uploaded_urls:
                await ctx.paginator_content(uploaded_urls)
            else:
                await ctx.send_warning(f"No valid stories found for **{username}**.")
        except Exception as e:
            return await ctx.send_warning(f"Couldn't get stories from **{username}**: {str(e)}")

    async def process_snapchat_story(self, session: aiohttp.ClientSession, url: str, timestamp_str: str, author: str, index: int, total_stories: int, semaphore: asyncio.Semaphore) -> str:
        async with semaphore:
            try:
                timestamp = int(timestamp_str)
                r2_url = await self.upload_to_r2(url, session, author)
                if not r2_url:
                    return None
                message_content = f"**@{author}** — Posted <t:{timestamp}:R>\n({index + 1}/{total_stories}) {r2_url}"
                return message_content
            except Exception:
                return None
            
    @command(aliases=["igposts"], usage="instagramposts nike")
    async def instagramposts(self, ctx: EvelinaContext, username: str):
        """Fetch Instagram post from a username"""
        try:
            await ctx.message.edit(suppress=True)
            data = await self.bot.session.get_json("https://api.evelina.bot/instagram/posts", params={"username": username, "key": config.EVELINA})
            items = data.get("items", [])
            if not items:
                return await ctx.send_warning(f"Couldn't get posts from **{username}**")
            embeds = []
            total_posts = len(items)
            for index, item in enumerate(items):
                author = item.get("author", {})
                username = author.get("username", "unknown")
                avatar_url = author.get("avatar", "")
                caption = item.get("caption", "")
                code = item.get("code", "")
                likes = item.get("likes", 0)
                comments = item.get("comments", 0)
                media = item.get("media", [])
                if not media:
                    continue
                total_slides = len(media)
                for media_index, media_item in enumerate(media):
                    if media_item.get("type") == "image":
                        image_url = media_item.get("url")
                        embed = discord.Embed(color=colors.INSTAGRAM, description=f"[{caption}](https://instagram.com/p/{code})")
                        embed.set_author(name=f"{username}", icon_url=f"{avatar_url}", url=f"https://instagram.com/{username}")
                        embed.set_image(url=image_url)
                        embed.set_footer(text=f"Post {index + 1}/{total_posts} ・ Slide {media_index + 1}/{total_slides} ・ ❤️ {likes:,}  💬 {comments:,} | {ctx.author.name}")
                        embeds.append(embed)
            if not embeds:
                return await ctx.send_warning("Error fetching information from the Instagram URL.")
            return await ctx.paginator(embeds=embeds)
        except Exception:
            return await ctx.send_warning(f"Couldn't get images from **{username}**")

    @command(aliases=["igpost"], usage="instagrampost https://instagram/p/.....")
    async def instagrampost(self, ctx: EvelinaContext, url: str):
        """Fetch Instagram post from a URL"""
        try:
            await ctx.message.edit(suppress=True)
            async with ctx.typing():
                data = await self.bot.session.get_json("https://api.evelina.bot/instagram/post", params={"url": url, "key": config.EVELINA})
                username = data["author"]["username"]
                image_urls = data["media"]["urls"]
                post_time = data["media"]["time"]
                if not image_urls:
                    return await ctx.send_warning(f"An error occurred while fetching the post from **{url}**")
                semaphore = asyncio.Semaphore(5)
                tasks = [
                    self.process_instagram_post(self.bot.session._session, image_url, post_time, username, index, len(image_urls), semaphore)
                    for index, image_url in enumerate(image_urls)
                ]
                uploaded_urls = await asyncio.gather(*tasks)
                uploaded_urls = [msg for msg in uploaded_urls if msg]
                if uploaded_urls:
                    await ctx.paginator_content(uploaded_urls)
                else:
                    await ctx.send_warning(f"No valid posts found for **{url}**")
        except Exception as e:
            return await ctx.send_warning(f"An error occurred while fetching the post from **{url}**: {str(e)}")

    async def process_instagram_post(self, session: aiohttp.ClientSession, image_url: str, post_time: int, username: str, index: int, total_images: int, semaphore: asyncio.Semaphore) -> str:
        async with semaphore:
            try:
                r2_url = await self.upload_to_r2(image_url, session, username)
                if not r2_url:
                    return None
                message_content = (
                    f"**@{username}** — Posted <t:{int(post_time)}:R>\n"
                    f"({index + 1}/{total_images}) {r2_url}\n"
                )
                return message_content
            except Exception:
                return None
        
    @command(aliases=["igstory"], usage="instagramstory nike")
    async def instagramstory(self, ctx: EvelinaContext, username: str):
        """Gets all current stories for the given Instagram user"""
        try:
            async with ctx.typing():
                data = await self.bot.session.get_json("https://api.evelina.bot/instagram/story", params={"username": username.lower(), "key": config.EVELINA})
            story_urls = data.get("stories", {}).get("urls", [])
            story_times = data.get("stories", {}).get("times", [])
            author = data.get("author", {}).get("username", "unknown")
            if not story_urls or not story_times:
                return await ctx.send_warning(f"Couldn't get stories from **{username}** - no stories found.")
            if len(story_urls) != len(story_times):
                return await ctx.send_warning(f"Couldn't get stories from **{username}** - mismatch between story URLs und times.")
            semaphore = asyncio.Semaphore(5)
            tasks = [
                self.process_instagram_story(self.bot.session._session, url, timestamp_str, author, index, len(story_urls), semaphore)
                for index, (url, timestamp_str) in enumerate(zip(story_urls, story_times))
            ]
            uploaded_urls = await asyncio.gather(*tasks)
            uploaded_urls = [msg for msg in uploaded_urls if msg]
            if uploaded_urls:
                await ctx.paginator_content(uploaded_urls)
            else:
                await ctx.send_warning(f"No valid stories found for **{username}**.")
        except Exception as e:
            return await ctx.send_warning(f"Couldn't get stories from **{username}**: {str(e)}")

    async def process_instagram_story(self, session: aiohttp.ClientSession, url: str, timestamp_str: str, author: str, index: int, total_stories: int, semaphore: asyncio.Semaphore) -> str:
        async with semaphore:
            try:
                timestamp = int(timestamp_str)
                r2_url = await self.upload_to_r2(url, session, author)
                if not r2_url:
                    return None
                message_content = f"**@{author}** — Posted <t:{timestamp}:R>\n({index + 1}/{total_stories}) {r2_url}"
                return message_content
            except Exception:
                return None

    @command(name="minecraft", usage="minecraft <username>")
    async def minecraft(self, ctx: EvelinaContext, username: str):
        """Gets profile information on the given Minecraft player"""
        data, status = await self.bot.session.get_json(f"https://api.evelina.bot/minecraft?username={username}&key=X3pZmLq82VnHYTd6Cr9eAw", return_status=True)
        if status != 200:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
        history = sorted(data['history'], key=lambda x: x['changed'] if x['changed'] is not None else 0, reverse=True)
        history_entries = []
        for entry in history:
            changed_date = (f"<t:{entry['changed']}:R>" if entry['changed'] else "Original Name")
            history_entries.append(f"**{entry['name']}** - {changed_date}")
        embed = discord.Embed(
            title=f"{data['name']}",
            url=f"https://laby.net/{data['uuid']}",
            color=colors.NEUTRAL,
            description="\n".join(history_entries)
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_thumbnail(url=data['skin'])
        embed.set_footer(text=f"UUID: {data['uuid']}", icon_url=icons.XBOX)
        await ctx.send(embed=embed)

    @group(name="fortnite", invoke_without_command=True, case_insensitive=True)
    async def fortnite(self, ctx: EvelinaContext):
        """Fortnite related commands"""
        return await ctx.create_pages()

    @fortnite.command(name="lifetime", usage="fortnite lifetime bender 么")
    async def fortnite_lifetime(self, ctx: EvelinaContext, *, username: str):
        """Gets lifetime stats on the given fortnite player"""
        headers = {'Authorization': '344f3f03-718c-4b23-b163-d32605e2072d'}
        params = {'name': username, 'accountType': "epic", 'timeWindow': "lifetime", 'image': "all"}

        data, status = await self.bot.session.get_json("https://fortnite-api.com/v2/stats/br/v2", headers=headers, params=params, return_status=True)
        if status == 200:
            embed = discord.Embed(title=f"Fortnite Stats - {data['data']['account']['name']}", color=colors.NEUTRAL)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_image(url=f"{data['data']['image']}")
            return await ctx.send(embed=embed)
        elif status == 401:
            return await ctx.send_warning(f"This player has changed their in-game settings to make their profile private :(")
        else:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")
                
    @fortnite.command(name="season", usage="fortnite season bender 么")
    async def fortnite_season(self, ctx: EvelinaContext, *, username: str):
        """Gets season stats on the given fortnite player"""
        headers = {'Authorization': '344f3f03-718c-4b23-b163-d32605e2072d'}
        params = {'name': username, 'accountType': "epic", 'timeWindow': "season", 'image': "all"}

        data, status = await self.bot.session.get_json("https://fortnite-api.com/v2/stats/br/v2", headers=headers, params=params, return_status=True)
        if status == 200:
            embed = discord.Embed(title=f"Fortnite Stats - {data['data']['account']['name']}", color=colors.NEUTRAL)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_image(url=f"{data['data']['image']}")
            return await ctx.send(embed=embed)
        elif status == 401:
            return await ctx.send_warning(f"This player has changed their in-game settings to make their profile private :(")
        else:
            return await ctx.send_warning(f"Couldn't get information about **{username}**")

    @fortnite.command(name="item", usage="fortnite item Renegade Raider")
    async def fortnite_item(self, ctx: EvelinaContext, *, cosmetic: str):
        """Searches for a Fortnite item by name and fetches its details"""
        data = await self.bot.session.get_json(f"https://fortnite-api.com/v2/cosmetics/br/search?name={cosmetic}")
        if not data.get("data"):
            return await ctx.send_warning(f"Couldn't find any item with the name **{cosmetic}**.")
        item_data = data["data"]
        embed = (
            discord.Embed(
                title=f"{item_data['name']} ({item_data['type']['displayValue']})",
                description=f"{item_data['description']}",
                color=colors.NEUTRAL,
            )
            .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            .set_thumbnail(url=item_data["images"]["icon"])
            .add_field(name="Added to Fortnite", value=f"**Chapter:** `{item_data['introduction']['chapter']}` **Season:** `{item_data['introduction']['season']}`", inline=False)
        )
        await ctx.send(embed=embed)

    @fortnite.command(name="shop", usage="fortnite shop")
    async def fortnite_shop(self, ctx: EvelinaContext):
        """Show daily fortnite shop rotation"""
        now = datetime.datetime.now()
        file = discord.File(await self.bot.getbyte(f"https://bot.fnbr.co/shop-image/fnbr-shop-{now.day}-{now.month}-{now.year}.png"), filename="fortnite.png")
        await ctx.send(file=file)

    async def upload_to_r2(self, url: str, session: aiohttp.ClientSession, author: str) -> str:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get('Content-Type')
                    if 'image' in content_type:
                        file_extension = 'png'
                    elif 'video' in content_type:
                        file_extension = 'mp4'
                    else:
                        return None
                    file_data = await resp.read()
                    file_name = f"{str(uuid.uuid4())[:8]}.{file_extension}"
                    upload_res = await self.bot.r2.upload_file("evelina-media", file_data, file_name, content_type)
                    file_url = f"https://m.evelina.bot/{file_name}"
                    return file_url
                else:
                    return None
        except Exception:
            return None

    @command(name="steam", usage="steam 76561199237717712")
    async def steam(self, ctx: EvelinaContext, steamid: int):
        """Gets profile information on the given Steam user"""
        data = await self.bot.session.get_json(f"https://api.evelina.bot/steam/user?id={steamid}&key=X3pZmLq82VnHYTd6Cr9eAw")
        if 'message' in data:
            return await ctx.send_warning(f"Couldn't get information about **{steamid}**")
        data = data['response']['players'][0]
        title = f"{data['personaname']}"
        if data.get('realname'):
            title += f" ({data['realname']})"
        embed = discord.Embed(
            title=title,
            url=f"{data['profileurl']}",
            color=colors.NEUTRAL,
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_thumbnail(url=data['avatarfull'])
        embed.add_field(name="Name", value=data['personaname'], inline=True)
        embed.add_field(name="Reigstered", value=f"<t:{data['timecreated']}:R>", inline=True)
        if 'lastlogoff' in data:
            embed.add_field(name="Last Online", value=f"<t:{data['lastlogoff']}:R>", inline=True)
        embed.set_footer(text=f"SteamID: {steamid}", icon_url=icons.STEAM)
        return await ctx.send(embed=embed)

    @command(name="valorant", aliases=["val"], usage="valorant bender#1234", cooldown=5)
    @cooldown(1, 5, BucketType.user)
    async def valorant(self, ctx: EvelinaContext, *, username: str):
        """Gets profile information on the given Valorant user"""
        async with ctx.typing():
            if "#" not in username:
                return await ctx.send_warning("Invalid username format. Please use the format 'username#tag'.")
            name, tag = username.split("#")
            clean_username = username.replace("#", "%23").replace(" ", "%20")
            data = await self.bot.session.get_json(f"https://api.henrikdev.xyz/valorant/v2/account/{name}/{tag}", headers={"Authorization": config.VALORANT})
            if data.get("status") == 200:
                current_level = data['data']['account_level']
            elif data.get("errors"):
                return await ctx.send_warning(f"{data['errors'][0]['message']}")
            else:
                return await ctx.send_warning(f"Couldn't get information about **{username}**")
            if data.get("data").get("region"):
                ranked_data = await self.bot.session.get_json(f"https://api.henrikdev.xyz/valorant/v2/mmr/{data['data']['region']}/{name}/{tag}", headers={"Authorization": config.VALORANT})
                if ranked_data.get("status") == 200:
                    current_rank = ranked_data['data']['current_data']['currenttierpatched']
                    current_elo = ranked_data['data']['current_data']['ranking_in_tier']
                    current_image = ranked_data['data']['current_data']['images']['large']
                else:
                    current_rank = "Unranked"
                    current_elo = "0"
                    current_image = None
                ranked_matches = await self.bot.session.get_json(f"https://api.henrikdev.xyz/valorant/v1/mmr-history/{data['data']['region']}/{name}/{tag}", headers={"Authorization": config.VALORANT})
                if ranked_matches.get("status") == 200:
                    matches = []
                    for match in ranked_matches['data'][:5]:
                        time = match['date_raw']
                        rank = match['currenttierpatched']
                        elo_change = match['mmr_change_to_last_game']
                        matches.append(f"<t:{time}:R> - **{rank}** (`{elo_change}`)")
                else:
                    matches = ["No matches found"]
            else:
                current_rank = "Unranked"
                current_elo = "0"
                current_image = None
                matches = ["No matches found"]
            embed = Embed(color=colors.NEUTRAL, title=username, url=f"https://tracker.gg/valorant/profile/riot/{clean_username}/overview", description=f"**Account Level:** {current_level}\n**Rank & Elo:** {current_rank} / {current_elo}")
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url=current_image)
            embed.add_field(name=f"Competitve Matches", value="\n".join(matches), inline=False)
            embed.set_footer(text=f"UID: {data['data']['puuid']}", icon_url=icons.VALORANT)
            return await ctx.send(embed=embed)

    @group(name="clashofclans", aliases=["coc"], invoke_without_command=True, case_insensitive=True)
    async def clashofclans(self, ctx: EvelinaContext):
        """Clash of Clans related commands"""
        return await ctx.create_pages()

    @clashofclans.command(name="verify", usage="clashofclans verify #8LOJ2PG9G")
    async def clashofclans_verify(self, ctx: EvelinaContext, tag: str):
        """Verify your Clash of Clans account"""
        check = await self.bot.db.fetchrow("SELECT * FROM clashofclans WHERE user_id = $1", ctx.author.id)
        if check:
            data = await self.bot.session.get_json(f"https://api.clashofclans.com/v1/players/%23{check['tag']}", headers={"Authorization": f"Bearer {config.CLASHOFCLANS}"})
            return await ctx.send_warning(f"Your Discord account is already linked with **{data['name']} | {data['tag']}**")
        if tag.startswith("#"):
            tag = tag[1:]
        data = await self.bot.session.get_json(f"https://api.clashofclans.com/v1/players/%23{tag}", headers={"Authorization": f"Bearer {config.CLASHOFCLANS}"})
        if data.get("reason"):
            return await ctx.send_warning(f"Couldn't get information about **{tag}**")
        embed = Embed(color=colors.NEUTRAL, title="Verification", description=f"You need to enter your API token to verify your Clash of Clans account\n> You can find your API token by going into [Settings -> More Settings](https://link.clashofclans.com/en/?action=OpenMoreSettings) and scrolling down.")
        embed.add_field(name="Tag", value=tag)
        embed.add_field(name="Name", value=data['name'])
        embed.add_field(name="Level", value=data['expLevel'])
        embed.set_footer(text="You need to verify in the next 2 minutes, otherwise the verification will be cancelled.")
        view = ClashOfClansVerifyView(self.bot, data, ctx.author.id)
        return await ctx.send(embed=embed, view=view)

    @clashofclans.command(name="info", usage="clashofclans info #8LOJ2PG9G")
    async def clashofclans_info(self, ctx: EvelinaContext, tag: str = None):
        """Gets profile information on the given Clash of Clans player"""
        if tag is None:
            check = await self.bot.db.fetchrow("SELECT * FROM clashofclans WHERE user_id = $1", ctx.author.id)
            if check:
                data = await self.bot.session.get_json(f"https://api.clashofclans.com/v1/players/%23{check['tag']}", headers={"Authorization": f"Bearer {config.CLASHOFCLANS}"})
            else:
                return await ctx.send_warning("You need to provide a tag or verify your account first")
        else:
            if tag.startswith("#"):
                tag = tag[1:]
            data = await self.bot.session.get_json(f"https://api.clashofclans.com/v1/players/%23{tag}", headers={"Authorization": f"Bearer {config.CLASHOFCLANS}"})
        if data.get("reason"):
            return await ctx.send_warning(f"Couldn't get information about **{tag}**")        
        embed = Embed(color=colors.NEUTRAL, title=f"{data['name']} | {data['tag']}", url=f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag={data['tag']}")
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        emoji = emojis.TH8 if data['townHallLevel'] == 8 else emojis.TH9 if data['townHallLevel'] == 9 else emojis.TH10 if data['townHallLevel'] == 10 else emojis.TH11 if data['townHallLevel'] == 11 else emojis.TH12 if data['townHallLevel'] == 12 else emojis.TH13 if data['townHallLevel'] == 13 else emojis.TH14 if data['townHallLevel'] == 14 else emojis.TH15 if data['townHallLevel'] == 15 else emojis.TH16 if data['townHallLevel'] == 16 else emojis.TH17 if data['townHallLevel'] == 17 else ""
        embed.add_field(name="Town Hall", value=f"{emoji} {data['townHallLevel']}", inline=True)
        embed.add_field(name="Exp Level", value=f"{emojis.XP} {data['expLevel']}", inline=True)
        embed.add_field(name="Clan", value=f"{emojis.LOOKING_FOR_CLAN} {data['clan']['name'] if 'clan' in data and data['clan'] else 'No Clan'}", inline=True)
        embed.add_field(name="Trophies", value=f"{emojis.TROPHY} {data['trophies']}", inline=True)
        embed.add_field(name="Personal Best", value=f"{emojis.CHAMPIONKING} {data['bestTrophies']}", inline=True)
        embed.add_field(name="War Stars", value=f"{emojis.STAR} {data['warStars']}", inline=True)
        embed.add_field(name="Troop Donations", value=f"{emojis.SPEEDUP} {data['donations']}", inline=True)
        embed.add_field(name="Multiplayer Wins", value=f"{emojis.SWORDS} {data['attackWins']}", inline=True)
        embed.add_field(name="Multiplayer Defenses", value=f"{emojis.SHIELD} {data['defenseWins']}", inline=True)
        embed.add_field(name="Builder Hall", value=f"{emojis.BH} {data['builderHallLevel']}", inline=True)
        embed.add_field(name="Builder Trophies", value=f"{emojis.VERSUSTROPHY} {data['builderBaseTrophies']}", inline=True)
        embed.add_field(name="Builder Personal Best", value=f"{emojis.NIGHTWITCH} {data['bestBuilderBaseTrophies']}", inline=True)
        return await ctx.send(embed=embed)

    @clashofclans.command(name="heroes", usage="clashofclans heroes #8LOJ2PG9G")
    async def clashofclans_heroes(self, ctx: EvelinaContext, tag: str = None):
        """Gets hero information on the given Clash of Clans player"""
        if tag is None:
            check = await self.bot.db.fetchrow("SELECT * FROM clashofclans WHERE user_id = $1", ctx.author.id)
            if check:
                data = await self.bot.session.get_json(f"https://api.clashofclans.com/v1/players/%23{check['tag']}", headers={"Authorization": f"Bearer {config.CLASHOFCLANS}"})
            else:
                return await ctx.send_warning("You need to provide a tag or verify your account first")
        else:
            if tag.startswith("#"):
                tag = tag[1:]
            data = await self.bot.session.get_json(f"https://api.clashofclans.com/v1/players/%23{tag}", headers={"Authorization": f"Bearer {config.CLASHOFCLANS}"})
        if data.get("reason"):
            return await ctx.send_warning(f"Couldn't get information about **{tag}**")
        heroes = data['heroes']
        embed = Embed(color=colors.NEUTRAL, title=f"{data['name']} | {data['tag']}", url=f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag={data['tag']}")
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        sorted_heroes = sorted(heroes, key=lambda x: x['level'], reverse=True)
        for hero in sorted_heroes:
            equipment_list = [f"{equip['name']} (Level {equip['level']})" for equip in hero.get('equipment', [])]
            equipment_str = "\n".join(equipment_list) if equipment_list else "No equipment"
            embed.add_field(name=f"{hero['name']} ({hero['level']}/{hero['maxLevel']})", value=equipment_str, inline=True)
        return await ctx.send(embed=embed) 

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Social(bot))