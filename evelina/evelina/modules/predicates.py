import json
import asyncio
import datetime
import humanize

from discord import Embed, Interaction
from discord.ext.commands import check, BadArgument

from modules.styles import emojis, colors
from modules.persistent.vm import rename_vc_bucket
from modules.helpers import EvelinaContext

"""
LEVELING PREDICATES
"""

def leveling_enabled():
    async def predicate(ctx: EvelinaContext):
        if await ctx.bot.db.fetchrow("SELECT * FROM leveling WHERE guild_id = $1", ctx.guild.id):
            return True
        await ctx.send_warning(f"Leveling is **not** enabled\n> Use `{ctx.clean_prefix}level enable` to enable it")
        return False
    return check(predicate)

"""
ANTINUKE PREDICATES
"""

def antinuke_owner():
    async def predicate(ctx: EvelinaContext):
        if owner_id := await ctx.bot.db.fetchval("SELECT owner_id FROM antinuke WHERE guild_id = $1", ctx.guild.id):
            if ctx.author.id != owner_id:
                await ctx.send_warning(f"Only <@!{owner_id}> can use this command!")
                return False
            return True
        await ctx.send_warning(f"Antinuke is **not** configured\n> Use `{ctx.clean_prefix}antinuke setup` to configure it")
        return False
    return check(predicate)

def antinuke_configured():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchval("SELECT configured FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        if not check or check == "false":
            await ctx.send_warning(f"Antinuke is **not** configured\n> Use `{ctx.clean_prefix}antinuke setup` to configure it")
        return str(check) == "true"
    return check(predicate)

def antiraid_configured():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchval("SELECT configured FROM antiraid WHERE guild_id = $1", ctx.guild.id)
        if not check or check == "false":
            await ctx.send_warning(f"Antiraid is **not** configured\n> Use `{ctx.clean_prefix}antiraid setup` to configure it")
        return str(check) == "true"
    return check(predicate)

def admin_antinuke():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT owner_id, admins FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        if check:
            allowed = [check["owner_id"]]
            if check["admins"]:
                allowed.extend([id for id in json.loads(check["admins"])])
            if not ctx.author.id in allowed:
                await ctx.send_warning("You **can't** use this command, you need to be an Antinuke admin")
                return False
            return True
        else:
            await ctx.send_warning(f"Antinuke is **not** configured\n> Use `{ctx.clean_prefix}antinuke setup` to configure it")
            return False
    return check(predicate)

"""
BOOSTER ROLES PREDICATES  
"""

def br_is_configured():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM booster_module WHERE guild_id = $1", ctx.guild.id)
        if not check:
            await ctx.send_warning(f"Booster roles are **not** configured\n> Use `{ctx.clean_prefix}boosterrole setup` to configure it")
        return check is not None
    return check(predicate)

def has_br_role():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id)
        if not check:
            await ctx.send_warning(f"You don't have a booster role set\n> Please use `{ctx.clean_prefix}boosterrole create` to create a booster role")
        return check is not None
    return check(predicate)

def boosterrole_blacklisted():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT reason FROM booster_blacklist WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id)
        if check:
            await ctx.send_warning(f"You got blacklisted from using boosterroles\n> **Reason:** {check['reason']}")
            return False
        return True
    return check(predicate)

"""
COLOR ROLES PREDICATES  
"""

def cr_is_configured():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM color_module WHERE guild_id = $1", ctx.guild.id)
        if not check:
            await ctx.send_warning(f"Color roles are **not** configured\n> Use `{ctx.clean_prefix}colorrole setup` to configure it")
        return check is not None
    return check(predicate)

def has_cr_role():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM color_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id)
        if not check:
            await ctx.send_warning(f"You don't have a color role set\nPlease use `{ctx.clean_prefix}colorrole create` to create a color role")
        return check is not None
    return check(predicate)

"""
LIMIT PREDICATES
"""

def query_limit(table: str):
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchval(f"SELECT COUNT(*) FROM {table} WHERE guild_id = $1", ctx.guild.id)
        if check == 5:
            await ctx.send_warning(f"You can't create more than **5** {table} messages")
            return False
        return True
    return check(predicate)

def boosted_to(level: int):
    async def predicate(ctx: EvelinaContext):
        if ctx.guild.premium_tier < level:
            await ctx.send_warning(f"The server has to be boosted to level **{level}** to be able to use this command")
        return ctx.guild.premium_tier >= level
    return check(predicate)

