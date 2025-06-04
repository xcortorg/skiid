import json
import os

import discord
import jishaku
import psycopg2
from discord import Activity, ActivityType, Embed
from discord.ext import commands, tasks
from discord.gateway import DiscordWebSocket
from dotenv import load_dotenv

load_dotenv()
allowed_ids = [598125772754124823]

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=",",
    intents=intents,
    allowed_mentions=discord.AllowedMentions(
        everyone=False, roles=False, replied_user=False, users=True
    ),
    owner_id=["598125772754124823"],
)


async def is_owner(user: discord.User):
    return user.id in allowed_ids


async def setup_hook():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            bot.load_extension(f"cogs.{filename[:-3]}")


bot.is_owner = is_owner

conn = psycopg2.connect(
    dbname=os.getenv("DB"),
    user=os.getenv("DBUSER"),
    password=os.getenv("PASSW"),
    host=os.getenv("HOST"),
    port=os.getenv("PORT"),
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} - {bot.user.id}")
    activity = Activity(
        type=ActivityType.custom,
        name="🔗 discord.gg/pretendbot",
        state="🔗 discord.gg/pretendbot",
    )
    await bot.change_presence(activity=activity)
    await bot.load_extension("jishaku")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS servers (
            guild_id BIGINT PRIMARY KEY,
            vanity TEXT,
            role_id BIGINT,
            notif_channel BIGINT,
            vanitylock BOOLEAN DEFAULT FALSE,
            notif BOOLEAN DEFAULT TRUE,
            keeprole BOOLEAN DEFAULT FALSE
        )
    """
    )
    conn.commit()
    cursor.close()
    check_activity.start()

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")


@bot.event
async def on_guild_join(self, guild: discord.Guild):
    embed = discord.Embed(
        color=0x729BB0,
        description=f"joined **{guild.name}**, owned by **{guild.owner}** with **{guild.member_count}** members",
    )
    embed.set_footer(text=f"ID: {guild.id}")
    await self.bot.get_channel(1251525688587190323).send(embed=embed)


@tasks.loop(seconds=1)
async def check_activity():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM servers")
    results = cursor.fetchall()
    cursor.close()

    for result in results:
        guild_id = result[0]
        role_id = result[2]
        notif_channel_id = result[3]
        vanitylock = result[4]
        notif = result[5]
        keeprole = result[6]

        guild = bot.get_guild(guild_id)
        if guild:
            role = guild.get_role(role_id)
            notif_channel = guild.get_channel(notif_channel_id)
            if role and notif_channel:
                vanity = result[1]
                for member in guild.members:
                    current_status = member.activity.name if member.activity else "None"
                    print(f"Member: {member.name}, Activity: {current_status}")
                    has_vanity = vanity.lower() in current_status.lower()
                    if vanitylock and has_vanity and current_status != vanity:
                        if role in member.roles and not keeprole:
                            if notif:
                                removerole = Embed(
                                    title=bot.user.name,
                                    description=f"Removed role <@&{role.id}> from <@{member.id}>",
                                    color=0x729BB0,
                                )
                                removerole.set_footer(
                                    text=f"{guild.name}", icon_url=guild.icon
                                )
                                await member.remove_roles(
                                    role,
                                    reason=f"{member.name} no longer has vanity in status",
                                )
                                await notif_channel.send(embed=removerole)
                    elif not vanitylock and not has_vanity:
                        if role in member.roles and not keeprole:
                            if notif:
                                removerole = Embed(
                                    title=bot.user.name,
                                    description=f"Removed role <@&{role.id}> from <@{member.id}>",
                                    color=0x729BB0,
                                )
                                removerole.set_footer(
                                    text=f"{guild.name}", icon_url=guild.icon
                                )
                                await member.remove_roles(
                                    role,
                                    reason=f"{member.name} no longer has vanity in status",
                                )
                                await notif_channel.send(embed=removerole)
                            else:
                                await member.remove_roles(
                                    role,
                                    reason=f"{member.name} no longer has vanity in status",
                                )
                    elif vanitylock and not has_vanity:
                        if role in member.roles and not keeprole:
                            if notif:
                                removerole = Embed(
                                    title=bot.user.name,
                                    description=f"Removed role <@&{role.id}> from <@{member.id}>",
                                    color=0x729BB0,
                                )
                                removerole.set_footer(
                                    text=f"{guild.name}", icon_url=guild.icon
                                )
                                await member.remove_roles(
                                    role,
                                    reason=f"{member.name} no longer has vanity in status",
                                )
                                await notif_channel.send(embed=removerole)
                            else:
                                await member.remove_roles(
                                    role,
                                    reason=f"{member.name} no longer has vanity in status",
                                )
                    elif not vanitylock and has_vanity:
                        if role not in member.roles:
                            await member.add_roles(
                                role, reason=f"{member.name} has vanity in status"
                            )
                            if notif:
                                addrole = Embed(
                                    title=bot.user.name,
                                    description=f"Added role <@&{role.id}> to <@{member.id}>",
                                    color=0x729BB0,
                                )
                                addrole.set_footer(
                                    text=f"{guild.name}", icon_url=guild.icon
                                )
                                await notif_channel.send(embed=addrole)
            else:
                print(f"Role or notification channel not found in guild '{guild.name}'")
        else:
            print("Guild not found.")


bot.remove_command("help")
load_dotenv()


# @bot.command()
# async def setvanity(ctx, vanity: str, role_id: int):
#     """
#     Sets the vanity for the guild and assigns the specified role.
#     """
#     guild = ctx.guild
#     role = guild.get_role(role_id)
#     if role:
#         if ctx.guild.me.guild_permissions.manage_roles:
#             cursor = conn.cursor()
#             cursor.execute("SELECT * FROM servers WHERE guild_id = %s", (guild.id,))
#             result = cursor.fetchone()
#             if result:
#                 cursor.execute("UPDATE servers SET vanity = %s, role_id = %s WHERE guild_id = %s", (vanity, role_id, guild.id))
#                 conn.commit()
#                 cursor.close()
#                 await ctx.reply(f"Vanity updated to '{vanity}' and role reassigned for guild '{guild.name}'.")
#             else:
#                 cursor.execute("INSERT INTO servers (guild_id, vanity, role_id) VALUES (%s, %s, %s)", (guild.id, vanity, role_id))
#                 conn.commit()
#                 cursor.close()
#                 await ctx.reply(f"Vanity set to '{vanity}' and role assigned for guild '{guild.name}'.")
#         else:
#             await ctx.reply("I don't have permission to manage roles.")
#     else:
#         await ctx.reply(f"The specified role does not exist.")
async def mobile(self):
    import sys

    payload = {
        "op": self.IDENTIFY,
        "d": {
            "token": self.token,
            "properties": {
                "$os": sys.platform,
                "$browser": "Discord iOS",
                "$device": "discord.py",
                "$referrer": "",
                "$referring_domain": "",
            },
            "compress": True,
            "large_threshold": 250,
            "v": 3,
        },
    }
    if self.shard_id is not None and self.shard_count is not None:
        payload["d"]["shard"] = [self.shard_id, self.shard_count]
    state = self._connection
    if state._activity is not None or state._status is not None:
        payload["d"]["presence"] = {
            "status": state._status,
            "game": state._activity,
            "since": 0,
            "afk": True,
        }
    if state._intents is not None:
        payload["d"]["intents"] = state._intents.value
    await self.call_hooks(
        "before_identify", self.shard_id, initial=self._initial_identify
    )
    await self.send_as_json(payload)


DiscordWebSocket.identify = mobile


@bot.command()
async def ping(ctx):
    """
    Displays the bot's latency.
    """
    await ctx.reply(
        embed=Embed(
            color=0x729BB0,
            description=f"📡 {ctx.author.mention}: ping `{round(bot.latency * 1000)}ms`",
        )
    )


bot.run(os.getenv("token"))
