import discord.ext.commands as commands
import humanize
from datetime import datetime, timedelta

original_cooldown_str = commands.CommandOnCooldown.__str__
original_no_pm_str = commands.NoPrivateMessage.__str__
original_missing_role_str = commands.MissingRole.__str__
original_missing_any_role_str = commands.MissingAnyRole.__str__

def custom_cooldown_str(self):
    retry_after = timedelta(seconds=self.retry_after)
    if retry_after.total_seconds() < 60:
        return f"Please wait {round(retry_after.total_seconds())} seconds before using this command again"
    return f"Please wait {humanize.naturaldelta(retry_after)} before using this command again"

def custom_no_pm_str(self):
    return "This command can only be used in servers, not in DMs!"

def custom_missing_role_str(self):
    return f"You need the {self.missing_role} role to use this command"

def custom_missing_any_role_str(self):
    roles = ", ".join(str(role) for role in self.missing_roles)
    return f"You need one of these roles to use this command: {roles}"

commands.CommandOnCooldown.__str__ = custom_cooldown_str
commands.NoPrivateMessage.__str__ = custom_no_pm_str
commands.MissingRole.__str__ = custom_missing_role_str
commands.MissingAnyRole.__str__ = custom_missing_any_role_str