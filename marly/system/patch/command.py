from discord.ext.commands.core import Command, hooked_wrapped_callback

from system.base.context import Context


class CommandCore(Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def permissions(self):
        if self.checks:
            for check in self.checks:
                check_str = str(check)
                if "has_permissions" in check_str:
                    return await check(0)
                elif "is_owner" in check_str:
                    return ["Bot Owner"]

        return []


Command.permissions = CommandCore.permissions
