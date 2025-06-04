from discord import TextChannel, Thread, app_commands, Interaction, ForumChannel
from discord.ext.commands import Cog, group, has_permissions
from typing import Optional

from tools import CompositeMetaClass, MixinMeta
from core.client.context import Context
from cogs.config.extended.suggest.modals import SuggestModal, SuggestionView
import discord
from discord import Embed
import datetime

class Suggest(MixinMeta, metaclass=CompositeMetaClass):
    """
    Stick messages to the bottom of a channel.
    """

    @group(name="suggestion", aliases=["suggest"], invoke_without_command=True)
    async def suggestion(self, ctx: Context):
        """
        Let your server members suggest stuff for your server.
        """
        await ctx.send_help(ctx.command)

    @has_permissions(manage_channels=True)
    @suggestion.command(name="channel", example="#suggestions")
    async def suggestion_add(self, ctx: Context, *, channel: Optional[TextChannel | Thread | ForumChannel]):
        """
        Set suggestions channel. Can be a text channel or forum channel.
        """
        if channel is None:
            channel = ctx.channel

        check = await self.bot.db.fetchrow(
            """
            SELECT * 
            FROM suggestion 
            WHERE guild_id = {}
            """
            .format(ctx.guild.id)
        )
       
        if check is not None:
            await self.bot.db.execute(
                """
                UPDATE suggestion 
                SET channel_id = $1 
                WHERE guild_id = $2
                """,
                channel.id,
                ctx.guild.id,
            )
        
        elif check is None:
            await self.bot.db.execute(
                """
                INSERT INTO 
                suggestion 
                (channel_id, guild_id)
                VALUES($1, $2)
                """, 
                channel.id, 
                ctx.guild.id
            )
        
        return await ctx.approve(f"I have set the suggestion channel to {channel.mention}.")
    
    @has_permissions(manage_channels=True)
    @suggestion.command(name="remove")
    async def suggestion_remove(self, ctx: Context):
        """
        Remove the suggestions config.
        """
        check = await self.bot.db.fetchrow("SELECT * FROM suggestion WHERE guild_id = $1", ctx.guild.id)
        if check is None:
            return await ctx.warn("Suggestions are already disabled.")
        
        await ctx.prompt("Are you sure you would like to remove the suggestion system?")
        await self.bot.db.execute("DELETE FROM suggestion WHERE guild_id = $1", ctx.guild.id)
        return await ctx.approve("Removed the suggestion channel.")
    
    @has_permissions(manage_messages=True)
    @suggestion.command(name="mute", example="43")
    async def suggestion_mute(self, ctx: Context, *, number: int):
        """
        Mute a member that send a specific suggestion.
        """
        check = await self.bot.db.fetchrow(
            "SELECT channel_id FROM suggestion WHERE guild_id = {}".format(ctx.guild.id)
        )
        if check is None:
            return await ctx.warn("Suggestions aren't **enabled** in this server.")

        re = await self.bot.db.fetchrow(
            """
            SELECT * FROM suggestion 
            WHERE guild_id = $1 
            AND suggestion_id = $2""",
            ctx.guild.id,
            number,
        )
        if re is None:
            return await ctx.warn("I **couldn't** find that suggestion.")

        member_id = re["author_id"]

        r = await self.bot.db.fetchrow(
            """
            SELECT * FROM confess_mute 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            ctx.guild.id,
            member_id,
        )
        if r:
            return await ctx.warn("This **member** is **already** suggestion muted.")

        await self.bot.db.execute(
            """
            INSERT INTO suggestion
            (guild_id, blacklisted_id)
            VALUES ($1,$2)
            """, 
            ctx.guild.id, 
            member_id
        )
        return await ctx.approve(
            f"I have **muted** the author of confession #{number}."
        )

    @app_commands.command(name="suggest", description="Create a new suggestion")
    @app_commands.describe(
        description="Detailed explanation of your suggestion",
        title="Brief summary of your suggestion (optional)",
        image="Attach an image to your suggestion (optional)"
    )
    async def suggest_slash(
        self, 
        interaction: Interaction, 
        description: str,
        title: Optional[str] = None,
        image: Optional[discord.Attachment] = None
    ):
        suggestion_data = await self.bot.db.fetchrow(
            """
            UPDATE suggestion 
            SET suggestion_id = COALESCE(suggestion_id, 0) + 1 
            WHERE guild_id = $1 
            RETURNING *
            """,
            interaction.guild.id
        )
        
        if not suggestion_data:
            return await interaction.response.send_message(
                "Suggestions are not enabled in this server!", ephemeral=True
            )

        if "http" in description.lower():
            return await interaction.response.send_message(
                "Links are not allowed in suggestions!", ephemeral=True
            )

        channel = interaction.guild.get_channel(suggestion_data["channel_id"])
        count = suggestion_data["suggestion_id"]
        is_anonymous = suggestion_data.get('anonymous_allowed', False)

        embed = Embed(
            description=description,
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        if title:
            embed.title = title

        embed.set_author(
            name=f"Suggestion #{count}" + (" (Anonymous)" if is_anonymous else ""),
            icon_url=interaction.guild.icon
        )

        embed.add_field(
            name="Votes",
            value=f"👍 `0` • 👎 `0`",
            inline=False
        )

        if not is_anonymous:
            embed.set_footer(
                text=f"Suggested by {interaction.user}",
                icon_url=interaction.user.display_avatar.url
            )
        else:
            embed.set_footer(text="Anonymous Suggestion")

        if image:
            embed.set_image(url=image.url)

        msg = None
        if isinstance(channel, discord.ForumChannel):
            thread_name = title if title else f"Suggestion #{count}"
            if not title:
                thread_name = f"Suggestion #{count}"
            else:
                thread_name = f"{title} #{count}"
            
            thread = await channel.create_thread(
                name=thread_name,
                content="",
                embed=embed,
                view=SuggestionView(self.bot)
            )
            msg = thread.message
        else:
            msg = await channel.send(embed=embed, view=SuggestionView(self.bot))
            if suggestion_data.get("thread_enabled", False):
                await msg.create_thread(
                    name=f"Suggestion #{count} Discussion",
                    auto_archive_duration=1440
                )

        # await self.bot.db.execute(
        #     """UPDATE suggestion 
        #     SET suggestion_id = $1 
        #     WHERE guild_id = $2""",
        #     count,
        #     interaction.guild.id
        # )

        await self.bot.db.execute(
            """INSERT INTO suggestion_entries 
            (guild_id, message_id, author_id, suggestion_id, is_anonymous)
            VALUES ($1, $2, $3, $4, $5)""",
            interaction.guild.id,
            msg.id if msg else 0,
            interaction.user.id,
            count,
            is_anonymous
        )

        success_embed = Embed(
            title="✅ Suggestion Posted",
            description=f"Your suggestion has been posted in {channel.mention}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=success_embed, ephemeral=True)

    @app_commands.command(name="suggest_edit", description="Edit your previous suggestion")
    @app_commands.describe(
        suggestion_id="The ID of the suggestion to edit",
        new_title="New title for the suggestion (optional)",
        new_description="New description for the suggestion",
        new_image="New image for the suggestion (optional)"
    )
    async def suggest_edit(
        self,
        interaction: Interaction,
        suggestion_id: int,
        new_description: str,
        new_title: Optional[str] = None,
        new_image: Optional[discord.Attachment] = None
    ):
        """Edit a previous suggestion"""
        suggestion = await self.bot.db.fetchrow(
            """
            SELECT se.*, s.channel_id 
            FROM suggestion_entries se
            JOIN suggestion s ON s.guild_id = se.guild_id
            WHERE se.guild_id = $1 
            AND se.suggestion_id = $2 
            AND se.author_id = $3
            AND se.is_anonymous = false
            """,
            interaction.guild.id,
            suggestion_id,
            interaction.user.id
        )

        if not suggestion:
            return await interaction.response.send_message(
                "You cannot edit this suggestion (it either doesn't exist, isn't yours, or was posted anonymously).",
                ephemeral=True
            )

        if "http" in new_description.lower():
            return await interaction.response.send_message(
                "Links are not allowed in suggestions", ephemeral=True
            )

        channel = interaction.guild.get_channel(suggestion["channel_id"])
        
        message = None
        if isinstance(channel, discord.ForumChannel):
            threads = [thread async for thread in channel.archived_threads(limit=None)]
            threads.extend(channel.threads)
            
            for thread in threads:
                if thread.name.startswith(f"Suggestion #{suggestion_id}"):
                    message = thread.starter_message or await thread.fetch_message(thread.id)
                    break
        else:
            message = await channel.fetch_message(suggestion["message_id"])

        if not message:
            return await interaction.response.send_message(
                "Could not find the suggestion message to edit.", ephemeral=True
            )

        embed = message.embeds[0]
        embed.title = new_title or embed.title
        embed.description = new_description
        
        if new_image:
            embed.set_image(url=new_image.url)

        await message.edit(embed=embed)
        
        if isinstance(channel, discord.ForumChannel) and message.thread:
            if new_title:
                new_thread_name = f"{new_title} #{suggestion_id}"
            else:
                new_thread_name = f"Suggestion #{suggestion_id}"
            await message.thread.edit(name=new_thread_name)

        return await interaction.response.send_message(
            "Your suggestion has been updated", ephemeral=True
        )

    @has_permissions(manage_channels=True)
    @suggestion.command(name="settings")
    async def suggestion_settings(self, ctx: Context):
        """View and modify suggestion settings"""
        settings = await self.bot.db.fetchrow(
            "SELECT * FROM suggestion WHERE guild_id = $1", ctx.guild.id
        )
        
        if not settings:
            return await ctx.warn("Suggestions are not enabled in this server.")

        embed = Embed(title="Suggestion Settings", color=discord.Color.blue())
        embed.add_field(
            name="Channel",
            value=f"<#{settings['channel_id']}>",
            inline=False
        )
        embed.add_field(
            name="Auto-Thread",
            value="✅ Enabled" if settings.get('thread_enabled') else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Anonymous Suggestions",
            value="✅ Allowed" if settings.get('anonymous_allowed') else "❌ Disabled",
            inline=True
        )
        
        await ctx.send(embed=embed)

    @has_permissions(manage_channels=True)
    @suggestion.command(name="threads")
    async def suggestion_threads(self, ctx: Context, enabled: bool):
        """Enable/disable automatic thread creation for suggestions"""
        await self.bot.db.execute(
            """UPDATE suggestion 
            SET thread_enabled = $1 
            WHERE guild_id = $2""",
            enabled,
            ctx.guild.id
        )
        
        await ctx.approve(
            f"Auto-threads for suggestions have been {'enabled' if enabled else 'disabled'}."
        )

    @has_permissions(manage_channels=True)
    @suggestion.command(name="anonymous")
    async def suggestion_anonymous(self, ctx: Context, enabled: bool):
        """Enable/disable anonymous suggestions"""
        await self.bot.db.execute(
            """UPDATE suggestion 
            SET anonymous_allowed = $1 
            WHERE guild_id = $2""",
            enabled,
            ctx.guild.id
        )
        
        await ctx.approve(
            f"Anonymous suggestions have been {'enabled' if enabled else 'disabled'}."
        )

async def setup(bot):
    await bot.add_cog(Suggest(bot))
    bot.add_view(SuggestionView(bot))