def max_gws():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchval("SELECT COUNT(*) FROM giveaway WHERE guild_id = $1", ctx.guild.id)
        if check == 5:
            await ctx.send_warning("You can't host more than **5** giveaways in the same time")
            return False
        return True
    return check(predicate)

"""
OWNER PREDICATES
"""

def guild_owner():
    async def predicate(ctx: EvelinaContext):
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send_warning(f"This command can be only used by **{ctx.guild.owner}**")
        return ctx.author.id == ctx.guild.owner_id
    return check(predicate)

"""
MODERATION PREDICATES
"""

def is_jail():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM jail WHERE guild_id = $1", ctx.guild.id)
        if not check:
            raise BadArgument(f"Jail is **not** configured\n> Use `{ctx.clean_prefix}setjail` to enable it")
        return True
    return check(predicate)

def antispam_enabled():
    async def predicate(ctx: EvelinaContext):
        if not await ctx.bot.db.fetchrow("SELECT * FROM automod_spam WHERE guild_id = $1", ctx.guild.id):
            await ctx.send_warning(f"Antispam is **not** enabled in this server\n> Use `{ctx.clean_prefix}filter spam enable` to enable it")
            return False
        return True
    return check(predicate)

def antirepeat_enabled():
    async def predicate(ctx: EvelinaContext):
        if not await ctx.bot.db.fetchrow("SELECT * FROM automod_repeat WHERE guild_id = $1", ctx.guild.id):
            await ctx.send_warning(f"Antirepeat is **not** enabled in this server\n> Use `{ctx.clean_prefix}filter repeat enable` to enable it")
            return False
        return True
    return check(predicate)

"""
DONATOR PREDICATES
"""

def has_perks():
    async def predicate(ctx: EvelinaContext):
        check_premium = await ctx.bot.db.fetchrow("SELECT * FROM premium WHERE guild_id = $1", ctx.guild.id)
        if check_premium:
            return True
        check_donor = await ctx.bot.db.fetchrow("SELECT * FROM donor WHERE user_id = $1", ctx.author.id)
        check_vote = await ctx.bot.db.fetchrow("SELECT * FROM votes WHERE user_id = $1", ctx.author.id)
        if check_vote and check_vote["vote_until"] and check_vote["vote_until"] > datetime.datetime.now().timestamp():
            return True
        if check_donor:
            return True
        guild = ctx.bot.get_guild(ctx.bot.logging_guild)
        if guild:
            member = guild.get_member(ctx.author.id)
            if member:
                role = guild.get_role(1228378828704055366)
                if role and role in member.roles:
                    return True
        await ctx.send_warning(f"You need [**donator**](https://evelina.bot/premium) perks or to have [**vote**](https://top.gg/bot/1242930981967757452/vote) to use this command")
        return False
    return check(predicate)

def has_premium():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM premium WHERE guild_id = $1", ctx.guild.id)
        if check:
            return True
        await ctx.send_warning(f"You need to have [**premium**](https://evelina.bot/premium) to use this command")
        return False
    return check(predicate)

"""
MUSIC PREDICATES
"""

def is_voice():
    async def predicate(ctx: EvelinaContext):
        if not ctx.author.voice:
            await ctx.send_warning("You are not in a voice channel")
            return False
        if ctx.guild.me.voice:
            if ctx.guild.me.voice.channel.id != ctx.author.voice.channel.id:
                await ctx.send_warning("You are not in the same voice channel as the bot")
                return False
        return True
    return check(predicate)

def bot_is_voice():
    async def predicate(ctx: EvelinaContext):
        if not ctx.guild.me.voice:
            await ctx.send_warning("The bot is not in a voice channel")
            return False
        if ctx.voice_client:
            if ctx.voice_client.connect != ctx:
                ctx.voice_client.connect = ctx
        return True
    return check(predicate)

def is_dj():
    async def predicate(ctx: EvelinaContext):
        record = await ctx.bot.db.fetchrow("SELECT role_id FROM music_dj WHERE guild_id = $1", ctx.guild.id)
        if record and record['role_id']:
            role = ctx.guild.get_role(record['role_id'])
            if role and role not in ctx.author.roles:
                await ctx.send_warning(f"You need the {role.mention} role to use this command.")
                return False
        return True
    return check(predicate)

