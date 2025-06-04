import io
import time
import asyncio

from time import time
from datetime import datetime
from collections import defaultdict

from discord import RawReactionActionEvent, Reaction, Member, Forbidden, NotFound, Message, Embed, File
from discord.ui import View, Button

from modules.styles import colors
from modules.evelinabot import Evelina

class ReactionMethods:
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.cache = {}
        self.star_cooldown = {}
        self.clown_cooldown = {}
        self.rate_limit_locks = defaultdict(asyncio.Lock)

    async def on_reactionrole_add(self, payload: RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return
        check = await self.bot.db.fetchrow("SELECT role_id FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4", payload.guild_id, payload.channel_id, payload.message_id, str(payload.emoji))
        if check:
            role = guild.get_role(check['role_id'])
            if role and role.is_assignable():
                if role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Reaction Role")
                    except Forbidden:
                        return
                    except NotFound:
                        return
                    
    async def on_starboard_add(self, payload: RawReactionActionEvent):
        if payload.channel_id in self.star_cooldown and time() - self.star_cooldown[payload.channel_id] < 2:
            return
        self.star_cooldown[payload.channel_id] = time()
        check = await self.bot.db.fetchrow("SELECT starboard FROM modules WHERE guild_id = $1", payload.guild_id)
        if not check or check['starboard'] is False:
            return
        check_ignored = await self.bot.db.fetchrow("SELECT * FROM starboard_ignored WHERE guild_id = $1 AND channel_id = $2", payload.guild_id, payload.channel_id)
        if check_ignored:
            return
        res = await self.bot.db.fetchrow("SELECT * FROM starboard WHERE guild_id = $1", payload.guild_id)
        if res and res["emoji"] and str(payload.emoji) == res["emoji"]:
            try:
                channel = self.bot.get_channel(payload.channel_id)
                if not channel:
                    channel = await self.bot.fetch_channel(payload.channel_id)
                if not channel:
                    return
                mes = channel.get_partial_message(payload.message_id)
                mes = await mes.fetch()
            except NotFound:
                try:
                    mes = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                except (NotFound, Forbidden):
                    return
            reactions = [r.count for r in mes.reactions if str(r.emoji) == res["emoji"]]
            if reactions and (reaction := reactions[0]) >= res.get("count", 0):
                channel = self.bot.get_channel(res["channel_id"])
                if channel and payload.channel_id != channel.id:
                    check = await self.bot.db.fetchrow("SELECT * FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
                    if not check:
                        embed, file = None, None
                        if not mes.embeds:
                            embed = Embed(color=colors.NEUTRAL, description=mes.content, timestamp=mes.created_at)
                            embed.set_author(name=str(mes.author), icon_url=mes.author.display_avatar.url)
                            if mes.attachments:
                                if mes.attachments[0].filename.endswith(("png", "jpeg", "jpg")):
                                    embed.set_image(url=mes.attachments[0].proxy_url)
                                elif mes.attachments[0].filename.endswith(("mp3", "mp4", "mov")):
                                    file = File(fp=io.BytesIO(await mes.attachments[0].read()), filename=mes.attachments[0].filename)
                        else:
                            em = mes.embeds[0]
                            embed = Embed(color=em.color, description=em.description or mes.content, title=em.title, url=em.url)
                            embed.set_author(name=em.author.name if em.author else str(mes.author), icon_url=(em.author.icon_url or mes.author.display_avatar.url))
                            embed.set_thumbnail(url=em.thumbnail.url if em.thumbnail else None)
                            embed.set_image(url=em.image.url if em.image else None)
                            embed.set_footer(text=em.footer.text, icon_url=em.footer.icon_url if em.footer else None)
                            if mes.attachments:
                                file = File(fp=io.BytesIO(await mes.attachments[0].read()), filename=mes.attachments[0].filename)
                        if mes.reference and mes.reference.resolved:
                            if isinstance(mes.reference.resolved, Message):
                                embed.description = (f"{embed.description}\n↩️ [replying to {mes.reference.resolved.author}]({mes.reference.resolved.jump_url})")
                            else:
                                embed.description = f"{embed.description}\n↩️ Replying to a deleted message"
                        view = View().add_item(Button(label="message", url=mes.jump_url))
                        if channel.permissions_for(channel.guild.me).send_messages:
                            m = await channel.send(content=f"{payload.emoji} **#{reaction}** {mes.channel.mention}", embed=embed, view=view, file=file)
                            await self.bot.db.execute("INSERT INTO starboard_messages VALUES ($1,$2,$3,$4)", payload.guild_id, payload.channel_id, payload.message_id, m.id)
                    else:
                        try:
                            m = channel.get_partial_message(check["starboard_message_id"])
                            await m.edit(content=f"{payload.emoji} **#{reaction}** {mes.channel.mention}")
                        except NotFound:
                            try:
                                m = await channel.fetch_message(check["starboard_message_id"])
                                await m.edit(content=f"{payload.emoji} **#{reaction}** {mes.channel.mention}")
                            except NotFound:
                                await self.bot.db.execute("DELETE FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
                    
    async def on_clownboard_add(self, payload: RawReactionActionEvent):
        if payload.channel_id in self.clown_cooldown and time() - self.clown_cooldown[payload.channel_id] < 2:
            return
        self.clown_cooldown[payload.channel_id] = time()
        check = await self.bot.db.fetchrow("SELECT clownboard FROM modules WHERE guild_id = $1", payload.guild_id)
        if not check or check['clownboard'] is False:
            return
        check_ignored = await self.bot.db.fetchrow("SELECT * FROM clownboard_ignored WHERE guild_id = $1 AND channel_id = $2", payload.guild_id, payload.channel_id)
        if check_ignored:
            return
        res = await self.bot.db.fetchrow("SELECT * FROM clownboard WHERE guild_id = $1", payload.guild_id)
        if res and res["emoji"] and str(payload.emoji) == res["emoji"]:
            try:
                channel = self.bot.get_channel(payload.channel_id)
                if not channel:
                    channel = await self.bot.fetch_channel(payload.channel_id)
                if not channel:
                    return
                mes = channel.get_partial_message(payload.message_id)
                mes = await mes.fetch()
            except NotFound:
                try:
                    mes = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                except (NotFound, Forbidden):
                    return
            reactions = [r.count for r in mes.reactions if str(r.emoji) == res["emoji"]]
            if reactions and (reaction := reactions[0]) >= res.get("count", 0):
                channel = self.bot.get_channel(res["channel_id"])
                if channel and payload.channel_id != channel.id:
                    check = await self.bot.db.fetchrow("SELECT * FROM clownboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
                    if not check:
                        embed, file = None, None
                        if not mes.embeds:
                            embed = Embed(color=colors.NEUTRAL, description=mes.content, timestamp=mes.created_at)
                            embed.set_author(name=str(mes.author), icon_url=mes.author.display_avatar.url)
                            if mes.attachments:
                                if mes.attachments[0].filename.endswith(("png", "jpeg", "jpg")):
                                    embed.set_image(url=mes.attachments[0].proxy_url)
                                elif mes.attachments[0].filename.endswith(("mp3", "mp4", "mov")):
                                    file = File(fp=io.BytesIO(await mes.attachments[0].read()), filename=mes.attachments[0].filename)
                        else:
                            em = mes.embeds[0]
                            embed = Embed(color=em.color, description=em.description or mes.content, title=em.title, url=em.url)
                            embed.set_author(name=em.author.name if em.author else str(mes.author), icon_url=(em.author.icon_url or mes.author.display_avatar.url))
                            embed.set_thumbnail(url=em.thumbnail.url if em.thumbnail else None)
                            embed.set_image(url=em.image.url if em.image else None)
                            embed.set_footer(text=em.footer.text, icon_url=em.footer.icon_url if em.footer else None)
                            if mes.attachments:
                                file = File(fp=io.BytesIO(await mes.attachments[0].read()), filename=mes.attachments[0].filename)
                        if mes.reference and mes.reference.resolved:
                            if isinstance(mes.reference.resolved, Message):
                                embed.description = (f"{embed.description}\n↩️ [replying to {mes.reference.resolved.author}]({mes.reference.resolved.jump_url})")
                            else:
                                embed.description = f"{embed.description}\n↩️ Replying to a deleted message"
                        view = View().add_item(Button(label="message", url=mes.jump_url))
                        if channel.permissions_for(channel.guild.me).send_messages:
                            m = await channel.send(content=f"{payload.emoji} **#{reaction}** {mes.channel.mention}", embed=embed, view=view, file=file)
                            await self.bot.db.execute("INSERT INTO clownboard_messages VALUES ($1,$2,$3,$4)", payload.guild_id, payload.channel_id, payload.message_id, m.id)
                    else:
                        try:
                            m = channel.get_partial_message(check["clownboard_message_id"])
                            await m.edit(content=f"{payload.emoji} **#{reaction}** {mes.channel.mention}")
                        except NotFound:
                            try:
                                m = await channel.fetch_message(check["clownboard_message_id"])
                                await m.edit(content=f"{payload.emoji} **#{reaction}** {mes.channel.mention}")
                            except NotFound:
                                await self.bot.db.execute("DELETE FROM clownboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)

    async def on_reactionrole_remove(self, payload: RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return
        check = await self.bot.db.fetchrow("SELECT role_id FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4", payload.guild_id, payload.channel_id, payload.message_id, str(payload.emoji))
        if check:
            role = guild.get_role(check['role_id'])
            if role and role.is_assignable():
                if role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Reaction Role")
                    except Forbidden:
                        return
                    except NotFound:
                        return
                    
    async def on_starboard_remove(self, payload: RawReactionActionEvent):
        check = await self.bot.db.fetchrow("SELECT starboard FROM modules WHERE guild_id = $1", payload.guild_id)
        if not check or check['starboard'] is False:
            return
        res = await self.bot.db.fetchrow("SELECT * FROM starboard WHERE guild_id = $1", payload.guild_id)
        if res:
            if not res["emoji"]:
                return
            reactions = None
            if str(payload.emoji) == res["emoji"]:
                try:
                    channel = self.bot.get_channel(payload.channel_id)
                    if not channel:
                        channel = await self.bot.fetch_channel(payload.channel_id)
                    if not channel:
                        return
                    mes = channel.get_partial_message(payload.message_id)
                    mes = await mes.fetch()
                except NotFound:
                    try:
                        mes = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                    except (NotFound, Forbidden):
                        return
                reactions = [r.count for r in mes.reactions if str(r.emoji) == res["emoji"]]
            if reactions and len(reactions) > 0 and reactions[0] < res["count"]:
                if not res["channel_id"]:
                    return
                channel = self.bot.get_channel(res["channel_id"])
                if channel:
                    check = await self.bot.db.fetchrow("SELECT * FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
                    if check:
                        try:
                            m = channel.get_partial_message(check["starboard_message_id"])
                            try:
                                m = await m.fetch()
                            except NotFound:
                                m = await channel.fetch_message(check["starboard_message_id"])
                            await m.delete()
                            await self.bot.db.execute("DELETE FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
                        except NotFound:
                            await self.bot.db.execute("DELETE FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
            else:
                if not reactions or len(reactions) == 0:
                    if not res["channel_id"]:
                        return
                    channel = self.bot.get_channel(res["channel_id"])
                    if channel:
                        check = await self.bot.db.fetchrow("SELECT * FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
                        if check:
                            try:
                                m = channel.get_partial_message(check["starboard_message_id"])
                                try:
                                    m = await m.fetch()
                                except NotFound:
                                    m = await channel.fetch_message(check["starboard_message_id"])
                                await m.delete()
                                await self.bot.db.execute("DELETE FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
                            except NotFound:
                                await self.bot.db.execute("DELETE FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)

    async def on_clownboard_remove(self, payload: RawReactionActionEvent):
        check = await self.bot.db.fetchrow("SELECT clownboard FROM modules WHERE guild_id = $1", payload.guild_id)
        if not check or check['clownboard'] is False:
            return
        res = await self.bot.db.fetchrow("SELECT * FROM clownboard WHERE guild_id = $1", payload.guild_id)
        if res:
            if not res["emoji"]:
                return
            reactions = None
            if str(payload.emoji) == res["emoji"]:
                try:
                    channel = self.bot.get_channel(payload.channel_id)
                    if not channel:
                        channel = await self.bot.fetch_channel(payload.channel_id)
                    if not channel:
                        return
                    mes = channel.get_partial_message(payload.message_id)
                    mes = await mes.fetch()
                except NotFound:
                    try:
                        mes = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                    except (NotFound, Forbidden):
                        return
                reactions = [r.count for r in mes.reactions if str(r.emoji) == res["emoji"]]
            if reactions and len(reactions) > 0 and reactions[0] < res["count"]:
                if not res["channel_id"]:
                    return
                channel = self.bot.get_channel(res["channel_id"])
                if channel:
                    check = await self.bot.db.fetchrow("SELECT * FROM clownboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
                    if check:
                        try:
                            m = channel.get_partial_message(check["clownboard_message_id"])
                            try:
                                m = await m.fetch()
                            except NotFound:
                                m = await channel.fetch_message(check["clownboard_message_id"])
                            await m.delete()
                            await self.bot.db.execute("DELETE FROM clownboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
                        except NotFound:
                            await self.bot.db.execute("DELETE FROM clownboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
            else:
                if not reactions or len(reactions) == 0:
                    if not res["channel_id"]:
                        return
                    channel = self.bot.get_channel(res["channel_id"])
                    if channel:
                        check = await self.bot.db.fetchrow("SELECT * FROM clownboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
                        if check:
                            try:
                                m = channel.get_partial_message(check["clownboard_message_id"])
                                try:
                                    m = await m.fetch()
                                except NotFound:
                                    m = await channel.fetch_message(check["clownboard_message_id"])
                                await m.delete()
                                await self.bot.db.execute("DELETE FROM clownboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)
                            except NotFound:
                                await self.bot.db.execute("DELETE FROM clownboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", payload.guild_id, payload.channel_id, payload.message_id)

    async def on_reactionsnipe_event(self, reaction: Reaction, user: Member):
        if user.bot:
            return
        await self.bot.db.execute("INSERT INTO snipes_reaction (channel_id, message_id, reaction, user_id, created_at) VALUES ($1, $2, $3, $4, $5)", reaction.message.channel.id, reaction.message.id, str(reaction.emoji), user.id, int(datetime.now().timestamp()))