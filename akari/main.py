import discord
from tools.bot import Akari
from tools.helpers import AkariContext

bot = Akari()


@bot.before_invoke
async def chunk_guild(ctx: AkariContext) -> None:
    if not ctx.guild.chunked:
        await ctx.guild.chunk(cache=True)


@bot.check
async def check_availability(ctx: AkariContext) -> bool:
    return True


@bot.check
async def disabled_command(ctx: AkariContext):
    if await ctx.bot.db.fetchrow(
        """
    SELECT * FROM disablecmd
    WHERE guild_id = $1
    AND cmd = $2
    """,
        ctx.guild.id,
        str(ctx.command),
    ):
        if not ctx.author.guild_permissions.administrator:
            await ctx.error(
                f"The command **{str(ctx.command)}** is **disabled** in this server"
            )
            return False
        return True

    global_disabled = await ctx.bot.db.fetchrow(
        """
   SELECT disabled FROM global_disabled_cmds
   WHERE cmd = $1
   """,
        ctx.bot.get_command(str(ctx.command)).name,
    )
    if global_disabled:
        if global_disabled.get("disabled") and ctx.author.id not in ctx.bot.owner_ids:
            await ctx.warning(
                "This command is currently disabled by the admin team of Akari, for further information please join the [Akari Server](https://discord.gg/akaribot)."
            )
            return False
    return True


@bot.check
async def disabled_module(ctx: AkariContext):
    if ctx.command.cog:
        if await ctx.bot.db.fetchrow(
            """
      SELECT FROM disablemodule
      WHERE guild_id = $1
      AND module = $2
      """,
            ctx.guild.id,
            ctx.command.cog_name,
        ):
            if not ctx.author.guild_permissions.administrator:
                await ctx.warning(
                    f"The module **{str(ctx.command.cog_name.lower())}** is **disabled** in this server"
                )
                return False
            else:
                return True
        else:
            return True
    else:
        return True


@bot.check
async def restricted_command(ctx: AkariContext):
    if ctx.author.id == ctx.guild.owner_id:
        return True

    if check := await ctx.bot.db.fetch(
        """
    SELECT * FROM restrictcommand
    WHERE guild_id = $1
    AND command = $2
    """,
        ctx.guild.id,
        ctx.command.qualified_name,
    ):
        for row in check:
            role = ctx.guild.get_role(row["role_id"])
            if not role:
                await ctx.bot.db.execute(
                    """
          DELETE FROM restrictcommand
          WHERE role_id = $1
          """,
                    row["role_id"],
                )

            if not role in ctx.author.roles:
                await ctx.warning(f"You cannot use `{ctx.command.qualified_name}`")
                return False
            return True
    return True


@bot.tree.context_menu(name="avatar")
async def avatar_user(interaction: discord.Interaction, member: discord.Member):
    """
    Get a member's avatar
    """

    embed = discord.Embed(
        color=await interaction.client.dominant_color(member.display_avatar.url),
        title=f"{member.name}'s avatar",
        url=member.display_avatar.url,
    )

    embed.set_image(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.context_menu(name="banner")
async def banner_user(interaction: discord.Interaction, member: discord.Member):
    """
    Get a member's banner
    """

    member = await interaction.client.fetch_user(member.id)

    if not member.banner:
        return await interaction.warn(f"{member.mention} doesn't have a banner")

    banner = member.banner.url
    embed = discord.Embed(
        color=await interaction.client.dominant_color(banner),
        title=f"{member.name}'s banner",
        url=banner,
    )
    embed.set_image(url=member.banner.url)
    return await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    bot.run()
