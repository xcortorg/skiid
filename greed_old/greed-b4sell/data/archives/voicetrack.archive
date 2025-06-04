from typing import Optional, Union
from discord import Member, User, File, VoiceState, Embed
from discord.ext import commands
import discord
import datetime
from io import BytesIO
import asyncio
from asyncio import Lock
from tool.worker import offloaded
from PIL import Image, ImageDraw, ImageMath
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib
import base64
import json

matplotlib.use('agg')
plt.switch_backend('agg')


@offloaded
def generate_pie_chart(member_name: str, time_data: dict, avatar_b64: str) -> dict:
    hours = time_data["hours"]
    minutes = time_data["minutes"]
    seconds = time_data["seconds"]

    # Pie chart data
    data = [seconds or 1, minutes or 1, hours or 1]
    colors = ['#7BB662', '#D61F1F', '#FFD301']
    labels = [f"{hours}h", f"{minutes}m", f"{seconds}s"]

    # Decode avatar from base64
    avatar_bytes = base64.b64decode(avatar_b64)
    avatar_image = Image.open(BytesIO(avatar_bytes)).convert("RGBA")

    # Create circular mask for the avatar
    mask = Image.new("L", avatar_image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + avatar_image.size, fill=255)
    alpha = ImageMath.eval("a*b/255", a=avatar_image.split()[3], b=mask).convert("L")
    avatar_image.putalpha(alpha)

    # Generate pie chart
    plt.figure(figsize=(6, 8))
    wedges, _ = plt.pie(data, colors=colors, startangle=90, wedgeprops=dict(width=0.3))
    plt.axis('equal')

    # Overlay avatar onto chart
    width, height = avatar_image.size
    aspect_ratio = height / width
    half_width = 0.91
    half_height = aspect_ratio * half_width
    extent = [-half_width, half_width, -half_height, half_height]
    plt.imshow(avatar_image, extent=extent, zorder=-1)

    plt.legend(wedges, labels, title=f"{member_name}'s Activity",
               loc="upper center", bbox_to_anchor=(0.5, 0.08),
               facecolor='#2C2F33', edgecolor='#23272A')

    # Save chart to base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', transparent=True)
    plt.close()

    image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()

    return {
        "image_b64": image_b64,
        "filename": f"{member_name}.png"
    }


class VoiceTrack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.locks = defaultdict(Lock)
        self.users = {}  # Tracks active voice activity timestamps

    async def cog_load(self):
        await self.bot.db.execute("""
        CREATE TABLE IF NOT EXISTS voice_activity (
            user_id BIGINT NOT NULL,
            guild_id BIGINT NOT NULL,
            time_in_voice INTERVAL NOT NULL DEFAULT INTERVAL '0 seconds',
            PRIMARY KEY (user_id, guild_id)
        );
        """)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        now = datetime.datetime.now(datetime.timezone.utc)

        if before.channel is None and after.channel is not None:  # User joined a channel
            self.users[member.id] = now.timestamp()

        elif before.channel is not None and after.channel is None:  # User left a channel
            if member.id in self.users:
                elapsed = now.timestamp() - self.users.pop(member.id)
                await self.log_voice_activity(member.id, member.guild.id, elapsed)

        elif before.channel != after.channel:  # User switched channels
            if member.id in self.users:
                elapsed = now.timestamp() - self.users[member.id]
                await self.log_voice_activity(member.id, member.guild.id, elapsed)
                self.users[member.id] = now.timestamp()

    async def log_voice_activity(self, user_id: int, guild_id: int, elapsed: float):
        async with self.locks[user_id]:
            await self.bot.db.execute("""
            INSERT INTO voice_activity (user_id, guild_id, time_in_voice)
            VALUES ($1, $2, INTERVAL '1 second' * $3)
            ON CONFLICT (user_id, guild_id) DO UPDATE
            SET time_in_voice = voice_activity.time_in_voice + INTERVAL '1 second' * $3
            """, user_id, guild_id, elapsed)

    @commands.command(name="voicetrack", aliases=["vt"], description="Show voice channel activity statistics")
    async def voicetrack(self, ctx: commands.Context, *, member: Optional[Union[Member, User]] = None):
        member = member or ctx.author
        data = await self.bot.db.fetchrow("""
        SELECT EXTRACT(EPOCH FROM time_in_voice) AS seconds
        FROM voice_activity
        WHERE user_id = $1 AND guild_id = $2
        """, member.id, ctx.guild.id)

        if not data:
            await ctx.fail(f"No voice activity data found for {member.mention}.")
            return

        time_in_voice = float(data["seconds"])
        hours, remainder = divmod(time_in_voice, 3600)
        minutes, seconds = divmod(remainder, 60)

        time_data = {"hours": int(hours), "minutes": int(minutes), "seconds": int(seconds)}
        avatar_bytes = await member.display_avatar.read()
        avatar_b64 = base64.b64encode(avatar_bytes).decode('utf-8')

        result = await generate_pie_chart(member.name, time_data, avatar_b64)
        image_data = base64.b64decode(result["image_b64"])

        f = BytesIO(image_data)
        file = File(f, filename=result["filename"])
        await ctx.send(
            f"{member.mention} has spent **{int(hours)}h** **{int(minutes)}m** **{int(seconds)}s** in this server's vcs.",
            file=file
        )


    @commands.command(name="voiceleaderboard", aliases=["vlb"], description="Show the top 10 users with the most voice activity")
    async def voiceleaderboard(self, ctx: commands.Context):
          # Fetch the top 10 users by time in voice for the current guild
          top_users = await self.bot.db.fetch("""
          SELECT user_id, time_in_voice
          FROM voice_activity
          WHERE guild_id = $1
          ORDER BY time_in_voice DESC
          LIMIT 10
          """, ctx.guild.id)

          if not top_users:
               await ctx.fail("No voice activity data found for this server.")
               return

          # Create the embed
          embed = Embed(title="Voice Activity Leaderboard", color=self.bot.color)
          embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
          embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

          # Populate the leaderboard
          for rank, record in enumerate(top_users, start=1):
               user_id = record['user_id']
               time_in_voice = record['time_in_voice']

               # Convert timedelta to total seconds
               if isinstance(time_in_voice, datetime.timedelta):
                    total_seconds = time_in_voice.total_seconds()
               else:
                    total_seconds = float(time_in_voice)  # Handles unexpected formats

               duration = str(datetime.timedelta(seconds=total_seconds))

               user = ctx.guild.get_member(user_id) or self.bot.get_user(user_id)
               user_name = user.display_name if user else f"User {user_id}"

               embed.add_field(
                    name=f"#{rank}: {user_name}",
                    value=f"Time in voice: {duration}",
                    inline=False
               )

          await ctx.send(embed=embed)



async def setup(bot):
    await bot.add_cog(VoiceTrack(bot))
