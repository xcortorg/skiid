import traceback


class UserSuspended(Exception):
    def __init__(self, message):
        self.message = message
        self.traceback_info = traceback.format_exc()
        super().__init__(f"{self.message} is suspended!")


class UserNotFound(Exception):
    def __init__(self, message):
        self.message = message
        self.traceback_info = traceback.format_exc()
        super().__init__(f"{self.message} is not a valid user!")


class TweetNotFound(Exception):
    def __init__(self, message):
        self.message = message
        self.traceback_info = traceback.format_exc()
        super().__init__(f"no tweet can be found from URL `{message}`")