def lastfm_user_exists():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM lastfm WHERE user_id = $1", ctx.author.id)
        if not check:
            await ctx.lastfm_send(f"You don't have a **Last.fm** account set.\n> Use `{ctx.clean_prefix}lastfm set` to login into your account.")
            return False
        return True
    return check(predicate)

"""
ECONOMY PREDICATES
"""

def create_account():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
        if not check:
            if ctx.author.created_at > datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14):
                await ctx.send_warning("You need to be on Discord for at least **14 days** to use this command")
                return False
            if ctx.author.avatar is None:
                await ctx.send_warning("Your account looks **suspicious**, you can't create an economy account")
                return False
            await ctx.bot.db.execute("INSERT INTO economy (user_id, cash, card) VALUES ($1, $2, $3)", ctx.author.id, 5000.00, 0.00)
            confirmed = asyncio.Future()
            async def yes_func(interaction: Interaction):
                await interaction.client.db.execute("UPDATE economy SET terms = $1 WHERE user_id = $2", True, interaction.user.id)
                await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: You accepted, you can now use the economy system"), view=None)
                confirmed.set_result(True)

            async def no_func(interaction: Interaction):
                await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: You rejected, you can't use the economy system"), view=None)
                confirmed.set_result(False)
            await ctx.confirmation_send(
                f"{emojis.QUESTION} {ctx.author.mention}: You need to accept the [**rules**](https://evelina.bot/economy) to use the economy system",
                yes_func=yes_func, no_func=no_func
            )
            return await confirmed
        elif check['terms'] is False:
            confirmed = asyncio.Future()
            async def yes_func(interaction: Interaction):
                await interaction.client.db.execute("UPDATE economy SET terms = $1 WHERE user_id = $2", True, interaction.user.id)
                await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: You accepted, you can now use the economy system"), view=None)
                confirmed.set_result(True)
            async def no_func(interaction: Interaction):
                await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: You rejected, you can't use the economy system"), view=None)
                confirmed.set_result(False)
            await ctx.confirmation_send(
                f"{emojis.QUESTION} {ctx.author.mention}: You need to accept the [**rules**](https://evelina.bot/economy) to use the economy system",
                yes_func=yes_func, no_func=no_func
            )
            return await confirmed
        elif check['cash'] < 0:
            await ctx.send_warning("You can't use the economy system with a negative balance.")
            return False
        return True
    return check(predicate)

def custom_humanize_date(dt):
    humanized = humanize.naturaltime(dt)
    if humanized.startswith('in '):
        return humanized[3:]
    elif ' from now' in humanized:
        return humanized.replace(' from now', '')
    return humanized

def daily_taken():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT daily FROM economy WHERE user_id = $1", ctx.author.id)
        if check:
            if check["daily"]:
                if datetime.datetime.now().timestamp() < check["daily"]:
                    await ctx.cooldown_send(f"You can run `{ctx.clean_prefix}daily` again **{ctx.bot.misc.humanize_date(datetime.datetime.fromtimestamp(check['daily']))}**")
                    return False
        return True
    return check(predicate)

def rob_taken():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT rob FROM economy WHERE user_id = $1", ctx.author.id)
        if check:
            if check["rob"]:
                if datetime.datetime.now().timestamp() < check["rob"]:
                    await ctx.cooldown_send(f"You can run `{ctx.clean_prefix}rob` again **{ctx.bot.misc.humanize_date(datetime.datetime.fromtimestamp(check['rob']))}**")
                    return False
        return True
    return check(predicate)

def work_taken():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT work FROM economy WHERE user_id = $1", ctx.author.id)
        if check:
            if check["work"]:
                if datetime.datetime.now().timestamp() < check["work"]:
                    await ctx.cooldown_send(f"You can run `{ctx.clean_prefix}work` again **{ctx.bot.misc.humanize_date(datetime.datetime.fromtimestamp(check['work']))}**")
                    return False
        return True
    return check(predicate)

def slut_taken():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT slut FROM economy WHERE user_id = $1", ctx.author.id)
        if check:
            if check["slut"]:
                if datetime.datetime.now().timestamp() < check["slut"]:
                    await ctx.cooldown_send(f"You can run `{ctx.clean_prefix}slut` again **{ctx.bot.misc.humanize_date(datetime.datetime.fromtimestamp(check['slut']))}**")
                    return False
        return True
    return check(predicate)

