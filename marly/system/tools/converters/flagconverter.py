from discord.ext.commands import (
    FlagConverter as OriginalFlagConverter,
)

from typing import Tuple, Self

from system.base.context import Context


class CustomFlagConverter(
    OriginalFlagConverter,
    case_insensitive=True,
    prefix="--",
    delimiter=" ",
):
    @property
    def values(self):
        return self.get_flags().values()

    async def convert(self, ctx: Context, argument: str):
        argument = argument.replace("—", "--")
        result = await super().convert(ctx, argument)
        return result

    async def find(
        self,
        ctx: Context,
        argument: str,
        *,
        remove: bool = True,
    ) -> Tuple[str, Self]:
        """
        Run the conversion and return the
        result with the remaining string.
        """
        argument = argument.replace("—", "--")
        flags = await self.convert(ctx, argument)

        if remove:
            for key, values in flags.parse_flags(argument).items():
                aliases = getattr(self.get_flags().get(key), "aliases", [])
                for _key in aliases:
                    argument = argument.replace(f"--{_key} {' '.join(values)}", "")
                argument = argument.replace(f"--{key} {' '.join(values)}", "")

        return argument.strip(), flags
