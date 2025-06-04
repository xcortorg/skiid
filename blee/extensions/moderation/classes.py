import datetime
from typing import Union

from discord import Embed, Member, User
from discord.ext.commands import check
from tools.bleed import Bleed
from tools.client.context import Context


class Mod:

    def is_mod_configured():
        async def predicate(ctx: Context):

            check = await ctx.bot.db.fetchrow(
                "SELECT * FROM mod WHERE guild_id = $1", ctx.guild.id
            )

            if not check:

                await ctx.warn(
                    f"Moderation isn't **enabled** in this server. Enable it using `{ctx.clean_prefix}setup` command"
                )

                return False
            return True

        return check(predicate)


class ModConfig:

    async def sendlogs(
        bot: Bleed,
        action: str,
        author: Member,
        victim: Union[Member, User],
        reason: str,
    ):
        check = await bot.db.fetchrow(
            "SELECT channel_id FROM mod WHERE guild_id = $1", author.guild.id
        )

        if check:

            res = await bot.db.fetchrow(
                "SELECT count FROM cases WHERE guild_id = $1", author.guild.id
            )
            case = int(res["count"]) + 1
            await bot.db.execute(
                "UPDATE cases SET count = $1 WHERE guild_id = $2", case, author.guild.id
            )

            embed = Embed(timestamp=datetime.datetime.now())

            embed.set_author(name="Modlog Entry", icon_url=author.display_avatar)

            embed.add_field(
                name="Information",
                value=f"**Case #{case}** | {action}\n**User**: {victim} (`{victim.id}`)\n**Moderator**: {author} (`{author.id}`)\n**Reason**: {reason}",
            )

            try:
                await author.guild.get_channel(int(check["channel_id"])).send(
                    embed=embed
                )

            except:
                pass
