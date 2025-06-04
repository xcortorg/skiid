import asyncio
import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import discord

from grief.core import Config, commands
from grief.core.bot import Grief

from .core.utils import QuickAction
from .core.warden.enums import Event as WardenEvent
from .core.warden.rule import WardenRule
from .enums import EmergencyModules, Rank


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


class MixinMeta(ABC):
    """
    Base class for well behaved type hint detection with composite class.
    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    def __init__(self, *_args):
        self.config: Config
        self.bot: Grief
        self.emergency_mode: dict
        self.active_warden_rules: dict
        self.invalid_warden_rules: dict
        self.warden_checks: dict
        self.joined_users: dict
        self.monitor: dict
        self.loop: asyncio.AbstractEventLoop
        self.quick_actions: Dict[int, Dict[int, QuickAction]]

    @abstractmethod
    async def rank_user(self, member: discord.Member) -> Rank:
        raise NotImplementedError()

    @abstractmethod
    async def is_rank_4(self, member: discord.Member) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def is_role_privileged(
        self, role: discord.Role, issuers_top_role: discord.Role = None
    ) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def make_message_log(
        self,
        obj,
        *,
        guild: discord.Guild,
        requester: discord.Member = None,
        replace_backtick=False,
        pagify_log=False
    ):
        raise NotImplementedError()

    @abstractmethod
    def has_staff_been_active(self, guild: discord.Guild, minutes: int) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def refresh_staff_activity(self, guild: discord.Guild, timestamp=None):
        raise NotImplementedError()

    @abstractmethod
    async def refresh_with_audit_logs_activity(self, guild: discord.Guild):
        raise NotImplementedError()

    @abstractmethod
    def is_in_emergency_mode(self, guild: discord.Guild) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def send_to_monitor(self, guild: discord.Guild, entry: str):
        raise NotImplementedError()

    @abstractmethod
    async def send_announcements(self):
        raise NotImplementedError()

    @abstractmethod
    async def inc_message_count(self, member: discord.Member):
        raise NotImplementedError()

    @abstractmethod
    async def get_total_recorded_messages(self, member: discord.Member) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def is_helper(self, member: discord.Member) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def is_emergency_module(self, guild, module: EmergencyModules):
        raise NotImplementedError()

    @abstractmethod
    async def create_modlog_case(
        self,
        bot,
        guild,
        created_at,
        action_type,
        user,
        moderator=None,
        reason=None,
        until=None,
        channel=None,
        last_known_username=None,
    ):
        raise NotImplementedError()

    @abstractmethod
    async def send_notification(
        self,
        destination: discord.abc.Messageable,
        description: str,
        *,
        title: str = None,
        fields: list = [],
        footer: str = None,
        thumbnail: str = None,
        ping=False,
        file: discord.File = None,
        react: str = None,
        jump_to: discord.Message = None,
        allow_everyone_ping=False,
        force_text_only=False,
        heat_key: str = None,
        no_repeat_for: datetime.timedelta = None,
        quick_action: QuickAction = None,
        view: discord.ui.View = None
    ) -> Optional[discord.Message]:
        raise NotImplementedError()

    @abstractmethod
    async def join_monitor_flood(self, member: discord.Member):
        raise NotImplementedError()

    @abstractmethod
    async def join_monitor_suspicious(self, member: discord.Member):
        raise NotImplementedError()

    @abstractmethod
    async def invite_filter(self, message: discord.Message):
        raise NotImplementedError()

    @abstractmethod
    async def detect_raider(self, message: discord.Message):
        raise NotImplementedError()

    @abstractmethod
    async def comment_analysis(self, message: discord.Message):
        raise NotImplementedError()

    @abstractmethod
    async def make_identify_embed(self, message, user, rank=True, link=True):
        raise NotImplementedError()

    @abstractmethod
    async def callout_if_fake_admin(self, ctx: commands.Context):
        raise NotImplementedError()

    @abstractmethod
    def get_warden_rules_by_event(
        self, guild: discord.Guild, event: WardenEvent
    ) -> List[WardenRule]:
        raise NotImplementedError()

    @abstractmethod
    def dispatch_event(self, event_name, *args):
        raise NotImplementedError()

    @abstractmethod
    async def format_punish_message(self, member: discord.Member) -> str:
        raise NotImplementedError()
