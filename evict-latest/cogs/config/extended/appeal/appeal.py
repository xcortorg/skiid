from tools import CompositeMetaClass, MixinMeta
from discord.ext.commands import Context, group, has_permissions
from discord import TextChannel, Embed, ButtonStyle, Member, User
from discord.ui import Modal, TextInput, View, Button
import discord
import json
from datetime import datetime
from typing import Union
import logging
import humanize

log = logging.getLogger(__name__)

class AppealButton(Button):
    def __init__(self, modal: bool = False, action_type: str = None, guild_id: int = None):
        super().__init__(
            label="Appeal",
            style=discord.ButtonStyle.primary,
            custom_id="appeal_button"
        )
        self.modal = modal
        self.action_type = action_type
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        try:
            if self.modal:
                config_cog = interaction.client.get_cog("Config")
                if not config_cog:
                    await interaction.response.send_message("Appeal system unavailable", ephemeral=True)
                    return

                config = await interaction.client.db.fetchrow(
                    "SELECT * FROM appeal_config WHERE guild_id = $1",
                    self.guild_id or interaction.guild_id
                )

                if not config:
                    await interaction.response.send_message("Appeal system not configured", ephemeral=True)
                    return

                if not config['direct_appeal']:
                    original_guild = interaction.client.get_guild(self.guild_id)
                    if not original_guild:
                        await interaction.response.send_message("Cannot verify ban status", ephemeral=True)
                        return

                    try:
                        ban = await original_guild.fetch_ban(interaction.user)
                        if not ban:
                            await interaction.response.send_message(
                                "You are not banned from the server!", 
                                ephemeral=True
                            )
                            return
                    except discord.NotFound:
                        await interaction.response.send_message(
                            "You are not banned from the server!", 
                            ephemeral=True
                        )
                        return

                try:
                    appeal_modal = await config_cog.get_appeal_modal(
                        self.guild_id or interaction.guild_id,
                        self.action_type
                    )
                    await interaction.response.send_modal(appeal_modal)
                except Exception as e:
                    log.error(f"Error creating appeal modal: {e}", exc_info=True)
                    await interaction.response.send_message("Error creating appeal form", ephemeral=True)
        except Exception as e:
            log.error(f"Error in appeal button callback: {e}", exc_info=True)
            await interaction.response.send_message("An error occurred", ephemeral=True)

