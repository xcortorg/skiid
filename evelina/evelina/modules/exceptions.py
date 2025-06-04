from discord.ext.commands import CommandError

class LastFmException(CommandError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class RenameRateLimit(CommandError):
    def __init__(self, message: str = "You renamed this channel too many times in a short amount of time"):
        self.message = message
        super().__init__(self.message)

class WrongMessageLink(CommandError):
    def __init__(self, message: str = "This message does not belong to this server"):
        self.message = message
        super().__init__(self.message)

class ApiError(CommandError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"The API returned **{self.status_code}** as the status code")