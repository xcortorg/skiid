from abc import ABC, abstractmethod
from typing import Any, Optional, Union

import discord
from autoroom.pcx_template import Template
from discord.ext.commands import CooldownMapping

from grief.core import Config
from grief.core.bot import Grief


class MixinMeta(ABC):
    """Base class for well-behaved type hint detection with composite class.

    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    bot: Grief
    config: Config
    template: Template
    bucket_autoroom_name: CooldownMapping
    extra_channel_name_change_delay: int

    perms_public: dict[str, bool]
    perms_locked: dict[str, bool]
    perms_private: dict[str, bool]

    @staticmethod
    @abstractmethod
    def get_template_data(
        member: Union[discord.Member, discord.User]
    ) -> dict[str, str]:
        raise NotImplementedError()

    @abstractmethod
    def format_template_room_name(self, template: str, data: dict, num: int = 1) -> str:
        raise NotImplementedError()

    @abstractmethod
    def check_perms_source_dest(
        self,
        autoroom_source: discord.VoiceChannel,
        category_dest: discord.CategoryChannel,
        *,
        with_manage_roles_guild: bool = False,
        with_optional_clone_perms: bool = False,
        detailed: bool = False,
    ) -> tuple[bool, bool, Optional[str]]:
        raise NotImplementedError()

    @abstractmethod
    async def get_all_autoroom_source_configs(
        self, guild: discord.Guild
    ) -> dict[int, dict[str, Any]]:
        raise NotImplementedError()

    @abstractmethod
    async def get_autoroom_source_config(
        self, autoroom_source: discord.VoiceChannel
    ) -> Optional[dict[str, Any]]:
        raise NotImplementedError()

    @abstractmethod
    async def get_autoroom_info(
        self, autoroom: Optional[discord.VoiceChannel]
    ) -> Optional[dict[str, Any]]:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def check_if_member_or_role_allowed(
        channel: discord.VoiceChannel,
        member_or_role: Union[discord.Member, discord.Role],
    ) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def get_member_roles(
        self, autoroom_source: discord.VoiceChannel
    ) -> list[discord.Role]:
        raise NotImplementedError()

    @abstractmethod
    async def get_bot_roles(self, guild: discord.Guild) -> list[discord.Role]:
        raise NotImplementedError()
