from __future__ import annotations

import asyncio
from abc import ABC, ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import discord
from aiohttp.abc import AbstractMatchInfo
from red_commons.logging import getLogger

from grief.core import Config, commands
from grief.core.bot import Grief
from grief.core.commands import Context
from grief.core.i18n import Translator

from .converter import (ButtonStyleConverter, RawUserIds, RoleEmojiConverter,
                        RoleHierarchyConverter, SelfRoleConverter)

log = getLogger("grief.roletools")
_ = Translator("Roletools", __file__)


class RoleToolsMixin(ABC):
    """
    Base class for well behaved type hint detection with composite class.

    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    def __init__(self, *_args):
        super().__init__()
        self.config: Config
        self.bot: Grief
        self.settings: Dict[Any, Any]
        self._ready: asyncio.Event
        self.views: Dict[int, Dict[str, discord.ui.View]]

    @commands.group()
    @commands.guild_only()
    async def roletools(self, ctx: Context) -> None:
        """
        Commands for creating custom role settings
        """

    #######################################################################
    # roletools.py                                                        #
    #######################################################################

    @abstractmethod
    async def confirm_selfassignable(
        self, ctx: commands.Context, roles: List[discord.Role]
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def giverole(
        self,
        ctx: commands.Context,
        role: RoleHierarchyConverter,
        *who: Union[discord.Role, discord.TextChannel, discord.Member, str],
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def removerole(
        self,
        ctx: commands.Context,
        role: RoleHierarchyConverter,
        *who: Union[discord.Role, discord.TextChannel, discord.Member, str],
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def forcerole(
        self,
        ctx: commands.Context,
        users: commands.Greedy[Union[discord.Member, RawUserIds]],
        *,
        role: RoleHierarchyConverter,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def forceroleremove(
        self,
        ctx: commands.Context,
        users: commands.Greedy[Union[discord.Member, RawUserIds]],
        *,
        role: RoleHierarchyConverter,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def viewroles(
        self, ctx: commands.Context, *, role: Optional[discord.Role]
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def roletools_slash(self, ctx: Context) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def roletools_global_slash(self, ctx: Context) -> None:
        raise NotImplementedError()

    #######################################################################
    # inclusive.py                                                        #
    #######################################################################

    @abstractmethod
    async def inclusive(self, ctx: commands.Context) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def inclusive_add(
        self,
        ctx: commands.Context,
        role: RoleHierarchyConverter,
        *,
        include: commands.Greedy[RoleHierarchyConverter],
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def mutual_inclusive_add(
        self, ctx: Context, *roles: RoleHierarchyConverter
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def inclusive_remove(
        self,
        ctx: commands.Context,
        role: RoleHierarchyConverter,
        *,
        include: commands.Greedy[RoleHierarchyConverter],
    ) -> None:
        raise NotImplementedError()

    #######################################################################
    # exclusive.py                                                        #
    #######################################################################

    @abstractmethod
    async def exclusive(self, ctx: commands.Context) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def exclusive_add(
        self,
        ctx: commands.Context,
        role: RoleHierarchyConverter,
        *,
        exclude: commands.Greedy[RoleHierarchyConverter],
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def mutual_exclusive_add(
        self, ctx: Context, *roles: RoleHierarchyConverter
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def exclusive_remove(
        self,
        ctx: commands.Context,
        role: RoleHierarchyConverter,
        *,
        exclude: commands.Greedy[RoleHierarchyConverter],
    ) -> None:
        raise NotImplementedError()

    #######################################################################
    # settings.py                                                         #
    #######################################################################

    #   @abstractmethod
    #   async def selfadd(
    #       self,
    #       ctx: commands.Context,
    #        true_or_false: Optional[bool] = None,
    #        *,
    #             role: RoleHierarchyConverter,
    #   ) -> None:
    #       raise NotImplementedError()

    #    @abstractmethod
    #    async def selfrem(
    #      self,
    #            ctx: commands.Context,
    #        true_or_false: Optional[bool] = None,
    #        *,
    #        role: RoleHierarchyConverter,
    #    ) -> None:
    #   raise NotImplementedError()

    #  @abstractmethod
    # async def atomic(
    # self, ctx: commands.Context, true_or_false: Optional[Union[bool, str]] = None
    # ) -> None:
    # raise NotImplementedError()

    #  @abstractmethod
    #   async def globalatomic(self, ctx: Context, true_or_false: Optional[bool] = None) -> None:
    #       raise NotImplementedError()

    @abstractmethod
    async def sticky(
        self,
        ctx: commands.Context,
        true_or_false: Optional[bool] = None,
        *,
        role: RoleHierarchyConverter,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def autorole(
        self,
        ctx: commands.Context,
        true_or_false: Optional[bool] = None,
        *,
        role: RoleHierarchyConverter,
    ) -> None:
        raise NotImplementedError()

    #######################################################################
    # events.py                                                           #
    #######################################################################

    @abstractmethod
    async def check_guild_verification(
        self, member: discord.Member, guild: discord.Guild
    ) -> Union[bool, int]:
        raise NotImplementedError()

    @abstractmethod
    async def wait_for_verification(
        self, member: discord.Member, guild: discord.Guild
    ) -> None:
        raise NotImplementedError()

        # @abstractmethod

    #  async def check_atomicity(self, guild: discord.Guild) -> bool:
    #      raise NotImplementedError()

    @abstractmethod
    async def give_roles(
        self,
        member: discord.Member,
        roles: List[discord.Role],
        reason: Optional[str] = None,
        *,
        check_required: bool = True,
        check_exclusive: bool = True,
        check_inclusive: bool = True,
        check_cost: bool = True,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def remove_roles(
        self,
        member: discord.Member,
        roles: List[discord.Role],
        reason: Optional[str] = None,
        *,
        check_inclusive: bool = True,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _auto_give(self, member: discord.Member) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _sticky_leave(self, member: discord.Member) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _sticky_join(self, member: discord.Member) -> None:
        raise NotImplementedError()
