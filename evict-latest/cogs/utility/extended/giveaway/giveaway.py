from contextlib import suppress
from datetime import timedelta
from logging import getLogger
from typing import List, Optional, cast, Annotated

from discord import Embed, HTTPException, Message, TextChannel, Role
from discord.ext.commands import (
    group, 
    has_permissions, 
    parameter,
    flag,
    Range,
    Greedy,
    Command
)
from discord.ext.tasks import loop
from discord.utils import format_dt

from core.client import FlagConverter

from tools import CompositeMetaClass, MixinMeta
from core.client.context import Context
from tools.conversion import Duration
from managers.paginator import Paginator

from .models import GiveawayEntry

log = getLogger("evict/giveaway")

# CREATE TABLE IF NOT EXISTS giveaway (
#   guild_id BIGINT NOT NULL,
#   user_id BIGINT NOT NULL,
#   channel_id BIGINT NOT NULL,
#   message_id BIGINT NOT NULL,
#   prize TEXT NOT NULL,
#   emoji TEXT NOT NULL,
#   winners INTEGER NOT NULL,
#   ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
#   created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
#   PRIMARY KEY (guild_id, channel_id, message_id)
# );


class GiveawayFlags(FlagConverter):
    required: Role = flag(
        default=None,
        description="Role required to enter the giveaway"
    )
    bonus: List[str] = flag(
        default=lambda _: [],
        description="Roles that get bonus entries (Role:entries)"
    )
    winners: Range[int, 1, 25] = flag(
        description="Number of winners"
    )
    prize: str = flag(
        description="The prize for the giveaway"
    )


