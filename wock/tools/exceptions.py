from discord.ext.commands import CommandError, CommandNotFound


class InvalidSubCommand(Exception):
    def __init__(self, message: str, **kwargs: dict):
        self.message = message
        super().__init__(self.message)
