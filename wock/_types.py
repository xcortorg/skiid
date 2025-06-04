import traceback
from contextlib import contextmanager
from logging import getLogger
from random import uniform
from typing import Any, Dict, List, Optional, Union

import orjson

logger = getLogger(__name__)


@contextmanager
def catch(exception_type=Exception):
    try:
        yield
    except exception_type as error:
        exc = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        logger.info(f"error raised: {exc}")
        raise error


Numeric = Union[float, int, str]


def maximum(self: Numeric, maximum: Numeric) -> Optional[Numeric]:
    return min(float(self), float(maximum))


def maximum_(self: Numeric, maximum: Numeric) -> Optional[Numeric]:
    return int(min(float(self), float(maximum)))


def minimum(self: Numeric, minimum: Numeric) -> Optional[Numeric]:
    return max(float(minimum), float(self))


def minimum_(self: Numeric, minimum: Numeric) -> Optional[Numeric]:
    return int(max(float(minimum), float(self)))


@property
def positive(self: Numeric) -> Optional[Numeric]:
    return max(float(0.00), float(self))


@property
def positive_(self: Numeric) -> Optional[Numeric]:
    return int(max(float(0.00), float(self)))


def calculate_(chance: Numeric, total: Optional[Numeric] = 100.0) -> bool:
    roll = uniform(0.0, float(total))
    return roll < float(chance)


def hyperlink(text: str, url: str, character: Optional[str] = None) -> str:
    if character:
        return f"[{character}{text}{character}]({url})"
    else:
        return f"[{text}]({url})"


def shorten(self: str, length: int) -> str:
    return self[:length]


class ObjectTransformer(dict):
    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'{self.__name__}' object has no attribute '{key}'")

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def __delattr__(self, key: str) -> None:
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'{self.__name__}' object has no attribute '{key}'")

    @classmethod
    def _convert(cls, value: Any, visited: set = None) -> Any:
        if visited is None:
            visited = set()

        if id(value) in visited:
            return value

        visited.add(id(value))

        if isinstance(value, dict):
            return cls({k: cls._convert(v, visited) for k, v in value.items()})
        elif isinstance(value, list):
            return [cls._convert(v, visited) for v in value]
        else:
            return value

    @classmethod
    async def from_data(cls, data: Union[Dict[str, Any], bytes]) -> "ObjectTransformer":
        parsed_data = orjson.loads(data) if isinstance(data, bytes) else data
        return cls(cls._convert(parsed_data))


def asDict(obj, max_depth=5) -> dict:
    """
    Recursively extract all properties from a class and its nested property classes into a dictionary.

    :param obj: The class instance from which to extract properties.
    :param max_depth: The maximum depth to recurse.
    :return: A dictionary containing the properties and their values.
    """

    def is_property(obj):
        return isinstance(obj, property)

    def get_properties(obj, depth, seen):
        if depth > max_depth or id(obj) in seen:
            return {}  # Avoid infinite recursion and limit depth
        seen.add(id(obj))

        properties = {}
        for name, value in obj.__class__.__dict__.items():
            if is_property(value):
                try:
                    prop_value = getattr(obj, name)
                    if hasattr(prop_value, "__class__") and not isinstance(
                        prop_value, (int, float, str, bool, type(None))
                    ):
                        try:
                            properties[name] = get_properties(
                                prop_value, depth + 1, seen
                            )
                        except AttributeError:
                            continue
                    else:
                        properties[name] = prop_value
                except RecursionError:
                    properties[name] = "RecursionError"
        return properties

    return get_properties(obj, 0, set())


# def test():
#     builtins.calculate = calculate_

#     _float = get_referents(float.__dict__)[0]
#     _int = get_referents(int.__dict__)[0]
#     __float = get_referents(builtins.float.__dict__)[0]
#     __int = get_referents(builtins.int.__dict__)[0]
#     _float["maximum"] = maximum
#     _float["minimum"] = minimum
#     _float["positive"] = positive
#     __float["maximum"] = maximum
#     __float["minimum"] = minimum
#     __float["positive"] = positive
#     _int["maximum"] = maximum_
#     _int["minimum"] = minimum_
#     _int["positive"] = positive_
#     __int["maximum"] = maximum_
#     __int["minimum"] = minimum_
#     __int["positive"] = positive_
#     n = int(1500)
#     number = float(1000.0)
#     print(f"{isinstance(number, float)}")
#     negative_number = float(-1.0)
#     if isinstance(n, int):
#         print("it is an integer")
#         print(", ".join(m for m in dir(n) if not m.startswith("__")))
#     else: print(f"not an integer its a {type(n)}")

#     print(f"positive float: {number}\nnegative float: {negative_number}\n\nmaximum set: 500.0\nminimum set: 1200.0")
#     print(f"float.maximum testing: {number.maximum(500.0)}\n")
#     print(f"float.positive testing: {negative_number.positive}\n")
#     print(f"float.minimum testing: {number.minimum(1200.0)}")

#     percentage = 10.0
#     total = 100.0
#     print(f"chance of winning {percentage}/{total}")
#     runs = []
#     for i in range(int(percentage)+1):
#         runs.append(calculate(percentage, total))

#     r = "".join(f"run {i}: {'lost' if v is False else 'won'}\n" for i, v in enumerate(runs, start = 1))
#     print(r)

# if __name__ == "__main__":
#     test()
