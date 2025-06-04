import os
import random

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.validators import ValidTime

from discord import User, Embed, __version__, utils, Permissions, ClientUser, Status
from discord.ext.commands import Cog, command, hybrid_command, cooldown, BucketType
from discord.ui import View, Button

from datetime import datetime
from platform import python_version

class Info(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Information commands"

    def create_bot_invite(self, user: User) -> View:
        """Create a view containing a button with the bot invite url"""
        view = View()
        view.add_item(Button(label=f"Invite {user.name}", url=utils.oauth_url(client_id=user.id, permissions=Permissions(8))))
        return view
    
    @hybrid_command(name="commands", aliases=["h", "cmds"], usage="help userinfo", description="View all commands or get help for a specific command")
    async def _help(self, ctx: EvelinaContext, *, command: str = None):
        """View all commands or get help for a specific command"""
        if not command:
            return await ctx.send_help()
        _command = self.bot.get_command(command)
        if _command is None:
            return await ctx.send_warning(f'No command called `{command}` found')
        cog = _command.cog_name
        if cog and isinstance(cog, str) and cog.lower() in ["jishaku", "owner", "auth", "helper"]:
            if ctx.author.id not in self.bot.owner_ids:
                staff = await self.bot.db.fetchrow("SELECT * FROM team_members WHERE user_id = $1", ctx.author.id)
                if not staff:
                    return await ctx.send_warning(f"No command called `{command}` found")
        if _command.hidden:
            return await ctx.send_warning(f'No command called `{command}` found')
        return await ctx.send_help(_command)

    @hybrid_command(name="ping", cooldown=5)
    @cooldown(1, 5, BucketType.user)
    async def ping(self, ctx: EvelinaContext):
        """Displays the bot's latency"""
        sentence = ["north korea", "no one", "ion even know wat to put here", "6ix9ines ankle monitor", "the chinese government", "horny asian women around your area", "the migos minecraft server", "your mom", "charlie's mud hut", "267 tries to wake trave up from hibernation", "that new evelina.bot domain", "a connection to the server", "franzi's lovense", "kjell's skyblock cheats", "kinex's downfall"]
        sentenceRandom = random.choice(sentence)
        start_time = datetime.utcnow()
        msg = await ctx.reply(f"it took `{round(self.bot.latency * 1000)}ms` to ping **{sentenceRandom}**")
        execution_time = round((datetime.utcnow() - start_time).total_seconds() * 1000, 1)
        await msg.edit(content=f"it took `{round(self.bot.latency * 1000)}ms` to ping **{sentenceRandom}** (edit: `{execution_time}ms`)")
    
    def analyze_code(self, directory: str):
        total_files = 0
        total_lines = 0
        total_classes = 0
        total_functions = 0
        total_imports = 0
        directories = ['cogs', 'modules', 'events']
        for directory in directories:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(".py"):
                        total_files += 1
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            total_lines += len(f.read().splitlines())
                        classes, functions, imports = self.count_elements_in_file(file_path)
                        total_classes += classes
                        total_functions += functions
                        total_imports += imports
        return total_files, total_lines, total_classes, total_functions, total_imports

    def count_elements_in_file(self, file_path: str):
        classes = 0
        functions = 0
        imports = 0
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("class "):
                        classes += 1
                    elif stripped.startswith("def ") or stripped.startswith("async def "):
                        functions += 1
                    elif stripped.startswith("import ") or stripped.startswith("from "):
                        imports += 1
        except Exception:
            pass
        return classes, functions, imports


    @hybrid_command(name="botinfo", aliases=["bi", "bot", "about"])
    async def botinfo(self, ctx: EvelinaContext):
        """Displays information about the bot"""
        data = await self.bot.session.get_json("http://localhost:8000/health") or {}

        text_channels = sum(1 for g in self.bot.guilds for c in g.text_channels)
        voice_channels = sum(1 for g in self.bot.guilds for c in g.voice_channels)
        categorie_channels = sum(1 for g in self.bot.guilds for c in g.categories)
        guilds_count = sum(
            cluster.get("guilds", 0)
            for cluster in data.get("clusters", {}).values()
        )
        embed = (
            Embed(
                color=colors.NEUTRAL,
                description=(
                    f"Premium multi-purpose discord bot made by the [**Evelina Team**](https://evelina.bot/team)\n"
                    f"Used by **{data.get("users", 0):,}** members in "
                    f"**{guilds_count:,}** servers on **{self.bot.shard_count:,}** shards"
                )
            )
            .set_author(
                name=self.bot.user.name,
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
            )
            .add_field(
                name="Members",
                value=(
                    f"> **Total:** {data.get("users", 0):,}\n"
                    f"> **Human:** ts pmo\n"
                    f"> **Bots:** ts pmo"
                )
            )
            .add_field(
                name="Channels",
                value=(
                    f"> **Text:** {text_channels:,}\n"
                    f"> **Voice:** {voice_channels:,}\n"
                    f"> **Categories:** {categorie_channels:,}"
                )
            )
            .add_field(
                name="System",
                value=(
                    f"> **Commands:** {len(set(self.bot.walk_commands()))}\n"
                    f"> **Discord.py:** [{__version__}](https://github.com/Rapptz/discord.py)\n"
                    f"> **Python:** [{python_version()}](https://www.python.org/downloads/release/python-31012)"
                )
            )
        )
        view = View()
        view.add_item(Button(label="Invite", url="https://discord.com/oauth2/authorize?client_id=1242930981967757452"))
        view.add_item(Button(label="Support Server", url="https://discord.gg/evelina"))
        view.add_item(Button(label="GitHub", url="https://github.com/evelinabot"))
        return await ctx.send(embed=embed, view=view)
    
    @hybrid_command(name="shards")
    async def shards(self, ctx: EvelinaContext):
        """Check status of each bot shard"""
        
        data = await self.bot.session.get_json("http://localhost:8000/health") or {}
        
        if not data:
            await ctx.send("Could not fetch shard data from API")
            return
        
        total_users = data.get("users", 0)
        total_guilds = data.get("guilds", 0)
        clusters = data.get("clusters", {})
        current_guild_shard_id = ctx.guild.shard_id
        
        shards_data = []
        for cluster_id, cluster_info in clusters.items():
            for shard in cluster_info.get("shards", []):
                shard_info = {
                    "shard_id": shard["id"],
                    "ping": round(shard["latency"] * 1000),
                    "guilds": shard["guilds"],
                    "users": shard["users"],
                    "is_current": shard["id"] == current_guild_shard_id,
                    "uptime": shard["uptime"],
                    "seconds_since_seen": shard["seconds_since_seen"]
                }
                shards_data.append(shard_info)
        
        shards_data.sort(key=lambda x: x["shard_id"])
        
        entries_per_page = 6
        total_pages = (len(shards_data) + entries_per_page - 1) // entries_per_page
        embeds = []
        
        for i in range(0, len(shards_data), entries_per_page):
            page_number = (i // entries_per_page) + 1
            embed = Embed(color=colors.NEUTRAL, title=f"Total shards ({len(shards_data)})")
            embed.set_image(url="https://storagevault.cloud/users/bender/output-onlinepngtools_(2).png")
            
            embed.description = f"**Total Users**: {total_users:,}\n**Total Guilds**: {total_guilds:,}"
            
            for shard_info in shards_data[i:i + entries_per_page]:
                shard_id = shard_info["shard_id"]
                shard_field_name = f"Shard {shard_id}"
                
                if shard_info["is_current"]:
                    shard_field_name += f" {emojis.LEFT} You"
                    
                shard_field_value = (
                    f"**ping**: {shard_info['ping']}ms\n"
                    f"**guilds**: {shard_info['guilds']}\n"
                    f"**users**: {shard_info['users']:,}"
                )
                
                embed.add_field(name=shard_field_name, value=shard_field_value, inline=True)
                
            embeds.append(embed)
        
        await ctx.paginator(embeds)

    @hybrid_command(name="invite", aliases=["link"])
    async def invite(self, ctx: EvelinaContext):
        """Send an invite link of the bot"""
        await ctx.reply(view=self.create_bot_invite(ctx.guild.me))

    @command(name="uptime", aliases=["up"])
    async def uptime(self, ctx: EvelinaContext):
        """Displays how long has the bot been online for"""
        return await ctx.reply(embed=Embed(color=colors.NEUTRAL, description=f"🕐 {ctx.author.mention}: **{self.bot.uptime}**"))
    
    @command(name="getbotinvite", aliases=["gbi"], usage="getbotinvite evelina#1355")
    async def getbotinvite(self, ctx: EvelinaContext, *, member: User):
        """Get the bot invite based on it's id"""
        if not member.bot:
            return await ctx.send_warning("This is **not** a bot")
        await ctx.reply(view=self.create_bot_invite(member))

    @command(name="topcommands", aliases=["topcmds"])
    async def topcommands(self, ctx: EvelinaContext, time: ValidTime = None):
        """View the top 50 most used commands"""
        base_query = "SELECT command, COUNT(command) AS usage_count FROM command_history"
        if time:
            since = datetime.now().timestamp() - time
            since_time = datetime.fromtimestamp(since)
            query = f"{base_query} WHERE timestamp >= EXTRACT(EPOCH FROM TIMESTAMP '{since_time}') GROUP BY command ORDER BY usage_count DESC LIMIT 50"
            results = await self.bot.db.fetch(query)
        else:
            query = f"{base_query} GROUP BY command ORDER BY usage_count DESC LIMIT 50"
            results = await self.bot.db.fetch(query)
        if not results:
            return await ctx.send_warning("No usage found")
        to_show = [f"**{check['command']}** used `{check['usage_count']:,.0f}` times" for check in results]
        since_message = f"since {since_time.strftime('%m/%d/%Y %H:%M')}" if time else "overall"
        return await ctx.paginate(to_show, f"Top commands {since_message}", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url})

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Info(bot))