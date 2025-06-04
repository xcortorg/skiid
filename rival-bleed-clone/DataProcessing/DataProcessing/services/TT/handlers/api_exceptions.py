class APIError(Exception):

    def __init__(self, status_code=None):
        self.status_code = status_code

    def display_error(self):
        return f"Error: {self.args[0]}." + (
            f" Status Code: {self.status_code}." if self.status_code else ""
        )


class APIConnectionError(APIError):

    def display_error(self):
        return f"API Connection Error: {self.args[0]}."


class APIUnavailableError(APIError):

    def display_error(self):
        return f"API Unavailable Error: {self.args[0]}."


class APINotFoundError(APIError):

    def display_error(self):
        return f"API Not Found Error: {self.args[0]}."


class APIResponseError(APIError):

    def display_error(self):
        return f"API Response Error: {self.args[0]}."


class APIRateLimitError(APIError):

    def display_error(self):
        return f"API Rate Limit Error: {self.args[0]}."


class APITimeoutError(APIError):

    def display_error(self):
        return f"API Timeout Error: {self.args[0]}."


class APIUnauthorizedError(APIError):

    def display_error(self):
        return f"API Unauthorized Error: {self.args[0]}."


class APIRetryExhaustedError(APIError):
    def display_error(self):
        return f"API Retry Exhausted Error: {self.args[0]}."
