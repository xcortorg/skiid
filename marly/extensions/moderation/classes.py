from system.base.context import Context
from discord.ext.commands import check
from discord.ext.commands import CommandError


class ModConfig:
    def is_mod_configured():
        async def predicate(ctx: Context):
            settings = await ctx.settings.fetch(ctx.bot, ctx.guild)

            if not settings.mod_log:
                raise CommandError(
                    f"Moderation isn't **enabled** in this server",
                    f"Enable it using `{ctx.clean_prefix}setup` command",
                )
            return True

        return check(predicate)
