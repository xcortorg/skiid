"""
Copyright 2024 Samuel Davis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from typing import (TYPE_CHECKING, Any, Awaitable, Callable, Coroutine, Dict,
                    List, Optional, TypeVar, Union)

if TYPE_CHECKING:
    from discord.ext.commands import (AutoShardedBot, Bot, Cog, CommandError,
                                      Context)

T = TypeVar("T")

_Bot = Union["Bot", "AutoShardedBot"]
Coro = Coroutine[Any, Any, T]
CoroFunc = Callable[..., Coro[Any]]
MaybeCoro = Union[T, Coro[T]]
MaybeAwaitable = Union[T, Awaitable[T]]

CogT = TypeVar("CogT", bound="Optional[Cog]")
UserCheck = Callable[["ContextT"], MaybeCoro[bool]]
Hook = Union[
    Callable[["CogT", "ContextT"], Coro[Any]], Callable[["ContextT"], Coro[Any]]
]
Error = Union[
    Callable[["CogT", "ContextT", "CommandError"], Coro[Any]],
    Callable[["ContextT", "CommandError"], Coro[Any]],
]

ContextT = TypeVar("ContextT", bound="Context[Any]")
BotT = TypeVar("BotT", bound=_Bot, covariant=True)

ContextT_co = TypeVar("ContextT_co", bound="Context[Any]", covariant=True)

JSON = Dict[Any, Any]