class Giveaway(MixinMeta, metaclass=CompositeMetaClass):
    """
    Various giveaway utilities.
    """

    async def cog_load(self) -> None:
        self.check_giveaways.start()
        return await super().cog_load()

    async def cog_unload(self) -> None:
        self.check_giveaways.cancel()
        return await super().cog_unload()

    @loop(seconds=15)
    async def check_giveaways(self):
        """
        Check if a giveaway has ended.
        """

        giveaways = [
            GiveawayEntry.from_record(self.bot, record)
            for record in await self.bot.db.fetch(
                """
                SELECT *
                FROM giveaway
                WHERE ends_at <= NOW()
                AND ended = FALSE
                """,
            )
        ]

        scheduled_deletion: List[GiveawayEntry] = []
        for giveaway in giveaways:
            if not giveaway.channel:
                scheduled_deletion.append(giveaway)
                continue

            message = await giveaway.message()
            if not message:
                scheduled_deletion.append(giveaway)
                continue

            if not message.reactions:
                scheduled_deletion.append(giveaway)
                continue

            with suppress(HTTPException):
                await self.draw_giveaway(giveaway, message)

        if scheduled_deletion:
            await self.bot.db.executemany(
                """
                DELETE FROM giveaway
                WHERE guild_id = $1
                AND channel_id = $2
                AND message_id = $3
                """,
                [
                    (
                        giveaway.guild_id,
                        giveaway.channel_id,
                        giveaway.message_id,
                    )
                    for giveaway in scheduled_deletion
                ],
            )

    async def draw_giveaway(
        self,
        giveaway: GiveawayEntry,
        message: Message,
    ):
        """
        Choose winners and end the giveaway.
        """

        await giveaway.end()
        winners = await giveaway.draw_winners(message)
        await message.edit(
            content="🎉 **GIVEAWAY ENDED** 🎉",
            embed=giveaway.embed(winners),
        )

        if winners:
            await message.reply(
                content=(
                    f"Congratulations {' '.join(w.mention for w in winners)}!"
                    f" You won **{giveaway.prize}**!"
                ),
            )

    @group(
        aliases=["gw"],
        invoke_without_command=True,
    )
    @has_permissions(manage_messages=True)
    async def giveaway(self, ctx: Context) -> Message:
        """
        Manage giveaways.
        """

        return await ctx.send_help(ctx.command)

    @giveaway.command(
        name="start",
        aliases=["create"],
        example="#giveaways 1w 1x nitro",
    )
    @has_permissions(manage_messages=True)
    async def giveaway_start(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        duration: Annotated[
            timedelta,
            Duration(
                min=timedelta(minutes=5),
                max=timedelta(weeks=4),
            )
        ],
        *,
        flags: GiveawayFlags,
    ) -> Optional[Message]:
        """
        Start a giveaway.

        The duration must be between 15 seconds and 1 month.
        If multiple winners are specified, the prize will
        automatically contain the winners, eg: `2x nitro`.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only start giveaways in text channels!")

        bonus_roles = {}
        for bonus in flags.bonus:
            role_id = int(bonus.split(':')[0].strip('<@&>'))
            entries = int(bonus.split(':')[1])
            if role := ctx.guild.get_role(role_id):
                bonus_roles[role.id] = entries

        giveaway = GiveawayEntry(
            bot=self.bot,
            guild_id=ctx.guild.id,
            user_id=ctx.author.id,
            channel_id=channel.id,
            prize=flags.prize,
            emoji="🎉",
            winners=flags.winners,
            ends_at=ctx.message.created_at + duration,
            required_roles=[flags.required.id] if flags.required else [],
            bonus_roles=bonus_roles
        )

        embed = Embed(title=giveaway.prize)
        embed.description = f"React with 🎉 to enter!\n> Ends {format_dt(giveaway.ends_at, 'R')}"
        
        if flags.required:
            embed.add_field(
                name="Required Roles",
                value=flags.required.mention,
                inline=True
            )
        
        if bonus_roles:
            bonus_desc = []
            for role_id, entries in bonus_roles.items():
                if role := ctx.guild.get_role(role_id):
                    bonus_desc.append(f"{role.mention}: {entries + 1}x entries")
            
            if bonus_desc:
                embed.add_field(
                    name="Bonus Entries",
                    value="\n".join(bonus_desc),
                    inline=True
                )

        message = await channel.send(
            content="🎉 **GIVEAWAY** 🎉",
            embed=embed
        )

        async def check_reaction(payload):
            if (
                payload.message_id == message.id 
                and payload.emoji.name == "🎉"
                and payload.user_id != self.bot.user.id
            ):
                member = channel.guild.get_member(payload.user_id)
                if flags.required and flags.required not in member.roles:
                    await message.remove_reaction(payload.emoji, member)

        self.bot.add_listener(check_reaction, name='on_raw_reaction_add')
        await message.add_reaction("🎉")
        await giveaway.save(message)

        if channel == ctx.channel:
            return await ctx.check()

        return await ctx.approve(
            f"Giveaway started in {channel.mention} for [**{giveaway.prize}**]({message.jump_url})",
        )

    @giveaway.command(
        name="end",
        aliases=["stop"],
        example="1234567890",
    )
    @has_permissions(manage_messages=True)
    async def giveaway_end(
        self,
        ctx: Context,
        giveaway: GiveawayEntry = parameter(
            default=GiveawayEntry.fallback,
        ),
    ) -> Optional[Message]:
        """
        End a giveaway.
        """

        if giveaway.is_ended:
            return await ctx.warn("That giveaway has already ended!")

        message = await giveaway.message()
        if not message:
            return await ctx.warn("That giveaway no longer exists!")

        await self.draw_giveaway(giveaway, message)
        if message.channel == ctx.channel:
            return await ctx.check()

        return await ctx.approve(
            f"Giveaway ended for [**{giveaway.prize}**]({message.jump_url})"
        )

    @giveaway.command(
        name="reroll",
        aliases=["redraw"],
        example="1234567890",
    )
    @has_permissions(manage_messages=True)
    async def giveaway_reroll(
        self,
        ctx: Context,
        giveaway: GiveawayEntry = parameter(
            default=GiveawayEntry.fallback,
        ),
    ) -> Optional[Message]:
        """
        Reroll a giveaway.
        """

        if not giveaway.is_ended:
            return await ctx.warn("That giveaway hasn't ended yet!")

        message = await giveaway.message()
        if not message:
            return await ctx.warn("That giveaway no longer exists!")

        await self.draw_giveaway(giveaway, message)
        if message.channel == ctx.channel:
            return await ctx.check()

        return await ctx.approve(
            f"Giveaway rerolled for [**{giveaway.prize}**]({message.jump_url})"
        )

    @giveaway.command(
        name="entrants",
        aliases=["entries"],
        example="1234567890",
    )
    @has_permissions(manage_messages=True)
    async def giveaway_entrants(
        self,
        ctx: Context,
        giveaway: GiveawayEntry = parameter(
            default=GiveawayEntry.fallback,
        ),
    ) -> Optional[Message]:
        """
        View all giveaway entrants.
        """

        message = await giveaway.message()
        if not message:
            return await ctx.warn("That giveaway no longer exists!")

        entries = await giveaway.entrants(message)
        if not entries:
            return await ctx.warn("No one has entered that giveaway!")

        paginator = Paginator(
            ctx,
            entries=[f"**{member}** (`{member.id}`)" for member in entries],
            embed=Embed(title="Giveaway Entrants"),
        )
        return await paginator.start()

    @giveaway.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_messages=True)
    async def giveaway_list(self, ctx: Context) -> Message:
        """
        View all active giveaways.
        """

        giveaways = [
            GiveawayEntry.from_record(self.bot, record)
            for record in await self.bot.db.fetch(
                """
                SELECT *
                FROM giveaway
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
        ]
        if not giveaways:
            return await ctx.warn("No giveaways exist for this server!")

        paginator = Paginator(
            ctx,
            entries=[
                (
                    f"**{giveaway.prize}**"
                    f" - [`{giveaway.message_id}`]({giveaway.message_url})"
                    + (" [ENDED]" if giveaway.is_ended else "")
                )
                for giveaway in giveaways
            ],
            embed=Embed(title="Giveaways"),
        )
        return await paginator.start()

    @giveaway.command(
        name="settings",
        aliases=["config"],
    )
    @has_permissions(manage_messages=True)
    async def giveaway_settings(self, ctx: Context):
        """
        Configure server-wide giveaway settings
        """
        settings = await self.bot.db.fetchval(
            """
            SELECT bonus_roles FROM giveaway_settings
            WHERE guild_id = $1
            """,
            ctx.guild.id
        ) or {}

        embed = Embed(title="Giveaway Settings")
        desc = ["**Global Bonus Entries:**"]
        
        for role_id, bonus in settings.items():
            role = ctx.guild.get_role(int(role_id))
            if role:
                desc.append(f"{role.mention}: +{bonus} entries")
        
        embed.description = "\n".join(desc) if len(desc) > 1 else "No bonus roles configured"
        return await ctx.send(embed=embed)

    @giveaway.command(name="addrole")
    @has_permissions(manage_messages=True)
    async def giveaway_addrole(
        self, 
        ctx: Context,
        role: Role,
        bonus: int = 1
    ):
        """
        Add a role that gets bonus entries in all giveaways
        """
        await self.bot.db.execute(
            """
            INSERT INTO giveaway_settings (guild_id, bonus_roles)
            VALUES ($1, $2::jsonb)
            ON CONFLICT (guild_id) DO UPDATE
            SET bonus_roles = giveaway_settings.bonus_roles || $2::jsonb
            """,
            ctx.guild.id,
            {str(role.id): bonus}
        )
        return await ctx.approve(f"Added {role.mention} with +{bonus} bonus entries")
