import discord
from discord.ext import commands
from discord.ui import View
from discord.ext.commands import Context, CommandError, check, Boolean, Cog
from lib.classes.color import ColorConverter
from discord import Embed, Member, Role, TextChannel, Thread, Client
import orjson
from typing import Union, Optional


def boolean_to_emoji(ctx: Context, boolean: bool):
    if boolean:
        return ctx.bot.config["emojis"]["success"]
    return ctx.bot.config["emojis"]["fail"]


def clownboard_check():
    async def predicate(ctx: Context):
        query = "SELECT EXISTS(SELECT 1 FROM clownboard WHERE guild_id = $1)"
        if await ctx.bot.db.fetchval(query, ctx.guild.id):
            return True
        else:
            raise CommandError(
                f"**clownboard** hasn't been setup using `{ctx.prefix}clownboard set`"
            )

    return check(predicate)


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot

    @commands.group(
        name="clownboard",
        usage="(subcommand) <args>",
        aliases=["clowns", "cb"],
        description="Showcase the worst messages in your server",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_guild=True)
    async def clownboard(self: "Commands", ctx: Context):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command.qualified_name)

    @clownboard.command(
        name="threshold",
        aliases=["amount"],
        description="Sets the default amount stars needed to post",
        example=",clownboard threshold 5",
    )
    @clownboard_check()
    @commands.has_permissions(manage_guild=True)
    async def clownboard_threshold(self: "Commands", ctx: Context, *, number: int):
        query = "UPDATE clownboard SET threshold = $1 WHERE guild_id = $2"
        await ctx.bot.db.execute(query, number, ctx.guild.id)
        return await ctx.success(f"**clownboard** threshold has been set to `{number}`")

    @clownboard.command(
        name="selfstar", description="Allow an author to star their own message"
    )
    @clownboard_check()
    @commands.has_permissions(manage_guild=True)
    async def clownboard_selfstar(self: "Commands", ctx: Context, *, option: Boolean):
        query = "UPDATE clownboard SET self_star = $1 WHERE guild_id = $2"
        await ctx.bot.db.execute(query, option, ctx.guild.id)
        return await ctx.success(f"**clownboard** selfstar has been set to `{option}`")

    @clownboard.command(
        name="set",
        usage="(channel) (emoji) (amount)",
        example=",clownboard set #highlights ⭐",
        description="Set the channel for the clownboard.",
        parameters={
            "threshold": {
                "converter": int,
                "description": "The number of reactions required to be saved",
                "default": 1,
                "minimum": 1,
                "maximum": 120,
                "aliases": ["amount", "count"],
            }
        },
        aliases=["create"],
    )
    @commands.has_permissions(manage_guild=True)
    async def clownboard_set(
        self: "Commands",
        ctx: Context,
        channel: Optional[Union[discord.TextChannel, discord.Thread]] = None,
        emoji: Optional[str] = "⭐",
    ):
        channel = channel or ctx.channel
        if await self.bot.db.fetchrow(
            """SELECT * FROM clownboard WHERE guild_id = $1""", ctx.guild.id
        ):
            raise CommandError(
                f"**clownboard** has already been setup. -to reset use `{ctx.prefix}clownboard reset`"
            )
        try:
            await ctx.message.add_reaction(emoji)
        except discord.HTTPException:
            return await ctx.fail(f"**{emoji}** is not a valid emoji")
        threshold = ctx.parameters.get("threshold")
        if threshold == 1:
            m = ""
        else:
            m = f"with a threshold of `{threshold}`"
        try:
            await self.bot.db.execute(
                "INSERT INTO clownboard (guild_id, channel_id, emoji, threshold) VALUES ($1, $2, $3, $4)",
                ctx.guild.id,
                channel.id,
                emoji,
                ctx.parameters.get("threshold"),
            )
        except Exception as e:
            raise e
            await ctx.fail(f"There is already a **clownboard** using **{emoji}**")
        else:
            await ctx.success(
                f"**clownboard** channel has been set to {channel.mention} using **{emoji}** {m}"
            )

    @clownboard.command(
        name="lock", description="Disables/locks clownboard from operating"
    )
    @commands.has_permissions(manage_guild=True)
    @clownboard_check()
    async def clownboard_lock(self: "Commands", ctx: Context):
        prefix = (
            await self.bot.db.fetchval(
                """SELECT prefix FROM config WHERE guild_id = $1""", ctx.guild.id
            )
            or ","
        )
        current_state = await self.bot.db.fetchval(
            """SELECT lock FROM clownboard WHERE guild_id = $1""", ctx.guild.id
        )
        if current_state:
            return await ctx.fail(
                f"**clownboard** is **already locked**, use `{prefix}clownboard unlock` to unlock."
            )
        await self.bot.db.execute(
            """UPDATE clownboard SET lock = $1 WHERE guild_id = $2""",
            True,
            ctx.guild.id,
        )
        return await ctx.success(
            f"**clownboard** has been **locked**. Use `{prefix}clownboard unlock` to revert."
        )

    @clownboard.command(
        name="unlock", description="Enables/unlocks clownboard from operating"
    )
    @commands.has_permissions(manage_guild=True)
    @clownboard_check()
    async def clownboard_unlock(self: "Commands", ctx: Context):
        prefix = (
            await self.bot.db.fetchval(
                """SELECT prefix FROM config WHERE guild_id = $1""", ctx.guild.id
            )
            or ","
        )
        current_state = await self.bot.db.fetchval(
            """SELECT lock FROM clownboard WHERE guild_id = $1""", ctx.guild.id
        )
        if not current_state:
            return await ctx.fail(
                f"**clownboard** is **already unlocked**, use `{prefix}clownboard lock` to lock"
            )
        await self.bot.db.execute(
            """UPDATE clownboard SET lock = $1 WHERE guild_id = $2""",
            False,
            ctx.guild.id,
        )
        return await ctx.success(
            f"**clownboard** has been **unlocked**, use `{prefix}clownboard lock` to revert."
        )

    @clownboard.command(
        name="color",
        aliases=["hexit"],
        description="set the clownboard embed color",
        example=",clownboard color #151515",
    )
    @commands.has_permissions(manage_guild=True)
    @clownboard_check()
    async def clownboard_color(
        self: "Commands", ctx: Context, *, color: ColorConverter
    ):
        await self.bot.db.execute(
            """UPDATE clownboard SET color = $1 WHERE guild_id = $2""",
            str(color),
            ctx.guild.id,
        )
        return await ctx.success(
            f"successfully set the clownboard color to `#{str(color)}`"
        )

    @clownboard.command(
        name="timestamp",
        aliases=["ts", "time"],
        description="Allow a timestamp to appear on a clownboard post",
        example=",clownboard timestamp true",
    )
    @commands.has_permissions(manage_guild=True)
    @clownboard_check()
    async def clownboard_timestamp(self: "Commands", ctx: Context, *, option: Boolean):
        await self.bot.db.execute(
            """INSERT INTO clownboard (guild_id, ts) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET ts = excluded.ts""",
            ctx.guild.id,
            option,
        )
        return await ctx.success(
            f"successfully **{'ENABLED' if option else 'DISABLED'}** clownboard timestamps"
        )

    @clownboard.command(
        name="attachments",
        aliases=["files", "a", "images", "img", "imgs"],
        description="Allow attachments to appear on clownboard posts",
        example=",clownboard attachments true",
    )
    @commands.has_permissions(manage_guild=True)
    @clownboard_check()
    async def clownboard_attachments(
        self: "Commands", ctx: Context, *, option: Boolean
    ):
        await self.bot.db.execute(
            """INSERT INTO clownboard (guild_id, attachments) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET attachments = excluded.attachments""",
            ctx.guild.id,
            option,
        )
        return await ctx.success(
            f"successfully **{'ENABLED' if option else 'DISABLED'}** clownboard attachments"
        )

    @clownboard.command(
        name="jumpurl",
        aliases=["jump", "url"],
        description="Allow the jump URL to appear on a clownboard post",
        example=",clownboard jumpurl true",
    )
    @commands.has_permissions(manage_guild=True)
    @clownboard_check()
    async def clownboard_jumpurl(self: "Commands", ctx: Context, *, option: Boolean):
        await self.bot.db.execute(
            """INSERT INTO clownboard (guild_id, jump) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET jump = excluded.jump""",
            ctx.guild.id,
            option,
        )
        await ctx.success(
            f"successfully **{'ENABLED' if option else 'DISABLED'}** clownboard jump urls on embeds"
        )

    @clownboard.command(
        name="emoji",
        aliases=["emote"],
        description="Sets the emoji that triggers the clownboard messages",
        example=",clownboard emoji 💀",
    )
    @commands.has_permissions(manage_guild=True)
    @clownboard_check()
    async def clownboard_emoji(self: "Commands", ctx: Context, *, emoji: str):
        await self.bot.db.execute(
            """INSERT INTO clownboard (guild_id, emoji) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET emoji = excluded.emoji""",
            ctx.guild.id,
            str(emoji),
        )
        return await ctx.success(
            f"successfully set the clownboard emoji as {str(emoji)}"
        )

    @clownboard.command(
        name="reset",
        description="Reset the guild's clownboard configuration",
        aliases=[
            "delete",
        ],
    )
    @clownboard_check()
    @commands.has_permissions(manage_guild=True)
    async def clownboard_reset(self: "Commands", ctx: Context):
        class ConfirmReset(View):
            def __init__(self, bot):
                super().__init__(timeout=15)
                self.bot = bot
                self.value = None

            @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
            async def approve(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                if interaction.user != ctx.author:
                    embed = discord.Embed(
                        description=f"<:warning:1286583936113311755> {interaction.user.mention}: Your interaction is not allowed on this embed",
                        color=0xE69705,
                    )
                    return await interaction.response.send_message(
                        embed=embed, ephemeral=True
                    )

                await interaction.response.defer()
                await self.bot.db.execute(
                    """DELETE FROM clownboard WHERE guild_id = $1""", ctx.guild.id
                )
                prefix = (
                    await self.bot.db.fetchval(
                        """SELECT prefix FROM config WHERE guild_id = $1""",
                        ctx.guild.id,
                    )
                    or ","
                )
                embed = discord.Embed(
                    description=f"<:check:1286583241905803356> {ctx.author.mention}: clownboard has been **reset**. Run `{prefix}help clownboard` to see a list of options.",
                    color=0x90DA68,
                )
                await message.edit(embed=embed, view=None)
                self.value = True
                self.stop()

            @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
            async def decline(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                if interaction.user != ctx.author:
                    embed = discord.Embed(
                        description=f"<:warning:1286583936113311755> {interaction.user.mention}: Your interaction is not allowed on this embed",
                        color=0xE69705,
                    )
                    return await interaction.response.send_message(
                        embed=embed, ephemeral=True
                    )
                await message.delete()
                self.value = False
                self.stop()

        embed = discord.Embed(
            description=f"<:settings:1287327423746146334> {ctx.author.mention}: Are you sure that you want to **reset** your clownboard settings?",
            color=0x6E879C,
        )
        view = ConfirmReset(self.bot)
        message = await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is None:
            await message.delete()

    @clownboard.command(
        name="settings",
        aliases=["config"],
        description="Display your current clownboard settings",
    )
    @commands.has_permissions(manage_guild=True)
    async def clownboard_settings(self: "Commands", ctx: Context):
        clownboard = await self.bot.db.fetchrow(
            """SELECT * FROM clownboard WHERE guild_id = $1""", ctx.guild.id
        )
        if not clownboard:
            return await ctx.warning(
                "**clownboard** hasn't been setup using `{ctx.prefix}clownboard set"
            )

        description = f"**Locked:** {boolean_to_emoji(ctx, clownboard.lock)}"

        general_value = f"**Channel:** {f'<#{clownboard.channel_id}>' if clownboard.channel_id else 'No channel set'}\n**Color:** {f'`#{clownboard.color}' if clownboard.color else 'Author color'}\n**Threshold:** {clownboard.threshold}\n**Emoji:** {clownboard.emoji}"

        options_value = f"**Show Attachments:** {boolean_to_emoji(ctx, clownboard.attachments)}\n**Show Timestamps:** {boolean_to_emoji(ctx, clownboard.ts)}\n**Show Jump URL:** {boolean_to_emoji(ctx, clownboard.jump)}\n**Self Star:** {boolean_to_emoji(ctx, clownboard.self_star)}"
        roles = 0
        channels = 0
        members = 0
        if clownboard.ignore_entries:
            data = orjson.loads(clownboard.ignore_entries)
            for d in data:
                if ctx.guild.get_channel(d):
                    channels += 1
                elif ctx.guild.get_member(d):
                    members += 1
                elif ctx.guild.get_role(d):
                    roles += 1
                else:
                    continue

        count_value = f"**Blacklisted Channels:** {channels}\n**Blacklisted Users:** {members}\n**Blacklisted Roles:** {roles}"
        embed = Embed(
            color=0x6E879C, title="Clownboard configuration", description=description
        )

        embed.add_field(name="General", value=general_value, inline=True)
        embed.add_field(name="Options", value=options_value, inline=True)
        embed.add_field(name="Count", value=count_value, inline=True)
        return await ctx.send(embed=embed)

    @clownboard.group(
        name="ignore",
        description="Ignore a channel, member, or role, for reactions",
        example=",clownboard ignore @kuzay",
        usage="channel or member or role",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_guild=True)
    @clownboard_check()
    async def clownboard_ignore(
        self: "Commands",
        ctx: Context,
        *,
        member_channel_role: Union[Member, Role, TextChannel, Thread],
    ):
        if member_channel_role is None:
            return await ctx.fail(
                "You must mention a valid **channel**, **role**, or **user**"
            )
        data = orjson.loads(
            await self.bot.db.fetchval(
                """SELECT ignore_entries FROM clownboard WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or "[]"
        )
        if member_channel_role.id not in data:
            data.append(member_channel_role.id)
            option = f"**clownboard** will now **ignore** {member_channel_role.mention}"
        else:
            data.remove(member_channel_role.id)
            option = (
                f"**clownboard** will no longer ignore {member_channel_role.mention}"
            )

        await self.bot.db.execute(
            """UPDATE clownboard SET ignore_entries = $1 WHERE guild_id = $2""",
            orjson.dumps(data),
            ctx.guild.id,
        )
        return await ctx.success(f"{option}")

    @clownboard_ignore.command(
        name="list",
        aliases=["show", "all"],
        description="View ignored roles, members and channels for clownboard",
    )
    @commands.has_permissions(manage_guild=True)
    @clownboard_check()
    async def clownboard_ignore_list(self: "Commands", ctx: Context):
        data = orjson.loads(
            await self.bot.db.fetchval(
                """SELECT ignore_entries FROM clownboard WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or "[]"
        )
        if not data:
            return await ctx.fail(
                "**clownboard** has no ignored **roles**, **members**, or **channels**"
            )
        rows = []
        diff = 0
        for i, entry in enumerate(data, start=1):
            if ctx.guild.get_role(entry):
                rows.append(
                    f"`{i - diff}` {ctx.guild.get_role(entry).mention} --**role**"
                )
            elif ctx.guild.get_member(entry):
                rows.append(
                    f"`{i - diff}` {ctx.guild.get_member(entry).mention} --**member**"
                )
            elif ctx.guild.get_channel(entry):
                rows.append(
                    f"`{i - diff}` {ctx.guild.get_channel(entry).mention} --**channel**"
                )
            else:
                diff += 1
                continue
        return await ctx.paginate(
            Embed(color=self.bot.color, title="Clownboard Blacklists"), rows
        )
