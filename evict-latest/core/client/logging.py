from logging import INFO, basicConfig, getLogger, Filter


class IgnoreSpecificMessages(Filter):
    def filter(self, record):
        if (
            "HTTP Request: POST" in record.getMessage()
            or "HTTP/1.1 429 Too Many Requests" in record.getMessage()
        ):
            return False
        return True


ignore = (
    "pomice",
    "client",
    "web_log",
    "gateway",
    "launcher",
    "pyppeteer",
    "__init__",
    "_client",
)

for module in ignore:
    logger = getLogger(module)
    logger.disabled = True
    logger.propagate = False

basicConfig(
    level=INFO,
    format="\x1b[30;46m{process}\033[0m:{levelname:<9} (\x1b[35m{asctime}\033[0m) \x1b[37;3m@\033[0m \x1b[31m{module:<9}\033[0m -> {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
)

root_logger = getLogger()
root_logger.addFilter(IgnoreSpecificMessages())
