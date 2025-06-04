from discord import Member, ButtonStyle, Interaction, Embed
from discord.ext.commands import group, has_permissions
from discord.ui import Button, View
from tools.conversion.embed import EmbedScript
from core.client.context import Context
from tools import CompositeMetaClass, MixinMeta
import asyncio
from collections import defaultdict
import time
from typing import Dict, List, Tuple
from tools.parser import Script
from discord.ext.commands import Cog
import discord
import config


class InfoButton(Button):
    def __init__(self, guild_id: int):
        super().__init__(
            style=ButtonStyle.primary,
            label="Information",
            emoji=config.EMOJIS.SOCIAL.WEBSITE,
            custom_id=f"joindm_info_{guild_id}"
        )
        self.guild_id = guild_id

    async def callback(self, interaction: Interaction):
        guild = interaction.client.get_guild(self.guild_id)
        if not guild:
            return

        embed = Embed(
            title=f"About {guild.name}",
            color=0x0a0a0a,
        )
        
        embed.add_field(
            name="Server Information",
            value=f"🏷️ **Name:** {guild.name}\n"
                  f"👑 **Owner:** {guild.owner}\n"
                  f"📅 **Created:** <t:{int(guild.created_at.timestamp())}:R>\n"
                  f"👥 **Members:** {guild.member_count:,}\n",
            inline=False
        )

        embed.add_field(
            name="Protect Yourself",
            value="- Never share your account token or password\n"
                  "- Be cautious of links from unknown users\n"
                  "- Enable 2FA for extra security\n"
                  "- Report suspicious DMs to [evict's team](https://discord.gg/evict)\n"
                  "- Don't download files you don't trust\n"
                  "More info on staying safe on Discord: [Discord Safety Center](https://discord.com/safety)",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class InfoView(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.add_item(InfoButton(guild_id))


class JoinDM(MixinMeta, metaclass=CompositeMetaClass):
    """Configure welcome DMs for new members"""

    dm_queue: Dict[int, List[Tuple[Member, str]]] = defaultdict(list)
    processing = False
    rate_limits: Dict[int, float] = {}
    max_per_minute = 12

    def __init__(self, bot):
        self.bot = bot
        self.name = "Join DM"
        self.queue_processor_task = None  

    async def cog_load(self) -> None:
        """Start queue processor when cog loads"""
        try:
            print("Starting JoinDM queue processor")
            if not hasattr(self, 'queue_processor_task') or not self.queue_processor_task:
                self.queue_processor_task = self.bot.loop.create_task(self.process_dm_queue())
        except Exception as e:
            print(f"Error starting queue processor: {e}")
        
        await super().cog_load()

    async def cog_unload(self) -> None:
        """Cleanup when cog is unloaded"""
        try:
            print("Unloading JoinDM cog")
            if hasattr(self, 'queue_processor_task') and self.queue_processor_task:
                print("Cancelling queue processor task")
                self.queue_processor_task.cancel()
                self.queue_processor_task = None
        except Exception as e:
            print(f"Error in cog unload: {e}")
        
        await super().cog_unload()

    async def process_dm_queue(self):
        """Process the DM queue with rate limiting"""
        while True:
            try:
                self.processing = True
                current_time = time.time()
                
                if self.dm_queue:
                    print(f"Processing DM queue: {dict(self.dm_queue)}")

                for guild_id in list(self.dm_queue.keys()):
                    if not self.dm_queue[guild_id]:
                        continue

                    last_dm = self.rate_limits.get(guild_id, 0)
                    if current_time - last_dm < (60 / self.max_per_minute):
                        continue

                    member, message = self.dm_queue[guild_id].pop(0)
                    try:
                        print(f"Sending DM to {member} in {member.guild}")
                        script = Script(message, [member.guild, member, member.guild.system_channel])
                        data = script.data
                        
                        view = InfoView(member.guild.id)
                        if isinstance(data, dict):
                            data['view'] = view
                            
                        content = None if data['content'] == message else data['content']
                        await member.send(
                            content=content,
                            embed=data.get('embed'),
                            view=view
                        )
                        print(f"DM sent successfully to {member}")
                        self.rate_limits[guild_id] = current_time
                    except Exception as e:
                        print(f"Failed to send DM to {member}: {e}")
                        self.bot.logger.error(f"DM Error: {str(e)}")
                        pass

                    if not self.dm_queue[guild_id]:
                        del self.dm_queue[guild_id]
                        self.rate_limits.pop(guild_id, None)

                await asyncio.sleep(1)
            except Exception as e:
                print(f"Queue processor error: {e}")
                self.bot.logger.error(f"Error in DM queue processor: {e}")
                await asyncio.sleep(5)

    @group(aliases=["jdm", "welcomedm"], invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def joindm(self, ctx: Context):
        """Configure join DM settings"""
        return await ctx.send_help(ctx.command)

    @joindm.command(name="message", aliases=["msg"])
    @has_permissions(manage_guild=True)
    async def joindm_message(self, ctx: Context, *, message: str):
        """Set the join DM message"""
        try:
            script = EmbedScript(message)
            await script.compile(
                user=ctx.author,
                guild=ctx.guild,
                channel=ctx.channel,
                roles=ctx.guild.roles
            )
        except Exception as e:
            return await ctx.warn(f"Invalid message format: {str(e)}")

        await self.bot.db.execute(
            """
            INSERT INTO joindm.config (guild_id, message)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET message = $2
            """,
            ctx.guild.id,
            message
        )
        
        await ctx.approve("Join DM message has been set!")

    @joindm.command(name="test")
    @has_permissions(manage_guild=True)
    async def joindm_test(self, ctx: Context):
        """Test the current join DM message"""
        config = await self.bot.db.fetchrow(
            """
            SELECT * FROM joindm.config
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        if not config or not config['message']:
            return await ctx.warn("No join DM message has been set!")

        try:
            script = Script(config['message'], [ctx.guild, ctx.author, ctx.channel])
            data = script.data
            
            view = InfoView(ctx.guild.id)
            if isinstance(data, dict):
                data['view'] = view
                
            content = None if data['content'] == config['message'] else data['content']
            await ctx.author.send(
                content=content,
                embed=data.get('embed'),
                view=view
            )
            await ctx.approve("Test message sent to your DMs!")
        except Exception as e:
            await ctx.warn(f"Couldn't send test message: {str(e)}")

    @joindm.command(name="toggle")
    @has_permissions(manage_guild=True)
    async def joindm_toggle(self, ctx: Context):
        """Toggle join DMs on/off"""
        config = await self.bot.db.fetchrow(
            """
            INSERT INTO joindm.config (guild_id, enabled)
            VALUES ($1, true)
            ON CONFLICT (guild_id) 
            DO UPDATE SET enabled = NOT joindm.config.enabled
            RETURNING enabled
            """,
            ctx.guild.id
        )

        await ctx.approve(f"Join DMs have been {'enabled' if config['enabled'] else 'disabled'}!")

    @joindm.command(name="view")
    @has_permissions(manage_guild=True)
    async def joindm_view(self, ctx: Context):
        """View the current join DM message"""
        config = await self.bot.db.fetchrow(
            """
            SELECT * FROM joindm.config
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        if not config or not config['message']:
            return await ctx.warn("No join DM message has been set!")

        queue_size = len(self.dm_queue.get(ctx.guild.id, []))
        status = (
            f"{'Enabled' if config['enabled'] else 'Disabled'}"
            f"{f' | Pending DMs: {queue_size}' if queue_size else ''}"
        )

        await ctx.approve(
            f"Current join DM message:\n```\n{config['message']}\n```",
            f"Status: {status}"
        )

    @joindm.command(name="queue")
    @has_permissions(manage_guild=True)
    async def joindm_queue(self, ctx: Context):
        """View the current DM queue for your server"""
        queue = self.dm_queue.get(ctx.guild.id, [])
        if not queue:
            return await ctx.warn("No pending DMs in queue!")

        await ctx.approve(
            f"Current DM queue size: {len(queue)}",
            f"Rate limit: {self.max_per_minute} DMs per minute"
        )

    # @Cog.listener()
    # async def on_member_join(self, member: Member):
    #     """Queue welcome DM when a member joins"""
    #     if member.bot:
    #         return
            
    #     config = await self.bot.db.fetchrow(
    #         """
    #         SELECT * FROM joindm.config
    #         WHERE guild_id = $1 AND enabled = true
    #         """,
    #         member.guild.id
    #     )

    #     if not config or not config['message']:
    #         return

    #     print(f"Queueing DM for {member} in {member.guild}")
    #     self.dm_queue[member.guild.id].append((member, config['message']))
    #     print(f"Current queue size for {member.guild}: {len(self.dm_queue[member.guild.id])}")
    #     print(f"Processing status: {self.processing}") 