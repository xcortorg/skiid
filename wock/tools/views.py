from contextlib import suppress
from dataclasses import dataclass
from typing import Union

import aiohttp
import discord
from discord import (ButtonStyle, Embed, HTTPException, Interaction, Member,
                     Message)
from discord.ui import Button, View, button
from loguru import logger


class PlayModal(discord.ui.Modal, title="Play"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    firstfield = discord.ui.TextInput(
        label="Play a song thru wock",
        placeholder="example: ram ranch",
        min_length=1,
        max_length=500,
        style=discord.TextStyle.short,
    )

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.data["components"][0]["components"][0]["value"]:
            name = interaction.data["components"][0]["components"][0]["value"]
            logger.info(f"Play Modal got query {name}")
            from cogs.music import enqueue

            return await enqueue(self.bot, interaction, name)


class RenameModal(discord.ui.Modal, title="Rename"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    firstfield = discord.ui.TextInput(
        label="Rename your voice channel",
        placeholder="example: Movie night",
        min_length=1,
        max_length=32,
        style=discord.TextStyle.short,
    )

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.data["components"][0]["components"][0]["value"]:
            name = interaction.data["components"][0]["components"][0]["value"]
            if name is None:
                name = f"{interaction.author}'s channel"
            if interaction.user.voice.channel:
                data = await self.bot.db.fetchval(
                    """
                    SELECT channel_id
                    FROM voicemaster_data
                    WHERE channel_id = $1
                    AND owner_id = $2
                    """,
                    interaction.user.voice.channel.id,
                    interaction.user.id,
                )
                if data:
                    vc = interaction.guild.get_channel(data)
                    await vc.edit(name=name)
                    embed = discord.Embed(
                        description=f"> Your **voice channel** has been **renamed** to **{name}**",
                        color=0x2D2B31,
                    )
                    return await interaction.response.send_message(
                        embed=embed, ephemeral=True
                    )
                else:
                    embed = discord.Embed(
                        description="> You **don't** own this **voice channel**",
                        color=0x2D2B31,
                    )
                    return await interaction.response.send_message(
                        embed=embed, ephemeral=True
                    )
            else:
                embed = discord.Embed(
                    description="> You **aren't** connected to a **voicemaster channel**",
                    color=0x2D2B31,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )


async def reclaim(
    channel: discord.VoiceChannel,
    old_owner: Union[discord.Member, discord.User],
    new_owner: discord.Member,
):
    o = channel.overwrites
    o[new_owner] = o[old_owner]
    o.pop(old_owner)
    await channel.edit(overwrites=o)


# Label, Description, Value

OPTIONS = [
    ["Lock Channel", "Lock your voice channel from non admins joining", "lock"],
    ["Unlock Channel", "Unlock your channel so anyone can join", "unlock"],
    ["Hide Channel", "Hide your channel from users seeing it", "hide"],
    ["Reveal Channel", "Allow users to see your channel", "reveal"],
    ["Rename Channel", "Rename your channel", "rename"],
    ["Claim Ownership", "Claim ownership of the current voice channel", "claim"],
    ["Increase User Limit", "Increase the user limit of your channel", "increase"],
    ["Decrease User Limit", "Decrease the user limit of your channel", "decrease"],
    ["Delete Channel", "Delete your channel", "delete"],
    [
        "Show Information",
        "Show information regarding your voice channel",
        "information",
    ],
    ["Play", "Play a song thru wock", "play"],
]


class VoicemasterInterface(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.options = [
            discord.SelectOption(label=_[0], description=_[1], value=_[2])
            for _ in OPTIONS
        ]

        self.add_item(VmSelectMenu(self.bot))


class VmSelectMenu(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(label=_[0], description=_[1], value=_[2])
            for _ in OPTIONS
        ]
        super().__init__(
            custom_id="VM:Select",
            placeholder="select task...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def lock(self, interaction: discord.Interaction):
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

    async def unlock(self, interaction: discord.Interaction):
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

    async def hide(self, interaction: discord.Interaction):
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

    async def play(self, interaction: discord.Interaction):
        return await interaction.response.send_modal(PlayModal(self.bot))

    async def reveal(self, interaction: discord.Interaction):
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

    async def rename(self, interaction: discord.Interaction):
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

    async def claim(self, interaction: discord.Interaction):
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

    async def increase(self, interaction: discord.Interaction):
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

    async def decrease(self, interaction: discord.Interaction):
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

    async def delete(self, interaction: discord.Interaction):
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

    async def information(self, interaction: discord.Interaction):
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

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        await getattr(self, value)(interaction)
        self.values.clear()
        return await interaction.message.edit(view=self.view)


class GiveawayView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(emoji="🎉", style=ButtonStyle.blurple, custom_id="persistent:join_gw")
    async def join_gw(self, interaction: Interaction, button: Button):
        if not await interaction.client.db.fetchrow(
            """SELECT * FROM giveaways WHERE guild_id = $1 AND message_id = $2""",
            interaction.guild.id,
            interaction.message.id,
        ):
            return await interaction.response.send_message(
                "this giveaway has ended", ephemeral=True
            )
        count = (
            await interaction.client.db.fetchval(
                """SELECT entry_count FROM giveaway_entries WHERE guild_id = $1 AND message_id = $2 AND user_id = $3""",
                interaction.guild.id,
                interaction.message.id,
                interaction.user.id,
            )
            or 0
        )
        max_count = await interaction.client.db.fetch(
            """
            SELECT *
            FROM giveaway_settings
            WHERE guild_id = $1
            AND role_id = ANY ($2)
        """,
            interaction.guild.id,
            [r.id for r in interaction.user.roles],
        )
        if max_count:
            max_count = max([i["entries"] for i in max_count])
        else:
            max_count = 1
        if count >= max_count:
            return await interaction.response.send_message(
                "You have reached the maximum number of entries for this giveaway",
                ephemeral=True,
            )
        await interaction.client.db.execute(
            """
            INSERT INTO giveaway_entries (guild_id, message_id, user_id, entry_count)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, message_id, user_id)
            DO UPDATE SET entry_count = giveaway_entries.entry_count + 1
        """,
            interaction.guild.id,
            interaction.message.id,
            interaction.user.id,
            count + 1,
        )
        return await interaction.response.send_message(
            "You have joined the giveaway", ephemeral=True
        )

    @button(
        emoji=None,
        style=ButtonStyle.gray,
        custom_id="persistent:participants",
        label="Participants",
    )
    async def paricipants(self, interaction: Interaction, button: Button):
        if not await interaction.client.db.fetchrow(
            """SELECT * FROM giveaways WHERE guild_id = $1 AND message_id = $2""",
            interaction.guild.id,
            interaction.message.id,
        ):
            return await interaction.response.send_message(
                "this giveaway has ended", ephemeral=True
            )
        participants = await interaction.client.db.fetch(
            """SELECT user_id, entry_count FROM giveaway_entries WHERE guild_id = $1 AND message_id = $2""",
            interaction.guild.id,
            interaction.message.id,
        )
        if not participants:
            return await interaction.response.send_message(
                "There are no participants in this giveaway", ephemeral=True
            )
        embed = Embed(
            description=f"These are the members that have participated in the givaway of **{interaction.message.embeds[0].title}**"
        )
        embed.description += "\n"
        for i, participant in enumerate(participants, start=1):
            embed.description += f"`{i}` **{interaction.guild.get_member(participant['user_id']).mention}** - `{participant['entry_count']}`\n"
        embed.set_footer(text=f"Total: {len(participants)}")
        return await interaction.response.send_message(embed=embed, ephemeral=True)


@dataclass
class EmojiEntry:
    name: str
    id: int
    url: str
    animated: bool


class PrivacyConfirmation(View):
    def __init__(
        self: "Confirmation", message: Message, invoker: Member = None
    ) -> None:
        super().__init__(timeout=60)

        self.value = False
        self.message = message
        self.invoker = invoker

    @button(style=ButtonStyle.green, label="Approve")
    async def approve(self: "Confirmation", interaction: Interaction, _: None):
        """
        The approve button.

        Parameters:
            interaction (Interaction): The interaction object.
            _: Button: The unused button object.
        """

        await self.confirmation(interaction, True)

    @button(style=ButtonStyle.red, label="Decline")
    async def decline(self: "Confirmation", interaction: Interaction, _: None):
        """
        The decline button.

        Parameters:
            interaction (Interaction): The interaction object.
            _: None: The unused button object.
        """

        await self.confirmation(interaction, False)

    async def on_timeout(self):
        embed = discord.Embed(
            description="> you have **failed** to **accept** our [privacy policy](https://wock.bot/privacy) in time and as a result have been **blacklisted**, to retry use the `reset` command",
            color=self.message.embeds[0].color,
        )
        with suppress(HTTPException):
            await self.message.edit(embed=embed, view=None)
        return None

    async def confirmation(
        self: "Confirmation", interaction: Interaction, value: bool
    ) -> None:
        """
        Handles the confirmation of an interaction.

        Parameters:
            interaction (Interaction): The interaction object representing the user's interaction.
            value (bool): The boolean value indicating the confirmation.
        """

        await interaction.response.defer()

        if interaction.user.id != self.invoker.id:
            return

        with suppress(HTTPException):
            await self.message.edit(view=None)

        self.value = value
        self.stop()


class Confirmation(View):
    def __init__(
        self: "Confirmation", message: Message, invoker: Member = None
    ) -> None:
        super().__init__(timeout=60)

        self.value = False
        self.message = message
        self.invoker = invoker

    @button(style=ButtonStyle.green, label="Approve")
    async def approve(self: "Confirmation", interaction: Interaction, _: None):
        """
        The approve button.

        Parameters:
            interaction (Interaction): The interaction object.
            _: Button: The unused button object.
        """

        await self.confirmation(interaction, True)

    @button(style=ButtonStyle.red, label="Decline")
    async def decline(self: "Confirmation", interaction: Interaction, _: None):
        """
        The decline button.

        Parameters:
            interaction (Interaction): The interaction object.
            _: None: The unused button object.
        """

        await self.confirmation(interaction, False)

    async def confirmation(
        self: "Confirmation", interaction: Interaction, value: bool
    ) -> None:
        """
        Handles the confirmation of an interaction.

        Parameters:
            interaction (Interaction): The interaction object representing the user's interaction.
            value (bool): The boolean value indicating the confirmation.
        """

        await interaction.response.defer()

        if interaction.user.id != self.invoker.id:
            return

        with suppress(HTTPException):
            await self.message.edit(view=None)

        self.value = value
        self.stop()


class EmojiConfirmation(View):
    def __init__(
        self: "EmojiConfirmation",
        message: Message,
        emojis: EmojiEntry,
        invoker: Member = None,
    ) -> None:
        super().__init__(timeout=None)
        self.index = 0
        self.emojis = emojis
        self.value = False
        self.message = message
        self.invoker = invoker

    @button(style=ButtonStyle.grey, emoji="✂️")
    async def approve(self: "Confirmation", interaction: Interaction, _: None):
        """
        The approve button.

        Parameters:
            interaction (Interaction): The interaction object.
            _: Button: The unused button object.
        """
        self.value = True
        await self.confirmation(interaction, True)

    @button(style=ButtonStyle.red, emoji="<:stop:1110883418708901928>")
    async def decline(self: "Confirmation", interaction: Interaction, _: None):
        """
        The decline button.

        Parameters:
            interaction (Interaction): The interaction object.
            _: None: The unused button object.
        """
        self.value = False
        await self.confirmation(interaction, False)

    async def confirmation(
        self: "Confirmation", interaction: Interaction, value: bool
    ) -> None:
        """
        Handles the confirmation of an interaction.

        Parameters:
            interaction (Interaction): The interaction object representing the user's interaction.
            value (bool): The boolean value indicating the confirmation.
        """

        await interaction.response.defer()

        if interaction.user.id != self.invoker.id:
            return

        with suppress(HTTPException):
            if self.value is True:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.emojis.url) as resp:
                        image = await resp.read()
                await interaction.guild.create_custom_emoji(
                    name=self.emojis.name, image=image
                )
                await self.message.edit(
                    embed=discord.Embed(
                        description=f"{interaction.user.mention}: **added** [{self.emojis.name}]({self.emojis.url})",
                        color=0x2B2D31,
                    ),
                    view=None,
                )
            else:
                await self.message.edit(
                    embed=discord.Embed(
                        description="**cancelled** emoji steal", color=0x2B2D31
                    ),
                    view=None,
                )

        self.stop()