def bonus_taken():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT bonus FROM economy WHERE user_id = $1", ctx.author.id)
        if check:
            if check["bonus"]:
                if datetime.datetime.now().timestamp() < check["bonus"]:
                    await ctx.cooldown_send(f"You can run `{ctx.clean_prefix}bonus` again **{ctx.bot.misc.humanize_date(datetime.datetime.fromtimestamp(check['bonus']))}**")
                    return False
        return True
    return check(predicate)

def beg_taken():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT beg FROM economy WHERE user_id = $1", ctx.author.id)
        if check:
            if check["beg"]:
                if datetime.datetime.now().timestamp() < check["beg"]:
                    await ctx.cooldown_send(f"You can run `{ctx.clean_prefix}beg` again **{ctx.bot.misc.humanize_date(datetime.datetime.fromtimestamp(check['beg']))}**")
                    return False
        return True
    return check(predicate)

def quest_taken():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT quest FROM economy WHERE user_id = $1", ctx.author.id)
        if check:
            if check["quest"]:
                if datetime.datetime.now().timestamp() < check["quest"]:
                    await ctx.cooldown_send(f"You can run `{ctx.clean_prefix}quest start` again **{ctx.bot.misc.humanize_date(datetime.datetime.fromtimestamp(check['quest']))}**")
                    return False
        return True
    return check(predicate)

"""
VOICEMASTER PREDICATES
"""

def rename_cooldown():
    async def predicate(ctx: EvelinaContext):
        return await rename_vc_bucket(ctx.bot, ctx.author.voice.channel)
    return check(predicate)

async def check_in_voice_channel(ctx: EvelinaContext):
    if ctx.author.voice is None:
        await ctx.send_warning("You must be connected to a voice channel to use this command.")
        return False
    return True

async def check_owner(ctx: EvelinaContext):
    if not await check_in_voice_channel(ctx):
        return False
    check = await ctx.bot.db.fetchrow(
        "SELECT * FROM voicemaster_channels WHERE voice = $1 AND user_id = $2",
        ctx.author.voice.channel.id,
        ctx.author.id,
    )
    if check is None:
        await ctx.send_warning("You are not the owner of this voice channel")
        return True

async def check_voice(ctx: EvelinaContext):
    check = await ctx.bot.db.fetchrow("SELECT * FROM voicemaster WHERE guild_id = $1", ctx.guild.id)
    if check is not None:
        channeid = check[1]
        voicechannel = ctx.guild.get_channel(channeid)
        if voicechannel is None:
            await ctx.send_warning("The voice channel linked to the bot no longer exists")
            await ctx.bot.db.execute("DELETE FROM voicemaster WHERE guild_id = $1", ctx.guild.id)
            return True
        category = voicechannel.category
        if not await check_in_voice_channel(ctx):
            return True
        if check['category']:
            category_obj = ctx.guild.get_channel(check['category'])
            if ctx.author.voice.channel.category != category_obj:
                await ctx.send_warning("You are not in a voice channel created by the bot")
                return True
        else:
            if ctx.author.voice.channel.category != category:
                await ctx.send_warning("You are not in a voice channel created by the bot")
                return True

def is_vm():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM voicemaster WHERE guild_id = $1", ctx.guild.id)
        if check:
            raise BadArgument(f"VoiceMaster is **already** configured\n> Use `{ctx.clean_prefix}voicemaster unsetup` to reset it")
        return True
    return check(predicate)

def check_vc_owner():
    async def predicate(ctx: EvelinaContext):
        if not await check_in_voice_channel(ctx):
            return False
        if await check_voice(ctx) or await check_owner(ctx):
            return False
        return True
    return check(predicate)

"""
TICKET PREDICATES
"""

def get_ticket():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM ticket_opened WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, ctx.channel.id)
        if check is None:
            await ctx.send_warning("Command can only be used in a opened ticket")
            return False
        return True
    return check(predicate)

