from main import Evict
from typing import Union
from core.client.context import Context
from discord.ext import commands
from discord.ext.commands.core import has_permissions
from discord import Member, User, Embed
from discord.ui import Modal, TextInput, Button, View
import config

import datetime
import discord
import config
import humanize
from datetime import timedelta
from tools.conversion.embed1 import EmbedScript
from processors.moderation import process_mod_action, process_dm_script
import psutil
import asyncio

class Mod:
    def is_mod_configured():
        async def predicate(ctx: Context):
            if not ctx.command:
                return False
                
            required_perms = []
            for check in ctx.command.checks:
                if hasattr(check, 'perms'):
                    required_perms.extend(
                        perm for perm, value in check.perms.items() if value
                    )
            
            if required_perms:
                missing_perms = [
                    perm for perm in required_perms 
                    if not getattr(ctx.author.guild_permissions, perm)
                ]
                if missing_perms:
                    perm_name = missing_perms[0].replace('_', ' ').title()
                    await ctx.warn(f"You're missing the **{perm_name}** permission!")
                    return False

            check = await ctx.bot.db.fetchrow(
                "SELECT * FROM mod WHERE guild_id = $1", ctx.guild.id
            )

            if not check:
                await ctx.warn(
                    f"Moderation isn't **enabled** in this server. Enable it using `{ctx.clean_prefix}setme` command"
                )
                return False
                
            return True

        return commands.check(predicate)


