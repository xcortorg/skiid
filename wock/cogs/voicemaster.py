from typing import Union  # noqa: F401

import discord  # type: ignore
from discord.ext import commands  # type: ignore
from discord.ui import View  # type: ignore
from tools import views
from tools.views import RenameModal, reclaim


class VmButtons(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.value = None

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="<:wock_lock:1207661056554700810>",
        custom_id="lock_button",
    )
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice:
            embed = discord.Embed(
                description="> You **aren't** connected to a **Voicemaster channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not interaction.user.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            interaction.user.voice.channel.id,
            interaction.guild.id,
        ):
            embed = discord.Embed(
                description="> You **don't own** this **voice channel**", color=0x2D2B31
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            interaction.guild.id,
            interaction.user.id,
            interaction.user.voice.channel.id,
        )
        if channel_id:
            vc = interaction.guild.get_channel(channel_id)
            if vc.overwrites_for(interaction.guild.default_role).connect is False:
                embed = discord.Embed(
                    description="> Your **voice channel** is already **locked**",
                    color=0x2D2B31,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )
            await vc.set_permissions(interaction.guild.default_role, connect=False)
            embed = discord.Embed(
                description="> Your **voice channel** has been **locked**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="<:wock_unlock:1207661072086073344>",
        custom_id="unlock_button",
    )
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice:
            embed = discord.Embed(
                description="> You **aren't** connected to a **voicemaster channel**"
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not interaction.user.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            interaction.user.voice.channel.id,
            interaction.guild.id,
        ):
            embed = discord.Embed(
                description="> You **don't own** this **voice channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            interaction.guild.id,
            interaction.user.id,
            interaction.user.voice.channel.id,
        )
        if channel_id:
            vc = interaction.guild.get_channel(channel_id)
            if vc.overwrites_for(interaction.guild.default_role).connect is True:
                embed = discord.Embed(
                    description="> Your **voice channel** isn't **locked**",
                    color=0x2D2B31,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )
            await vc.set_permissions(interaction.guild.default_role, connect=True)
            embed = discord.Embed(
                description="> Your **voice channel** has been **unlocked**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="<:wock_hide:1207661052288827393>",
        custom_id="hide_button",
    )
    async def hide(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.user.voice:
                embed = discord.Embed(
                    description="> You **aren't** connected to a **voicemaster channel**",
                    color=0x2D2B31,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )

            if not interaction.user.id == await self.bot.db.fetchval(
                """
                SELECT owner_id
                FROM voicemaster_data
                WHERE channel_id = $1
                AND guild_id = $2
                """,
                interaction.user.voice.channel.id,
                interaction.guild.id,
            ):
                embed = discord.Embed(
                    description="> You **don't own** this **voice channel**",
                    color=0x2D2B31,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )

            channel_id = await self.bot.db.fetchval(
                """
                SELECT channel_id
                FROM voicemaster_data
                WHERE guild_id = $1
                AND owner_id = $2
                AND channel_id = $3
                """,
                interaction.guild.id,
                interaction.user.id,
                interaction.user.voice.channel.id,
            )
            if channel_id:
                vc = interaction.guild.get_channel(channel_id)
                if (
                    vc.overwrites_for(interaction.guild.default_role).view_channel
                    is False
                ):
                    embed = discord.Embed(
                        description="> Your **voice channel** is **already hidden**",
                        color=0x2D2B31,
                    )
                    return await interaction.response.send_message(
                        embed=embed, ephemeral=True
                    )
                await vc.set_permissions(
                    interaction.guild.default_role, view_channel=False
                )
                embed = discord.Embed(
                    description="> Your **voice channel** has been **hidden**",
                    color=0x2D2B31,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(e)

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="<:wock_view:1207661072929132645>",
        custom_id="reveal_button",
    )
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice:
            embed = discord.Embed(
                description="> You **aren't** connected to a **Voicemaster channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not interaction.user.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            interaction.user.voice.channel.id,
            interaction.guild.id,
        ):
            embed = discord.Embed(
                description="> You **don't own** this **voice channel**", color=0x2D2B31
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            interaction.guild.id,
            interaction.user.id,
            interaction.user.voice.channel.id,
        )
        if channel_id:
            vc = interaction.guild.get_channel(channel_id)
            if vc.overwrites_for(interaction.guild.default_role).view_channel is True:
                embed = discord.Embed(
                    description="> Your **voice channel** isn't **hidden**",
                    color=0x2D2B31,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )
            await vc.set_permissions(interaction.guild.default_role, view_channel=True)
            embed = discord.Embed(
                description="> Your **voice channel** is **no longer hidden**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="<:wock_rename:1207661067707093003>",
        custom_id="rename_button",
    )
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice:
            embed = discord.Embed(
                description="> You **aren't** connected to a **Voicemaster channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not interaction.user.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            interaction.user.voice.channel.id,
            interaction.guild.id,
        ):
            embed = discord.Embed(
                description="> You **don't own** this **voice channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            interaction.guild.id,
            interaction.user.id,
            interaction.user.voice.channel.id,
        )
        if channel_id:
            await interaction.response.send_modal(RenameModal(self.bot))

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="<:wock_owner:1207661061264904222>",
        custom_id="claim_button",
    )
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Check if the user is not connected to a voice channel
            if not interaction.user.voice:
                embed = discord.Embed(
                    description="> You **aren't** connected to a **Voicemaster channel**",
                    color=0x2D2B31,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )

            # Check if the user is not the owner of the current voice channel
            channel_data = await self.bot.db.fetchrow(
                """
                SELECT channel_id, owner_id
                FROM voicemaster_data
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                interaction.guild.id,
                interaction.user.voice.channel.id,
            )

            if not channel_data:
                embed = discord.Embed(
                    description="> You do not **own** the current **voice channel**",
                    color=0x2D2B31,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )

            channel_id, owner_id = channel_data

            # Check if the owner is not in the voice channel
            owner = interaction.guild.get_member(owner_id)
            if owner and owner in interaction.user.voice.channel.members:
                embed = discord.Embed(
                    description="> The owner is **still** in the **voice channel**",
                    color=0x2D2B31,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )
            await reclaim(interaction.user.voice.channel, owner, interaction.user)
            # Update the owner in the database
            await self.bot.db.execute(
                """
                UPDATE voicemaster_data
                SET owner_id = $1
                WHERE guild_id = $2
                AND channel_id = $3
                """,
                interaction.user.id,
                interaction.guild.id,
                channel_id,
            )
            embed = discord.Embed(
                description="> You are now the **owner** of the **voice channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            return await interaction.response.send_message(str(e), ephemeral=True)

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="<:wock_add:1207661050951106580>",
        custom_id="increase_button",
    )
    async def increase(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not interaction.user.voice:
            embed = discord.Embed(
                description="> You **aren't** connected to a **voicemaster channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not interaction.user.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            interaction.user.voice.channel.id,
            interaction.guild.id,
        ):
            embed = discord.Embed(
                description="> You **don't own** this **voice channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            interaction.guild.id,
            interaction.user.id,
            interaction.user.voice.channel.id,
        )
        if channel_id:
            vc = interaction.guild.get_channel(channel_id)
            await vc.edit(user_limit=vc.user_limit + 1)
            embed = discord.Embed(
                description=f"> Your **voice channel's user limit** has been **increased** to `{vc.user_limit}`",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="<:wock_minus:1207661058114715698>",
        custom_id="decrease_button",
    )
    async def decrease(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not interaction.user.voice:
            embed = discord.Embed(
                description="> You **aren't** connected to a **voicemaster channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not interaction.user.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            interaction.user.voice.channel.id,
            interaction.guild.id,
        ):
            embed = discord.Embed(
                description="> You **don't own** this **voice channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            interaction.guild.id,
            interaction.user.id,
            interaction.user.voice.channel.id,
        )
        if channel_id:
            vc = interaction.guild.get_channel(channel_id)
            await vc.edit(user_limit=vc.user_limit - 1)
            embed = discord.Embed(
                description=f"> Your **voice channel's user limit** has been **decreased** to `{vc.user_limit}`"
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="<:wock_trash:1207661070936703007>",
        custom_id="delete_button",
    )
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice:
            embed = discord.Embed(
                description="> You **aren't** connected to a **voicemaster channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not interaction.user.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            interaction.user.voice.channel.id,
            interaction.guild.id,
        ):
            embed = discord.Embed(
                description="> You **don't own** this **voice channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            interaction.guild.id,
            interaction.user.id,
            interaction.user.voice.channel.id,
        )
        if channel_id:
            vc = interaction.guild.get_channel(channel_id)
            await self.bot.db.execute(
                """
                DELETE FROM voicemaster_data
                WHERE channel_id = $1
                """,
                vc.id,
            )
            await vc.delete()
            embed = discord.Embed(
                description="> Your **voice channel** has been **deleted**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="<:wock_list:1207661055338086440>",
        custom_id="information_button",
    )
    async def information(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not interaction.user.voice:
            embed = discord.Embed(
                description="> You **aren't** connected to a **Voicemaster channel**",
                color=0x2D2B31,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            interaction.guild.id,
            interaction.user.id,
            interaction.user.voice.channel.id,
        )
        if channel_id:
            vc = interaction.guild.get_channel(channel_id)
            owner = await self.bot.db.fetchval(
                """
                SELECT owner_id
                FROM voicemaster_data
                WHERE channel_id = $1
                AND guild_id = $2
                """,
                interaction.user.voice.channel.id,
                interaction.guild.id,
            )
            owner = interaction.guild.get_member(owner)
            embed = discord.Embed(
                color=self.bot.color,
                description=f""">>> **Bitrate:** {vc.bitrate/1000} KBPS
**Members:** {len(vc.members)}
**Created:** <t:{round(vc.created_at.timestamp())}:D>
**Owner:** {owner.mention}""",
            )
            embed.set_author(name=vc.name, icon_url=owner.display_avatar)
            embed.set_thumbnail(url=owner.display_avatar)
            return await interaction.response.send_message(embed=embed, ephemeral=True)


class Voicemaster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(
        name="voicemaster", aliases=["vm", "vc"], invoke_without_command=True
    )
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster(self, ctx):
        """Manage the voicemaster interface configuration"""

        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @voicemaster.command(
        name="setup",
        aliases=["create", "start", "configure"],
        brief="setup a voicemaster configuration",
    )
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def setup(self, ctx, category: discord.CategoryChannel = None):
        data = await self.bot.db.fetch(
            """
            SELECT *
            FROM voicemaster
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if not data:
            category = await ctx.guild.create_category_channel("wock voicemaster")
            text = await ctx.guild.create_text_channel("menu", category=category)
            await text.set_permissions(
                ctx.guild.default_role,
                overwrite=discord.PermissionOverwrite(
                    send_messages=False, add_reactions=False
                ),
            )
            voice = await ctx.guild.create_voice_channel("create", category=category)

            # Setting author as guild name and icon as guild's profile picture if available
            guild_name = ctx.guild.name
            guild_icon = ctx.guild.icon.url if ctx.guild.icon else None

            embed = discord.Embed(
                color=0x2B2D31,
                title="**Voicemaster Menu**",
                description="Click on the buttons below to control your voice channel",
            )
            embed.set_author(name=guild_name, icon_url=guild_icon)
            embed.set_thumbnail(url=self.bot.user.avatar if ctx.guild.icon else None)

            message = await text.send(
                embed=embed, view=views.VoicemasterInterface(self.bot)
            )
            await self.bot.db.execute(
                """INSERT INTO voicemaster
                (guild_id, category_id, voicechannel_id, channel_id, message_id)
                VALUES ($1, $2, $3, $4, $5)
                """,
                ctx.guild.id,
                category.id,
                voice.id,
                text.id,
                message.id,
            )
            await ctx.success("**Voicemaster interface** has been **setup.**")
        else:
            await ctx.fail("**Voicemaster interface** has already been **setup**")

    @voicemaster.command(
        name="reset", aliases=["remove"], brief="reset the voicemaster configuration"
    )
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def reset(self, ctx):
        if data := await self.bot.db.fetch(
            """
            SELECT voicechannel_id,
            channel_id, category_id
            FROM voicemaster
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        ):
            for voice, text, category in data:
                try:
                    vc = ctx.guild.get_channel(voice)
                    txt = ctx.guild.get_channel(text)
                    if vc:
                        await vc.delete()
                    if txt:
                        if category := ctx.guild.get_channel(category):
                            await category.delete()
                        await txt.delete()
                    await self.bot.db.execute(
                        """
                        DELETE FROM voicemaster
                        WHERE guild_id = $1
                        AND voicechannel_id = $2
                        AND channel_id = $3
                        """,
                        ctx.guild.id,
                        voice,
                        text,
                    )
                except discord.errors.NotFound:
                    pass

            active_vcs = []
            if active_vc := await self.bot.db.fetch(
                """
                SELECT channel_id
                FROM voicemaster_data
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            ):
                for vc in active_vc:
                    if vc := ctx.guild.get_channel(vc["channel_id"]):
                        active_vcs.append(vc)

            if active_vcs:
                for vc in active_vcs:
                    try:
                        try:
                            await vc.delete()
                        except Exception:
                            pass
                        await self.bot.db.execute(
                            """
                            DELETE FROM voicemaster_data
                            WHERE guild_id = $1
                            AND channel_id = $2
                            """,
                            ctx.guild.id,
                            vc.id,
                        )
                    except discord.errors.NotFound:
                        pass

            return await ctx.success("**Voicemaster interface** has been **reset**")

        return await ctx.fail("**Voicemaster interface** hasn't been **set up**")

    @voicemaster.command(name="lock", brief="lock your voice channel")
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx):
        if not ctx.author.voice:
            return await ctx.fail("You **are not** in a **voice channel**")

        if not ctx.author.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            ctx.author.voice.channel.id,
            ctx.guild.id,
        ):
            return await ctx.fail("You **don't own** this **voice channel**")

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.author.voice.channel.id,
        )
        if channel_id:
            vc = ctx.guild.get_channel(channel_id)
            if vc.overwrites_for(ctx.guild.default_role).connect is False:
                return await ctx.fail("Your **voice channel** is already **locked**")

            await vc.set_permissions(ctx.guild.default_role, connect=False)
            return await ctx.success("Your **voice channel** has been **locked**")

    @voicemaster.command(name="unlock", brief="unlock your voice channel")
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        if not ctx.author.voice:
            return await ctx.fail("You **are not** in a **voice channel**")

        if not ctx.author.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            ctx.author.voice.channel.id,
            ctx.guild.id,
        ):
            return await ctx.fail("You **don't own** this **voice channel**")

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.author.voice.channel.id,
        )
        if channel_id:
            vc = ctx.guild.get_channel(channel_id)
            if vc.overwrites_for(ctx.guild.default_role).connect is True:
                return await ctx.fail("Your **voice channel** isn't **locked**")

            await vc.set_permissions(ctx.guild.default_role, connect=True)
            return await ctx.success("Your **voice channel** has been **unlocked**")

    @voicemaster.command(
        name="hide", aliases=["ghost"], brief="hide your voice channel"
    )
    @commands.bot_has_permissions(manage_channels=True)
    async def hide(self, ctx):
        if not ctx.author.voice:
            return await ctx.fail("You **are not** in a **voice channel**")

        if not ctx.author.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            ctx.author.voice.channel.id,
            ctx.guild.id,
        ):
            return await ctx.fail("You **don't own** this **voice channel**")

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.author.voice.channel.id,
        )
        if channel_id:
            vc = ctx.guild.get_channel(channel_id)
            if vc.overwrites_for(ctx.guild.default_role).view_channel is False:
                return await ctx.fail("Your **voice channel** is already **hidden**")
            await vc.set_permissions(ctx.guild.default_role, view_channel=False)
            return await ctx.success("Your **voice channel** is now **hidden**")

    @voicemaster.command(
        name="reveal",
        aliases=["show", "unhide"],
        brief="reveal your hidden voice channel",
    )
    @commands.bot_has_permissions(manage_channels=True)
    async def reveal(self, ctx):
        if not ctx.author.voice:
            return await ctx.fail("You **are not** in a **voice channel**")

        if not ctx.author.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            ctx.author.voice.channel.id,
            ctx.guild.id,
        ):
            return await ctx.fail("You **don't own** this **voice channel**")

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.author.voice.channel.id,
        )
        if channel_id:
            vc = ctx.guild.get_channel(channel_id)
            if vc.overwrites_for(ctx.guild.default_role).view_channel is True:
                return await ctx.fail("Your **voice channel** isn't **hidden**")
            await vc.set_permissions(ctx.guild.default_role, view_channel=True)
            return await ctx.success("Your **voice channel** is no longer **hidden**")

    @voicemaster.command(
        name="rename", aliases=["name"], brief="rename your voice channel"
    )
    @commands.bot_has_permissions(manage_channels=True)
    async def rename(self, ctx, *, name):
        if not ctx.author.voice:
            return await ctx.fail("You **are not** in a **voice channel**")

        if not ctx.author.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            ctx.author.voice.channel.id,
            ctx.guild.id,
        ):
            return await ctx.fail("You **don't own** this **voice channel**")

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.author.voice.channel.id,
        )
        if channel_id:
            vc = ctx.guild.get_channel(channel_id)
            await vc.edit(name=name)
            return await ctx.success(
                f"""Your **voice channel** has been renamed to **{name}**"""
            )

    @voicemaster.command(
        name="status", brief="set the status of all of your voice master channels"
    )
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_status(self, ctx: commands.Context, *, status: str):
        await self.bot.db.execute(
            """INSERT INTO vm_status (user_id, status) VALUES($1, $2) ON CONFLICT(user_id) DO UPDATE SET status = excluded.status""",
            ctx.author.id,
            status[:499],
        )
        if ctx.author.voice:
            await ctx.author.voice.channel.edit(status=status[:499])
        return await ctx.success(
            f"**voicemaster status** has been set to `{status[:499]}`"
        )

    @voicemaster.command(
        name="claim", aliases=["own"], brief="claim an unclaimed voice channel"
    )
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_claim(self, ctx):
        if not ctx.author.voice:
            return await ctx.fail("You **are not** in a **voice channel**")

        # Check if the user is not the owner of the current voice channel
        channel_data = await self.bot.db.fetchrow(
            """
            SELECT channel_id, owner_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            ctx.guild.id,
            ctx.author.voice.channel.id,
        )

        if not channel_data:
            return await ctx.fail("You **don't own** this **voice channel**")

        channel_id, owner_id = channel_data

        # Check if the owner is not in the voice channel
        owner = ctx.guild.get_member(owner_id)
        if owner and owner in ctx.author.voice.channel.members:
            return await ctx.fail("The **owner** is still in the **voice channel**")
        await reclaim(ctx.author.voice.channel, owner, ctx.author)
        # Update the owner in the database
        await self.bot.db.execute(
            """
            UPDATE voicemaster_data
            SET owner_id = $1
            WHERE guild_id = $2
            AND channel_id = $3
            """,
            ctx.author.id,
            ctx.guild.id,
            channel_id,
        )

        return await ctx.success("You are now the **owner** of this **voice channel**")

    @voicemaster.command(
        name="information", brief="view information on the current voice channel"
    )
    async def voicemaster_information(self, ctx):
        if not ctx.author.voice:
            return await ctx.fail("You **are not** in a **voice channel**")

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.author.voice.channel.id,
        )
        if channel_id:
            vc = ctx.guild.get_channel(channel_id)
            owner = await self.bot.db.fetchval(
                """
                SELECT owner_id
                FROM voicemaster_data
                WHERE channel_id = $1
                AND guild_id = $2
                """,
                ctx.author.voice.channel.id,
                ctx.guild.id,
            )
            owner = ctx.guild.get_member(owner)
            embed = discord.Embed(
                color=self.bot.color,
                description=f""">>> **Bitrate:** {vc.bitrate/1000} KBPS
**Members:** {len(vc.members)}
**Created:** <t:{round(vc.created_at.timestamp())}:D>
**Owner:** {owner.mention}""",
            )
            embed.set_author(name=vc.name, icon_url=owner.display_avatar)
            embed.set_thumbnail(url=owner.display_avatar)
            return await ctx.send(embed=embed)

    @voicemaster.command(
        name="limit", brief="limit the amount of users that can join your voice channel"
    )
    @commands.bot_has_permissions(manage_channels=True)
    async def limit(self, ctx, limit: int):
        if not ctx.author.voice:
            return await ctx.fail("You **are not** in a **voice channel**")

        if limit > 99:
            return await ctx.fail("User limit **cannot** be higher than `99`")

        if not ctx.author.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            ctx.author.voice.channel.id,
            ctx.guild.id,
        ):
            return await ctx.fail("You **don't own** this **voice channel**")

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.author.voice.channel.id,
        )
        if channel_id:
            vc = ctx.guild.get_channel(channel_id)
            await vc.edit(user_limit=limit)
            return await ctx.success(
                f"""Your **voice channel's user limit** has been set to `{limit}`"""
            )

    @voicemaster.command(name="delete", brief="delete your voice channel")
    @commands.bot_has_permissions(manage_channels=True)
    async def delete(self, ctx):
        if not ctx.author.voice:
            return await ctx.fail("You **are not** in a **voice channel**")

        if not ctx.author.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            ctx.author.voice.channel.id,
            ctx.guild.id,
        ):
            return await ctx.fail("You **don't own** this **voice channel**")

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.author.voice.channel.id,
        )
        if channel_id:
            vc = ctx.guild.get_channel(channel_id)
            await self.bot.db.execute(
                """
                DELETE FROM voicemaster_data
                WHERE channel_id = $1
                """,
                channel_id,
            )
            await vc.delete()
            return await ctx.success("""Your **voice channel** has been **deleted**""")

    @voicemaster.command(
        name="reject",
        aliases=["kick"],
        brief="reject and kick a user out of your voice channel",
    )
    @commands.bot_has_permissions(manage_channels=True)
    async def reject(self, ctx, *, member: discord.Member):
        if not ctx.author.voice:
            return await ctx.fail("You **are not** in a **voice channel**")

        if not ctx.author.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            ctx.author.voice.channel.id,
            ctx.guild.id,
        ):
            return await ctx.fail("You **don't own** this **voice channel**")

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.author.voice.channel.id,
        )
        if channel_id:
            vc = ctx.guild.get_channel(channel_id)
            overwrite = vc.overwrites_for(member)
            overwrite.connect = False
            overwrite.view_channel = False
            await vc.set_permissions(member, overwrite=overwrite)

            if member.voice and member.voice.channel == vc:
                await member.move_to(None)
                await ctx.success(
                    f"**Kicked** {member.mention} and **revoked access** to your **voice channel**"
                )
            else:
                await ctx.success(
                    f"**Revoked** {member.mention}'s access to your **voice channel**"
                )

    @voicemaster.command(
        name="permit",
        aliases=["allow"],
        brief="permit a user to join your voice channel",
    )
    @commands.bot_has_permissions(manage_channels=True)
    async def permit(self, ctx, *, member: discord.Member):
        if not ctx.author.voice:
            return await ctx.fail("You **are not** in a **voice channel**")

        if not ctx.author.id == await self.bot.db.fetchval(
            """
            SELECT owner_id
            FROM voicemaster_data
            WHERE channel_id = $1
            AND guild_id = $2
            """,
            ctx.author.voice.channel.id,
            ctx.guild.id,
        ):
            return await ctx.fail("You **don't own** this **voice channel**")

        channel_id = await self.bot.db.fetchval(
            """
            SELECT channel_id
            FROM voicemaster_data
            WHERE guild_id = $1
            AND owner_id = $2
            AND channel_id = $3
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.author.voice.channel.id,
        )
        if channel_id:
            vc = ctx.guild.get_channel(channel_id)
            overwrite = vc.overwrites_for(member)
            overwrite.connect = True
            overwrite.view_channel = True
            await vc.set_permissions(member, overwrite=overwrite)
            await ctx.success(
                f"**Permitted** {member.mention} to access your **voice channel**"
            )


async def setup(bot):
    await bot.add_cog(Voicemaster(bot))
