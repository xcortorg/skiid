from modules.helpers import EvelinaContext
from modules.checks.calls import disabled_command, disabled_module, restricted_command, restricted_module, blacklisted

@staticmethod
async def disabled_command_check(ctx: EvelinaContext):
    return await disabled_command(ctx)

@staticmethod
async def disabled_module_check(ctx: EvelinaContext):
    return await disabled_module(ctx)

@staticmethod
async def restricted_command_check(ctx: EvelinaContext):
    return await restricted_command(ctx)

@staticmethod
async def restricted_module_check(ctx: EvelinaContext):
    return await restricted_module(ctx)

@staticmethod
async def blacklisted_check(ctx: EvelinaContext):
    return await blacklisted(ctx)

# @staticmethod
# async def availability_check(ctx: EvelinaContext):
#     return await check_availability(ctx)