def manage_ticket():
    async def predicate(ctx: EvelinaContext):
        permitted_roles = []
        topic_roles_list = []
        global_roles_list = []
        ticket_topic = await ctx.bot.db.fetchval("SELECT topic FROM ticket_opened WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, ctx.channel.id)
        if ticket_topic:
            topic_support_roles = await ctx.bot.db.fetchval("SELECT support_roles FROM ticket_topics WHERE guild_id = $1 AND name = $2", ctx.guild.id, ticket_topic)
            if topic_support_roles and topic_support_roles != "[]":
                try:
                    topic_roles_list = json.loads(topic_support_roles)
                    if not isinstance(topic_roles_list, list):
                        return await ctx.send_warning(f"Unexpected data format for topic support roles.")
                    topic_roles_list = [int(role_id) for role_id in topic_roles_list]
                    permitted_roles += [role for role in ctx.guild.roles if role.id in topic_roles_list]
                    if any(role.id in [r.id for r in ctx.author.roles] for role in permitted_roles):
                        return True
                except json.JSONDecodeError:
                    return await ctx.send_warning("Invalid JSON format for topic support roles.")
            else:
                global_support_roles = await ctx.bot.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", ctx.guild.id)
                if global_support_roles:
                    try:
                        global_roles_list = json.loads(global_support_roles)
                        if not isinstance(global_roles_list, list):
                            return await ctx.send_warning("Unexpected data format for **default** support roles.")
                        global_roles_list = [int(role_id) for role_id in global_roles_list]
                        permitted_roles += [role for role in ctx.guild.roles if role.id in global_roles_list]
                    except json.JSONDecodeError:
                        return await ctx.send_warning("Invalid JSON format for **default** support roles.")
        if any(role.id in [r.id for r in ctx.author.roles] for role in permitted_roles):
            return True
        if permitted_roles:
            permitted_role_names = ', '.join([role.mention for role in permitted_roles])
            warning_message = f"Only members with the support role ({permitted_role_names}) or members with the `manage_channels` permission can manage tickets."
        else:
            warning_message = "Only members with the `manage_channels` permission can manage tickets."
        if not ctx.author.guild_permissions.manage_channels:
            await ctx.send_warning(warning_message)
            return False
        return True
    return check(predicate)

def close_ticket():
    async def predicate(ctx: EvelinaContext):
        permitted_roles = []
        topic_roles_list = []
        global_roles_list = []
        ticket_topic = await ctx.bot.db.fetchval("SELECT topic FROM ticket_opened WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, ctx.channel.id)
        if ticket_topic:
            topic_support_roles = await ctx.bot.db.fetchval("SELECT support_roles FROM ticket_topics WHERE guild_id = $1 AND name = $2", ctx.guild.id, ticket_topic)
            if topic_support_roles and topic_support_roles != "[]":
                try:
                    topic_roles_list = json.loads(topic_support_roles)
                    if not isinstance(topic_roles_list, list):
                        return await ctx.send_warning(f"Unexpected data format for topic support roles.")
                    topic_roles_list = [int(role_id) for role_id in topic_roles_list]
                    permitted_roles += [role for role in ctx.guild.roles if role.id in topic_roles_list]
                    if any(role.id in [r.id for r in ctx.author.roles] for role in permitted_roles):
                        return True
                except json.JSONDecodeError:
                    return await ctx.send_warning("Invalid JSON format for topic support roles.")
            else:
                global_support_roles = await ctx.bot.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", ctx.guild.id)
                if global_support_roles:
                    try:
                        global_roles_list = json.loads(global_support_roles)
                        if not isinstance(global_roles_list, list):
                            return await ctx.send_warning("Unexpected data format for **default** support roles.")
                        global_roles_list = [int(role_id) for role_id in global_roles_list]
                        permitted_roles += [role for role in ctx.guild.roles if role.id in global_roles_list]
                    except json.JSONDecodeError:
                        return await ctx.send_warning("Invalid JSON format for **default** support roles.")
        if any(role.id in [r.id for r in ctx.author.roles] for role in permitted_roles):
            return True
        if permitted_roles:
            permitted_role_names = ', '.join([role.mention for role in permitted_roles])
            warning_message = f"Only members with the support role ({permitted_role_names}) or members with the `manage_channels` permission can close tickets."
        else:
            warning_message = "Only members with the `manage_channels` permission can close tickets."
        if not ctx.author.guild_permissions.manage_channels:
            await ctx.send_warning(warning_message)
            return False
        return True
    return check(predicate)

def ticket_exists():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM ticket WHERE guild_id = $1", ctx.guild.id)
        if not check:
            await ctx.bot.db.execute("INSERT INTO ticket (guild_id) VALUES ($1)", ctx.guild.id)
        return True
    return check(predicate)

"""
MISC
"""

def is_development():
    async def predicate(ctx: EvelinaContext):
        guild = ctx.bot.get_guild(ctx.bot.logging_guild)
        if guild is None:
            return False
        member = guild.get_member(ctx.author.id)
        if member is None:
            return False
        role = guild.get_role(1237426196422328381)
        if role is None:
            return False
        if role not in member.roles:
            await ctx.send_warning("Command can be only used by **development** team\n> Be patient, it will be available for everyone soon")
            return False
        return True
    return check(predicate)

def is_afk():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM afk WHERE user_id = $1", ctx.author.id)
        return check is None
    return check(predicate)

def is_supporter():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM team_members WHERE user_id = $1 AND rank IN ('Supporter', 'Moderator', 'Manager', 'Developer')", ctx.author.id)
        if check:
            return True
        return False
    return check(predicate)

def is_moderator():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM team_members WHERE user_id = $1 AND rank IN ('Moderator', 'Manager', 'Developer')", ctx.author.id)
        if check:
            return True
        return False
    return check(predicate)

def is_manager():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM team_members WHERE user_id = $1 AND rank IN ('Manager', 'Developer')", ctx.author.id)
        if check:
            return True
        return False
    return check(predicate)

def is_developer():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM team_members WHERE user_id = $1 AND rank = 'Developer'", ctx.author.id)
        if check:
            return True
        elif ctx.author.id in ctx.bot.owner_ids:
            return True
        return False
    return check(predicate)

def whitelist_enabled():
    async def predicate(ctx: EvelinaContext):
        if not await ctx.bot.db.fetchrow("SELECT * FROM whitelist_module WHERE guild_id = $1", ctx.guild.id):
            await ctx.send_warning(f"Whitelist is **not** enabled\n> Use `{ctx.clean_prefix}whitelist enable` to enable it")
            return False
        return True
    return check(predicate)

def nsfw_channel():
    async def predicate(ctx: EvelinaContext):
        if ctx.channel.is_nsfw():
            return True
        else:
            await ctx.send_warning("This command can only be used in **NSFW** channels.")
            return False
    return check(predicate)

"""
SUGGESTION
"""

def suggestion_blacklisted():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT reason FROM suggestions_blacklist WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id)
        if check:
            await ctx.send_warning(f"You got blacklisted from creating suggestion.\n> **Reason:** {check['reason']}")
            return False
        return True
    return check(predicate)

"""
MODULES
"""

def suggestion_enabled():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT suggestion FROM modules WHERE guild_id = $1", ctx.guild.id)
        if not check or check['suggestion'] is False:
            await ctx.send_warning(f"Suggestion module is **not** enabled\n> Use `{ctx.clean_prefix}suggestion enable` to enable it")
            return False
        return True
    return check(predicate)

def suggestion_disabled():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT suggestion FROM modules WHERE guild_id = $1", ctx.guild.id)
        if check and check['suggestion'] is True:
            await ctx.send_warning(f"Suggestion module is **already** enabled\n> Use `{ctx.clean_prefix}suggestion disable` to disable it")
            return False
        return True
    return check(predicate)

def starboard_enabled():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT starboard FROM modules WHERE guild_id = $1", ctx.guild.id)
        if not check or check['starboard'] is False:
            await ctx.send_warning(f"Starboard module is **not** enabled\n> Use `{ctx.clean_prefix}starboard enable` to enable it")
            return False
        return True
    return check(predicate)

def starboard_disabled():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT starboard FROM modules WHERE guild_id = $1", ctx.guild.id)
        if check and check['starboard'] is True:
            await ctx.send_warning(f"Starboard module is **already** enabled\n> Use `{ctx.clean_prefix}starboard disable` to disable it")
            return False
        return True
    return check(predicate)

def clownboard_enabled():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT clownboard FROM modules WHERE guild_id = $1", ctx.guild.id)
        if not check or check['clownboard'] is False:
            await ctx.send_warning(f"Clownboard module is **not** enabled\n> Use `{ctx.clean_prefix}clownboard enable` to enable it")
            return False
        return True
    return check(predicate)

def clownboard_disabled():
    async def predicate(ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT clownboard FROM modules WHERE guild_id = $1", ctx.guild.id)
        if check and check['clownboard'] is True:
            await ctx.send_warning(f"Clownboard module is **already** enabled\n> Use `{ctx.clean_prefix}starboard disable` to disable it")
            return False
        return True
    return check(predicate)