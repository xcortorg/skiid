class CoreException(Exception):
    pass


class MisconfigurationError(CoreException):
    pass


class WardenException(Exception):
    pass


class InvalidRule(WardenException):
    pass


class ExecutionError(WardenException):
    pass


class StopExecution(WardenException):
    pass
