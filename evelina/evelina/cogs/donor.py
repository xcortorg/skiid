import os
import string
import asyncio
import random
import openai
import datetime
import tempfile

from openai import AsyncOpenAI

from io import BytesIO

from discord import User, Embed, Member, AllowedMentions, Forbidden, File
from discord.ext.commands import Cog, command, cooldown, BadArgument, BucketType, group, has_guild_permissions, bot_has_guild_permissions, hybrid_command, hybrid_group
from discord.errors import HTTPException

from modules import config
from modules.styles import colors
from modules.evelinabot import Evelina
from modules.converters import NoStaff
from modules.helpers import EvelinaContext
from modules.predicates import has_perks, create_account

class Donor(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.lock = asyncio.Lock()

    def shorten(self, value: str, length: int = 32):
        if len(value) > length:
            value = value[: length - 2] + ("..." if len(value) > length else "").strip()
        return value
    
    @hybrid_command(name="redeem", aliases=["claim"], usage="redeem 22AD-AED2-45D2-87FB")
    @create_account()
    async def redeem(self, ctx: EvelinaContext, key: str):
        """Redeem your product keys"""
        check = await self.bot.db.fetchrow("SELECT * FROM store_orders WHERE serial_code = $1", key)
        if not check:
            return await ctx.send_warning("Product key is **invalid**")
        if check["claimed"] == True:
            return await ctx.send_warning(f"Product key is **already claimed** by <@{check['claimed_by']}>")
        if check["product_id"] == 1:
            check_donator = await self.bot.db.fetchrow("SELECT * FROM donor WHERE user_id = $1", ctx.author.id)
            if not check_donator:
                await self.bot.db.execute("UPDATE store_orders SET claimed = $1, claimed_by = $2 WHERE serial_code = $3", True, ctx.author.id, key)
                await self.bot.db.execute("INSERT INTO donor VALUES ($1, $2, $3)", ctx.author.id, datetime.datetime.utcnow().timestamp(), "purchased")
                await self.bot.manage.add_role(ctx.author, 1242474452353290291)
                channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
                embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **donator** to {ctx.author.mention} `{ctx.author.name}`\n > **Key:** {key}"))
                await channel.send(embed=embed)
                return await ctx.send_success("You have **redeemed** your **donator perks**")
            elif check_donator["status"] == "boosted":
                await self.bot.db.execute("UPDATE store_orders SET claimed = $1, claimed_by = $2 WHERE serial_code = $3", True, ctx.author.id, key)
                await self.bot.db.execute("UPDATE donor SET status = $1 WHERE user_id = $2", "purchased", ctx.author.id)
                await self.bot.manage.add_role(ctx.author, 1242474452353290291)
                channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
                embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **donator** to {ctx.author.mention} `{ctx.author.name}`\n > **Key:** {key}"))
                await channel.send(embed=embed)
                return await ctx.send_success("You have **redeemed** your **donator perks**")
            else:
                return await ctx.send_warning("You already have **donator perks**\n> If you need help, create a Ticket in our [**Support Server**](https://discord.gg/evelina)")
        if check["product_id"] == 2:
            await self.bot.db.execute("UPDATE store_orders SET claimed = $1, claimed_by = $2 WHERE serial_code = $3", True, ctx.author.id, key)
            await self.bot.db.execute("UPDATE economy SET item_booster = item_booster + 1 WHERE user_id = $1", ctx.author.id)
            channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
            embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **booster** to {ctx.author.mention} (`{ctx.author.id}`)\n > **Key:** {key}"))
            await channel.send(embed=embed)
            return await ctx.send_success(f"You have **redeemed** your **economy booster**\n > Use `{ctx.clean_prefix}item use booster` to activate it")
        if check["product_id"] == 3:
            await self.bot.db.execute("UPDATE store_orders SET claimed = $1, claimed_by = $2 WHERE serial_code = $3", True, ctx.author.id, key)
            channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
            embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **custom instance** to {ctx.author.mention} (`{ctx.author.id}`)\n > **Key:** {key}"))
            await channel.send(embed=embed)
            return await ctx.send_success("You have **redeemed** your **custom instance**\n> Please open a ticket in our [**Support Server**](https://discord.gg/evelina) to get started")
        if check["product_id"] == 4:
            await self.bot.db.execute("UPDATE store_orders SET claimed = $1, claimed_by = $2 WHERE serial_code = $3", True, ctx.author.id, key)
            channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
            embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **premium** to {ctx.author.mention} (`{ctx.author.id}`)\n > **Key:** {key}"))
            await channel.send(embed=embed)
            return await ctx.send_success("You have **redeemed** your **premium**\n> Please open a ticket in our [**Support Server**](https://discord.gg/evelina) to get started")
        if check["product_id"] == 5:
            await self.bot.db.execute("UPDATE store_orders SET claimed = $1, claimed_by = $2 WHERE serial_code = $3", True, ctx.author.id, key)
            await self.bot.db.execute("UPDATE economy SET cash = cash + 10000000 WHERE user_id = $1", ctx.author.id)
            channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
            embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **10.000.000 💵** to {ctx.author.mention} (`{ctx.author.id}`)\n > **Key:** {key}"))
            await channel.send(embed=embed)
            return await ctx.send_success("You have **redeemed** your **10.000.000 💵**\n> Use `;balance` to check your balance")
        if check["product_id"] == 7:
            company = await self.bot.db.fetchrow("SELECT * FROM company WHERE $1 = ANY(members)", ctx.author.id)
            if not company:
                return await ctx.send_warning("You are **not** in a company")
            await self.bot.db.execute("UPDATE store_orders SET claimed = $1, claimed_by = $2 WHERE serial_code = $3", True, ctx.author.id, key)
            company_voters = await self.bot.db.fetchrow("SELECT * FROM company_voters WHERE company_id = $1 AND user_id = $2", company['id'], ctx.author.id)
            if company_voters:
                await self.bot.db.execute("UPDATE company_voters SET votes = votes + $1 WHERE company_id = $2 AND user_id = $3", 25, company['id'], ctx.author.id)
            else:
                await self.bot.db.execute("INSERT INTO company_voters VALUES ($1,$2,$3)", ctx.author.id, company['id'], 25)
            await self.bot.db.execute("UPDATE company SET votes = votes + $1 WHERE id = $2", 25, company['id'])
            channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
            embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **25 votes** to {ctx.author.mention} (`{ctx.author.id}`)\n > **Key:** {key}"))
            await channel.send(embed=embed)
            return await ctx.send_success("You have **redeemed** your **25 votes** for your company")

    @group(name="lookup", aliases=["pomelo", "handles"], brief="donator", invoke_without_command=True, case_insensitive=True)
    async def lookup(self, ctx: EvelinaContext):
        """Lookup commands"""
        return await ctx.create_pages()

    @lookup.command(name="username", aliases=["usernames"], brief="donator", usage="lookup username 5")
    @has_perks()
    async def lookup_username(self, ctx: EvelinaContext, length: int = None):
        """Get the most recent username changes"""
        if length is not None:
            query = "SELECT user_name, time FROM usernames WHERE LENGTH(user_name) = $1 ORDER BY time DESC"
            results = await self.bot.db.fetch(query, length)
        else:
            time_threshold = int((datetime.datetime.utcnow() - datetime.timedelta(days=21)).timestamp())
            query = "SELECT user_name, time FROM usernames WHERE time > $1 ORDER BY time DESC LIMIT 10000"
            results = await self.bot.db.fetch(query, time_threshold)
        if not results:
            return await ctx.send_warning(f"No usernames found with {length} characters" if length else "No usernames found")
        output = [f"{result['user_name']} - <t:{result['time']}:R>" for result in results]
        return await ctx.paginate(output, f"Pomelo Usernames")
    
    @lookup.command(name="vanity", aliases=["vanitys"], brief="donator", usage="lookup vanity 5")
    @has_perks()
    async def lookup_vanity(self, ctx: EvelinaContext, length: int = None):
        """Get the most recent vanity changes"""
        if length is not None:
            query = "SELECT vanity, time FROM vanitys WHERE LENGTH(vanity) = $1 ORDER BY time DESC"
            results = await self.bot.db.fetch(query, length)
        else:
            query = "SELECT vanity, time FROM vanitys ORDER BY time DESC"
            results = await self.bot.db.fetch(query)
        if not results:
            return await ctx.send_warning(f"No vanity URLs found with {length} characters" if length else "No vanity URLs found")
        output = [f"{result['vanity']} - <t:{result['time']}:R>" for result in results]
        return await ctx.paginate(output, f"Pomelo Vanity URLs")

    @command(name="selfpurge", brief="donator", usage="selfpurge 10")
    @has_perks()
    async def selfpurge(self, ctx: EvelinaContext, amount: int = 100):
        """Delete your own messages"""
        await ctx.channel.purge(limit=amount, check=lambda m: m.author.id == ctx.author.id and not m.pinned, bulk=True)

    @group(name="forcenick", aliases=["fn"], brief="manage nicknames, donator", invoke_without_command=True, case_insensitive=True)
    @has_perks()
    @has_guild_permissions(manage_nicknames=True)
    @bot_has_guild_permissions(manage_nicknames=True)
    async def forcenick(self, ctx: EvelinaContext):
        """Managing force nicknames"""
        return await ctx.create_pages()

    @forcenick.command(name="set", brief="manage nicknames, donator", usage="forcenick set comminate King")
    async def forcenick_set(self, ctx: EvelinaContext, member: NoStaff, *, nickname: str):
        """Set or update a member's forced nickname"""
        if len(nickname) > 32:
            return await ctx.send_warning("Nickname can't be longer than 32 characters")
        try:
            if await self.bot.db.fetchrow("SELECT * FROM force_nick WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id):
                await self.bot.db.execute("UPDATE force_nick SET nickname = $1 WHERE guild_id = $2 AND user_id = $3", nickname, ctx.guild.id, member.id)
            else:
                await self.bot.db.execute("INSERT INTO force_nick VALUES ($1,$2,$3)", ctx.guild.id, member.id, nickname)
            await member.edit(nick=nickname, reason="Force nickname applied to this member")
            await ctx.send_success(f"Force nicknamed {member.mention} to **{nickname}**")
        except Forbidden:
            return await ctx.send_warning("I don't have permission to change this member's nickname. Please check the role hierarchy")
        except HTTPException:
            return await ctx.send_warning("Display name contains community flagged words")
    
    @forcenick.command(name="remove", brief="manage nicknames, donator", usage="forcenick remove comminate")
    async def forcenick_remove(self, ctx: EvelinaContext, member: NoStaff):
        """Remove a force nickname from a member"""
        try:
            if await self.bot.db.fetchrow("SELECT * FROM force_nick WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id):
                await self.bot.db.execute("DELETE FROM force_nick WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
                await member.edit(nick=None, reason="Removed the force nickname from this member")
                return await ctx.send_success("Removed the nickname from this member")
            else:
                return await ctx.send_warning("There is no force nickname assigned for this member")
        except Forbidden:
            return await ctx.send_warning("I don't have permission to change this member's nickname. Please check the role hierarchy")
        except HTTPException:
            return await ctx.send_warning("Display name contains community flagged words")
        
    @forcenick.command(name="list", brief="manage nicknames, donator")
    async def forcenick_list(self, ctx: EvelinaContext):
        """List all members with force nicknames"""
        rows = await self.bot.db.fetch("SELECT * FROM force_nick WHERE guild_id = $1", ctx.guild.id)
        if not rows:
            return await ctx.send_warning("No force nicknames set")
        nickname_list = [f"<@{row['user_id']}>: {row['nickname']}" for row in rows]
        await ctx.paginate(nickname_list, "Force Nicknames", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @hybrid_group(name="selfprefix", brief="donator", description="Manage your self prefix", invoke_without_command=True)
    async def selfprefix(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @selfprefix.command(name="set", brief="donator", usage="selfprefix set ,", description="Set your self prefix")
    @has_perks()
    async def selfprefix_set(self, ctx: EvelinaContext, prefix: str):
        if len(prefix) > 7:
            raise BadArgument("Prefix is too long!")
        if not prefix:
            return await ctx.send_warning(f"Self prefix is **too short**")
        try:
            await self.bot.db.execute("INSERT INTO selfprefix VALUES ($1,$2)", ctx.author.id, prefix)
        except:
            await self.bot.db.execute("UPDATE selfprefix SET prefix = $1 WHERE user_id = $2", prefix, ctx.author.id,)
        self.bot.prefix_cache["users"][ctx.author.id] = prefix
        return await ctx.send_success(f"Self prefix now **configured** as `{prefix}`")

    @selfprefix.command(name="remove", brief="donator", description="Remove your self prefix")
    @has_perks()
    async def selfprefix_remove(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT prefix FROM selfprefix WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.send_warning("You do **not** have any self prefix")
        await self.bot.db.execute("DELETE FROM selfprefix WHERE user_id = $1", ctx.author.id)
        self.bot.prefix_cache["users"].pop(ctx.author.id, None)
        return await ctx.send_success("Self prefix removed")

    @selfprefix.command(name="leaderboard", aliases=["lb"])
    @has_perks()
    async def prefix_leaderboard(self, ctx: EvelinaContext):
        """View the leaderboard of selfprefixes used for the bot"""
        prefixes = await self.bot.db.fetch("SELECT prefix, COUNT(*) as usage_count FROM selfprefix GROUP BY prefix ORDER BY usage_count DESC")
        if not prefixes:
            return await ctx.send_warning("No prefixes found")
        leaderboard = [f"**{row['prefix']}** - {row['usage_count']} uses" for i, row in enumerate(prefixes)]
        return await ctx.paginate(leaderboard, "Selfprefix Leaderboard", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url})

    @group(name="selfalias", brief="donator", invoke_without_command=True, case_insensitive=True)
    async def selfalias(self, ctx: EvelinaContext):
        """Create your own shortcuts for commands"""
        return await ctx.create_pages()

    @selfalias.command(name="add", brief="donator", usage="selfalias add byebye ban")
    @has_perks()
    async def selfalias_add(self, ctx: EvelinaContext, alias: str, command: str, *, args: str = None):
        """Create or update a selfalias for command"""
        _command = self.bot.get_command(command)
        if not _command:
            return await ctx.send_warning(f"`{command}` is not a command")
        if self.bot.get_command(alias):
            return await ctx.send_warning(f"`{alias}` is already a command")
        exists = await self.bot.db.fetchrow("SELECT alias FROM selfaliases WHERE user_id = $1 AND alias = $2", ctx.author.id, alias)
        if exists:
            await self.bot.db.execute("UPDATE selfaliases SET command = $1, args = $2 WHERE user_id = $3 AND alias = $4", command, args, ctx.author.id, alias)
            await ctx.send_success(f"Updated `{alias}` to now alias `{_command.qualified_name}`")
        else:
            if len(await self.bot.db.fetch("SELECT alias FROM selfaliases WHERE user_id = $1", ctx.author.id)) >= 75:
                return await ctx.send_warning(f"You can only have **75 selfaliases**")
            await self.bot.db.execute("INSERT INTO selfaliases VALUES ($1, $2, $3, $4)", ctx.author.id, command, alias, args)
            await ctx.send_success(f"Added `{alias}` as an alias for `{_command.qualified_name}`")

    @selfalias.command(name="remove", brief="donator", usage="selfalias remove byebye")
    @has_perks()
    async def selfalias_remove(self, ctx: EvelinaContext, *, alias: str):
        """Remove an selfalias for command"""
        if not await self.bot.db.fetchrow("SELECT * FROM selfaliases WHERE user_id = $1 AND alias = $2", ctx.author.id, alias):
            return await ctx.send_warning(f"`{alias}` is **not** an alias")
        await self.bot.db.execute("DELETE FROM selfaliases WHERE user_id = $1 AND alias = $2", ctx.author.id, alias)
        return await ctx.send_success(f"Removed the **alias** `{alias}`")
    
    @selfalias.command(name="list", brief="donator")
    @has_perks()
    async def selfalias_list(self, ctx: EvelinaContext):
        """List every selfalias for all commands"""
        results = await self.bot.db.fetch("SELECT * FROM selfaliases WHERE user_id = $1", ctx.author.id)
        if not results:
            return await ctx.send_warning(f"No **selfaliases** are set")
        await ctx.paginate([f"**{result['alias']}** - `{result['command']}{' ' if result['args'] else ''}{result['args'] if result['args'] else ''}`" for result in results], title=f"Selfaliases", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon or None})

    @command(name='impersonate', aliases=['imp'],  brief="donator", usage='impersonate comminate hi')
    @has_perks()
    @bot_has_guild_permissions(manage_webhooks=True)
    async def impersonate(self, ctx: EvelinaContext, member: User, *, message: str = ''):
        """Impersonate a member"""
        try:
            await ctx.message.delete()
            webhooks = await ctx.channel.webhooks()
            webhook = None
            for wh in webhooks:
                if wh.user == ctx.guild.me:
                    webhook = wh
                    break
            if webhook is None:
                webhook = await ctx.channel.create_webhook(name=member.display_name)
            attachments = ctx.message.attachments
            if attachments:
                attachment = attachments[0]
                file = await attachment.to_file()
                await webhook.send(content=message, username=member.display_name, avatar_url=member.avatar.url if member.avatar else member.default_avatar.url, file=file, allowed_mentions=AllowedMentions.none())
            else:
                await webhook.send(content=message, username=member.display_name, avatar_url=member.avatar.url if member.avatar else member.default_avatar.url, allowed_mentions=AllowedMentions.none())
        except HTTPException:
            await ctx.send_warning('Please **provide** a message to impersonate')

    @command(name='uwulock', usage="uwulock comminate", brief="donator")
    @has_perks()
    @has_guild_permissions(manage_webhooks=True)
    @bot_has_guild_permissions(manage_webhooks=True)
    async def uwulock(self, ctx: EvelinaContext, member: Member):
        """Uwuify messages of a specific user"""
        cache_key = f'uwuifyer_{ctx.guild.id}_{member.id}'
        is_uwuified = await self.bot.cache.get(cache_key)
        if member.id not in self.bot.owner_ids:
            if is_uwuified:
                await self.bot.cache.delete(cache_key)
                await ctx.send_success(f'Messages of **{member.mention}** will **no longer** be uwuified.')
            else:
                await self.bot.cache.set(cache_key, True, 900)
                await ctx.send_success(f'Messages of **{member.mention}** will now be uwuified for **15 minutes**')
        else:
            await ctx.send_warning("You cannot uwulock the owner of the bot")

    @command(name="reverse", aliases=["reverseimage", "reverseimg"], brief="donator", usage="reverse https://evelina.bot/icon.png", cooldown=5)
    @has_perks()
    @cooldown(1, 5, BucketType.user)
    async def reverse(self, ctx: EvelinaContext, *, url: str = None):
        """Search Google for similar images using reverse image search"""
        if url is None:
            url = await ctx.get_attachment()
            if not url:
                return await ctx.send_help(ctx.command)
            else:
                url = url.url
        try:
            data = await self.bot.getbyte(url)
            code = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
            input_path = f"/var/www/html/generation/{code}.png"
            with open(input_path, "wb") as f:
                f.write(data.getbuffer())
            url = f"https://{self.bot.transcript}/generation/{code}.png"
            data = await self.bot.session.get_json(
                f"https://api.evelina.bot/google/reverse",
                params={"image": url, "key": "8F6qVxN55aoODT0FRh16pydP"}
            )
            embeds = [
                Embed(
                    title=f"{result.get('name', 'Untitled')} ({result.get('rank', '0')}/10 ⭐)",
                    url=result.get('url', ''),
                    color=colors.NEUTRAL
                )
                .set_image(url=result.get('image', ''))
                .set_footer(text=f"Page: {index + 1}/{len(data['results'])} ({len(data['results'])} entries)")
                for index, result in enumerate(data.get('results', []))
            ]
            if not embeds:
                return await ctx.send_warning(f"Couldn't find any results for the image.")
            await ctx.paginator(embeds=embeds)
        except Exception:
            await ctx.send_warning(f"An error occurred while performing the reverse image search")
        
    @command(name="deeplookup", aliases=["dlu", "deep"], brief="donator", usage="deeplookup comminate")
    @has_perks()
    async def deeplookup(self, ctx: EvelinaContext, user: User = None):
        """Deep lookup a member"""
        if user is None:
            user = ctx.author
        if user.id in self.bot.owner_ids:
            if ctx.author.id not in self.bot.owner_ids:
                return await ctx.send_warning("You can't deep lookup the owner of the bot")
        message_data = await self.bot.db.fetch(
            "SELECT server_id, SUM(message_count) as total_messages FROM activity_messages WHERE user_id = $1 GROUP BY server_id ORDER BY total_messages DESC",
            user.id
        )
        if not message_data:
            return await ctx.send_warning(f"No data found for {user.mention}")
        content = []
        for entry in message_data:
            guild = self.bot.get_guild(entry["server_id"])
            if guild:
                content.append(f"**{guild.name}** - `{entry['total_messages']:,.0f}` messages")
            else:
                guild_name = await self.bot.db.fetchval("SELECT guild_name FROM guild_names WHERE guild_id = $1", entry["server_id"])
                if guild_name:
                    content.append(f"**{guild_name}** - `{entry['total_messages']:,.0f}` messages")
                else:
                    content.append(f"**{entry['server_id']}** - `{entry['total_messages']:,.0f}` messages")
        if not content:
            return await ctx.send_warning(f"{user.mention} has no message records across any servers")
        await ctx.paginate(
            content,
            f"Deep lookup for {user.name}",
            {"name": user.name, "icon_url": user.avatar.url if user.avatar else user.default_avatar.url}
        )

    @command(name="ask", aliases=["ai"], brief="donator", usage="ask what is discord", cooldown=5)
    @has_perks()
    @cooldown(1, 5, BucketType.user)
    async def ask(self, ctx: EvelinaContext, *, prompt: str):
        """Ask the AI something"""
        async with ctx.typing():
            try:
                client = AsyncOpenAI(
                    api_key="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",
                    base_url="https://api.openai.com/v1",
                    timeout=30,
                    max_retries=3,
                )
                response = await client.chat.completions.create(
                    model="gpt-4o-mini-search-preview",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You\'re Evelina, a helpful assistant, in reality you\'re GPT-4o-mini with web-search/going on websites capabilities. You\'re operating on discord, You\'re a discord bot called Evelina (https://evelina.bot/ , commands at https://evelina.bot/commands) (support: https://discord.gg/evelina , everytime you mention the support discord user < and > tags cause it prevents it from being embedded). Do not mention top.gg or anything else like that. Always provide short answers, as you\'re used in a discord context. Helpful, straight to the point and concise. Reply using short answers, but make sure to stay informative, if the question requires a longer answer try to make as short as possible."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ]
                )
                answer = response.choices[0].message.content
            except Exception as e:
                answer = f"Error: {e}"
            if len(answer) > 2000:
                return await ctx.send_warning("The response is too long to send")
            return await ctx.send(content=answer, reference=ctx.message, mention_author=False)
        
    @command(name="transcribe", brief="donator", usage="transcribe https://evelina.bot/audio.mp3")
    @has_perks()
    async def transcribe(self, ctx: EvelinaContext, url: str = None):
        """Transcribe an audio file"""
        if url is None:
            attachment = await ctx.get_attachment()
            if not attachment:
                return await ctx.send_help(ctx.command)
            url = attachment.url
        async with ctx.typing():
            try:
                data = await self.bot.session.get_bytes(url)
                if not data:
                    return await ctx.send_warning("An error occurred while downloading the audio file")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
                    tmpfile.write(data)
                    tmpfile_path = tmpfile.name
                client = openai.OpenAI(api_key=config.OPENAI)
                with open(tmpfile_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                os.remove(tmpfile_path)
                text = transcript.text
                if len(text) > 1900:
                    file = File(fp=BytesIO(text.encode()), filename="transcription.txt")
                    await ctx.reply(embed=None, file=file)
                else:
                    await ctx.reply(content=text, embed=None)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while transcribing the audio file:\n```{e}```")

async def setup(bot: Evelina) -> None:
    await bot.add_cog(Donor(bot))