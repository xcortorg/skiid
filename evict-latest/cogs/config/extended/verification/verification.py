import discord
import logging
import aiohttp
import json
import random
import string
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import asyncio

from discord.ext.commands import group, command, has_permissions
from discord.ext import commands
from discord import Embed, Message

from typing import Optional, Tuple

from core.client.context import Context
from tools import CompositeMetaClass, MixinMeta

log = logging.getLogger(__name__)

class Verification(MixinMeta, metaclass=CompositeMetaClass):
    """
    Server verification and member screening system.
    """
    
    @group(
        name="verify",
        invoke_without_command=True,
        description="View or manage server verification settings."
    )
    @has_permissions(administrator=True)
    async def verify(self, ctx: Context) -> Message:
        """View current verification settings for the server."""
        if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
            return
            
        settings = await self.bot.db.fetchrow(
            """
            SELECT * FROM guild_verification
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if not settings:
            embed = Embed(
                title="Verification Settings",
                description="Verification is not set up for this server.\nUse `verify setup` to configure verification.",
                color=ctx.color
            )
            return await ctx.send(embed=embed)
            
        embed = Embed(
            title="Verification Settings",
            color=ctx.color
        )
        
        level_names = {
            1: "Email Verification",
            2: "OAuth2 Verification",
            3: "CAPTCHA Verification",
            4: "Custom Questions"
        }
        
        embed.add_field(
            name="Verification Level",
            value=level_names.get(settings['level'], "Unknown"),
            inline=True
        )
        
        embed.add_field(
            name="Auto-kick Timer",
            value=f"{settings['kick_after']} minutes" if settings['kick_after'] else "Disabled",
            inline=True
        )
        
        embed.add_field(
            name="Anti-alt Detection",
            value="Enabled" if settings['antialt'] else "Disabled",
            inline=True
        )
        
        embed.add_field(
            name="Rate Limit",
            value=f"{settings['ratelimit']} attempts per hour" if settings['ratelimit'] else "Disabled",
            inline=True
        )
        
        return await ctx.send(embed=embed)

    @verify.command(name="remove")
    @has_permissions(administrator=True)
    async def verify_remove(self, ctx: Context) -> Message:
        """Remove verification setup from the server."""
        result = await self.bot.db.execute(
            """
            DELETE FROM guild_verification
            WHERE guild_id = $1
            RETURNING verified_role_id
            """,
            ctx.guild.id
        )
        
        if not result:
            return await ctx.warn("Verification is not set up in this server")
            
        role_id = result[0]['verified_role_id']
        if role_id:
            role = ctx.guild.get_role(role_id)
            if role and role.managed is False:
                try:
                    await role.delete(reason="Verification system removed")
                except discord.Forbidden:
                    pass
                
        return await ctx.approve("Verification system has been removed from this server")

    @verify.command(name="setup")
    @has_permissions(administrator=True)
    async def verify_setup(self, ctx: Context) -> Message:
        """Set up the verification system."""
        if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
            return
            
        settings = await self.bot.db.fetchrow(
            """
            SELECT * FROM guild_verification
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if settings:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="Continue Setup",
                style=discord.ButtonStyle.green,
                custom_id="continue"
            ))
            view.add_item(discord.ui.Button(
                label="Cancel",
                style=discord.ButtonStyle.red,
                custom_id="cancel"
            ))
            
            msg = await ctx.send(
                "⚠️ Verification is already set up for this server. Would you like to reconfigure it?",
                view=view
            )
            
            try:
                interaction = await self.bot.wait_for(
                    "interaction",
                    check=lambda i: i.message.id == msg.id and i.user.id == ctx.author.id,
                    timeout=30
                )
                
                if interaction.data["custom_id"] == "cancel":
                    await msg.edit(content="Setup cancelled.", view=None)
                    return
                    
                await msg.delete()
            except TimeoutError:
                await msg.edit(content="Setup timed out.", view=None)
                return
        
        embed = Embed(
            title="Verification Setup",
            description=(
                "Welcome to the verification setup wizard! First, choose where you want verification to take place:\n\n"
                "🎮 **Discord Verification**\n"
                "- Simple button press\n"
                "- Word selection\n"
                "- Math problems\n"
                "- Emoji selection\n"
                "- Word Captcha\n\n"
                "🌐 **Web Verification**\n"
                "- Email verification\n"
                "- OAuth2 verification\n"
                "- CAPTCHA verification\n"
                "- Custom questions"
            ),
            color=ctx.color
        )
        
        platform_view = VerificationPlatformSelect(ctx)
        msg = await ctx.send(embed=embed, view=platform_view)
        
        try:
            platform = await platform_view.wait_for_selection()
            print(f"Selected platform: {platform}")
            if platform is None:
                await msg.edit(content="Setup timed out.", embed=None, view=None)
                return
        except TimeoutError:
            await msg.edit(content="Setup timed out.", embed=None, view=None)
            return
            
        await msg.edit(view=None)
        
        if platform == "discord":
            print("Discord platform selected")  
            embed = Embed(
                title="Verification Channel",
                description=(
                    "Select a channel for the verification process.\n\n"
                    "This channel will:\n"
                    "- Contain the verification message\n"
                    "- Be where users verify\n"
                    "- Need to be visible to new members\n\n"
                    "*Make sure unverified members can see this channel*"
                ),
                color=ctx.color
            )
            
            channel_view = VerificationChannelSelect(ctx)
            channel_msg = await ctx.send(embed=embed, view=channel_view)
            
            try:
                verification_channel_id = await channel_view.wait_for_selection()
                print(f"Selected channel ID: {verification_channel_id}")
                if verification_channel_id is None:
                    await channel_msg.edit(content="Setup timed out.", embed=None, view=None)
                    return
            except TimeoutError:
                await channel_msg.edit(content="Setup timed out.", embed=None, view=None)
                return
            
            await channel_msg.edit(view=None)
        
        view = VerificationLevelSelect(ctx, platform)
        embed = Embed(
            title="Verification Method",
            description=(
                "Select a verification method:\n\n" +
                ("**Web Verification Options:**\n"
                 "1️⃣ Email Verification - Users verify through email\n"
                 "2️⃣ OAuth2 Verification - Users verify through services like Google\n"
                 "3️⃣ CAPTCHA Verification - Simple human verification\n"
                 "4️⃣ Custom Questions - Users answer your custom questions"
                 if platform == "web" else
                 "**Discord Verification Options:**\n"
                 "1️⃣ Simple Button - One-click verification\n"
                 "2️⃣ Word Selection - Choose the correct word\n"
                 "3️⃣ Math Problem - Solve a simple math equation\n"
                 "4️⃣ Emoji Selection - Select the correct emoji\n"
                 "5️⃣ Word Captcha - Type the text from the image"
                 )
            ),
            color=ctx.color
        )
        
        msg = await ctx.send(embed=embed, view=view)
        
        try:
            level = await view.wait_for_selection()
            if level is None:
                await msg.edit(content="Setup timed out.", embed=None, view=None)
                return
        except TimeoutError:
            await msg.edit(content="Setup timed out.", embed=None, view=None)
            return
            
        await msg.edit(view=None)
        
        embed = Embed(
            title="Auto-kick Configuration",
            description=(
                "Would you like to automatically kick members who don't verify within a specific time?\n\n"
                "**Options:**\n"
                "- ✅ Enable auto-kick and set timer\n"
                "- ❌ Disable auto-kick\n\n"
                "*Members will not be kicked if this is disabled.*"
            ),
            color=ctx.color
        )
        
        view = AutoKickSelect(ctx)
        msg = await ctx.send(embed=embed, view=view)
        
        try:
            kick_after = await view.wait_for_selection()
            if kick_after is None:
                await msg.edit(content="Setup timed out.", embed=None, view=None)
                return
        except TimeoutError:
            await msg.edit(content="Setup timed out.", embed=None, view=None)
            return
            
        await msg.edit(view=None)
        
        embed = Embed(
            title="Rate Limit Configuration",
            description=(
                "How many verification attempts should users be allowed per hour?\n\n"
                "**Options:**\n"
                "- Set a number between 1-10\n"
                "- 0 to disable rate limiting\n\n"
                "*This helps prevent verification spam.*"
            ),
            color=ctx.color
        )
        
        view = RateLimitSelect(ctx)
        msg = await ctx.send(embed=embed, view=view)
        
        try:
            ratelimit = await view.wait_for_selection()
            if ratelimit is None:
                await msg.edit(content="Setup timed out.", embed=None, view=None)
                return
        except TimeoutError:
            await msg.edit(content="Setup timed out.", embed=None, view=None)
            return
            
        await msg.edit(view=None)
        
        embed = Embed(
            title="Anti-alt Configuration",
            description=(
                "Would you like to enable anti-alt detection?\n\n"
                "This will prevent new accounts from verifying based on:\n"
                "- Account age\n"
                "- Previous verification attempts\n"
                "- Suspicious patterns\n\n"
                "*This helps prevent alt account abuse.*"
            ),
            color=ctx.color
        )
        
        view = AntiAltSelect(ctx)
        msg = await ctx.send(embed=embed, view=view)
        
        try:
            antialt = await view.wait_for_selection()
            if antialt is None:
                await msg.edit(content="Setup timed out.", embed=None, view=None)
                return
        except TimeoutError:
            await msg.edit(content="Setup timed out.", embed=None, view=None)
            return
            
        await msg.edit(view=None)
        
        prevent_vpn = False
        if platform == "web":
            embed = Embed(
                title="VPN Prevention Configuration",
                description=(
                    "Would you like to prevent users using VPNs/Proxies from verifying?\n\n"
                    "This will check for:\n"
                    "- VPN connections\n"
                    "- Proxy servers\n"
                    "- Tor exit nodes\n\n"
                    "*This helps prevent abuse and bypassing restrictions.*"
                ),
                color=ctx.color
            )
            
            view = VPNSelect(ctx)
            msg = await ctx.send(embed=embed, view=view)
            
            try:
                prevent_vpn = await view.wait_for_selection()
                if prevent_vpn is None:
                    await msg.edit(content="Setup timed out.", embed=None, view=None)
                    return
            except TimeoutError:
                await msg.edit(content="Setup timed out.", embed=None, view=None)
                return
                
            await msg.edit(view=None)
        
        embed = Embed(
            title="Role Configuration",
            description=(
                "Select a role to give to verified members, or create a new one.\n\n"
                "The role should be below my highest role for me to assign it."
            ),
            color=ctx.color
        )
        
        view = RoleSelect(ctx)
        msg = await ctx.send(embed=embed, view=view)
        
        try:
            role_id = await view.wait_for_selection()
            if role_id is None:
                await msg.edit(content="Setup timed out.", embed=None, view=None)
                return
        except TimeoutError:
            await msg.edit(content="Setup timed out.", embed=None, view=None)
            return
            
        await msg.edit(view=None)
        
        embed = Embed(
            title="Log Channel Configuration",
            description=(
                "Select a channel for verification logs and notifications.\n\n"
                "This channel will receive:\n"
                "- Manual verification requests\n"
                "- Verification attempt logs\n"
                "- System notifications"
            ),
            color=ctx.color
        )
        
        view = LogChannelSelect(ctx)
        msg = await ctx.send(embed=embed, view=view)
        
        try:
            log_channel_id = await view.wait_for_selection()
            if log_channel_id is None:
                await msg.edit(content="Setup timed out.", embed=None, view=None)
                return
        except TimeoutError:
            await msg.edit(content="Setup timed out.", embed=None, view=None)
            return
            
        await msg.edit(view=None)
        
        await self.bot.db.execute(
            """
            UPDATE guild_verification
            SET log_channel_id = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            log_channel_id
        )
        
        platform_str = str(platform)  

        if platform == "web":
            await self.bot.db.execute(
                """
                INSERT INTO guild_verification (
                    guild_id, platform, level, kick_after, ratelimit, antialt, prevent_vpn, verified_role_id, log_channel_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (guild_id) DO UPDATE SET
                    platform = $2,
                    level = $3,
                    kick_after = $4,
                    ratelimit = $5,
                    antialt = $6,
                    prevent_vpn = $7,
                    verified_role_id = $8,
                    log_channel_id = $9
                """,
                ctx.guild.id,
                platform_str,
                level,
                kick_after,
                ratelimit,
                antialt,  
                prevent_vpn,  
                role_id,
                log_channel_id
            )
        else:  
            await self.bot.db.execute(
                """
                INSERT INTO guild_verification (
                    guild_id, platform, level, kick_after, ratelimit, antialt, verified_role_id, log_channel_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (guild_id) DO UPDATE SET
                    platform = $2,
                    level = $3,
                    kick_after = $4,
                    ratelimit = $5,
                    antialt = $6,
                    verified_role_id = $7,
                    log_channel_id = $8
                """,
                ctx.guild.id,
                platform_str,
                level,
                kick_after,
                ratelimit,
                antialt, 
                role_id,
                log_channel_id
            )
        
        level_names = {
            1: "Email Verification",
            2: "OAuth2 Verification",
            3: "CAPTCHA Verification",
            4: "Custom Questions"
        }
        
        if platform == "discord":
            discord_level_names = {
                10: "Simple Button Verification",
                11: "Word Selection",
                12: "Math Problem",
                13: "Emoji Selection",
                14: "Word Captcha"
            }
            
            verification_channel = ctx.guild.get_channel(verification_channel_id)
            if not verification_channel:
                return await ctx.warn("Failed to find verification channel. Please try setup again.")
            
            await self.setup_verification_channel(
                ctx.guild.id, 
                verification_channel_id, 
                level,
                role_id  
            )
            
            embed = Embed(
                title="✅ Verification Setup Complete",
                description=(
                    f"Your verification settings have been saved:\n\n"
                    f"- Platform: Discord Verification\n"
                    f"- Method: {discord_level_names[level]}\n"
                    f"- Verification Channel: {verification_channel.mention}\n"
                    f"- Auto-kick: {f'After {kick_after} minutes' if kick_after else 'Disabled'}\n"
                    f"- Rate Limit: {f'{ratelimit} attempts per hour' if ratelimit else 'Disabled'}\n"
                    f"- Anti-alt: {'Enabled' if antialt else 'Disabled'}\n\n"
                    f"The verification message has been set up in {verification_channel.mention}"
                ),
                color=ctx.color
            )
        else:
            embed = Embed(
                title="✅ Verification Setup Complete",
                description=(
                    f"Your verification settings have been saved:\n\n"
                    f"- Method: {level_names[level]}\n"
                    f"- Auto-kick: {f'After {kick_after} minutes' if kick_after else 'Disabled'}\n"
                    f"- Rate Limit: {f'{ratelimit} attempts per hour' if ratelimit else 'Disabled'}\n"
                    f"- Anti-alt: {'Enabled' if antialt else 'Disabled'}\n"
                    f"- VPN Prevention: {'Enabled' if prevent_vpn else 'Disabled'}\n\n"
                    f"Users can now verify at: https://evict.bot/verify/{ctx.guild.id}"
                ),
                color=ctx.color
            )
        
        return await ctx.send(embed=embed)

    @verify.command(name="level")
    @has_permissions(administrator=True)
    async def verify_level(self, ctx: Context, level: int) -> Message:
        """Set the verification level (1-4)."""
        if level not in range(1, 5):
            return await ctx.warn("Invalid verification level. Choose between 1-4:\n1: Email\n2: OAuth2\n3: CAPTCHA\n4: Custom Questions")
        
        await self.bot.db.execute(
            """
            INSERT INTO guild_verification (guild_id, level)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET level = $2
            """,
            ctx.guild.id,
            level
        )
        
        level_names = {
            1: "Email Verification",
            2: "OAuth2 Verification",
            3: "CAPTCHA Verification",
            4: "Custom Questions"
        }
        
        return await ctx.approve(f"Verification level set to: {level_names[level]}")

    @verify.command(name="bypass")
    @has_permissions(administrator=True)
    async def verify_bypass(self, ctx: Context, duration: Optional[int] = None) -> Message:
        """Temporarily disable verification for all users."""
        if duration and duration < 1:
            return await ctx.warn("Duration must be at least 1 minute")
            
        await self.bot.db.execute(
            """
            UPDATE guild_verification
            SET bypass_until = CASE 
                WHEN $2 IS NULL THEN NULL 
                ELSE NOW() + ($2 || ' minutes')::interval 
            END
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            duration
        )
        
        if duration:
            return await ctx.approve(f"Verification bypassed for {duration} minutes")
        return await ctx.approve("Verification bypass disabled")

    @verify.command(name="bypassrole")
    @has_permissions(administrator=True)
    async def verify_bypassrole(self, ctx: Context, role: discord.Role) -> Message:
        """Add a role that can bypass verification."""
        await self.bot.db.execute(
            """
            INSERT INTO verification_bypass_roles (guild_id, role_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id, role_id) DO NOTHING
            """,
            ctx.guild.id,
            role.id
        )
        
        return await ctx.approve(f"Added {role.mention} to verification bypass roles")

    @verify.command(name="autokick")
    @has_permissions(administrator=True)
    async def verify_autokick(self, ctx: Context, minutes: Optional[int] = None) -> Message:
        """Set time before unverified members are kicked."""
        if minutes and minutes < 5:
            return await ctx.warn("Auto-kick timer must be at least 5 minutes")
            
        await self.bot.db.execute(
            """
            UPDATE guild_verification
            SET kick_after = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            minutes
        )
        
        if minutes:
            return await ctx.approve(f"Members will be kicked after {minutes} minutes if not verified")
        return await ctx.approve("Auto-kick disabled")

    @verify.command(name="ratelimit")
    @has_permissions(administrator=True)
    async def verify_ratelimit(self, ctx: Context, attempts: Optional[int] = None) -> Message:
        """Set verification attempt rate limit per hour."""
        if attempts and attempts < 1:
            return await ctx.warn("Rate limit must be at least 1 attempt per hour")
            
        await self.bot.db.execute(
            """
            UPDATE guild_verification
            SET ratelimit = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            attempts
        )
        
        if attempts:
            return await ctx.approve(f"Rate limit set to {attempts} attempts per hour")
        return await ctx.approve("Rate limiting disabled")

    @verify.command(name="antialt")
    @has_permissions(administrator=True)
    async def verify_antialt(self, ctx: Context, enabled: bool = None) -> Message:
        """Toggle anti-alt detection."""
        if enabled is None:
            settings = await self.bot.db.fetchrow(
                """
                SELECT antialt FROM guild_verification
                WHERE guild_id = $1
                """,
                ctx.guild.id
            )
            enabled = not settings['antialt'] if settings else True
            
        await self.bot.db.execute(
            """
            UPDATE guild_verification
            SET antialt = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            enabled
        )
        
        status = "enabled" if enabled else "disabled"
        return await ctx.approve(f"Anti-alt detection {status}")

    @verify.command(name="disable")
    @has_permissions(administrator=True)
    async def verify_disable(self, ctx: Context) -> Message:
        """Disable the verification system."""
        await self.bot.db.execute(
            """
            DELETE FROM guild_verification
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        return await ctx.approve("Verification system disabled")

    @verify.command(name="role")
    @has_permissions(administrator=True)
    async def verify_role(self, ctx: Context, role: discord.Role) -> Message:
        """Set the role given to verified members."""
        if role.position >= ctx.guild.me.top_role.position:
            return await ctx.warn("That role is higher than my highest role")
            
        if role.managed:
            return await ctx.warn("Cannot use managed roles")
            
        await self.bot.db.execute(
            """
            INSERT INTO guild_verification (guild_id, verified_role_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) 
            DO UPDATE SET verified_role_id = $2
            """,
            ctx.guild.id,
            role.id
        )
        
        return await ctx.approve(f"Verification role set to {role.mention}")
        
    @verify.command(name="checkrole")
    @has_permissions(administrator=True)
    async def verify_checkrole(self, ctx: Context) -> Message:
        """Check the current verification role."""
        role_id = await self.bot.db.fetchval(
            """
            SELECT verified_role_id FROM guild_verification
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if not role_id:
            return await ctx.warn("No verification role set")
            
        role = ctx.guild.get_role(role_id)
        if not role:
            return await ctx.warn("Verification role no longer exists")
            
        return await ctx.neutral(f"Current verification role: {role.mention}")

    @verify.group(name="questions", invoke_without_command=True)
    @has_permissions(administrator=True)
    async def verify_questions(self, ctx: Context) -> Message:
        """View or manage custom verification questions."""
        questions = await self.bot.db.fetch(
            """
            SELECT question, options, correct_answer 
            FROM verification_questions
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if not questions:
            return await ctx.warn("No verification questions set up")
            
        embed = Embed(
            title="Verification Questions",
            description="Current questions for custom verification:",
            color=ctx.color
        )
        
        for i, q in enumerate(questions, 1):
            options = "\n".join(f"{i}. {opt}" for i, opt in enumerate(q['options'], 1))
            embed.add_field(
                name=f"Question {i}",
                value=f"Q: {q['question']}\nOptions:\n{options}\nCorrect: {q['correct_answer']}",
                inline=False
            )
            
        return await ctx.send(embed=embed)
        
    @verify_questions.command(name="add")
    @has_permissions(administrator=True)
    async def verify_questions_add(self, ctx: Context, question: str, correct_answer: int, *options: str) -> Message:
        """Add a verification question.
        
        Example:
        ;verify questions add "What color is the sky?" 1 "Blue" "Red" "Green"
        """
        if len(options) < 2:
            return await ctx.warn("Need at least 2 options")
            
        if correct_answer < 1 or correct_answer > len(options):
            return await ctx.warn(f"Correct answer must be between 1 and {len(options)}")
            
        await self.bot.db.execute(
            """
            INSERT INTO verification_questions (
                guild_id,
                question,
                options,
                correct_answer
            ) VALUES ($1, $2, $3, $4)
            """,
            ctx.guild.id,
            question,
            options,
            str(correct_answer)
        )
        
        return await ctx.approve("Question added successfully")
        
    @verify_questions.command(name="remove")
    @has_permissions(administrator=True)
    async def verify_questions_remove(self, ctx: Context, question_number: int) -> Message:
        """Remove a verification question by its number."""
        question = await self.bot.db.fetchrow(
            """
            WITH numbered AS (
                SELECT *, ROW_NUMBER() OVER () as num
                FROM verification_questions
                WHERE guild_id = $1
            )
            DELETE FROM verification_questions
            WHERE id = (
                SELECT id FROM numbered
                WHERE num = $2
            )
            RETURNING question
            """,
            ctx.guild.id,
            question_number
        )
        
        if not question:
            return await ctx.warn("Question not found")
            
        return await ctx.approve(f"Removed question: {question['question']}")

    @verify_questions.command(name="addtext")
    @has_permissions(administrator=True)
    async def verify_questions_addtext(self, ctx: Context, *, question: str) -> Message:
        """Add a text-based verification question (requires manual verification).
        
        Example:
        ;verify questions addtext Why do you want to join our server?
        """
        settings = await self.bot.db.fetchrow(
            """
            SELECT manual_verification FROM guild_verification
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if not settings or not settings['manual_verification']:
            return await ctx.warn(
                "Text questions require manual verification.\n"
                "Enable it first with: `verify mode manual`"
            )
            
        await self.bot.db.execute(
            """
            INSERT INTO verification_questions (
                guild_id,
                question,
                options,
                correct_answer,
                is_text
            ) VALUES ($1, $2, '[]'::jsonb, '-1', TRUE)
            """,
            ctx.guild.id,
            question
        )
        
        return await ctx.approve(
            "Text question added successfully.\n"
            "⚠️ Remember: Text questions require manual review of answers."
        )
        
    @verify_questions.command(name="removetext")
    @has_permissions(administrator=True)
    async def verify_questions_removetext(self, ctx: Context) -> Message:
        """Remove all text-based verification questions."""
        result = await self.bot.db.execute(
            """
            DELETE FROM verification_questions
            WHERE guild_id = $1 AND is_text = TRUE
            RETURNING id
            """,
            ctx.guild.id
        )
        
        if not result:
            return await ctx.warn("No text questions found")
            
        return await ctx.approve("All text questions removed")

    @verify_questions.command(name="list")
    @has_permissions(administrator=True)
    async def verify_questions_list(self, ctx: Context) -> Message:
        """List all verification questions."""
        questions = await self.bot.db.fetch(
            """
            SELECT question, options, correct_answer, is_text
            FROM verification_questions
            WHERE guild_id = $1
            ORDER BY is_text, id
            """,
            ctx.guild.id
        )
        
        if not questions:
            return await ctx.warn("No verification questions set up")
            
        embed = Embed(
            title="Verification Questions",
            color=ctx.color
        )
        
        multiple_choice = []
        text_questions = []
        
        for i, q in enumerate(questions, 1):
            if q['is_text']:
                text_questions.append(f"{i}. {q['question']}")
            else:
                options = "\n".join(f"  {j}. {opt}" for j, opt in enumerate(q['options'], 1))
                multiple_choice.append(f"{i}. {q['question']}\n{options}\n  ✓ Answer: {q['correct_answer']}")
        
        if multiple_choice:
            embed.add_field(
                name="Multiple Choice Questions",
                value="\n\n".join(multiple_choice),
                inline=False
            )
            
        if text_questions:
            embed.add_field(
                name="Text Questions (Manual Review)",
                value="\n".join(text_questions),
                inline=False
            )
            
        return await ctx.send(embed=embed)

    @verify.command(name="mode")
    @has_permissions(administrator=True)
    async def verify_mode(self, ctx: Context, mode: str = None) -> Message:
        """Set verification mode to 'auto' or 'manual'."""
        if mode not in ('auto', 'manual', None):
            return await ctx.warn("Mode must be 'auto' or 'manual'")
            
        if mode:
            await self.bot.db.execute(
                """
                UPDATE guild_verification
                SET manual_verification = $2
                WHERE guild_id = $1
                """,
                ctx.guild.id,
                mode == 'manual'
            )
            return await ctx.approve(f"Verification mode set to: {mode}")
        
        setting = await self.bot.db.fetchval(
            """
            SELECT manual_verification
            FROM guild_verification
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        current_mode = "manual" if setting else "auto"
        return await ctx.info(f"Current verification mode: {current_mode}")

    @verify.command(name="approve")
    @has_permissions(administrator=True)
    async def verify_approve(self, ctx: Context, member: discord.Member) -> Message:
        """Manually approve a member's verification."""
        settings = await self.bot.db.fetchrow(
            """
            SELECT verified_role_id, manual_verification
            FROM guild_verification
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if not settings:
            return await ctx.warn("Verification is not set up")
            
        if not settings['manual_verification']:
            return await ctx.warn("Manual verification is not enabled")
            
        role = ctx.guild.get_role(settings['verified_role_id'])
        if not role:
            return await ctx.warn("Verification role not found")
            
        if role in member.roles:
            return await ctx.warn("Member is already verified")
            
        try:
            await member.add_roles(role, reason=f"Manual verification by {ctx.author}")
            return await ctx.approve(f"Successfully verified {member.mention}")
        except discord.Forbidden:
            return await ctx.warn("Missing permissions to assign role")

    @verify.command(name="deny")
    @has_permissions(administrator=True)
    async def verify_deny(self, ctx: Context, member: discord.Member, *, reason: str = None) -> Message:
        """Deny a member's verification request."""
        settings = await self.bot.db.fetchrow(
            """
            SELECT manual_verification
            FROM guild_verification
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if not settings or not settings['manual_verification']:
            return await ctx.warn("Manual verification is not enabled")
            
        return await ctx.approve(f"Denied verification for {member.mention}" + (f": {reason}" if reason else ""))

    @verify.command(name="logchannel")
    @has_permissions(administrator=True)
    async def verify_logchannel(self, ctx: Context, channel: discord.TextChannel = None) -> Message:
        """Set the channel for verification logs and notifications."""
        if channel and not channel.permissions_for(ctx.guild.me).send_messages:
            return await ctx.warn("I need permission to send messages in that channel")
            
        await self.bot.db.execute(
            """
            UPDATE guild_verification
            SET log_channel_id = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            channel.id if channel else None
        )
        
        if channel:
            return await ctx.approve(f"Verification logs will be sent to {channel.mention}")
        return await ctx.approve("Verification logs disabled")

    @verify.command(name="vpn")
    @has_permissions(administrator=True)
    async def verify_vpn(self, ctx: Context, enabled: Optional[bool] = None) -> Message:
        """Toggle VPN/Proxy detection for verification."""
        if enabled is None:
            settings = await self.bot.db.fetchrow(
                """
                SELECT prevent_vpn FROM guild_verification
                WHERE guild_id = $1
                """,
                ctx.guild.id
            )
            enabled = False if not settings else not settings['prevent_vpn']
            
        await self.bot.db.execute(
            """
            UPDATE guild_verification
            SET prevent_vpn = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            enabled
        )
        
        status = "enabled" if enabled else "disabled"
        return await ctx.approve(f"VPN/Proxy prevention {status}")

    async def setup_simple_button(self, channel: discord.TextChannel) -> None:
        embed = Embed(
            title="Server Verification",
            description=(
                "Welcome to the server! To gain access, simply click the verify button below.\n\n"
                "This helps us ensure you're not a bot."
            ),
            color=discord.Color.blurple()
        ).set_footer(text="Click the button below to verify")
        
        view = SimpleVerificationView(self)
        
        try:
            await channel.send(embed=embed, view=view)
        except Exception as e:
            print(f"Error sending verification message: {e}")

    async def setup_verification_channel(self, guild_id: int, channel_id: int, level: int, role_id: int) -> None:
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
            
        # await channel.purge(limit=100)
        
        if level == 10:
            await self.setup_simple_button(channel)
        # elif level == 11: 
        #     words = ["VERIFY", "DISCORD", "SECURE", "ACCESS"]
        #     correct = random.choice(words)
            
        #     embed = Embed(
        #         title="Word Verification",
        #         description=f"Click the correct word: **{correct}**",
        #         color=discord.Color.blurple()
        #     )
            
        #     view = discord.ui.View(timeout=None)
        #     for word in words:
        #         view.add_item(discord.ui.Button(
        #             label=word,
        #             custom_id=f"verify_word_{word}_{role_id}_{correct}",
        #             style=discord.ButtonStyle.blurple
        #         ))
        #     await channel.send(content=f"@{role_id}", embed=embed, view=view)
            
        # elif level == 12:
        #     num1 = random.randint(1, 10)
        #     num2 = random.randint(1, 10)
        #     answer = num1 + num2
            
        #     embed = Embed(
        #         title="Math Verification",
        #         description=f"Click below to answer: What is {num1} + {num2}?",
        #         color=discord.Color.blurple()
        #     )
            
        #     view = discord.ui.View(timeout=None)
        #     view.add_item(discord.ui.Button(
        #         label="Answer",
        #         custom_id=f"verify_math_{role_id}_{answer}",
        #         style=discord.ButtonStyle.blurple
        #     ))
        #     await channel.send(content=f"@{role_id}", embed=embed, view=view)
            
        # elif level == 13:  
        #     emojis = ["🎮", "🎲", "🎯"]  
        #     correct = random.choice(emojis)
            
        #     embed = Embed(
        #         title="Emoji Verification",
        #         description=f"Click on the {correct} emoji",
        #         color=discord.Color.blurple()
        #     )
            
        #     view = discord.ui.View(timeout=None)
        #     for emoji in emojis:
        #         view.add_item(discord.ui.Button(
        #             emoji=emoji,
        #             custom_id=f"verify_emoji_{emoji}_{role_id}_{correct}",
        #             style=discord.ButtonStyle.blurple
        #         ))
        #     await channel.send(content=f"@{role_id}", embed=embed, view=view)
            
        # elif level == 14: 
        #     text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
        #     width = 280
        #     height = 90
        #     image = Image.new('RGB', (width, height), color='white')
        #     draw = ImageDraw.Draw(image)
            
        #     font = ImageFont.truetype("assets/fonts/Montserrat-SemiBold.ttf", 60)
            
        #     for i, char in enumerate(text):
        #         x = 40 + (i * 35)
        #         y = random.randint(20, 40)
        #         draw.text((x, y), char, font=font, fill='black')
                
        #     for _ in range(1000):
        #         x = random.randint(0, width)
        #         y = random.randint(0, height)
        #         draw.point((x, y), fill='gray')
                
        #     for _ in range(5):
        #         x1 = random.randint(0, width)
        #         y1 = random.randint(0, height)
        #         x2 = random.randint(0, width)
        #         y2 = random.randint(0, height)
        #         draw.line([(x1, y1), (x2, y2)], fill='gray', width=2)
            
        #     buffer = BytesIO()
        #     image.save(buffer, format='PNG')
        #     buffer.seek(0)
            
        #     file = discord.File(buffer, filename='captcha.png')
            
        #     embed = Embed(
        #         title="Word Captcha Verification",
        #         description=f"Welcome @{role_id}! Please verify by typing the word shown in the image.",
        #         color=discord.Color.blurple()
        #     )
        #     embed.set_image(url="attachment://captcha.png")
            
        #     view = discord.ui.View()
        #     view.add_item(discord.ui.Button(
        #         label="Enter Text",
        #         custom_id=f"verify_captcha_{role_id}_{text}",
        #         style=discord.ButtonStyle.blurple
        #     ))
            
        #     await channel.send(
        #         content=f"@{role_id}",
        #         embed=embed,
        #         file=file,
        #         view=view
        #     )

    async def get_random_words(self, count: int = 4) -> list:
        """Get random words from MIT's word list."""
        word_url = "https://www.mit.edu/~ecprice/wordlist.10000"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(word_url) as response:
                    if response.status == 200:
                        words = (await response.text()).splitlines()
                        return random.sample([w.upper() for w in words if 4 <= len(w) <= 8], count)
        except:
            return ["VERIFY", "DISCORD", "SECURE", "ACCESS"]

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        settings = await self.bot.db.fetchrow(
            """
            SELECT 
                platform,
                verification_channel_id,
                level,
                verified_role_id,
                COALESCE(kick_after, 0) as kick_after
            FROM guild_verification
            WHERE guild_id = $1
            """,
            member.guild.id
        )
        
        if not settings or settings['platform'] != 'discord':
            return
            
        channel = member.guild.get_channel(settings['verification_channel_id'])
        if not channel:
            return
            
        if settings['kick_after']:
            self.bot.loop.create_task(self.setup_auto_kick(member))
            
        if settings['level'] == 11:  
            words = await self.get_random_words()
            correct = random.choice(words)
            
            embed = Embed(
                title="Word Verification",
                description=f"Click the correct word: ||**{correct}**||",
                color=discord.Color.blurple()
            )
            
            view = discord.ui.View(timeout=None)
            for word in words:
                view.add_item(discord.ui.Button(
                    label=word,
                    custom_id=f"verify_word_{word}_{member.id}_{correct}",
                    style=discord.ButtonStyle.blurple
                ))
            await channel.send(content=member.mention, embed=embed, view=view)
            
        elif settings['level'] == 12:  
            num1 = random.randint(1, 10)
            num2 = random.randint(1, 10)
            answer = num1 + num2
            
            embed = Embed(
                title="Math Verification",
                description=f"Click below to answer: What is {num1} + {num2}?",
                color=discord.Color.blurple()
            )
            
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(
                label="Answer",
                custom_id=f"verify_math_{member.id}_{answer}",
                style=discord.ButtonStyle.blurple
            ))
            await channel.send(content=member.mention, embed=embed, view=view)
            
        elif settings['level'] == 13: 
            emojis = ["🎮", "🎲", "🎯"]
            correct = random.choice(emojis)
            
            embed = Embed(
                title="Emoji Verification",
                description=f"Click on the {correct} emoji",
                color=discord.Color.blurple()
            )
            
            view = discord.ui.View(timeout=None)
            for emoji in emojis:
                view.add_item(discord.ui.Button(
                    emoji=emoji,
                    custom_id=f"verify_emoji_{emoji}_{member.id}_{correct}",
                    style=discord.ButtonStyle.blurple
                ))
            await channel.send(content=member.mention, embed=embed, view=view)
            
        elif settings['level'] == 14:  
            text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            width = 280
            height = 90
            image = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(image)
            
            font = ImageFont.truetype("assets/fonts/Montserrat-SemiBold.ttf", 60)
            
            for i, char in enumerate(text):
                x = 40 + (i * 35)
                y = random.randint(20, 40)
                draw.text((x, y), char, font=font, fill='black')
                
            for _ in range(1000):
                x = random.randint(0, width)
                y = random.randint(0, height)
                draw.point((x, y), fill='gray')
                
            for _ in range(5):
                x1 = random.randint(0, width)
                y1 = random.randint(0, height)
                x2 = random.randint(0, width)
                y2 = random.randint(0, height)
                draw.line([(x1, y1), (x2, y2)], fill='gray', width=2)
            
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            buffer.seek(0)
            
            file = discord.File(buffer, filename='captcha.png')
            
            embed = Embed(
                title="Word Captcha Verification",
                description=f"Welcome @{member.id}! Please verify by typing the word shown in the image.",
                color=discord.Color.blurple()
            )
            embed.set_image(url="attachment://captcha.png")
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="Enter Text",
                custom_id=f"verify_captcha_{member.id}_{text}",
                style=discord.ButtonStyle.blurple
            ))
            
            await channel.send(
                content=member.mention,
                embed=embed,
                file=file,
                view=view
            )

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data.get("custom_id", "").startswith("verify_"):
            return
            
        custom_id = interaction.data["custom_id"]
        
        try:
            if custom_id.startswith("verify_word_"):
                _, _, word, user_id, correct_word = custom_id.split("_")
                if int(user_id) != interaction.user.id:
                    return await interaction.response.send_message("This verification is not for you!", ephemeral=True)
                    
                if word == correct_word:
                    await self.verify_member(interaction)
                else:
                    await interaction.response.send_message("Incorrect word! Try again.", ephemeral=True)
                    
            elif custom_id.startswith("verify_math_"):
                _, _, user_id, correct_answer = custom_id.split("_")
                if int(user_id) != interaction.user.id:
                    return await interaction.response.send_message("This verification is not for you!", ephemeral=True)
                    
                modal = MathVerificationModal(int(correct_answer), self)
                await interaction.response.send_modal(modal)
                
            elif custom_id.startswith("verify_emoji_"):
                _, _, emoji, user_id, correct_emoji = custom_id.split("_")
                if int(user_id) != interaction.user.id:
                    return await interaction.response.send_message("This verification is not for you!", ephemeral=True)
                    
                if emoji == correct_emoji:
                    await self.verify_member(interaction)
                else:
                    await interaction.response.send_message("Incorrect emoji! Try again.", ephemeral=True)
                    
            elif custom_id.startswith("verify_captcha_"):
                _, _, user_id, correct_text = custom_id.split("_")
                if int(user_id) != interaction.user.id:
                    return await interaction.response.send_message("This verification is not for you!", ephemeral=True)
                    
                modal = CaptchaVerificationModal(correct_text, self)
                await interaction.response.send_modal(modal)
                
        except Exception as e:
            print(f"Verification error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)
            else:
                await interaction.followup.send("An error occurred. Please try again.", ephemeral=True)

    async def verify_member(self, interaction: discord.Interaction):
        try:
            if interaction.response.is_done():
                return
            
            settings = await self.bot.db.fetchrow(
                """
                SELECT verified_role_id, level FROM guild_verification
                WHERE guild_id = $1
                """,
                interaction.guild_id
            )
            
            if not settings:
                return await interaction.response.send_message("Verification system is not set up properly.", ephemeral=True)
                
            role = interaction.guild.get_role(settings['verified_role_id'])
            if not role:
                return await interaction.response.send_message("Verification role not found.", ephemeral=True)
                
            if role in interaction.user.roles:
                return await interaction.response.send_message("You are already verified!", ephemeral=True)
                
            try:
                await interaction.response.defer(ephemeral=True)
                await interaction.user.add_roles(role, reason="Verification completed")
                await interaction.followup.send("✅ You have been verified!", ephemeral=True)
                
                await self.log_verification(interaction.guild_id, interaction.user, "verified")
                
                if settings['level'] != 10 and interaction.message:
                    try:
                        await interaction.message.delete()
                    except discord.NotFound:
                        pass
                    
            except discord.Forbidden:
                await interaction.followup.send("Failed to assign role. Please contact an administrator.", ephemeral=True)
                
        except Exception as e:
            print(f"Error in verify_member: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("An error occurred during verification. Please try again.", ephemeral=True)
                else:
                    await interaction.followup.send("An error occurred during verification. Please try again.", ephemeral=True)
            except:
                pass

    async def log_verification(self, guild_id: int, member: discord.Member, action: str, reason: str = None):
        """Log verification events to the configured log channel."""
        settings = await self.bot.db.fetchrow(
            """
            SELECT log_channel_id FROM guild_verification
            WHERE guild_id = $1
            """,
            guild_id
        )
        
        if not settings or not settings['log_channel_id']:
            return
            
        channel = self.bot.get_channel(settings['log_channel_id'])
        if not channel:
            return
            
        embed = Embed(
            title="Verification Log",
            description=f"{member.mention} ({member.id})",
            color=discord.Color.green() if action == "verified" else discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Action", value=action.title())
        if reason:
            embed.add_field(name="Reason", value=reason)
            
        await channel.send(embed=embed)

    async def setup_auto_kick(self, member: discord.Member):
        """Setup auto-kick timer for unverified members."""
        settings = await self.bot.db.fetchrow(
            """
            SELECT kick_after FROM guild_verification
            WHERE guild_id = $1
            """,
            member.guild.id
        )
        
        if not settings or not settings['kick_after']:
            return
            
        await asyncio.sleep(settings['kick_after'] * 60)  
        
        settings = await self.bot.db.fetchrow(
            """
            SELECT verified_role_id FROM guild_verification
            WHERE guild_id = $1
            """,
            member.guild.id
        )
        
        if not settings:
            return
            
        role = member.guild.get_role(settings['verified_role_id'])
        if not role or role not in member.roles:
            try:
                await member.kick(reason="Failed to verify in time")
                await self.log_verification(member.guild.id, member, "kicked", "Failed to verify in time")
            except discord.Forbidden:
                pass

class VerificationPlatformSelect(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None
        
        self.discord_btn = discord.ui.Button(
            label="Discord Verification",
            emoji="🎮",
            custom_id="discord",
            style=discord.ButtonStyle.blurple
        )
        self.web_btn = discord.ui.Button(
            label="Web Verification",
            emoji="🌐",
            custom_id="web",
            style=discord.ButtonStyle.gray
        )
        
        self.discord_btn.callback = self.discord_callback
        self.web_btn.callback = self.web_callback
        
        self.add_item(self.discord_btn)
        self.add_item(self.web_btn)
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This setup is not for you!", ephemeral=True)
            return False
        return True
        
    async def discord_callback(self, interaction: discord.Interaction):
        print("Discord button clicked")  
        self.value = "discord"
        await interaction.response.defer()
        self.stop()
        
    async def web_callback(self, interaction: discord.Interaction):
        print("Web button clicked")  
        self.value = "web"
        await interaction.response.defer()
        self.stop()

    async def wait_for_selection(self):
        await self.wait()
        print(f"Platform value: {self.value}") 
        return self.value

class VerificationLevelSelect(discord.ui.View):
    def __init__(self, ctx, platform):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None
        
        if platform == "web":
            self.add_item(discord.ui.Button(
                label="Email",
                emoji="1️⃣",
                custom_id="1",
                style=discord.ButtonStyle.blurple
            ))
            self.add_item(discord.ui.Button(
                label="OAuth2",
                emoji="2️⃣", 
                custom_id="2",
                style=discord.ButtonStyle.gray,
                disabled=True
            ))
            self.add_item(discord.ui.Button(
                label="CAPTCHA",
                emoji="3️⃣",
                custom_id="3", 
                style=discord.ButtonStyle.blurple
            ))
            self.add_item(discord.ui.Button(
                label="Questions",
                emoji="4️⃣",
                custom_id="4",
                style=discord.ButtonStyle.blurple
            ))
        else:  
            self.add_item(discord.ui.Button(
                label="Simple Button",
                emoji="1️⃣",
                custom_id="10",
                style=discord.ButtonStyle.blurple
            ))
            self.add_item(discord.ui.Button(
                label="Word Selection",
                emoji="2️⃣",
                custom_id="11",
                style=discord.ButtonStyle.blurple
            ))
            self.add_item(discord.ui.Button(
                label="Math Problem",
                emoji="3️⃣",
                custom_id="12",
                style=discord.ButtonStyle.blurple
            ))
            self.add_item(discord.ui.Button(
                label="Emoji Selection",
                emoji="4️⃣",
                custom_id="13",
                style=discord.ButtonStyle.blurple
            ))
            self.add_item(discord.ui.Button(
                label="Word Captcha",
                emoji="5️⃣",
                custom_id="14",
                style=discord.ButtonStyle.blurple
            ))
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This setup is not for you!", ephemeral=True)
            return False
        return True
        
    async def wait_for_selection(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.callback = self.button_callback
        return await self.wait()
        
    async def button_callback(self, interaction: discord.Interaction):
        self.value = int(interaction.data["custom_id"])
        await interaction.response.defer()
        self.stop()
        
    async def wait(self):
        await super().wait()
        return self.value

class AutoKickSelect(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None
        
        self.add_item(discord.ui.Button(
            label="Enable",
            emoji="✅",
            custom_id="enable",
            style=discord.ButtonStyle.green
        ))
        self.add_item(discord.ui.Button(
            label="Disable",
            emoji="❌", 
            custom_id="disable",
            style=discord.ButtonStyle.red
        ))
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This setup is not for you!", ephemeral=True)
            return False
        return True
        
    async def wait_for_selection(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.callback = self.button_callback
        return await self.wait()
        
    async def button_callback(self, interaction: discord.Interaction):
        if interaction.data["custom_id"] == "disable":
            self.value = 0  
            await interaction.response.defer()
            self.stop()
        else:
            modal = AutoKickModal(self)
            await interaction.response.send_modal(modal)

class AutoKickModal(discord.ui.Modal, title="Set Auto-kick Timer"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        
        self.minutes = discord.ui.TextInput(
            label="Minutes",
            placeholder="5",
            required=True,
            max_length=3
        )
        self.add_item(self.minutes)
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            minutes = int(self.minutes.value.strip())
            if minutes < 5:
                await interaction.response.send_message("Auto-kick timer must be at least 5 minutes", ephemeral=True)
                return
            self.view.value = minutes
            await interaction.response.send_message("Auto-kick timer set successfully", ephemeral=True)
            self.view.stop()
        except ValueError:
            await interaction.response.send_message("Invalid input. Please enter a valid number", ephemeral=True)

class RateLimitSelect(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None
        
        select = discord.ui.Select(
            placeholder="Select attempts per hour",
            options=[
                discord.SelectOption(label="Disabled", value="0"),
                *[discord.SelectOption(label=f"{i} attempts", value=str(i)) for i in range(1, 11)]
            ]
        )
        select.callback = self.select_callback
        self.add_item(select)
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This setup is not for you!", ephemeral=True)
            return False
        return True
        
    async def wait_for_selection(self):
        return await self.wait()
        
    async def select_callback(self, interaction: discord.Interaction):
        self.value = int(interaction.data["values"][0])
        await interaction.response.defer()
        self.stop()
        
    async def wait(self):
        await super().wait()
        return self.value

class AntiAltSelect(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None
        
        self.add_item(discord.ui.Button(
            label="Enable",
            emoji="✅",
            custom_id="enable",
            style=discord.ButtonStyle.green
        ))
        self.add_item(discord.ui.Button(
            label="Disable",
            emoji="❌",
            custom_id="disable",
            style=discord.ButtonStyle.red
        ))
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This setup is not for you!", ephemeral=True)
            return False
        return True
        
    async def wait_for_selection(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.callback = self.button_callback
        return await self.wait()
        
    async def button_callback(self, interaction: discord.Interaction):
        self.value = interaction.data["custom_id"] == "enable"
        await interaction.response.defer()
        self.stop()
        
    async def wait(self):
        await super().wait()
        return self.value

class RoleSelect(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None
        
        select = discord.ui.Select(
            placeholder="Select role or create new",
            options=[
                discord.SelectOption(label="Create New Role", value="new", description="Create a new verification role"),
                *[
                    discord.SelectOption(label=role.name, value=str(role.id))
                    for role in ctx.guild.roles
                    if role.position < ctx.guild.me.top_role.position
                    and not role.managed
                    and role.name != "@everyone"
                ][:24]
            ]
        )
        select.callback = self.select_callback
        self.add_item(select)
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This setup is not for you!", ephemeral=True)
            return False
        return True
        
    async def select_callback(self, interaction: discord.Interaction):
        if interaction.data["values"][0] == "new":
            modal = RoleCreateModal(self.ctx)
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.value = modal.role.id if modal.role else None
        else:
            self.value = int(interaction.data["values"][0])
            await interaction.response.defer()
        self.stop()

    async def wait_for_selection(self):
        await self.wait()
        print(f"Selected role ID: {self.value}")  
        return self.value

class RoleCreateModal(discord.ui.Modal, title="Create Verification Role"):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.role = None
        
        self.name = discord.ui.TextInput(
            label="Role Name",
            placeholder="Verified",
            default="Verified",
            required=True,
            max_length=100
        )
        self.add_item(self.name)
        
        self.color = discord.ui.TextInput(
            label="Role Color (hex)",
            placeholder="#7289DA",
            required=False,
            max_length=7
        )
        self.add_item(self.color)
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            color = int(self.color.value.strip('#'), 16) if self.color.value else 0x7289DA
            self.role = await self.ctx.guild.create_role(
                name=self.name.value,
                color=discord.Color(color),
                reason="Verification role creation"
            )
            await interaction.response.send_message(f"Created role {self.role.mention}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Invalid color hex code", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Missing permissions to create role", ephemeral=True)

class LogChannelSelect(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None
        
        select = discord.ui.ChannelSelect(
            placeholder="Select log channel",
            channel_types=[discord.ChannelType.text]
        )
        select.callback = self.select_callback
        self.add_item(select)
        
        self.add_item(discord.ui.Button(
            label="Skip",
            style=discord.ButtonStyle.secondary,
            custom_id="skip"
        ))
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This setup is not for you!", ephemeral=True)
            return False
        return True
        
    async def select_callback(self, interaction: discord.Interaction):
        channel_id = int(interaction.data["values"][0])
        channel = interaction.guild.get_channel(channel_id)
        
        if not channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message("I need permission to send messages in that channel!", ephemeral=True)
            return
            
        self.value = channel_id
        await interaction.response.defer()
        self.stop()
        
    async def button_callback(self, interaction: discord.Interaction):
        if interaction.data["custom_id"] == "skip":
            self.value = None
        await interaction.response.defer()
        self.stop()

    async def wait_for_selection(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.callback = self.button_callback
        await self.wait()
        return self.value

class VPNSelect(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None
        
        self.add_item(discord.ui.Button(
            label="Enable",
            emoji="✅",
            custom_id="enable",
            style=discord.ButtonStyle.green
        ))
        self.add_item(discord.ui.Button(
            label="Disable",
            emoji="❌",
            custom_id="disable",
            style=discord.ButtonStyle.red
        ))
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This setup is not for you!", ephemeral=True)
            return False
        return True
        
    async def button_callback(self, interaction: discord.Interaction):
        self.value = interaction.data["custom_id"] == "enable"
        await interaction.response.defer()
        self.stop()

    async def wait_for_selection(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.callback = self.button_callback
        await self.wait()
        return self.value  

class VerificationChannelSelect(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None
        
        channel_select = discord.ui.ChannelSelect(
            placeholder="Select verification channel",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )
        channel_select.callback = self.channel_callback
        self.add_item(channel_select)
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id
        
    async def channel_callback(self, interaction: discord.Interaction):
        channel = interaction.data["values"][0]
        self.value = int(channel)
        await interaction.response.defer()
        self.stop()

    async def wait_for_selection(self):
        await self.wait()
        return self.value 

class VerificationEmbeds:
    @staticmethod
    def simple_button() -> Embed:
        return Embed(
            title="Server Verification",
            description=(
                "Welcome to the server! To gain access, simply click the verify button below.\n\n"
                "This helps us ensure you're not a bot."
            ),
            color=discord.Color.blurple()
        ).set_footer(text="Click the button below to verify")

    @staticmethod
    def word_selection() -> Embed:
        return Embed(
            title="Word Verification",
            description=(
                "To verify, you need to find the hidden word in this channel.\n\n"
                "**Instructions:**\n"
                "- Look for a message containing a specific word\n"
                "- Type that word in this channel\n"
                "- The word is unique for each user\n"
                "- The word will be highlighted when you hover over it"
            ),
            color=discord.Color.blurple()
        ).set_footer(text="Type the hidden word to verify")

    @staticmethod
    def math_problem(problem: str) -> Embed:
        return Embed(
            title="Math Verification",
            description=(
                "Solve the following math problem to verify:\n\n"
                f"```{problem}```\n"
                "Type your answer as a number in this channel."
            ),
            color=discord.Color.blurple()
        ).set_footer(text="Type the answer to verify")

    @staticmethod
    def emoji_selection(emoji: str) -> Embed:
        return Embed(
            title="Emoji Verification",
            description=(
                f"Select the {emoji} emoji from the options below to verify.\n\n"
                "This helps us ensure you're human!"
            ),
            color=discord.Color.blurple()
        ).set_footer(text="Click the correct emoji to verify")

    @staticmethod
    def image_captcha() -> Embed:
        return Embed(
            title="Image Verification",
            description=(
                "Type the text you see in the image below.\n\n"
                "**Note:**\n"
                "- The text is case-sensitive\n"
                "- Only includes letters and numbers\n"
                "- Ignore any spaces"
            ),
            color=discord.Color.blurple()
        ).set_footer(text="Type the text from the image to verify")

class ImageCaptcha:
    def __init__(self):
        self.font = ImageFont.truetype("assets/fonts/Montserrat-SemiBold.ttf", 36)
        
    def generate(self, text: str) -> discord.File:
        img = Image.new('RGB', (200, 80), color='white')
        draw = ImageDraw.Draw(img)
        
        draw.text((30, 20), text, font=self.font, fill='black')
        
        for _ in range(8):
            x1 = random.randint(0, 200)
            y1 = random.randint(0, 80)
            x2 = random.randint(0, 200)
            y2 = random.randint(0, 80)
            draw.line([(x1, y1), (x2, y2)], fill='gray', width=2)
            
        for _ in range(1000):
            x = random.randint(0, 200)
            y = random.randint(0, 80)
            draw.point((x, y), fill='gray')
            
        img = img.transform(
            img.size, 
            Image.AFFINE, 
            (1, 0.1, 0, 0, 1, 0),
            fillcolor='white'
        )
        
        buffer = BytesIO()
        img.save(buffer, 'PNG')
        buffer.seek(0)
        return discord.File(buffer, 'captcha.png')

    async def send_captcha(self, channel: discord.TextChannel, member: discord.Member) -> str:
        """Generates and sends a captcha, returns the correct text"""
        text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        file = self.generate(text)
        
        embed = VerificationEmbeds.image_captcha()
        await channel.send(
            content=member.mention,
            embed=embed,
            file=file
        )
        
        return text

class VerificationHandler:
    def __init__(self, bot):
        self.bot = bot
        self.captcha = ImageCaptcha()
        
    async def setup_verification(self, guild_id: int, channel_id: int, level: int):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        if level == 10:  
            embed = VerificationEmbeds.simple_button()
            view = SimpleVerifyButton()
            await channel.send(embed=embed, view=view)
            
        elif level == 11:  
            embed = VerificationEmbeds.word_selection()
            await channel.send(embed=embed)
            
        elif level == 12:  
            embed = VerificationEmbeds.math_problem("Loading...")
            await channel.send(embed=embed)
            
        elif level == 13:  
            embed = VerificationEmbeds.emoji_selection("Loading...")
            await channel.send(embed=embed)
            
        elif level == 14: 
            text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            file = self.captcha.generate(text)
            
            embed = VerificationEmbeds.image_captcha()
            await channel.send(
                embed=embed,
                file=file
            )

class SimpleVerificationView(discord.ui.View):
    def __init__(self, cog=None):
        super().__init__(timeout=None)
        self.cog = cog
        
    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.green,
        custom_id="verify_button"
    )
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.cog or interaction.client.get_cog("Config")
        if not cog:
            return await interaction.response.send_message("Verification system is not available.", ephemeral=True)
        await cog.verify_member(interaction)

    async def verify_member(self, interaction: discord.Interaction):
        try:
            if interaction.response.is_done():
                return
            
            settings = await self.bot.db.fetchrow(
                """
                SELECT verified_role_id, level FROM guild_verification
                WHERE guild_id = $1
                """,
                interaction.guild_id
            )
            
            if not settings:
                return await interaction.response.send_message("Verification system is not set up properly.", ephemeral=True)
                
            role = interaction.guild.get_role(settings['verified_role_id'])
            if not role:
                return await interaction.response.send_message("Verification role not found.", ephemeral=True)
                
            if role in interaction.user.roles:
                return await interaction.response.send_message("You are already verified!", ephemeral=True)
                
            try:
                await interaction.response.defer(ephemeral=True)
                await interaction.user.add_roles(role, reason="Verification completed")
                await interaction.followup.send("✅ You have been verified!", ephemeral=True)
                
                await self.log_verification(interaction.guild_id, interaction.user, "verified")
                
                if settings['level'] != 10 and interaction.message:
                    try:
                        await interaction.message.delete()
                    except discord.NotFound:
                        pass
                    
            except discord.Forbidden:
                await interaction.followup.send("Failed to assign role. Please contact an administrator.", ephemeral=True)
                
        except Exception as e:
            print(f"Error in verify_member: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("An error occurred during verification. Please try again.", ephemeral=True)
                else:
                    await interaction.followup.send("An error occurred during verification. Please try again.", ephemeral=True)
            except:
                pass

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data.get("custom_id", "").startswith("verify_"):
            return
            
        custom_id = interaction.data["custom_id"]
        
        try:
            if custom_id.startswith("verify_word_"):
                _, _, word, user_id, correct_word = custom_id.split("_")
                if int(user_id) != interaction.user.id:
                    return await interaction.response.send_message("This verification is not for you!", ephemeral=True)
                    
                if word == correct_word:
                    await self.verify_member(interaction)
                else:
                    await interaction.response.send_message("Incorrect word! Try again.", ephemeral=True)
                    
            elif custom_id.startswith("verify_math_"):
                _, _, user_id, correct_answer = custom_id.split("_")
                if int(user_id) != interaction.user.id:
                    return await interaction.response.send_message("This verification is not for you!", ephemeral=True)
                    
                modal = MathVerificationModal(int(correct_answer), self)
                await interaction.response.send_modal(modal)
                
            elif custom_id.startswith("verify_emoji_"):
                _, _, emoji, user_id, correct_emoji = custom_id.split("_")
                if int(user_id) != interaction.user.id:
                    return await interaction.response.send_message("This verification is not for you!", ephemeral=True)
                    
                if emoji == correct_emoji:
                    await self.verify_member(interaction)
                else:
                    await interaction.response.send_message("Incorrect emoji! Try again.", ephemeral=True)
                    
            elif custom_id.startswith("verify_captcha_"):
                _, _, user_id, correct_text = custom_id.split("_")
                if int(user_id) != interaction.user.id:
                    return await interaction.response.send_message("This verification is not for you!", ephemeral=True)
                    
                modal = CaptchaVerificationModal(correct_text, self)
                await interaction.response.send_modal(modal)
                
        except Exception as e:
            print(f"Verification error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)
            else:
                await interaction.followup.send("An error occurred. Please try again.", ephemeral=True)

class SimpleVerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.green,
        custom_id="verify_button"
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await self.bot.db.fetchrow(
            "SELECT * FROM guild_verification WHERE guild_id = $1",
            interaction.guild_id
        )
        
        if not settings:
            return await interaction.response.send_message(
                "Verification is not set up for this server.",
                ephemeral=True
            )
            
        role = interaction.guild.get_role(settings['verified_role_id'])
        if not role:
            return await interaction.response.send_message(
                "Verification role not found. Please contact an administrator.",
                ephemeral=True
            )
            
        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            "✅ You have been verified! Welcome to the server.",
            ephemeral=True
        )

class MathVerificationModal(discord.ui.Modal, title="Math Verification"):
    def __init__(self, correct_answer: int, cog):
        super().__init__()
        self.correct_answer = correct_answer
        self.cog = cog  
        
        self.answer = discord.ui.TextInput(
            label="Your Answer",
            placeholder="Enter the sum",
            required=True,
            max_length=3
        )
        self.add_item(self.answer)
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            if int(self.answer.value) == self.correct_answer:
                await self.cog.verify_member(interaction)  
            else:
                await interaction.response.send_message("Incorrect answer! Try again.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Please enter a valid number!", ephemeral=True)

class CaptchaVerificationModal(discord.ui.Modal, title="Image Verification"):
    def __init__(self, correct_text: str, cog):
        super().__init__()
        self.correct_text = correct_text
        self.cog = cog  
        
        self.text = discord.ui.TextInput(
            label="Image Text",
            placeholder="Enter the text from the image",
            required=True,
            max_length=6
        )
        self.add_item(self.text)
        
    async def on_submit(self, interaction: discord.Interaction):
        if self.text.value == self.correct_text:
            await self.cog.verify_member(interaction) 
        else:
            await interaction.response.send_message("Incorrect text! Try again.", ephemeral=True)