class AppealModal(Modal):
    def __init__(self, questions: list, appeal_id: int = None):
        super().__init__(title="Appeal Form")
        
        for question in questions:
            self.add_item(
                TextInput(
                    label=question['question'][:45],  # Discord has a 45 char limit for labels
                    style=discord.TextStyle.paragraph if question.get('long', False) else discord.TextStyle.short,
                    required=question.get('required', True),
                    placeholder="Your response...",
                    max_length=4000 if question.get('long', False) else 1024
                )
            )

    async def on_submit(self, interaction: discord.Interaction):
        config_cog = interaction.client.get_cog("Config")
        if not config_cog:
            return await interaction.response.send_message("Appeal system unavailable", ephemeral=True)

        responses = [item.value for item in self.children]
        
        try:
            await config_cog.create_appeal(
                interaction.guild_id,
                interaction.user.id,
                responses,
                getattr(self, 'action_type', None)
            )
            await interaction.response.send_message("Your appeal has been submitted!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("Failed to submit appeal", ephemeral=True)

class AppealSetup(Modal, title="Appeal Setup"):
    def __init__(self):
        super().__init__()
        self.add_item(
            TextInput(
                label="Appeal Channel Name",
                placeholder="appeals",
                default="appeals",
                required=True
            )
        )
        self.add_item(
            TextInput(
                label="Logs Channel Name",
                placeholder="appeal-logs",
                default="appeal-logs",
                required=True
            )
        )

class SetupView(View):
    def __init__(self, ctx: Context):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None

    @discord.ui.button(label="Direct Appeals", style=discord.ButtonStyle.primary)
    async def direct(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("This isn't your setup!", ephemeral=True)
        self.value = "direct"
        self.stop()

    @discord.ui.button(label="Appeal Server", style=discord.ButtonStyle.secondary)
    async def server(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("This isn't your setup!", ephemeral=True)
        self.value = "server"
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

class AppealActionButton(Button):
    def __init__(self, action: str, appeal_id: int, quick: bool = False):
        style = discord.ButtonStyle.green if "accept" in action.lower() else discord.ButtonStyle.red
        super().__init__(
            label=f"{'Quick ' if quick else ''}{action}",
            style=style,
            custom_id=f"appeal_{action.lower()}_{appeal_id}_{quick}"
        )
        self.appeal_id = appeal_id
        self.quick = quick
        self.action = action.lower()

    async def callback(self, interaction: discord.Interaction):
        config_cog = interaction.client.get_cog("Config")
        if not config_cog:
            return await interaction.response.send_message("Appeal system unavailable", ephemeral=True)

        if not await config_cog._check_appeal_perms(interaction):
            return await interaction.response.send_message("You don't have permission to handle appeals", ephemeral=True)

        if self.quick:
            await config_cog.handle_appeal(
                interaction, 
                self.appeal_id, 
                self.action, 
                "No reason provided (Quick Action)"
            )
            return

        modal = AppealActionModal(self.appeal_id, self.action)
        await interaction.response.send_modal(modal)

class AppealActionModal(Modal):
    def __init__(self, appeal_id: int, action: str):
        super().__init__(title=f"Appeal {action.title()}")
        self.appeal_id = appeal_id
        self.action = action
        self.add_item(
            TextInput(
                label="Reason",
                style=discord.TextStyle.paragraph,
                required=True,
                placeholder="Enter your reason..."
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        config_cog = interaction.client.get_cog("Config")
        if not config_cog:
            return await interaction.response.send_message("Appeal system unavailable", ephemeral=True)

        reason = self.children[0].value
        await config_cog.handle_appeal(interaction, self.appeal_id, self.action, reason)

class HistoryButton(Button):
    def __init__(self, user_id: int, guild_id: int):
        super().__init__(
            label="View History",
            style=discord.ButtonStyle.secondary,
            custom_id=f"appeal_history_{user_id}_{guild_id}"
        )
        self.user_id = user_id
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        cases = await interaction.client.db.fetch(
            """
            SELECT * FROM history.moderation 
            WHERE user_id = $1 AND guild_id = $2 
            ORDER BY case_id DESC
            """,
            self.user_id,
            self.guild_id,
        )

        if not cases:
            return await interaction.response.send_message("No moderation history found", ephemeral=True)

        entries = []
        for case in cases:
            try:
                mod = await interaction.client.fetch_user(case["moderator_id"])
                mod_str = f"{mod} (`{mod.id}`)"
            except:
                mod_str = f"Unknown Moderator (`{case['moderator_id']}`)"

            duration_str = (
                f"\nDuration: {humanize.naturaldelta(case['duration'])}"
                if case["duration"]
                else ""
            )
            timestamp = f"<t:{int(case['timestamp'].timestamp())}:f>"

            entries.append(
                f"**Case #{case['case_id']}**\n"
                f"Action: {case['action']}\n"
                f"Moderator: {mod_str}\n"
                f"Date: {timestamp}\n"
                f"Reason: {case['reason']}"
                f"{duration_str}"
            )

        embed = Embed(title=f"Moderation History")
        embed.set_footer(text=f"{len(cases)} total cases")
        
        embed.description = "\n\n".join(entries[:3])
        if len(entries) > 3:
            embed.set_footer(text=f"Showing 3/{len(cases)} cases")

        await interaction.response.send_message(embed=embed, ephemeral=True)

class AppealActionsView(View):
    def __init__(self, appeal_id: int, user_id: int, guild_id: int):
        super().__init__(timeout=None)  
        self.add_item(AppealActionButton("Accept", appeal_id, quick=True))
        self.add_item(AppealActionButton("Accept", appeal_id))
        self.add_item(AppealActionButton("Deny", appeal_id, quick=True))
        self.add_item(AppealActionButton("Deny", appeal_id))
        self.add_item(HistoryButton(user_id, guild_id))

    async def create_appeal(self, guild_id: int, user_id: int, responses: list, action_type: str = None):
        """Create a new appeal and notify moderators"""
        appeal = await self.bot.db.fetchrow(
            """
            INSERT INTO appeals 
            (guild_id, user_id, action_type, status)
            VALUES ($1, $2, $3, 'pending')
            RETURNING id
            """,
            guild_id,
            user_id,
            action_type
        )

        config = await self.bot.db.fetchrow(
            "SELECT * FROM appeal_config WHERE guild_id = $1",
            guild_id
        )

        if not config:
            return

        user = self.bot.get_user(user_id)
        guild = self.bot.get_guild(guild_id)
        
        embed = Embed(
            description="A new appeal has been submitted.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.set_author(
            name=f"Appeal #{appeal['id']} | {user}",
            icon_url=user.display_avatar.url
        )
        
        user_info = [
            f"**User:** {user.mention} (`{user.id}`)",
            f"**Created:** <t:{int(user.created_at.timestamp())}:R>",
            f"**Server:** {guild.name}"
        ]
        
        if action_type:
            user_info.append(f"**Action:** {action_type.title()}")
            
        embed.add_field(
            name="User Information",
            value="\n".join(user_info),
            inline=False
        )

        try:
            questions = json.loads(config['questions']) if isinstance(config['questions'], str) else config['questions']
            
            responses_text = []
            for question, response in zip(questions, responses):
                responses_text.append(
                    f"**{question['question']}**\n{response[:1024] if response else 'No response'}"
                )
            
            embed.add_field(
                name="Appeal Responses",
                value="\n\n".join(responses_text),
                inline=False
            )

            logs_channel = None
            if config['direct_appeal']:
                logs_channel = self.bot.get_channel(config['logs_channel_id'])
            else:
                appeal_server = self.bot.get_guild(config['appeal_server_id'])
                if appeal_server:
                    logs_channel = appeal_server.get_channel(config['logs_channel_id'])

            if logs_channel:
                view = AppealActionsView(appeal['id'], user_id, guild_id)
                await logs_channel.send(embed=embed, view=view)
            else:
                return

        except Exception as e:
            import traceback

class Appeal(MixinMeta, metaclass=CompositeMetaClass):
    """Appeal system for the bot"""

    default_questions = [
        {
            "question": "Why were you punished?",
            "required": True,
            "long": False
        },
        {
            "question": "Why should we accept your appeal?",
            "required": True,
            "long": True
        },
        {
            "question": "What will you do differently?",
            "required": True,
            "long": True
        }
    ]

    async def handle_appeal(self, interaction: discord.Interaction, appeal_id: int, action: str, reason: str):
        """Handle an appeal action (accept/deny)"""
        try:
            if action == "accept":
                await self.appeal_accept(interaction, appeal_id, reason=reason)
            else:
                await self.appeal_reject(interaction, appeal_id, reason=reason)
            
            try:
                if interaction.message and interaction.message.components:  
                    view = interaction.message.view or View() 
                    for item in view.children:
                        item.disabled = True
                    await interaction.message.edit(view=view)
            except Exception as e:
                log.error(f"Failed to disable buttons: {e}")
                
        except Exception as e:
            log.error(f"Error handling appeal: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred while handling the appeal", ephemeral=True)

    async def appeal_accept(self, ctx_or_interaction, appeal_id: int, *, reason: str = "No reason provided"):
        """Accept an appeal"""
        if not await self._check_appeal_perms(ctx_or_interaction):
            return

        if isinstance(ctx_or_interaction, discord.Interaction):
            guild_id = ctx_or_interaction.guild_id
            author = ctx_or_interaction.user
            warn = lambda msg: ctx_or_interaction.response.send_message(msg, ephemeral=True)
            approve = lambda msg: ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            guild_id = ctx_or_interaction.guild.id
            author = ctx_or_interaction.author
            warn = ctx_or_interaction.warn
            approve = ctx_or_interaction.approve

        appeal = await self.bot.db.fetchrow(
            """
            UPDATE appeals 
            SET status = 'accepted', 
                moderator_id = $1::bigint,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $2 AND status = 'pending'
            RETURNING *
            """,
            author.id,
            appeal_id
        )

        if not appeal:
            return await warn("Appeal not found or already handled!")

        user = self.bot.get_user(appeal['user_id'])
        if not user:
            return await warn("Could not find the user who appealed!")

        reversed_actions = []
        try:
            if appeal['action_type']:
                if appeal['action_type'] == 'ban':
                    try:
                        guild = self.bot.get_guild(appeal['guild_id'])
                        await guild.unban(user, reason=f"Appeal accepted: {reason}")
                        reversed_actions.append('ban')
                    except discord.NotFound:
                        pass
                elif appeal['action_type'] == 'timeout':
                    guild = self.bot.get_guild(appeal['guild_id'])
                    member = guild.get_member(user.id)
                    if member:
                        await member.timeout(None, reason=f"Appeal accepted: {reason}")
                        reversed_actions.append('timeout')
            else:
                guild = self.bot.get_guild(appeal['guild_id'])
                try:
                    await guild.unban(user, reason=f"Appeal accepted: {reason}")
                    reversed_actions.append('ban')
                except discord.NotFound:
                    pass

                member = guild.get_member(user.id)
                if member and member.is_timed_out():
                    await member.timeout(None, reason=f"Appeal accepted: {reason}")
                    reversed_actions.append('timeout')

        except discord.HTTPException as e:
            await warn(f"Failed to reverse some actions: {e}")

        embed = Embed(
            title="Appeal Accepted",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Appeal ID", value=appeal_id, inline=True)
        embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=True)
        embed.add_field(name="Moderator", value=author.mention, inline=True)
        if reversed_actions:
            embed.add_field(name="Actions Reversed", value=", ".join(a.title() for a in reversed_actions), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

        try:
            guild = self.bot.get_guild(appeal['guild_id'])
            invite = None
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).create_instant_invite:
                    invite = await channel.create_invite(max_age=86400)  
                    break

            view = View()
            if invite:
                view.add_item(Button(
                    label=f"Join {guild.name}", 
                    url=str(invite),
                    style=discord.ButtonStyle.url
                ))
            
            await user.send(embed=embed, view=view)
        except:
            pass

        success_msg = f"Accepted appeal #{appeal_id}"
        if reversed_actions:
            success_msg += f" and reversed: {', '.join(reversed_actions)}"
        await approve(success_msg)

    async def appeal_reject(self, ctx_or_interaction, appeal_id: int, *, reason: str = "No reason provided"):
        """Reject an appeal"""
        if not await self._check_appeal_perms(ctx_or_interaction):
            return

        if isinstance(ctx_or_interaction, discord.Interaction):
            guild_id = ctx_or_interaction.guild_id
            author = ctx_or_interaction.user
            warn = lambda msg: ctx_or_interaction.response.send_message(msg, ephemeral=True)
            approve = lambda msg: ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            guild_id = ctx_or_interaction.guild.id
            author = ctx_or_interaction.author
            warn = ctx_or_interaction.warn
            approve = ctx_or_interaction.approve

        appeal = await self.bot.db.fetchrow(
            """
            UPDATE appeals 
            SET status = 'rejected', 
                moderator_id = $1::bigint,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $2 AND status = 'pending'
            RETURNING *
            """,
            author.id,
            appeal_id
        )

        if not appeal:
            return await warn("Appeal not found or already handled!")

        user = self.bot.get_user(appeal['user_id'])
        if not user:
            return await warn("Could not find the user who appealed!")

        embed = Embed(
            title="Appeal Rejected",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Appeal ID", value=appeal_id, inline=True)
        embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=True)
        embed.add_field(name="Moderator", value=author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

        try:
            await user.send(embed=embed)
        except:
            pass

        await approve(f"Rejected appeal #{appeal_id}")

    async def _check_appeal_perms(self, ctx_or_interaction) -> bool:
        """Check if user has permission to handle appeals"""
        if isinstance(ctx_or_interaction, discord.Interaction):
            guild_id = ctx_or_interaction.guild_id
            author = ctx_or_interaction.user
            warn = lambda msg: ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            guild_id = ctx_or_interaction.guild.id
            author = ctx_or_interaction.author
            warn = ctx_or_interaction.warn

        config = await self.bot.db.fetchrow(
            "SELECT appeal_server_id, bypass_roles, direct_appeal FROM appeal_config WHERE guild_id = $1",
            guild_id
        )
        
        if not config:
            config = await self.bot.db.fetchrow(
                "SELECT appeal_server_id, bypass_roles, direct_appeal FROM appeal_config WHERE appeal_server_id = $1",
                guild_id
            )
            if not config:
                await warn("Appeal system not setup!")
                return False

        if config['bypass_roles']:
            user_roles = [role.id for role in author.roles]
            if any(role_id in user_roles for role_id in config['bypass_roles']):
                return True

        if config['direct_appeal']:
            return author.guild_permissions.moderate_members

        appeal_server = self.bot.get_guild(config['appeal_server_id'])
        if not appeal_server:
            await warn("Appeal server not found!")
            return False

        appeal_member = appeal_server.get_member(author.id)
        if not appeal_member or not appeal_member.guild_permissions.moderate_members:
            await warn("You need moderate members permission in both servers!")
            return False

        return author.guild_permissions.moderate_members

    async def create_appeal(self, guild_id: int, user_id: int, responses: list, action_type: str = None):
        """Create a new appeal and notify moderators"""
        appeal = await self.bot.db.fetchrow(
            """
            INSERT INTO appeals 
            (guild_id, user_id, action_type, status)
            VALUES ($1, $2, $3, 'pending')
            RETURNING id
            """,
            guild_id,
            user_id,
            action_type
        )

        config = await self.bot.db.fetchrow(
            "SELECT * FROM appeal_config WHERE guild_id = $1",
            guild_id
        )

        if not config:
            return

        user = self.bot.get_user(user_id)
        guild = self.bot.get_guild(guild_id)
        
        embed = Embed(
            description="A new appeal has been submitted.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.set_author(
            name=f"Appeal #{appeal['id']} | {user}",
            icon_url=user.display_avatar.url
        )
        
        user_info = [
            f"**User:** {user.mention} (`{user.id}`)",
            f"**Created:** <t:{int(user.created_at.timestamp())}:R>",
            f"**Server:** {guild.name}"
        ]
        
        if action_type:
            user_info.append(f"**Action:** {action_type.title()}")
            
        embed.add_field(
            name="User Information",
            value="\n".join(user_info),
            inline=False
        )

        try:
            questions = json.loads(config['questions']) if isinstance(config['questions'], str) else config['questions']
            
            responses_text = []
            for question, response in zip(questions, responses):
                responses_text.append(
                    f"**{question['question']}**\n{response[:1024] if response else 'No response'}"
                )
            
            embed.add_field(
                name="Appeal Responses",
                value="\n\n".join(responses_text),
                inline=False
            )

            logs_channel = None
            if config['direct_appeal']:
                logs_channel = self.bot.get_channel(config['logs_channel_id'])
            else:
                appeal_server = self.bot.get_guild(config['appeal_server_id'])
                if appeal_server:
                    logs_channel = appeal_server.get_channel(config['logs_channel_id'])

            if logs_channel:
                view = AppealActionsView(appeal['id'], user_id, guild_id)
                await logs_channel.send(embed=embed, view=view)
            else:
                return

        except Exception as e:
            import traceback

    async def get_appeal_modal(self, guild_id: int, action_type: str = None) -> AppealModal:
        """Get the appeal modal with custom questions for the guild"""
        config = await self.bot.db.fetchrow(
            "SELECT questions FROM appeal_config WHERE guild_id = $1",
            guild_id
        )
        
        if not config:
            questions = self.default_questions
        else:
            try:
                questions = json.loads(config['questions']) if isinstance(config['questions'], str) else config['questions']
            except:
                questions = self.default_questions
        
        modal = AppealModal(questions)
        modal.action_type = action_type 
        return modal

    @group(invoke_without_command=True)
    async def appeal(self, ctx: Context):
        """Appeal system"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @appeal.command(name="setup")
    @has_permissions(administrator=True)
    async def appeal_setup(self, ctx: Context):
        """Interactive setup for the appeal system"""
        existing_appeal_server = await self.bot.db.fetchrow(
            "SELECT guild_id FROM appeal_config WHERE appeal_server_id = $1",
            ctx.guild.id
        )
        
        if existing_appeal_server:
            return await ctx.warn(
                "This server is already being used as an appeal server! "
                f"It cannot be configured for appeals itself."
            )

        config = await self.bot.db.fetchrow(
            "SELECT * FROM appeal_config WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if config:
            prompt = await ctx.prompt(
                "Appeal system is already configured! Would you like to:\n"
                "- Reset the current configuration\n"
                "- Set up a new configuration\n"
                "**This will delete existing appeal channels!**"
            )
            
            if not prompt:
                return await ctx.send("Setup cancelled.")
                
            if not config['direct_appeal']:
                appeal_server = self.bot.get_guild(config['appeal_server_id'])
                if appeal_server:
                    appeal_channel = appeal_server.get_channel(config['appeal_channel_id'])
                    logs_channel = appeal_server.get_channel(config['logs_channel_id'])
                    
                    if appeal_channel:
                        try:
                            await appeal_channel.delete()
                        except:
                            pass
                    if logs_channel:
                        try:
                            await logs_channel.delete()
                        except:
                            pass

        embed = Embed(
            title="Appeal System Setup",
            description="How would you like to handle appeals?\n\n"
                      "**Direct Appeals**: Appeals are handled via DM\n"
                      "**Appeal Server**: Appeals are handled in a separate server",
            color=ctx.color
        )
        
        view = SetupView(ctx)
        view.message = await ctx.send(embed=embed, view=view)
        await view.wait()
        
        if view.value is None:
            return await ctx.warn("Setup timed out!")

        if view.value == "direct":
            logs_channel = await ctx.guild.create_text_channel(
                "appeal-logs",
                overwrites={
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
            )
            
            await self.bot.db.execute(
                """
                INSERT INTO appeal_config 
                (guild_id, logs_channel_id, direct_appeal)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id) 
                DO UPDATE SET 
                    logs_channel_id = $2,
                    direct_appeal = $3
                """,
                ctx.guild.id,
                logs_channel.id,
                True
            )

            embed = Embed(
                title="Setup Complete!",
                description=f"Direct appeals enabled!\nLogs Channel: {logs_channel.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

        else:
            embed = Embed(
                title="Appeal Server Setup",
                description="Please enter the ID of the server you want to use for appeals.\n"
                          "You must have administrator permissions in that server.",
                color=ctx.color
            )
            await ctx.send(embed=embed)

            try:
                msg = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                    timeout=30
                )
            except TimeoutError:
                return await ctx.warn("Setup timed out!")

            try:
                appeal_server_id = int(msg.content)
            except ValueError:
                return await ctx.warn("That's not a valid server ID!")

            appeal_server = self.bot.get_guild(appeal_server_id)
            if not appeal_server:
                return await ctx.warn("I'm not in that server!")

            appeal_member = appeal_server.get_member(ctx.author.id)
            if not appeal_member or not appeal_member.guild_permissions.administrator:
                return await ctx.warn("You need administrator permissions in the appeal server!")

            appeal_channel = await appeal_server.create_text_channel("appeals")
            logs_channel = await appeal_server.create_text_channel(
                "appeal-logs",
                overwrites={
                    appeal_server.default_role: discord.PermissionOverwrite(read_messages=False),
                    appeal_server.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
            )

            embed = Embed(
                title="Appeal System",
                description="Click the button below to submit an appeal.",
                color=discord.Color.blurple()
            )
            view = View(timeout=None)
            view.add_item(AppealButton(modal=True, action_type=None, guild_id=ctx.guild.id))
            await appeal_channel.send(embed=embed, view=view)

            await self.bot.db.execute(
                """
                INSERT INTO appeal_config 
                (guild_id, appeal_server_id, appeal_channel_id, logs_channel_id, direct_appeal)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (guild_id) 
                DO UPDATE SET 
                    appeal_server_id = $2,
                    appeal_channel_id = $3,
                    logs_channel_id = $4,
                    direct_appeal = $5
                """,
                ctx.guild.id,
                appeal_server_id,
                appeal_channel.id,
                logs_channel.id,
                False
            )

            embed = Embed(
                title="Setup Complete!",
                description=f"Appeal server setup complete!\n"
                          f"Appeal Channel: {appeal_channel.mention}\n"
                          f"Logs Channel: {logs_channel.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

    @appeal.command(name="search")
    @has_permissions(moderate_members=True)
    async def appeal_search(self, ctx: Context, *, query: str):
        """Search appeals by user ID, flag, or action type"""
        try:
            user_id = int(query)
            where_clause = "user_id = $3"
        except ValueError:
            where_clause = "action_type ILIKE $3 OR $3 = ANY(flags)"
            query = f"%{query}%"

        appeals = await self.bot.db.fetch(
            f"""
            SELECT * FROM appeals 
            WHERE guild_id = $1 
            AND {where_clause}
            ORDER BY created_at DESC
            LIMIT 10
            """,
            ctx.guild.id,
            query
        )

        if not appeals:
            return await ctx.warn("No appeals found matching your search!")

        embed = Embed(
            title="Appeal Search Results",
            color=ctx.color
        )

        for appeal in appeals:
            user = self.bot.get_user(appeal['user_id'])
            flags = appeal['flags'] or []
            embed.add_field(
                name=f"Appeal #{appeal['id']} ({appeal['status']})",
                value=(
                    f"User: {user.mention if user else appeal['user_id']}\n"
                    f"Action: {appeal['action_type']}\n"
                    f"Created: <t:{int(appeal['created_at'].timestamp())}:R>\n"
                    f"Flags: {', '.join(flags) if flags else 'None'}"
                ),
                inline=False
            )

        await ctx.send(embed=embed)

    @appeal.command(name="stats")
    @has_permissions(moderate_members=True)
    async def appeal_stats(self, ctx: Context):
        """View appeal statistics"""
        stats = await self.bot.db.fetchrow(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'accepted') as accepted,
                COUNT(*) FILTER (WHERE status = 'rejected') as rejected,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(DISTINCT moderator_id) as unique_mods,
                ARRAY_AGG(DISTINCT action_type) as action_types
            FROM appeals
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        if not stats or stats['total'] == 0:
            return await ctx.warn("No appeals data found!")

        embed = Embed(
            title="Appeal Statistics",
            color=ctx.color
        )
        embed.add_field(name="Total Appeals", value=stats['total'], inline=True)
        embed.add_field(name="Pending", value=stats['pending'], inline=True)
        embed.add_field(name="Accepted", value=stats['accepted'], inline=True)
        embed.add_field(name="Rejected", value=stats['rejected'], inline=True)
        embed.add_field(name="Unique Users", value=stats['unique_users'], inline=True)
        embed.add_field(name="Unique Moderators", value=stats['unique_mods'], inline=True)
        embed.add_field(
            name="Action Types",
            value=", ".join(stats['action_types']) if stats['action_types'] else "None",
            inline=False
        )

        await ctx.send(embed=embed)

    @appeal.command(name="bulk")
    @has_permissions(administrator=True)
    async def appeal_bulk(self, ctx: Context, status: str, *, reason: str):
        """Bulk accept/reject pending appeals"""
        if status.lower() not in ['accept', 'reject']:
            return await ctx.warn("Status must be 'accept' or 'reject'!")

        pending = await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM appeals WHERE guild_id = $1 AND status = 'pending'",
            ctx.guild.id
        )

        if not pending:
            return await ctx.warn("No pending appeals found!")

        result = await self.bot.db.execute(
            """
            UPDATE appeals 
            SET status = $1, 
                moderator_id = $2,
                updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = $3 
            AND status = 'pending'
            RETURNING id, user_id
            """,
            f"{status.lower()}ed",
            ctx.author.id,
            ctx.guild.id
        )

        if not result:
            return await ctx.warn("No pending appeals found!")

        count = len(result)
        await ctx.approve(f"Bulk {status.lower()}ed {count} appeals with reason: {reason}")

        for record in result:
            user = self.bot.get_user(record['user_id'])
            if user:
                embed = Embed(
                    title=f"Appeal {status.title()}ed",
                    color=discord.Color.green() if status.lower() == 'accept' else discord.Color.red()
                )
                embed.add_field(name="Appeal ID", value=record['id'])
                embed.add_field(name="Reason", value=reason)
                try:
                    await user.send(embed=embed)
                except:
                    pass

    @appeal.command(name="mode")
    @has_permissions(administrator=True)
    async def appeal_mode(self, ctx: Context, direct: bool):
        """
        Set whether appeals should be handled directly in DMs
        
        If True: All appeals (including bans/kicks) will be handled via DM
        If False: Banned/kicked users will need to join the appeal server
        """
        await self.bot.db.execute(
            """
            UPDATE appeal_config 
            SET direct_appeal = $1 
            WHERE guild_id = $2
            """,
            direct,
            ctx.guild.id
        )

        mode = "direct DM" if direct else "appeal server"
        await ctx.approve(f"Appeals will now be handled via {mode}")

    @appeal.command(name="status")
    @has_permissions(administrator=True)
    async def appeal_status(self, ctx: Context):
        """Check appeal system status"""
        config = await self.bot.db.fetchrow(
            "SELECT * FROM appeal_config WHERE guild_id = $1",
            ctx.guild.id
        )

        if not config:
            return await ctx.warn("Appeal system is not setup!")

        embed = Embed(
            title="Appeal System Status",
            color=ctx.color
        )
        embed.add_field(
            name="Appeal Mode",
            value="Direct DM" if config['direct_appeal'] else "Appeal Server",
            inline=False
        )

        if not config['direct_appeal']:
            appeal_server = self.bot.get_guild(config['appeal_server_id'])
            if appeal_server:
                appeal_channel = appeal_server.get_channel(config['appeal_channel_id'])
                logs_channel = appeal_server.get_channel(config['logs_channel_id'])
                
                embed.add_field(
                    name="Appeal Server",
                    value=f"{appeal_server.name} (`{appeal_server.id}`)",
                    inline=False
                )
                embed.add_field(
                    name="Appeal Channel",
                    value=appeal_channel.mention if appeal_channel else "Not found",
                    inline=True
                )
                embed.add_field(
                    name="Logs Channel",
                    value=logs_channel.mention if logs_channel else "Not found",
                    inline=True
                )
            else:
                embed.add_field(name="Warning", value="Appeal server not found!", inline=False)
        else:
            logs_channel = ctx.guild.get_channel(config['logs_channel_id'])
            embed.add_field(
                name="Logs Channel",
                value=logs_channel.mention if logs_channel else "Not found",
                inline=True
            )

        await ctx.send(embed=embed)

    @appeal.group(name="questions")
    @has_permissions(administrator=True)
    async def appeal_questions(self, ctx: Context):
        """Manage appeal questions"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @appeal_questions.command(name="add")
    async def questions_add(self, ctx: Context, *, question: str):
        """Add a new appeal question"""
        raw_data = await self.bot.db.fetchval(
            "SELECT questions FROM appeal_config WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not raw_data:
            return await ctx.warn("Appeal system not setup!")

        questions = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        questions.append({
            "question": question,
            "required": True,
            "long": False
        })

        await self.bot.db.execute(
            """
            UPDATE appeal_config 
            SET questions = $1::jsonb 
            WHERE guild_id = $2
            """,
            json.dumps(questions),
            ctx.guild.id
        )

        await ctx.approve(f"Added question: {question}")

    @appeal_questions.command(name="remove")
    async def questions_remove(self, ctx: Context, index: int):
        """Remove an appeal question by index"""
        raw_data = await self.bot.db.fetchval(
            "SELECT questions FROM appeal_config WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not raw_data:
            return await ctx.warn("Appeal system not setup!")

        questions = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        if index < 0 or index >= len(questions):
            return await ctx.warn("Invalid question index!")

        removed = questions.pop(index)
        await self.bot.db.execute(
            """
            UPDATE appeal_config 
            SET questions = $1::jsonb 
            WHERE guild_id = $2
            """,
            json.dumps(questions),
            ctx.guild.id
        )

        await ctx.approve(f"Removed question: {removed['question']}")

    @appeal_questions.command(name="list")
    async def questions_list(self, ctx: Context):
        """List current appeal questions"""
        raw_data = await self.bot.db.fetchval(
            "SELECT questions FROM appeal_config WHERE guild_id = $1",
            ctx.guild.id
        )
        
        
        if not raw_data:
            return await ctx.warn("No questions found!")

        try:
            questions = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        except Exception as e:
            return await ctx.warn("Error parsing questions")

        embed = Embed(
            title="Appeal Questions",
            color=ctx.color
        )

        try:
            for i, q in enumerate(questions):
                embed.add_field(
                    name=f"Question {i+1}",
                    value=q.get('question', str(q)),
                    inline=False
                )
        except Exception as e:
            return await ctx.warn(f"Error displaying questions: {e}")

        await ctx.send(embed=embed)

    @appeal.command(name="flag")
    @has_permissions(moderate_members=True)
    async def appeal_flag(self, ctx: Context, appeal_id: int, flag: str):
        """Add a flag to an appeal"""
        if not await self._check_appeal_perms(ctx):
            return
        appeal = await self.bot.db.fetchrow(
            """
            UPDATE appeals 
            SET flags = array_append(flags, $1)
            WHERE id = $2 AND guild_id = $3
            RETURNING *
            """,
            flag.lower(),
            appeal_id,
            ctx.guild.id
        )

        if not appeal:
            return await ctx.warn("Appeal not found!")

        await ctx.approve(f"Added flag `{flag}` to appeal #{appeal_id}")

    @appeal.command(name="list")
    @has_permissions(moderate_members=True)
    async def appeal_list(self, ctx: Context, status: str = "pending"):
        """List appeals by status"""
        if not await self._check_appeal_perms(ctx):
            return
        appeals = await self.bot.db.fetch(
            """
            SELECT * FROM appeals 
            WHERE guild_id = $1 AND status = $2
            ORDER BY created_at DESC
            LIMIT 10
            """,
            ctx.guild.id,
            status.lower()
        )

        if not appeals:
            return await ctx.warn(f"No {status} appeals found!")

        embed = Embed(
            title=f"{status.title()} Appeals",
            color=ctx.color
        )

        for appeal in appeals:
            user = self.bot.get_user(appeal['user_id'])
            flags = appeal['flags'] or []
            embed.add_field(
                name=f"Appeal #{appeal['id']}",
                value=(
                    f"User: {user.mention if user else appeal['user_id']}\n"
                    f"Action: {appeal['action_type']}\n"
                    f"Created: <t:{int(appeal['created_at'].timestamp())}:R>\n"
                    f"Flags: {', '.join(flags) if flags else 'None'}"
                ),
                inline=False
            )

        await ctx.send(embed=embed) 

    @appeal.group(name="bypass")
    @has_permissions(administrator=True)
    async def bypass_roles(self, ctx: Context):
        """Manage appeal bypass roles"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @bypass_roles.command(name="add")
    async def bypass_add(self, ctx: Context, role: discord.Role):
        """Add a role that can bypass appeal permissions"""
        await self.bot.db.execute(
            """
            UPDATE appeal_config 
            SET bypass_roles = array_append(bypass_roles, $1)
            WHERE guild_id = $2
            """,
            role.id,
            ctx.guild.id
        )
        await ctx.approve(f"Added {role.mention} to appeal bypass roles")

    @bypass_roles.command(name="remove")
    async def bypass_remove(self, ctx: Context, role: discord.Role):
        """Remove a role from appeal bypass"""
        await self.bot.db.execute(
            """
            UPDATE appeal_config 
            SET bypass_roles = array_remove(bypass_roles, $1)
            WHERE guild_id = $2
            """,
            role.id,
            ctx.guild.id
        )
        await ctx.approve(f"Removed {role.mention} from appeal bypass roles")

    @bypass_roles.command(name="list")
    async def bypass_list(self, ctx: Context):
        """List appeal bypass roles"""
        config = await self.bot.db.fetchrow(
            "SELECT bypass_roles FROM appeal_config WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not config or not config['bypass_roles']:
            return await ctx.warn("No bypass roles configured!")

        roles = [ctx.guild.get_role(role_id) for role_id in config['bypass_roles']]
        roles = [role.mention for role in roles if role]  

        embed = Embed(
            title="Appeal Bypass Roles",
            description="\n".join(roles) if roles else "No valid bypass roles found",
            color=ctx.color
        )
        await ctx.send(embed=embed) 

    @appeal.command(name="view")
    @has_permissions(moderate_members=True)
    async def appeal_view(self, ctx: Context, appeal_id: int):
        """View details of a specific appeal"""
        if not await self._check_appeal_perms(ctx):
            return

        appeal = await self.bot.db.fetchrow(
            """
            SELECT a.*, 
                   h.reason as action_reason,
                   h.moderator_id as action_moderator_id
            FROM appeals a
            LEFT JOIN history.moderation h ON 
                h.guild_id = a.guild_id AND 
                h.user_id = a.user_id AND 
                h.action = a.action_type
            WHERE a.id = $1 AND a.guild_id = $2
            """,
            appeal_id,
            ctx.guild.id
        )

        if not appeal:
            return await ctx.warn("Appeal not found!")

        user = self.bot.get_user(appeal['user_id'])
        action_mod = self.bot.get_user(appeal['action_moderator_id']) if appeal['action_moderator_id'] else None
        mod = self.bot.get_user(appeal['moderator_id']) if appeal['moderator_id'] else None

        embed = Embed(
            title=f"Appeal #{appeal_id}",
            color=ctx.color,
            timestamp=appeal['created_at']
        )
        embed.add_field(name="User", value=f"{user} (`{user.id}`)" if user else f"Unknown (`{appeal['user_id']}`)", inline=True)
        embed.add_field(name="Status", value=appeal['status'].title(), inline=True)
        embed.add_field(name="Action Type", value=appeal['action_type'] or "Unknown", inline=True)
        
        if action_mod:
            embed.add_field(name="Action Moderator", value=f"{action_mod} (`{action_mod.id}`)", inline=True)
        if appeal['action_reason']:
            embed.add_field(name="Action Reason", value=appeal['action_reason'], inline=False)
        
        if mod:
            embed.add_field(name="Handled By", value=f"{mod} (`{mod.id}`)", inline=True)
        
        if appeal['flags']:
            embed.add_field(name="Flags", value=", ".join(appeal['flags']), inline=False)

        await ctx.send(embed=embed)

    @appeal.command(name="history")
    @has_permissions(moderate_members=True)
    async def appeal_history(self, ctx: Context, user: Union[Member, User]):
        """View appeal history for a user"""
        if not await self._check_appeal_perms(ctx):
            return

        appeals = await self.bot.db.fetch(
            """
            SELECT * FROM appeals 
            WHERE guild_id = $1 AND user_id = $2
            ORDER BY created_at DESC
            """,
            ctx.guild.id,
            user.id
        )

        if not appeals:
            return await ctx.warn(f"No appeal history found for {user}")

        embed = Embed(
            title=f"Appeal History for {user}",
            color=ctx.color
        )

        for appeal in appeals:
            value = (
                f"Status: {appeal['status'].title()}\n"
                f"Action: {appeal['action_type'] or 'Unknown'}\n"
                f"Created: <t:{int(appeal['created_at'].timestamp())}:R>\n"
                f"Flags: {', '.join(appeal['flags']) if appeal['flags'] else 'None'}"
            )
            embed.add_field(
                name=f"Appeal #{appeal['id']}",
                value=value,
                inline=False
            )

        await ctx.send(embed=embed)

    @appeal.command(name="pending")
    @has_permissions(moderate_members=True)
    async def appeal_pending(self, ctx: Context):
        """View all pending appeals"""
        if not await self._check_appeal_perms(ctx):
            return

        appeals = await self.bot.db.fetch(
            """
            SELECT * FROM appeals 
            WHERE guild_id = $1 AND status = 'pending'
            ORDER BY created_at ASC
            """,
            ctx.guild.id
        )

        if not appeals:
            return await ctx.warn("No pending appeals!")

        embed = Embed(
            title="Pending Appeals",
            color=ctx.color
        )

        for appeal in appeals:
            user = self.bot.get_user(appeal['user_id'])
            value = (
                f"User: {user.mention if user else appeal['user_id']}\n"
                f"Action: {appeal['action_type'] or 'Unknown'}\n"
                f"Created: <t:{int(appeal['created_at'].timestamp())}:R>\n"
                f"Flags: {', '.join(appeal['flags']) if appeal['flags'] else 'None'}"
            )
            embed.add_field(
                name=f"Appeal #{appeal['id']}",
                value=value,
                inline=False
            )

        await ctx.send(embed=embed) 
        
    @appeal.group(name="template")
    @has_permissions(administrator=True)
    async def appeal_template(self, ctx: Context):
        """Manage appeal response templates"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @appeal_template.command(name="add")
    async def template_add(self, ctx: Context, name: str, *, response: str):
        """Add a response template"""
        await self.bot.db.execute(
            """
            INSERT INTO appeal_templates (guild_id, name, response)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, name) 
            DO UPDATE SET response = $3
            """,
            ctx.guild.id,
            name.lower(),
            response
        )
        await ctx.approve(f"Added template `{name}`")

    @appeal_template.command(name="remove")
    async def template_remove(self, ctx: Context, name: str):
        """Remove a response template"""
        result = await self.bot.db.execute(
            """
            DELETE FROM appeal_templates 
            WHERE guild_id = $1 AND name = $2
            """,
            ctx.guild.id,
            name.lower()
        )
        if result == "DELETE 0":
            return await ctx.warn(f"Template `{name}` not found!")
        await ctx.approve(f"Removed template `{name}`")

    @appeal_template.command(name="list")
    async def template_list(self, ctx: Context):
        """List response templates"""
        templates = await self.bot.db.fetch(
            "SELECT name, response FROM appeal_templates WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not templates:
            return await ctx.warn("No templates found!")

        embed = Embed(title="Appeal Response Templates", color=ctx.color)
        for template in templates:
            embed.add_field(
                name=template['name'],
                value=template['response'][:1024],
                inline=False
            )
        await ctx.send(embed=embed)

    @appeal.command(name="use")
    @has_permissions(moderate_members=True)
    async def appeal_use_template(self, ctx: Context, appeal_id: int, template_name: str):
        """Use a template to respond to an appeal"""
        if not await self._check_appeal_perms(ctx):
            return

        template = await self.bot.db.fetchrow(
            """
            SELECT response FROM appeal_templates 
            WHERE guild_id = $1 AND name = $2
            """,
            ctx.guild.id,
            template_name.lower()
        )

        if not template:
            return await ctx.warn(f"Template `{template_name}` not found!")

        appeal = await self.bot.db.fetchrow(
            "SELECT user_id FROM appeals WHERE id = $1 AND guild_id = $2",
            appeal_id,
            ctx.guild.id
        )

        if not appeal:
            return await ctx.warn("Appeal not found!")

        user = self.bot.get_user(appeal['user_id'])
        if user:
            embed = Embed(
                title="Appeal Response",
                description=template['response'],
                color=ctx.color
            )
            try:
                await user.send(embed=embed)
                await ctx.approve(f"Sent template response to {user}")
            except:
                await ctx.warn(f"Couldn't DM {user}")

    @appeal.command(name="reset")
    @has_permissions(administrator=True)
    async def appeal_reset(self, ctx: Context):
        """Reset appeal system configuration"""
        config = await self.bot.db.fetchrow(
            "SELECT * FROM appeal_config WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not config:
            return await ctx.warn("Appeal system is not configured!")
            
        prompt = await ctx.prompt(
            "Are you sure you want to reset the appeal system? This will:\n"
            "- Delete all appeal channels\n"
            "- Remove all configuration\n"
            "- Clear appeal questions\n"
            "**This action cannot be undone!**"
        )
        
        if not prompt:
            return await ctx.send("Reset cancelled.")

        appeal_server = self.bot.get_guild(config['appeal_server_id'])
        if appeal_server:
            if config['appeal_channel_id']:
                appeal_channel = appeal_server.get_channel(config['appeal_channel_id'])
                if appeal_channel:
                    try:
                        await appeal_channel.delete(reason="Appeal system reset")
                    except Exception as e:
                        await ctx.warn(f"Could not delete appeal channel: {e}")
            
            if config['logs_channel_id']:
                logs_channel = appeal_server.get_channel(config['logs_channel_id'])
                if logs_channel:
                    try:
                        await logs_channel.delete(reason="Appeal system reset")
                    except Exception as e:
                        await ctx.warn(f"Could not delete logs channel: {e}")

        await self.bot.db.execute(
            "DELETE FROM appeal_config WHERE guild_id = $1",
            ctx.guild.id
        )
        
        await ctx.approve("Appeal system has been reset!")