class ModConfig:
    async def sendlogs(
        bot: Evict,
        action: str,
        author: Member,
        victim: Union[Member, User],
        reason: str,
        duration: Union[timedelta, int, None] = None,
        role: discord.Role = None
    ):
        try:  
            settings = await bot.db.fetchrow(
                "SELECT * FROM mod WHERE guild_id = $1",
                author.guild.id
            )
            
            action_data = {
                'action': action,
                'duration': duration
            }
            
            processed_action = await bot.loop.run_in_executor(
                None,
                bot.process_pool.apply,
                process_mod_action,
                (action_data,)
            )

            if not settings:
                return

            res = await bot.db.fetchrow(
                "SELECT count FROM cases WHERE guild_id = $1", author.guild.id
            )
            
            if not res:
                await bot.db.execute(
                    "INSERT INTO cases (guild_id, count) VALUES ($1, $2)",
                    author.guild.id, 0
                )
                case = 1
            else:
                case = int(res["count"]) + 1

            await bot.db.execute(
                "UPDATE cases SET count = $1 WHERE guild_id = $2", case, author.guild.id
            )

            duration_value = (
                int(duration.total_seconds())
                if isinstance(duration, timedelta)
                else duration
            )

            await bot.db.execute(
                """
                INSERT INTO history.moderation 
                (guild_id, case_id, user_id, moderator_id, action, reason, duration, role_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                author.guild.id,
                case,
                victim.id,
                author.id,
                action,
                reason,
                duration_value,
                role.id if role else None
            )

            if settings.get("channel_id"):
                embed = Embed(
                    timestamp=datetime.datetime.now(),
                    color=(
                        discord.Color.green() if action in ['role_add', 'unban', 'untimeout', 'unjail']
                        else discord.Color.red() if action in ['ban', 'kick', 'timeout', 'jail']
                        else discord.Color.green() if action == 'role_add'
                        else discord.Color.red() if action == 'role_remove'
                        else discord.Color.blurple()
                    )
                )
                embed.set_author(name="Modlog Entry", icon_url=author.display_avatar)
                
                if action in ['role_add', 'role_remove']:
                    embed.add_field(
                        name="Information",
                        value=f"**Case #{case}** | {action}\n**User**: {victim} (`{victim.id}`)\n**Moderator**: {author} (`{author.id}`)\n**Role**: {role.mention}\n**Reason**: {reason}",
                    )
                else:
                    duration_text = f"\n**Duration**: {humanize.naturaldelta(duration)}" if duration else ""
                    embed.add_field(
                        name="Information",
                        value=f"**Case #{case}** | {action}\n**User**: {victim} (`{victim.id}`)\n**Moderator**: {author} (`{author.id}`)\n**Reason**: {reason}{duration_text}",
                    )

                try:
                    await author.guild.get_channel(int(settings["channel_id"])).send(embed=embed)
                except:
                    pass

            if processed_action['should_dm'] and settings.get('dm_enabled'):
                mutual_guilds = [g for g in bot.guilds if victim in g.members]
                if not mutual_guilds and action not in ['ban', 'kick', 'hardban']:
                    return

                if action in ['ban', 'kick']:
                    try:
                        script = settings.get(f"dm_{action.lower()}")
                        
                        if script and script.lower() != 'true':
                            script_obj = EmbedScript(script)
                            await script_obj.send(
                                victim,
                                guild=author.guild,
                                moderator=author,
                                reason=reason,
                                duration=duration,
                                role=role
                            )
                        else:
                            if action in ['role_add', 'role_remove']:
                                embed = Embed(
                                    title=f"Role {'Added' if action == 'role_add' else 'Removed'}",
                                    color=discord.Color.green() if action == 'role_add' else discord.Color.red(),
                                    timestamp=datetime.datetime.now()
                                )
                                embed.add_field(
                                    name="Server",
                                    value=author.guild.name,
                                    inline=True
                                )
                                embed.add_field(
                                    name="Role",
                                    value=role.name,
                                    inline=True
                                )
                                embed.add_field(
                                    name="Moderator",
                                    value=str(author),
                                    inline=True
                                )
                                if reason:
                                    embed.add_field(
                                        name="Reason",
                                        value=reason,
                                        inline=False
                                    )
                            else:
                                duration_text = f"{humanize.naturaldelta(duration)}" if duration else ""
                                embed = Embed(
                                    title=processed_action['title'].title(),
                                    description=duration_text if duration else "",
                                    color=discord.Color.green() if processed_action['is_unaction'] else discord.Color.red(),
                                    timestamp=datetime.datetime.now()
                                )
                                embed.add_field(
                                    name=f"You have been {processed_action['title']} in",
                                    value=author.guild.name,
                                    inline=True
                                )
                                embed.add_field(
                                    name="Moderator",
                                    value=str(author),
                                    inline=True
                                )
                                embed.add_field(
                                    name="Reason",
                                    value=reason,
                                    inline=True
                                )

                            appeal_config = await bot.db.fetchrow(
                                "SELECT * FROM appeal_config WHERE guild_id = $1",
                                author.guild.id
                            )

                            view = View()
                            if appeal_config:
                                if appeal_config.get('direct_appeal', False) or action in ['timeout', 'jail']:
                                    view = View()
                                    view.add_item(AppealButton(modal=True, action_type=action, guild_id=author.guild.id))
                                elif action in ['ban', 'kick']:
                                    appeal_server = bot.get_guild(appeal_config['appeal_server_id'])
                                    if appeal_server and not appeal_config.get('direct_appeal', False):
                                        appeal_channel = appeal_server.get_channel(appeal_config['appeal_channel_id'])
                                        if appeal_channel:
                                            try:
                                                invite = await appeal_channel.create_invite(max_uses=1)
                                                view = View()
                                                view.add_item(Button(
                                                    label="Join Appeal Server",
                                                    url=invite.url,
                                                    style=discord.ButtonStyle.link
                                                ))
                                                embed.add_field(
                                                    name="Appeal",
                                                    value=f"You can appeal this action in our appeal server",
                                                    inline=False
                                                )
                                            except:
                                                embed.add_field(
                                                    name="Appeal",
                                                    value="To appeal, please join discord.gg/evict to get mutual server access with the bot",
                                                    inline=False
                                                )

                            await victim.send(embed=embed, view=view)

                    except Exception as e:
                        import traceback
                else:
                    asyncio.create_task(
                        send_non_critical_dm(
                            bot, settings, action, author, victim, 
                            reason, duration, role, processed_action
                        )
                    )

            try:
                properties = {
                    "action": action,
                    "guild_id": str(author.guild.id),
                    "guild_name": author.guild.name,
                    "moderator_id": str(author.id),
                    "moderator_name": str(author),
                    "moderator_roles": [str(role.id) for role in author.roles[1:]],
                    "target_id": str(victim.id),
                    "target_name": str(victim),
                    "reason": reason,
                    "case_id": case,
                    "duration_seconds": (
                        int(duration.total_seconds()) if isinstance(duration, timedelta)
                        else duration if isinstance(duration, int)
                        else None
                    ),
                    "role_id": str(role.id) if role else None,
                    "role_name": role.name if role else None,
                    "dm_success": False,
                    "system_metrics": {
                        "cpu_percent": psutil.cpu_percent(),
                        "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024,
                        "thread_count": psutil.Process().num_threads()
                    },
                    "guild_metrics": {
                        "member_count": author.guild.member_count,
                        "case_count": case,
                        "verification_level": str(author.guild.verification_level),
                        "boost_level": author.guild.premium_tier
                    }
                }

            except Exception as e:
                print(f"Error in modlog: {e}")
                traceback.print_exc()

        except Exception as e:
            print(f"Error in modlog: {e}")
            traceback.print_exc()

async def send_non_critical_dm(bot, settings, action, author, victim, reason, duration, role, processed_action):
    """Handles sending DMs for non-critical moderation actions"""
    try:
        script = settings.get(f"dm_{action.lower()}")
        
        if script and script.lower() != 'true':
            script_obj = EmbedScript(script)
            await script_obj.send(
                victim,
                guild=author.guild,
                moderator=author,
                reason=reason,
                duration=duration,
                role=role
            )
        else:
            if action in ['role_add', 'role_remove']:
                embed = Embed(
                    title=f"Role {'Added' if action == 'role_add' else 'Removed'}",
                    color=discord.Color.green() if action == 'role_add' else discord.Color.red(),
                    timestamp=datetime.datetime.now()
                )
                embed.add_field(name="Server", value=author.guild.name, inline=True)
                embed.add_field(name="Role", value=role.name, inline=True)
                embed.add_field(name="Moderator", value=str(author), inline=True)
                if reason:
                    embed.add_field(name="Reason", value=reason, inline=False)
            else:
                duration_text = f"{humanize.naturaldelta(duration)}" if duration else ""
                embed = Embed(
                    title=processed_action['title'].title(),
                    description=duration_text if duration else "",
                    color=discord.Color.green() if processed_action['is_unaction'] else discord.Color.red(),
                    timestamp=datetime.datetime.now()
                )
                embed.add_field(name=f"You have been {processed_action['title']} in", value=author.guild.name, inline=True)
                embed.add_field(name="Moderator", value=str(author), inline=True)
                embed.add_field(name="Reason", value=reason, inline=True)

            appeal_config = await bot.db.fetchrow(
                "SELECT * FROM appeal_config WHERE guild_id = $1",
                author.guild.id
            )

            view = View()
            if appeal_config:
                if appeal_config.get('direct_appeal', False) or action in ['timeout', 'jail']:
                    view = View()
                    view.add_item(AppealButton(modal=True, action_type=action, guild_id=author.guild.id))
                elif action in ['ban', 'kick']:
                    appeal_server = bot.get_guild(appeal_config['appeal_server_id'])
                    if appeal_server and not appeal_config.get('direct_appeal', False):
                        appeal_channel = appeal_server.get_channel(appeal_config['appeal_channel_id'])
                        if appeal_channel:
                            try:
                                invite = await appeal_channel.create_invite(max_uses=1)
                                view = View()
                                view.add_item(Button(
                                    label="Join Appeal Server",
                                    url=invite.url,
                                    style=discord.ButtonStyle.link
                                ))
                                embed.add_field(
                                    name="Appeal",
                                    value=f"You can appeal this action in our appeal server",
                                    inline=False
                                )
                            except:
                                embed.add_field(
                                    name="Appeal",
                                    value="To appeal, please join discord.gg/evict to get mutual server access with the bot",
                                    inline=False
                                )

            await victim.send(embed=embed, view=view)

    except Exception as e:
        pass

class ClearMod(discord.ui.View):
    def __init__(self, ctx: Context):
        super().__init__()
        self.ctx = ctx
        self.status = False

    @discord.ui.button(emoji=config.EMOJIS.CONTEXT.APPROVE)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.ctx.author.id:
            return await interaction.warn("You are not the author of this embed")

        check = await interaction.client.db.fetchrow(
            "SELECT * FROM mod WHERE guild_id = $1", interaction.guild.id
        )

        channelid = check["channel_id"]
        roleid = check["role_id"]
        logsid = check["jail_id"]

        channel = interaction.guild.get_channel(channelid)
        role = interaction.guild.get_role(roleid)
        logs = interaction.guild.get_channel(logsid)

        try:
            await channel.delete()

        except:
            pass

        try:
            await role.delete()

        except:
            pass

        try:
            await logs.delete()

        except:
            pass

        await interaction.client.db.execute(
            "DELETE FROM mod WHERE guild_id = $1", interaction.guild.id
        )

        self.status = True

        return await interaction.response.edit_message(
            view=None,
            embed=Embed(
                description=f"I have **disabled** the jail system.",
            ),
        )

    @discord.ui.button(emoji=config.EMOJIS.CONTEXT.DENY)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.ctx.author.id:

            return await interaction.warn("You are not the author of this embed")

        await interaction.response.edit_message(
            embed=Embed(description="Aborting action"), view=None
        )
        self.status = True

    async def on_timeout(self) -> None:
        if self.status == False:
            for item in self.children:
                item.disabled = True

            await self.message.edit(view=self)

class InviteButton(discord.ui.View):
    def __init__(self, url: str):
        super().__init__()
        self.add_item(discord.ui.Button(
            emoji=config.EMOJIS.SOCIAL.WEBSITE,
            url=url,
            style=discord.ButtonStyle.link
        ))

class AppealButton(Button):
    def __init__(self, modal: bool = False, action_type: str = None, guild_id: int = None):
        super().__init__(
            label="Appeal",
            style=discord.ButtonStyle.primary,
            custom_id="appeal_button"
        )
        self.guild_id = guild_id
        self.modal = modal
        self.action_type = action_type

    async def callback(self, interaction: discord.Interaction):
        if self.modal:
            config_cog = interaction.client.get_cog("Config")
            if not config_cog:
                await interaction.response.send_message("Appeal system unavailable", ephemeral=True)
                return

            try:
                appeal_config = await interaction.client.db.fetchrow(
                    "SELECT * FROM appeal_config WHERE guild_id = $1",
                    self.guild_id
                )
                
                if not appeal_config:
                    await interaction.response.send_message("Appeal system not configured", ephemeral=True)
                    return

                appeal_modal = await config_cog.get_appeal_modal(
                    self.guild_id,
                    self.action_type
                )
                await interaction.response.send_modal(appeal_modal)
            except Exception as e:
                await interaction.response.send_message("Error creating appeal form", ephemeral=True)
