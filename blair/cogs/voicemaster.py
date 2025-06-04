import random

import asyncpg
import discord
from discord.ext import commands
from discord.ui import Button, View
from tools.config import color, emoji
from tools.context import Context


class Voicemaster(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def load(self, guild):
        row = await self.client.pool.fetchrow(
            "SELECT * FROM voicemaster WHERE guild_id = $1", guild.id
        )
        if row:
            category = guild.get_channel(row["category_id"])
            interface = guild.get_channel(row["interface_id"])
            channel = guild.get_channel(row["create_channel_id"])
            return category, interface, channel
        return None, None, None

    async def save(self, guild, category, interface, channel):
        category_id = category.id if category else None
        interface_id = interface.id if interface else None
        channel_id = channel.id if channel else None

        await self.client.pool.execute(
            """
            INSERT INTO voicemaster (guild_id, category_id, interface_id, create_channel_id) 
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id) 
            DO UPDATE SET category_id = $2, interface_id = $3, create_channel_id = $4
            """,
            guild.id,
            category_id,
            interface_id,
            channel_id,
        )

    async def set_owner(self, channel_id, owner_id):
        await self.client.pool.execute(
            """
            INSERT INTO vc_owners (channel_id, owner_id) 
            VALUES ($1, $2)
            ON CONFLICT (channel_id) 
            DO UPDATE SET owner_id = $2
            """,
            channel_id,
            owner_id,
        )

    async def get_owner(self, channel_id):
        row = await self.client.pool.fetchrow(
            "SELECT owner_id FROM vc_owners WHERE channel_id = $1", channel_id
        )
        return row["owner_id"] if row else None

    @commands.group(description="VoiceMaster with an interface", aliases=["vm"])
    @commands.has_permissions(manage_channels=True)
    async def voicemaster(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @voicemaster.command(
        name="setup", description="Setup the VoiceMaster", aliases=["sp"]
    )
    @commands.has_permissions(manage_channels=True)
    async def voicemaster_setup(self, ctx: Context):
        guild = ctx.guild

        category, interface, channel = await self.load(guild)

        if category:
            await ctx.deny("Voicemaster is already **set up**")
            return

        category = await guild.create_category("Voicemaster")
        channel = await guild.create_voice_channel("Join to create", category=category)
        interface = await guild.create_text_channel("Interface", category=category)
        await interface.set_permissions(
            guild.default_role, send_messages=False, view_channel=True
        )

        await self.save(guild, category, interface, channel)

        await ctx.agree("**Set** the voicemaster up")
        await self.send_interface_message(guild, interface)

    @voicemaster.command(
        name="unsetup", description="Unsetup the VoiceMaster", aliases=["unsp"]
    )
    @commands.has_permissions(manage_channels=True)
    async def voicemaster_unsetup(self, ctx: Context):
        guild = ctx.guild

        category, interface, channel = await self.load(guild)

        if not category:
            await ctx.deny("Voicemaster **wasn't** set up")
            return

        for ch in category.channels:
            await ch.delete()
        await category.delete()

        await self.client.pool.execute(
            "DELETE FROM voicemaster WHERE guild_id = $1", guild.id
        )

        await ctx.agree("**Unsetup** the Voicemaster setup")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild = member.guild
        category, interface, channel = await self.load(guild)

        if after.channel and after.channel == channel:
            new_channel = await after.channel.guild.create_voice_channel(
                f"{member.display_name}'s lounge",
                category=category,
                user_limit=after.channel.user_limit,
            )
            await new_channel.set_permissions(
                member, connect=True, manage_channels=True
            )
            await self.set_owner(new_channel.id, member.id)
            await member.move_to(new_channel)

        if before.channel and before.channel != channel and not before.channel.members:
            if before.channel.category == category and before.channel != channel:
                await before.channel.delete()
        elif before.channel and before.channel != channel and before.channel.members:
            owner_id = await self.get_owner(before.channel.id)
            if owner_id == member.id:
                if before.channel.members:
                    new_owner = random.choice(before.channel.members)
                    await before.channel.set_permissions(
                        new_owner, connect=True, manage_channels=True
                    )
                    await self.set_owner(before.channel.id, new_owner.id)
                else:
                    await self.client.pool.execute(
                        "DELETE FROM vc_owners WHERE channel_id = $1", before.channel.id
                    )

    async def send_interface_message(self, guild, interface):
        embed = discord.Embed(
            title="",
            description=f"> **Control** your voice channel with buttons",
            color=color.default,
        )
        embed.set_thumbnail(url=guild.icon.url)
        embed.set_author(name="Blare Voicemaster", icon_url=self.client.user.avatar.url)
        embed.add_field(
            name="",
            value=(
                "<:26:1298731245320011856>  [`lock`](https://discord.gg/blare) the voice channel\n"
                "<:27:1298731243059286077>  [`unlock`](https://discord.gg/blare) the voice channel\n"
                "<:23:1298731251641090089>  [`hide`](https://discord.gg/blare) the voice channel\n"
                "<:22:1298731253473874003>  [`reveal`](https://discord.gg/blare) the voice channel\n"
                "<:29:1298731238655266847> [`kick`](https://discord.gg/blare) a user from the voice channel\n"
                "<:24:1298731249497538632> [`increase`](https://discord.gg/blare) the voice channel limit\n"
                "<:21:1298731255621226496> [`decrease`](https://discord.gg/blare) the voice channel limit\n"
                "<:28:1298731241209729024> [`info`](https://discord.gg/blare) about the voice channel\n"
                "<:20:1298731391143379017>  [`rename`](https://discord.gg/blare) the voice channel\n"
                "<:25:1298731247773941847> [`delete`](https://discord.gg/blare) the voice channel"
            ),
            inline=False,
        )

        view = View()
        view.add_item(
            Button(
                label="",
                emoji="<:26:1298731245320011856>",
                style=discord.ButtonStyle.secondary,
                custom_id="lock",
            )
        )
        view.add_item(
            Button(
                label="",
                emoji="<:27:1298731243059286077>",
                style=discord.ButtonStyle.secondary,
                custom_id="unlock",
            )
        )
        view.add_item(
            Button(
                label="",
                emoji="<:23:1298731251641090089>",
                style=discord.ButtonStyle.secondary,
                custom_id="hide",
            )
        )
        view.add_item(
            Button(
                label="",
                emoji="<:22:1298731253473874003>",
                style=discord.ButtonStyle.secondary,
                custom_id="reveal",
            )
        )
        view.add_item(
            Button(
                label="",
                emoji="<:29:1298731238655266847>",
                style=discord.ButtonStyle.secondary,
                custom_id="kick",
            )
        )
        view.add_item(
            Button(
                label="",
                emoji="<:24:1298731249497538632>",
                style=discord.ButtonStyle.secondary,
                custom_id="increase",
            )
        )
        view.add_item(
            Button(
                label="",
                emoji="<:21:1298731255621226496>",
                style=discord.ButtonStyle.secondary,
                custom_id="decrease",
            )
        )
        view.add_item(
            Button(
                label="",
                emoji="<:28:1298731241209729024>",
                style=discord.ButtonStyle.secondary,
                custom_id="info",
            )
        )
        view.add_item(
            Button(
                label="",
                emoji="<:20:1298731391143379017>",
                style=discord.ButtonStyle.secondary,
                custom_id="rename",
            )
        )
        view.add_item(
            Button(
                label="",
                emoji="<:25:1298731247773941847>",
                style=discord.ButtonStyle.secondary,
                custom_id="delete",
            )
        )

        async for message in interface.history(limit=100):
            if message.author == self.client.user:
                await message.delete()
        await interface.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id")
        guild = interaction.guild

        category, interface, create_channel = await self.load(guild)

        if custom_id in [
            "lock",
            "unlock",
            "hide",
            "reveal",
            "rename",
            "decrease",
            "increase",
            "info",
            "kick",
            "delete",
        ]:
            user_channel = (
                interaction.user.voice.channel if interaction.user.voice else None
            )
            if (
                user_channel
                and user_channel.category == category
                and user_channel != create_channel
            ):
                owner_id = await self.get_owner(user_channel.id)
                if owner_id != interaction.user.id and custom_id != "delete":
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            description=f"> {emoji.deny} {interaction.user.mention}: You **aren't** the owner of this voice channel",
                            color=color.deny,
                        ),
                        ephemeral=True,
                    )
                    return

                if custom_id == "lock":
                    await self.lock(interaction, user_channel)
                elif custom_id == "unlock":
                    await self.unlock(interaction, user_channel)
                elif custom_id == "hide":
                    await self.hide(interaction, user_channel)
                elif custom_id == "reveal":
                    await self.reveal(interaction, user_channel)
                elif custom_id == "rename":
                    await self.rename(interaction, user_channel)
                elif custom_id == "decrease":
                    await self.decrease(interaction, user_channel)
                elif custom_id == "increase":
                    await self.increase(interaction, user_channel)
                elif custom_id == "info":
                    await self.info(interaction, user_channel)
                elif custom_id == "kick":
                    await self.kick(interaction, user_channel)
                elif custom_id == "delete":
                    await self.delete_channel(interaction, user_channel)
            else:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=f"> {emoji.deny} {interaction.user.mention}: You **aren't** in a voice channel",
                        color=color.deny,
                    ),
                    ephemeral=True,
                )

    async def lock(self, interaction, channel):
        await self.update_channel_permissions(interaction, channel, connect=False)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"> {emoji.agree} {interaction.user.mention}: **Locked** your voice channel",
                color=color.agree,
            ),
            ephemeral=True,
        )

    async def unlock(self, interaction, channel):
        await self.update_channel_permissions(interaction, channel, connect=True)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"> {emoji.agree} {interaction.user.mention}: **Unlocked** your voice channel",
                color=color.agree,
            ),
            ephemeral=True,
        )

    async def hide(self, interaction, channel):
        await self.update_channel_permissions(interaction, channel, view_channel=False)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"> {emoji.agree} {interaction.user.mention}: **Hidden** your voice channel",
                color=color.agree,
            ),
            ephemeral=True,
        )

    async def reveal(self, interaction, channel):
        await self.update_channel_permissions(interaction, channel, view_channel=True)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"> {emoji.agree} {interaction.user.mention}: **Revealed** your voice channel",
                color=color.agree,
            ),
            ephemeral=True,
        )

    async def rename(self, interaction, channel):
        await interaction.response.send_modal(self.RenameModal(channel, self))

    class RenameModal(discord.ui.Modal):
        def __init__(self, channel, cog):
            super().__init__(title="Rename")
            self.channel = channel
            self.cog = cog
            self.new_name = discord.ui.TextInput(
                label="Rename your voice channel",
                placeholder="Enter a better name",
                required=True,
            )
            self.add_item(self.new_name)

        async def on_submit(self, interaction: discord.Interaction):
            await self.channel.edit(name=self.new_name.value)
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"> {emoji.agree} {interaction.user.mention}: **Renamed** your voice channel to: {self.new_name.value}",
                    color=color.agree,
                ),
                ephemeral=True,
            )
            self.cog.set_owner(self.channel.id, interaction.user.id)

    async def decrease(self, interaction, channel):
        await self.change_user_limit(interaction, channel, -1)

    async def increase(self, interaction, channel):
        await self.change_user_limit(interaction, channel, 1)

    async def info(self, interaction, channel):
        embed = discord.Embed(
            title=f"{channel.name}'s information", color=color.default
        )
        embed.add_field(name="Channel ID", value=channel.id, inline=True)
        embed.add_field(name="Member Limit", value=channel.user_limit, inline=True)
        embed.add_field(name="Bitrate", value=channel.bitrate, inline=True)
        owner_id = self.get_owner(channel.id)
        owner = channel.guild.get_member(owner_id)
        embed.add_field(
            name="Owner", value=owner.display_name if owner else "Unknown", inline=True
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def kick(self, interaction, channel):
        await interaction.response.send_modal(self.KickModal(channel))

    class KickModal(discord.ui.Modal):
        def __init__(self, channel):
            super().__init__(title="Kick")
            self.channel = channel
            self.member_to_kick = discord.ui.TextInput(
                label="Kick a user",
                placeholder="Enter a user ID to kick",
                required=True,
            )
            self.add_item(self.member_to_kick)

        async def on_submit(self, interaction: discord.Interaction):
            member_id = int(self.member_to_kick.value)
            member = self.channel.guild.get_member(member_id)
            if member and member in self.channel.members:
                await member.move_to(None)
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=f"> {emoji.agree} {interaction.user.mention}: **Kicked** {member.mention} from the voice channel",
                        color=color.agree,
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=f"> {emoji.deny} {interaction.user.mention}: **Could not** find the user in the voice channel",
                        color=color.deny,
                    ),
                    ephemeral=True,
                )

    async def delete_channel(self, interaction, channel):
        await channel.delete()
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"> {emoji.agree} {interaction.user.mention}: **Deleted** the voice channel",
                color=color.agree,
            ),
            ephemeral=True,
        )

    async def update_channel_permissions(self, interaction, channel, **permissions):
        await channel.set_permissions(interaction.guild.default_role, **permissions)

    async def change_user_limit(self, interaction, channel, delta):
        new_limit = max(0, (channel.user_limit or 0) + delta)
        await channel.edit(user_limit=new_limit)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"> {emoji.agree} {interaction.user.mention}: **Set** the member limit to: {new_limit}",
                color=color.agree,
            ),
            ephemeral=True,
        )


async def setup(client):
    await client.add_cog(Voicemaster(client))
