import json
import asyncio

from typing import Union
from collections import defaultdict

from discord import Member, Permissions, Role, VoiceState, VoiceChannel, Embed, PermissionOverwrite, CategoryChannel, HTTPException, TextChannel, User
from discord.ext.commands import Cog, has_guild_permissions, command, group, bot_has_guild_permissions, BucketType, cooldown
from discord.errors import Forbidden, NotFound

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.handlers.embed import EmbedBuilder
from modules.persistent.vm import VoiceMasterView, ButtonScript
from modules.predicates import is_vm, check_vc_owner, rename_cooldown

class Voicemaster(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "VoiceMaster commands"
        self.locks = defaultdict(asyncio.Lock)
        self.values = [
            (f"{emojis.LOCK}", "[`Lock`](https://discord.gg/evelina) the voice channel"),
            (f"{emojis.UNLOCK}", "[`Unlock`](https://discord.gg/evelina) the voice channel"),
            (f"{emojis.HIDE}", "[`Hide`](https://discord.gg/evelina) the voice channel"),
            (f"{emojis.REVEAL}", "[`Reveal`](https://discord.gg/evelina) the voice channel"),
            (f"{emojis.CLAIM}", "[`Claim`](https://discord.gg/evelina) the voice channel"),
            (f"{emojis.KICK}", "[`Manage`](https://discord.gg/evelina) permited & rejected users"),
            (f"{emojis.INFO}", "[`Info`](https://discord.gg/evelina) about the voice channel"),
            (f"{emojis.RENAME}", "[`Rename`](https://discord.gg/evelina) the voice channel"),
            (f"{emojis.INCREASE}", "[`Increase`](https://discord.gg/evelina) the user limit"),
            (f"{emojis.DECREASE}", "[`Decrease`](https://discord.gg/evelina) the user limit"),
        ]
        self.evelina_server_id = 1228371886690537624
        self.allowed_role_id = 1351298298207535156

    async def get_banned_words(self, guild_id):
        banned_words_json = await self.bot.db.fetchval("SELECT banned_words FROM voicemaster WHERE guild_id = $1", guild_id)
        if banned_words_json:
            return json.loads(banned_words_json)
        return []

    async def save_banned_words(self, guild_id, banned_words):
        banned_words_json = json.dumps(banned_words)
        await self.bot.db.execute("UPDATE voicemaster SET banned_words = $1 WHERE guild_id = $2", banned_words_json, guild_id)

    def contains_banned_words(self, banned_words, text):
        text_lower = text.lower()
        return any(banned_word in text_lower for banned_word in banned_words)

    async def notify_user_about_missing_perms(self, member: Member, action: str):
        try:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {member.mention}: **{action.capitalize()}** action failed because I lack the required permissions")
            await member.send(embed=embed)
        except Forbidden:
            pass

    async def get_channel_categories(self, channel: VoiceChannel, member: Member) -> bool:
        if channel.category and len(channel.category.channels) == 50:
            await member.move_to(channel=None)
            return True
        return False

    async def get_channel_overwrites(self, channel: VoiceChannel, member: Member) -> bool:
        if not member.bot:
            if che := await self.bot.db.fetchrow("SELECT * FROM voicemaster_channels WHERE voice = $1", channel.id):
                if che["user_id"] != member.id:
                    if (channel.overwrites_for(channel.guild.default_role).connect == False):
                        if (channel.overwrites_for(member).connect == False or channel.overwrites_for(member).connect is None):
                            if member.id != member.guild.owner_id and not (member.guild_permissions.administrator or member.guild_permissions.manage_guild):
                                try:
                                    return await member.move_to(channel=None, reason="Not allowed to join this voice channel")
                                except Forbidden:
                                    await self.notify_user_about_missing_perms(member, "move to a different voice channel")

    async def create_temporary_channel(self, member: Member, category: CategoryChannel) -> None:
        try:
            region = await self.bot.db.fetchval("SELECT region FROM voicemaster WHERE guild_id = $1", member.guild.id)
            bitrate = await self.bot.db.fetchval("SELECT bitrate FROM voicemaster WHERE guild_id = $1", member.guild.id)
            if bitrate:
                bitrate_limits = [96000, 128000, 256000]
                for tier, limit in enumerate(bitrate_limits, start=1):
                    if member.guild.premium_tier < tier and bitrate > limit:
                        bitrate = limit
                        break
            name = await self.bot.db.fetchval("SELECT name FROM voicemaster WHERE guild_id = $1", member.guild.id)
            if not name:
                name = "{user.name}'s lounge"
            name = name.replace("{user}", member.name).replace("{user.name}", member.name).replace("{user.display_name}", member.display_name)
            savesettings = await self.bot.db.fetchval("SELECT savesettings FROM voicemaster WHERE guild_id = $1", member.guild.id)
            if savesettings:
                savedname = await self.bot.db.fetchval("SELECT name FROM voicemaster_names WHERE guild_id = $1 AND user_id = $2", member.guild.id, member.id)
                if savedname:
                    name = savedname
            preset = await self.bot.db.fetchrow("SELECT * FROM voicemaster_presets WHERE user_id = $1 AND autoload = True", member.id)
            overwrites = {}
            j2c_channel_id = await self.bot.db.fetchval("SELECT channel_id FROM voicemaster WHERE guild_id = $1", member.guild.id)
            if j2c_channel_id:
                j2c_channel = member.guild.get_channel(j2c_channel_id)
                if j2c_channel:
                    overwrites = {target: overwrite for target, overwrite in j2c_channel.overwrites.items()}
            overwrites[member] = PermissionOverwrite(view_channel=True, connect=True, move_members=True)
            channel = await member.guild.create_voice_channel(
                name=name,
                category=category, 
                reason="creating temporary voice channel", 
                overwrites=overwrites,
                rtc_region=region if region else None,
                bitrate=bitrate if bitrate else None
            )
            if member.voice and member.voice.channel:
                try:
                    await member.move_to(channel=channel)
                    await self.bot.db.execute("INSERT INTO voicemaster_channels VALUES ($1, $2)", member.id, channel.id)
                except:
                    await channel.delete(reason="Member was not connected to a voice channel, so temporary channel is not needed")
                    return None
            else:
                await channel.delete(reason="Member was not connected to a voice channel, so temporary channel is not needed")
                return None
            if preset:
                settings = json.loads(preset["settings"])
                preset_overwrites = json.loads(preset["overwrites"]) if isinstance(preset["overwrites"], str) else preset["overwrites"]
                user_limit = settings.get("user_limit", 0)
                if user_limit is None or not isinstance(user_limit, int):
                    user_limit = 0
                skipped = []
                try:
                    await channel.edit(
                        name=settings["name"], 
                        bitrate=settings["bitrate"], 
                        user_limit=user_limit, 
                        reason=f"Loaded preset for {member.name}"
                    )
                    new_overwrites = {}
                    for target_id, data in preset_overwrites.items():
                        target = (
                            member.guild.get_role(int(target_id)) if data["type"] == "role" else member.guild.get_member(int(target_id))
                        )
                        if target:
                            new_overwrites[target] = PermissionOverwrite.from_pair(Permissions(data["allow"]), Permissions(data["deny"]))
                        else:
                            skipped.append(target_id)
                    await channel.edit(overwrites=new_overwrites)
                except Exception as e:
                    await self.notify_user_about_missing_perms(member, f"load preset: {e}")
            await asyncio.sleep(0.9)
            try:
                channel = await channel.guild.fetch_channel(channel.id)
            except NotFound:
                return None
            if channel and len(channel.members) == 0:
                try:
                    await channel.delete(reason="No one inside the temporary voice channel")
                except (Forbidden, NotFound):
                    pass
                await self.bot.db.execute("DELETE FROM voicemaster_channels WHERE voice = $1", channel.id)
        except Forbidden:
            await self.notify_user_about_missing_perms(member, "create temporary voice channel")
        return None

    async def delete_temporary_channel(self, channel: VoiceChannel) -> None:
        channel_data = await self.bot.db.fetchrow("SELECT * FROM voicemaster_channels WHERE voice = $1", channel.id)
        if not channel_data:
            return
        if len(channel.members) > 0:
            return
        await self.bot.db.execute("DELETE FROM voicemaster_channels WHERE voice = $1", channel.id)
        cache_key = f"vc-bucket-{channel.id}"
        if cache_key in self.bot.cache.cache_inventory:
            await self.bot.cache.delete(cache_key)
        try:
            await channel.delete(reason="no one in the temporary voice channel")
        except Forbidden:
            owner_id = channel_data["user_id"]
            owner = channel.guild.get_member(owner_id)
            if owner:
                await self.notify_user_about_missing_perms(owner, "delete your voice channel")
        except Exception:
            pass

    async def get_custom_category(self, guild_id: int, after: VoiceState) -> Union[CategoryChannel, None]:
        category_id = await self.bot.db.fetchval("SELECT category FROM voicemaster WHERE guild_id = $1", guild_id)
        if not category_id:
            return after.channel.category
        return self.bot.get_channel(category_id)

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if (member.guild.me.guild_permissions.administrator and before.channel != after.channel):
            if check := await self.bot.db.fetchrow("SELECT * FROM voicemaster WHERE guild_id = $1", member.guild.id):
                jtc = int(check["channel_id"])
                if not before.channel and after.channel:
                    if after.channel.id == jtc:
                        if await self.get_channel_categories(after.channel, member):
                            return
                        custom_category = await self.get_custom_category(member.guild.id, after)
                        if custom_category:
                            return await self.create_temporary_channel(member, custom_category)
                        else:
                            return await self.create_temporary_channel(member, after.channel.category)
                    #else:
                        #return await self.get_channel_overwrites(after.channel, member)
                elif before.channel and after.channel:
                    if before.channel.id == jtc:
                        return
                    if before.channel.category == after.channel.category:
                        if after.channel.id == jtc:
                            if await self.bot.db.fetchrow("SELECT * FROM voicemaster_channels WHERE voice = $1", before.channel.id):
                                if len(before.channel.members) == 0:
                                    try:
                                        return await member.move_to(channel=before.channel)
                                    except Exception:
                                        pass
                            if await self.get_channel_categories(after.channel, member):
                                return
                            custom_category = await self.get_custom_category(member.guild.id, after)
                            if custom_category:
                                return await self.create_temporary_channel(member, custom_category)
                            else:
                                return await self.create_temporary_channel(member, after.channel.category)
                        elif before.channel.id != after.channel.id:
                            #await self.get_channel_overwrites(after.channel, member)
                            await self.delete_temporary_channel(before.channel)
                    else:
                        if after.channel.id == jtc:
                            if await self.get_channel_categories(after.channel, member):
                                return
                            if custom_category := await self.get_custom_category(member.guild.id, after):
                                return await self.create_temporary_channel(member, custom_category)
                            else: 
                                return await self.create_temporary_channel(member, after.channel.category)
                        else:
                            #await self.get_channel_overwrites(after.channel, member)
                            await self.delete_temporary_channel(before.channel)
                elif before.channel and not after.channel:
                    if before.channel.id == jtc:
                        return
                    await self.delete_temporary_channel(before.channel)

    @group(name="voicemaster", aliases=["vm"], description="Make temporary voice channels in your server", invoke_without_command=True, case_insensitive=True)
    async def voicemaster(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @voicemaster.command(name="setup", brief="administrator", usage="voicemaster setup", description="Start the setup for the VoiceMaster module")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True)
    @is_vm()
    async def vm_setup(self, ctx: EvelinaContext):
        try:
            async with self.locks[ctx.guild.id]:
                mes = await ctx.send(embed=Embed(color=colors.LOADING, description=f"{emojis.LOADING} {ctx.author.mention}: Creating the VoiceMaster interface"))
                try:
                    category = await ctx.guild.create_category(name="voicemaster", reason="voicemaster category created")
                except Forbidden:
                    return await ctx.send_warning("I lack permissions to create categories in this server.", obj=mes)
                except HTTPException as e:
                    return await ctx.send_warning(f"Failed to create category, use `{ctx.clean_prefix}voicemaster unsetup` and try again", obj=mes)
                if not category:
                    return await ctx.send_warning("Failed to create the VoiceMaster category.", obj=mes)
                try:
                    voice = await ctx.guild.create_voice_channel(name="join to create", category=category, reason="voicemaster channel created")
                    text = await ctx.guild.create_text_channel(name="interface", category=category, reason="voicemaster interface created",
                    overwrites={ctx.guild.default_role: PermissionOverwrite(send_messages=False)})
                except HTTPException as e:
                    return await ctx.send_warning(f"Failed to create channels, use `{ctx.clean_prefix}voicemaster unsetup` and try again", obj=mes)
                embed = Embed(color=colors.NEUTRAL, title="VoiceMaster Interface", description=f"Control the voice channels created from {voice.mention}")
                embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
                embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
                embed.add_field(name="usage", value="\n".join(f"{x[0]} - {x[1]}" for x in self.values))
                view = VoiceMasterView(self.bot)
                await view.add_default_buttons(ctx.guild)
                await text.send(embed=embed, view=view)
                await self.bot.db.execute("INSERT INTO voicemaster VALUES ($1,$2,$3)", ctx.guild.id, voice.id, text.id)
                return await ctx.send_success(f"Created the VoiceMaster interface in {text.mention} and the voice channel in {voice.mention}", obj=mes)
        except Forbidden:
            return await ctx.send_warning("I am missing permissions to setup the **voicemaster** module", obj=mes)

    @voicemaster.command(name="unsetup", brief="administrator", usage="voicemaster unsetup", description="Reset server configuration for VoiceMaster")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def vm_unsetup(self, ctx: EvelinaContext):
        async with self.locks[ctx.guild.id]:
            check = await self.bot.db.fetchrow("SELECT * FROM voicemaster WHERE guild_id = $1", ctx.guild.id)
            if not check:
                return await ctx.send_warning("VoiceMaster is **not** configured")
            mes = await ctx.send(embed=Embed(color=colors.NEUTRAL, description=f"{emojis.LOADING} {ctx.author.mention}: Disabling the VoiceMaster interface"))
            voice = ctx.guild.get_channel(check["channel_id"])
            if voice:
                try:
                    if voice and isinstance(voice, VoiceChannel):
                        if voice.category:
                            for channel in voice.category.channels:
                                if channel:
                                    await channel.delete(reason=f"VoiceMaster module disabled by {ctx.author}")
                            await voice.category.delete(reason=f"VoiceMaster module disabled by {ctx.author}")
                        else:
                            await voice.delete(reason=f"VoiceMaster module disabled by {ctx.author}")
                    else:
                        raise ValueError("The voice channel does not exist anymore.")
                except HTTPException as e:
                    if e.code == 50074:
                        return await ctx.send_warning("Cannot delete a channel required for community servers.")
                    else:
                        raise
            await self.bot.db.execute("DELETE FROM voicemaster WHERE guild_id = $1", ctx.guild.id)
            await self.bot.db.execute("DELETE FROM voicemaster_buttons WHERE guild_id = $1", ctx.guild.id)
            return await mes.edit(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {ctx.author.mention}: Successfully disabled the VoiceMaster module"))
        
    @voicemaster.command(name="region", brief="administrator", usage="voicemaster region none", description="Set the region for the voice channels created by the bot")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def vm_region(self, ctx: EvelinaContext, region: str):
        if region not in ['none', 'brazil', 'hongkong', 'india', 'japan', 'rotterdam', 'russia', 'singapore', 'south-korea', 'southafrica', 'sydney', 'us-central', 'us-east', 'us-south', 'us-west']:
            return await ctx.send_warning("Invalid region, please choose one of the following: `brazil`, `hongkong`, `india`, `japan', 'rotterdam', `russia`, `singapore`, `south-korea`, `southafrica`, `sydney`, `us-central`, `us-east`, `us-south`, `us-west`")
        check = await self.bot.db.fetchrow("SELECT * FROM voicemaster WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("VoiceMaster is **not** configured")
        else:
            if region == 'none':
                await self.bot.db.execute("UPDATE voicemaster SET region = NULL WHERE guild_id = $1", ctx.guild.id)
                return await ctx.send_success("Set the voice channel region to **default**")
            else:
                await self.bot.db.execute("UPDATE voicemaster SET region = $1 WHERE guild_id = $2", region, ctx.guild.id)
                return await ctx.send_success(f"Set the default voice channel region to **{region}**")
            
    @voicemaster.command(name="name", bief="administrator", usage="voicemaster name {user.display_name}'s vc", description="Set the name for the voice channels created by the bot")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def vm_name(self, ctx: EvelinaContext, *, name: str):
        check = await self.bot.db.fetchrow("SELECT * FROM voicemaster WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("VoiceMaster is **not** configured")
        else:
            if name == 'none':
                await self.bot.db.execute("UPDATE voicemaster SET name = NULL WHERE guild_id = $1", ctx.guild.id)
                return await ctx.send_success("Set the voice channel name to **default**")
            await self.bot.db.execute("UPDATE voicemaster SET name = $1 WHERE guild_id = $2", name, ctx.guild.id)
            return await ctx.send_success(f"Set the default voice channel name to **{name}**")
        
    @voicemaster.command(name="bitrate", brief="administrator", usage="voicemaster bitrate 384", description="Set the bitrate for the voice channels created by the bot")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def vm_bitrate(self, ctx: EvelinaContext, bitrate: int):
        if bitrate < 8 or bitrate > 384:
            return await ctx.send_warning("Bitrate must be between 8 and 384")
        check = await self.bot.db.fetchrow("SELECT * FROM voicemaster WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("VoiceMaster is **not** configured")
        else:
            bitrate = bitrate * 1000
            await self.bot.db.execute("UPDATE voicemaster SET bitrate = $1 WHERE guild_id = $2", bitrate, ctx.guild.id)
            return await ctx.send_success(f"Set the default voice channel bitrate to **{bitrate}**")
        
    @voicemaster.command(name="category", brief="administrator", usage="voicemaster category Voice Channels", description="Set the category for the voice channels created by the bot")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def vm_category(self, ctx: EvelinaContext, *, category: CategoryChannel = None):
        check = await self.bot.db.fetchrow("SELECT * FROM voicemaster WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("VoiceMaster is **not** configured")
        else:
            if not category:
                await self.bot.db.execute("UPDATE voicemaster SET category = NULL WHERE guild_id = $1", ctx.guild.id)
                return await ctx.send_success("Set the voice channel category to **default**")
            await self.bot.db.execute("UPDATE voicemaster SET category = $1 WHERE guild_id = $2", category.id, ctx.guild.id)
            return await ctx.send_success(f"Set the default voice channel category to **{category.name}**")	
        
    @voicemaster.command(name="savesettings", brief="administrator", usage="voicemaster savesettings on", description="Enable or disable if user settings should be saved")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def vm_savesettings(self, ctx: EvelinaContext, option: str):
        check = await self.bot.db.fetchrow("SELECT * FROM voicemaster WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("VoiceMaster is **not** configured")
        else:
            if option.lower() == "on":
                await self.bot.db.execute("UPDATE voicemaster SET savesettings = $1 WHERE guild_id = $2", True, ctx.guild.id)
                return await ctx.send_success(f"Enabled that user settings get saved from old channel")
            elif option.lower() == "off":
                await self.bot.db.execute("UPDATE voicemaster SET savesettings = $1 WHERE guild_id = $2", False, ctx.guild.id)
                return await ctx.send_success(f"Disabled that user settings get saved from old channel")
            else:
                return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")
            
    @voicemaster.command(name="blacklist", brief="manage guild", usage="voicemaster blacklist word nig*a")
    @has_guild_permissions(manage_guild=True)
    async def vm_blacklist(self, ctx: EvelinaContext, *, words: str):
        """Blacklist a word that can no longer be used as a voicemaster name"""
        word_list = [word.strip().lower() for word in words.split(',')]
        banned_words = await self.get_banned_words(ctx.guild.id)
        new_banned_words = []
        for word in word_list:
            if word in banned_words:
                await ctx.send_warning(f"Word `{word}` is already banned.")
            else:
                banned_words.append(word)
                new_banned_words.append(word)
        if new_banned_words:
            await self.save_banned_words(ctx.guild.id, banned_words)
            new_banned_words_str = ', '.join(new_banned_words)
            await ctx.send_success(f"Following words have been added:\n> **{new_banned_words_str}**")
        else:
            await ctx.send_warning("No new words were added to the banned words list.")

    @voicemaster.command(name="unblacklist", brief="manage guild", usage="voicemaster unblacklist word nig*a")
    @has_guild_permissions(manage_guild=True)
    async def vm_unblacklist(self, ctx: EvelinaContext, *, words: str):
        """Unblacklist a word to allow it as a voicemaster name again"""
        word_list = [word.strip().lower() for word in words.split(',')]
        banned_words = await self.get_banned_words(ctx.guild.id)
        removed_words = []
        for word in word_list:
            if word in banned_words:
                banned_words.remove(word)
                removed_words.append(word)
            else:
                await ctx.send_warning(f"Word `{word}` is not banned.")
        if removed_words:
            await self.save_banned_words(ctx.guild.id, banned_words)
            removed_words_str = ', '.join(removed_words)
            await ctx.send_success(f"Following words have been removed:\n> **{removed_words_str}**")
        else:
            await ctx.send_warning("No words were removed from the banned words list.")

    @voicemaster.command(name="blacklisted", brief="manage guild")
    @has_guild_permissions(administrator=True)
    async def vm_blacklisted(self, ctx: EvelinaContext):
        """Shows all blacklisted words for voicemaster names"""
        banned_words = await self.get_banned_words(ctx.guild.id)
        if not banned_words:
            return await ctx.send("There are no banned words.")
        banned_words_list = [f"**{word}**" for index, word in enumerate(banned_words)]
        await ctx.paginate(banned_words_list, f"Blacklisted words", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command(name="interface", brief="administrator", usage="interface hello world", description="Create a custom voice master interface")
    @has_guild_permissions(administrator=True)
    async def interface(self, ctx: EvelinaContext, channel: TextChannel, *, code: str = None):
        """Create a custom voice master interface"""
        await self.bot.db.execute("DELETE FROM voicemaster_buttons WHERE guild_id = $1", ctx.guild.id)
        view = VoiceMasterView(self.bot)
        if not code:
            embed = (
                Embed(color=colors.NEUTRAL, title="VoiceMaster Interface", description=f"Click the buttons below to control your voice channel")
                .set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
                .set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
                .add_field(name="Button Usage", value="\n".join(f"{x[0]} — {x[1]}" for x in self.values))
            )
            await view.add_default_buttons(ctx.guild)
            return await channel.send(embed=embed, view=view)
        items = ButtonScript.script(EmbedBuilder().embed_replacement(ctx.author, code))
        if len(items[2]) == 0:
            await view.add_default_buttons(ctx.guild)
        else:
            for item in items[2]:
                await view.add_button(ctx.guild, item[0], label=item[1], emoji=item[2], style=item[3])
        await channel.send(content=items[0], embed=items[1], view=view)

    @group(name="voice", aliases=["vc"], description="Manage your VoiceMaster channel", invoke_without_command=True, case_insensitive=True)
    async def voice(self, ctx: EvelinaContext):
        """Manage your VoiceMaster channel"""
        return await ctx.create_pages()

    @voice.command(name="lock", brief="voice owner", description="Lock your voice channel")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def voice_lock(self, ctx: EvelinaContext):
        """Lock your voice channel"""
        overwrite = ctx.author.voice.channel.overwrites_for(ctx.guild.default_role)
        overwrite.connect = False
        await ctx.author.voice.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Channel locked by {ctx.author}")

        if ctx.guild.id == self.evelina_server_id:
            allowed_role = ctx.guild.get_role(self.allowed_role_id)
            if allowed_role:
                await ctx.author.voice.channel.set_permissions(allowed_role, connect=True, reason=f"Allow role {allowed_role.name} to connect")

        return await ctx.send_success(f"locked <#{ctx.author.voice.channel.id}>")

    @voice.command(name="unlock", brief="voice owner", description="Unlock your voice channel")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def voice_unlock(self, ctx: EvelinaContext):
        """Unlock your voice channel"""
        overwrite = ctx.author.voice.channel.overwrites_for(ctx.guild.default_role)
        overwrite.connect = True
        await ctx.author.voice.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Channel unlocked by {ctx.author}")
        return await ctx.send_success(f"Unlocked <#{ctx.author.voice.channel.id}>")

    @voice.command(name="rename", brief="voice owner", usage="voice rename Valorant Voice", description="Rename your voice channel")
    @check_vc_owner()
    @rename_cooldown()
    @bot_has_guild_permissions(manage_channels=True)
    async def voice_rename(self, ctx: EvelinaContext, *, name: str):
        """Rename your voice channel"""
        banned_words = await self.get_banned_words(ctx.guild.id)
        if self.contains_banned_words(banned_words, name):
            return await ctx.send_warning("This voice channel name contains a prohibited word. Please choose a different name.")
        try:
            await ctx.author.voice.channel.edit(name=name)
        except HTTPException:
            return await ctx.send_warning("Name contains words not allowed for servers in Server Discover")
        savesettings = await self.bot.db.fetchval("SELECT savesettings FROM voicemaster WHERE guild_id = $1", ctx.guild.id)
        if savesettings:
            await self.bot.db.execute("INSERT INTO voicemaster_names (guild_id, user_id, name) VALUES ($1, $2, $3) ON CONFLICT (guild_id, user_id) DO UPDATE SET name = $3", ctx.guild.id, ctx.author.id, name)
        return await ctx.send_success(f"Renamed the voice channel to **{name}**")

    @voice.command(name="hide", brief="voice owner", description="Hide your voice channel")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def voice_hide(self, ctx: EvelinaContext):
        """Hide your voice channel"""
        overwrite = ctx.author.voice.channel.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = False
        await ctx.author.voice.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Channel hidden by {ctx.author}")
        return await ctx.send_success(f"Hidden <#{ctx.author.voice.channel.id}>")

    @voice.command(name="reveal", brief="voice owner", description="Reveal your voice channel")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def voice_reveal(self, ctx: EvelinaContext):
        """Reveal your voice channel"""
        overwrite = ctx.author.voice.channel.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = True
        await ctx.author.voice.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Channel revealed by {ctx.author}")
        return await ctx.send_success(f"Revealed <#{ctx.author.voice.channel.id}>")

    @voice.command(name="permit", brief="voice owner", usage="voice permit comminate", description="Permit a member or role to join your voice channel")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def voice_permit(self, ctx: EvelinaContext, *, member: Member):
        """Permit a member or role to join your voice channel"""
        await ctx.author.voice.channel.set_permissions(member, connect=True, view_channel=True)
        return await ctx.send_success(f"{member.mention} is allowed to join <#{ctx.author.voice.channel.id}>")

    @voice.command(name="reject", brief="voice owner", usage="voice reject comminate", description="Reject a member or role from joining your voice channel")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def voice_reject(self, ctx: EvelinaContext, *, member: Member):
        """Reject a member or role from joining your voice channel"""
        if member.id == ctx.author.id:
            return await ctx.reply("why would u wanna kick urself >_<")
        if member in ctx.author.voice.channel.members:
            await member.move_to(channel=None)
        await ctx.author.voice.channel.set_permissions(member, connect=False)
        return await ctx.send_success(f"{member.mention} is not allowed to join <#{ctx.author.voice.channel.id}> anymore")

    @voice.command(name="kick", brief="voice owner", usage="voice kick comminate", description="Kick a member or role from joining your voice channel")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def voice_kick(self, ctx: EvelinaContext, *, member: Member):
        """Kick a member or role from joining your voice channel"""
        if member.id == ctx.author.id:
            return await ctx.send("why would u wanna kick urself >_<")
        if not member in ctx.author.voice.channel.members:
            return await ctx.send_warning(f"{member.mention} isn't in **your** voice channel")
        await member.move_to(channel=None)
        return await ctx.send_success(f"{member.mention} got kicked from <#{ctx.author.voice.channel.id}>")

    @voice.command(name="claim", description="Claim an inactive voice channel")
    async def voice_claim(self, ctx: EvelinaContext):
        """Claim an inactive voice channel"""
        if not ctx.author.voice:
            return await ctx.send_warning("You are **not** in a voice channel")
        check = await self.bot.db.fetchrow("SELECT user_id FROM voicemaster_channels WHERE voice = $1", ctx.author.voice.channel.id)
        if not check:
            return await ctx.send_warning("You are **not** in a voice channel made by the bot")
        if ctx.author.id == check[0]:
            return await ctx.send_warning("You are the **owner** of this voice channel")
        if check[0] in [m.id for m in ctx.author.voice.channel.members]:
            return await ctx.send_warning("The owner is still in the voice channel")
        await self.bot.db.execute("UPDATE voicemaster_channels SET user_id = $1 WHERE voice = $2", ctx.author.id, ctx.author.voice.channel.id)
        old_owner = ctx.guild.get_member(check[0])
        if old_owner:
            await ctx.author.voice.channel.set_permissions(old_owner, view_channel=None, connect=None)
        await ctx.author.voice.channel.set_permissions(ctx.author, view_channel=True, connect=True)
        return await ctx.send_success("You are the new **owner** of this voice channel")

    @voice.command(name="transfer", brief="voice owner", usage="voice transfer comminate", description="Transfer ownership of your voice channel to another member")
    @check_vc_owner()
    async def voice_transfer(self, ctx: EvelinaContext, *, member: Member):
        """Transfer ownership of your voice channel to another member"""
        if not member in ctx.author.voice.channel.members:
            return await ctx.send_warning(f"{member.mention} is not in your voice channel")
        if member == ctx.author:
            return await ctx.send_warning("You are already the **owner** of this **voice channel**")
        await self.bot.db.execute("UPDATE voicemaster_channels SET user_id = $1 WHERE voice = $2", member.id, ctx.author.voice.channel.id)
        return await ctx.send_success(f"Transfered the voice ownership to {member.mention}")
    
    @voice.command(name="status", brief="voice owner", usage="voice status Gaming", description="Chance the status of your voice channel")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def voice_status(self, ctx: EvelinaContext, *, status: str):
        """Change the status of your voice channel"""
        channel = ctx.author.voice.channel
        await channel.edit(status=status)
        return await ctx.send_success(f"Changed the voice channel status to **{status}**")
    
    @voice.command(name="limit", brief="voice owner", usage="voice limit 5", description="Change the user limit of your voice channel")
    @check_vc_owner()
    @bot_has_guild_permissions(manage_channels=True)
    async def voice_limit(self, ctx: EvelinaContext, limit: int):
        """Change the user limit of your voice channel"""
        if limit < 0 or limit > 99:
            return await ctx.send_warning("User limit must be between 0 and 99")
        await ctx.author.voice.channel.edit(user_limit=limit)
        return await ctx.send_success(f"Changed the user limit to **{limit}**")
    
    @voice.group(name="preset", aliases=["p"], invoke_without_command=True, case_insensitive=True)
    async def voice_preset(self, ctx: EvelinaContext):
        """Manage your voice channel presets"""
        return await ctx.create_pages()

    @voice_preset.command(name="add", usage="voice preset add friends")
    @check_vc_owner()
    async def voice_preset_add(self, ctx: EvelinaContext, *, name: str):
        """Create a preset for the current temp voice channel"""
        vc = ctx.author.voice
        channel = vc.channel
        if not vc or not vc.channel:
            return await ctx.send("You need to be in a **voice channel** to create a preset")
        presets = await self.bot.db.fetchval("SELECT COUNT(*) FROM voicemaster_presets WHERE user_id = $1", ctx.author.id)
        if presets >= 10:
            return await ctx.send_warning("You can only have up to **10 presets**")
        r = await self.bot.db.fetchrow("SELECT * FROM voicemaster_presets WHERE user_id = $1 AND name = $2", ctx.author.id, name)
        if r:
            return await ctx.send_warning(f"There is **already** a preset created named **{name}**")
        m = await ctx.send_loading("Creating your preset...")
        settings = {"name": channel.name, "bitrate": channel.bitrate, "user_limit": channel.user_limit}
        overwrites = {str(target.id): {"type": "role" if isinstance(target, Role) else "member", "allow": overwrite.pair()[0].value, "deny": overwrite.pair()[1].value} for target, overwrite in channel.overwrites.items()}
        hidden = channel.overwrites_for(ctx.guild.default_role).view_channel is False
        if hidden:
            overwrites[str(ctx.guild.default_role.id)] = {"type": "role", "allow": 0, "deny": 1024}

        locked = channel.overwrites_for(ctx.guild.default_role).connect is False
        if locked:
            if str(ctx.guild.default_role.id) in overwrites:
                overwrites[str(ctx.guild.default_role.id)]["deny"] |= 1048576
            else:
                overwrites[str(ctx.guild.default_role.id)] = {"type": "role", "allow": 0, "deny": 1048576}
        settings_json = json.dumps(settings)
        overwrites_json = json.dumps(overwrites)
        await self.bot.db.execute("INSERT INTO voicemaster_presets (user_id, name, settings, overwrites) VALUES ($1, $2, $3, $4)", ctx.author.id, name, settings_json, overwrites_json)
        return await ctx.send_success(f"Preset with name **{name}** has been created!", obj=m)

    @voice_preset.command(name="load", cooldown=60, usage="voice preset load friends")
    @check_vc_owner()
    @cooldown(1, 60, BucketType.user)
    async def voice_preset_load(self, ctx: EvelinaContext, *, name: str):
        """Apply a saved preset to the current temp voice channel"""
        vc = ctx.author.voice
        if not vc or not vc.channel:
            return await ctx.send("You need to be in a **voice channel** to load a preset")
        channel = vc.channel
        record = await self.bot.db.fetchrow("SELECT settings, overwrites FROM voicemaster_presets WHERE user_id = $1 AND name = $2", ctx.author.id, name)
        if not record:
            return await ctx.send_warning(f"No preset found with the name **{name}**")
        l = await ctx.send_loading(f"Loading **{name}** preset to your vc..")
        settings = json.loads(record["settings"])
        overwrites = json.loads(record["overwrites"])
        if isinstance(overwrites, str):
            overwrites = json.loads(overwrites)
        user_limit = settings.get("user_limit", 0)
        if user_limit is None or not isinstance(user_limit, int):
            user_limit = 0
        skipped = []
        try:
            await channel.edit(name=settings["name"], bitrate=settings["bitrate"], user_limit=user_limit, reason=f"Loaded preset {name} from {ctx.author.name}")
            new_overwrites = {}
            for target_id, data in overwrites.items():
                target = (ctx.guild.get_role(int(target_id)) if data["type"] == "role" else ctx.guild.get_member(int(target_id)))
                if target:
                    new_overwrites[target] = PermissionOverwrite.from_pair(Permissions(data["allow"]), Permissions(data["deny"]))
                else:
                    skipped.append(target_id)
            await channel.edit(overwrites=new_overwrites)
            msg = f"Preset **{name}** loaded successfully!"
            if skipped:
                msg += f"\nSkipped invalid targets: {', '.join(skipped)}"
            await ctx.send_success(msg, obj=l)
        except Exception as e:
            await ctx.send_warning(f"Error loading preset **{name}**\n```{e}```", obj=l)

    @voice_preset.command(name="autoload", usage="voice preset autoload trusted")
    async def voice_preset_autoload(self, ctx: EvelinaContext, name: str):
        """Automatically load the preset of the user when they join a voice channel"""
        check = await self.bot.db.fetch("SELECT * FROM voicemaster_presets WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.send_warning(f"You don't have a presets")
        if name == "none":
            await self.bot.db.execute("UPDATE voicemaster_presets SET autoload = $1 WHERE user_id = $2 AND autoload = $3", False, ctx.author.id, True)
            return await ctx.send_success(f"Disabled **autoload** for all presets")
        result = await self.bot.db.fetchrow("SELECT autoload FROM voicemaster_presets WHERE user_id = $1 AND name = $2", ctx.author.id, name)
        if not result:
            return await ctx.send_warning(f"No preset named **{name}** found")
        for preset in check:
            if preset['autoload'] == True:
                await self.bot.db.execute("UPDATE voicemaster_presets SET autoload = $1 WHERE user_id = $2 AND name = $3", False, ctx.author.id, preset['name'])
                await self.bot.db.execute("UPDATE voicemaster_presets SET autoload = $1 WHERE user_id = $2 AND name = $3", True, ctx.author.id, name)
            else:
                await self.bot.db.execute("UPDATE voicemaster_presets SET autoload = $1 WHERE user_id = $2 AND name = $3", True, ctx.author.id, name)
        return await ctx.send_success(f"Preset **{name}** will now be **automatically loaded** when you join a voice channel")

    @voice_preset.command(name="update", usage="voice preset update friends")
    @check_vc_owner()
    async def voice_preset_update(self, ctx: EvelinaContext, *, name: str):
        """Update an existing preset with the current temp voice channel's settings."""
        vc = ctx.author.voice
        if not vc or not vc.channel:
            return await ctx.send("You need to be in a **voice channel** to update a preset.")
        channel = vc.channel
        exists = await self.bot.db.fetchval("SELECT 1 FROM voicemaster_presets WHERE user_id = $1 AND name = $2", ctx.author.id, name)
        if not exists:
            return await ctx.send_warning(f"No preset named **{name}** found.\nUse `voice preset add {name}` instead.")
        settings = {"name": channel.name, "bitrate": channel.bitrate, "user_limit": channel.user_limit,}
        overwrites = {
            str(target.id): {"type": "role" if isinstance(target, Role) else "member", "allow": overwrite.pair()[0].value, "deny": overwrite.pair()[1].value,}
            for target, overwrite in channel.overwrites.items()
            if (isinstance(target, Role) and ctx.guild.get_role(target.id))
            or (isinstance(target, Member) and ctx.guild.get_member(target.id))
        }
        hidden = channel.overwrites_for(ctx.guild.default_role).view_channel is False
        if hidden:
            overwrites[str(ctx.guild.default_role.id)] = {"type": "role", "allow": 0, "deny": 1024}
        locked = channel.overwrites_for(ctx.guild.default_role).connect is False
        if locked:
            if str(ctx.guild.default_role.id) in overwrites:
                overwrites[str(ctx.guild.default_role.id)]["deny"] |= 1048576
            else:
                overwrites[str(ctx.guild.default_role.id)] = {"type": "role", "allow": 0, "deny": 1048576}
        settings_json = json.dumps(settings)
        overwrites_json = json.dumps(overwrites)
        await self.bot.db.execute("UPDATE voicemaster_presets SET settings = $3, overwrites = $4 WHERE user_id = $1 AND name = $2", ctx.author.id, name, settings_json, overwrites_json,)
        return await ctx.send_success(f"Preset **{name}** has been **successfully** updated!")

    @voice_preset.command(name="edit", usage="voice preset edit friends comminate")
    async def voice_preset_edit(self, ctx: EvelinaContext, name: str, *, target: Union[User, Role]):
        """Add/remove a user or role to the overwrites of a preset"""
        record = await self.bot.db.fetchrow("SELECT overwrites FROM voicemaster_presets WHERE user_id = $1 AND name = $2", ctx.author.id, name)
        if not record:
            return await ctx.send_warning(f"No preset found with the name **{name}**")
        overwrites = json.loads(record["overwrites"])
        if isinstance(overwrites, str):
            overwrites = json.loads(overwrites)
        if str(target.id) in overwrites:
            del overwrites[str(target.id)]
            await ctx.send_success(f"Removed **{target}** from the overwrites of the preset **{name}**")
        else:
            overwrites[str(target.id)] = {"type": "role" if isinstance(target, Role) else "member", "allow": 0, "deny": 0}
            await ctx.send_success(f"Added **{target}** to the overwrites of the preset **{name}**")
        overwrites_json = json.dumps(overwrites)
        await self.bot.db.execute("UPDATE voicemaster_presets SET overwrites = $3 WHERE user_id = $1 AND name = $2", ctx.author.id, name, overwrites_json)

    @voice_preset.command(name="delete", usage="voice preset delete friends")
    async def voice_preset_delete(self, ctx: EvelinaContext, *, name: str):
        """Delete a voicemaster preset"""
        res = await self.bot.db.fetchrow("SELECT * FROM voicemaster_presets WHERE user_id = $1 AND name = $2", ctx.author.id, name)
        if not res:
            return await ctx.send_warning(f"There is no preset saved with the name **{name}**")
        await self.bot.db.execute("DELETE FROM voicemaster_presets WHERE user_id = $1 AND name = $2", ctx.author.id, name)
        return await ctx.send_success(f"Preset **{name}** has been successfully deleted")

    @voice_preset.command(name="list", usage="voice preset list")
    async def voice_preset_list(self, ctx: EvelinaContext):
        """List all presets created by the user"""
        results = await self.bot.db.fetch("SELECT name, settings, overwrites FROM voicemaster_presets WHERE user_id = $1", ctx.author.id)
        if not results:
            return await ctx.send_warning("You have **no** presets created")
        embeds = []
        for i in range(0, len(results), 2):
            embed = Embed(color=colors.NEUTRAL, title=f"Voice Presets")
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            for preset in results[i:i+2]:
                settings = json.loads(preset["settings"])
                overwrites = json.loads(preset["overwrites"])
                allowed_entries, disallowed_entries = [], []
                for uid, perms in overwrites.items():
                    if uid == str(ctx.guild.id):
                        continue
                    target_mention = f"<@&{uid}>" if perms["type"] == "role" else f"<@{uid}>"
                    if perms["allow"] != 0:
                        allowed_entries.append(target_mention)
                    if perms["deny"] != 0:
                        disallowed_entries.append(target_mention)
                allowed_users = ", ".join(allowed_entries) if allowed_entries else "N/A"
                disallowed_users = ", ".join(disallowed_entries) if disallowed_entries else "N/A"
                embed.add_field(
                    name=f"**{preset['name']}**",
                    value=(
                        f"> **Channel Name:** {settings['name']}\n"
                        f"> **Bitrate:** {settings['bitrate']}\n"
                        f"> **User Limit:** {settings['user_limit'] or 'No limit'}\n"
                        f"> **Allowed:** {allowed_users}\n"
                        f"> **Disallowed:** {disallowed_users}"
                    ),
                    inline=True
                )
            embed.set_footer(text=f"Page {i // 3 + 1}/{len(results) // 3 + 1} ({len(results)} entries)")
            embeds.append(embed)
        if not embeds:
            return await ctx.send_warning("No presets found")
        return await ctx.paginator(embeds)

async def setup(bot: Evelina) -> None:
    await bot.add_cog(Voicemaster(bot))