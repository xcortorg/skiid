import asyncio
import discord
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple, Union, Any, NoReturn
from discord import Embed, app_commands
from discord.ext import commands, tasks
from dataclasses import dataclass, field
from enum import Enum
import traceback
import json

from tool.important.services.twitch import TwitchService
from tool.important.services.twitch import Stream, Channel, StreamResponse

from tool.greed import Greed
from loguru import logger

class StreamStatus(Enum):
    """Enum representing the status of a stream."""

    OFFLINE = 0  # Stream is not live
    LIVE = 1  # Stream is currently live
    UPDATED = 2  # Stream information has been updated


@dataclass
class StreamNotification:
    """Represents a notification sent to a Discord channel for a stream."""

    channel_id: int
    message_id: Optional[int] = None
    last_notified: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "channel_id": self.channel_id,
            "message_id": self.message_id,
            "last_notified": (
                self.last_notified.isoformat() if self.last_notified else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamNotification":
        """Create from dictionary from database storage."""
        return cls(
            channel_id=data["channel_id"],
            message_id=data["message_id"],
            last_notified=(
                datetime.fromisoformat(data["last_notified"])
                if data.get("last_notified")
                else None
            ),
        )


@dataclass
class StreamData:
    """Represents data for a Twitch stream."""

    stream_id: str
    username: str
    title: str
    game: str
    viewer_count: int
    thumbnail_url: str
    started_at: datetime
    is_live: bool = True
    notifications: List[StreamNotification] = field(default_factory=list)
    last_updated: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "stream_id": self.stream_id,
            "username": self.username,
            "title": self.title,
            "game": self.game,
            "viewer_count": self.viewer_count,
            "thumbnail_url": self.thumbnail_url,
            "started_at": self.started_at.isoformat(),
            "is_live": self.is_live,
            "notifications": [n.to_dict() for n in self.notifications],
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamData":
        """Create from dictionary from database storage."""
        return cls(
            stream_id=data["stream_id"],
            username=data["username"],
            title=data["title"],
            game=data["game"],
            viewer_count=data["viewer_count"],
            thumbnail_url=data["thumbnail_url"],
            started_at=datetime.fromisoformat(data["started_at"]),
            is_live=data["is_live"],
            notifications=[
                StreamNotification.from_dict(n) for n in data.get("notifications", [])
            ],
            last_updated=(
                datetime.fromisoformat(data["last_updated"])
                if data.get("last_updated")
                else None
            ),
        )

    def should_update_notification(self) -> bool:
        """Determine if notification should be updated based on changes."""
        if not self.last_updated:
            return False

        # Update if it's been at least 15 minutes since last update
        time_threshold = timedelta(minutes=15)
        # Ensure both datetimes are timezone-aware
        now = datetime.now(timezone.utc)
        last_updated = self.last_updated if self.last_updated.tzinfo else self.last_updated.replace(tzinfo=timezone.utc)
        return now - last_updated >= time_threshold


class FeedManager:
    """
    Manages feed subscriptions and notifications for Twitch streams.

    This class handles:
    - Stream monitoring and status tracking
    - Notification management
    - Subscription persistence with PostgreSQL
    - Adaptive polling with error handling
    """

    def __init__(self, bot: Greed) -> None:
        """
        Initialize the feed manager.

        Args:
            bot: The main bot instance providing database and config access
        """
        self.bot = bot
        self.db = bot.db
        self.twitch_service = TwitchService(self.bot.db)
        self.active_streams: Dict[str, StreamData] = {}
        self.stream_tasks: Dict[str, asyncio.Task] = {}
        self.subscriptions: Dict[str, Set[int]] = {}
        self.update_lock = asyncio.Lock()

    async def setup_database(self):
        """Create necessary database tables if they don't exist."""
        try:
            # Create schema if it doesn't exist
            await self.db.execute("CREATE SCHEMA IF NOT EXISTS twitch")

            # Create subscriptions table
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS twitch.subscriptions (
                    username TEXT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    PRIMARY KEY (username, channel_id)
                )
            """)

            # Create active streams table
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS twitch.active_streams (
                    stream_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    title TEXT NOT NULL,
                    game TEXT NOT NULL,
                    viewer_count INTEGER NOT NULL,
                    thumbnail_url TEXT NOT NULL,
                    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    is_live BOOLEAN NOT NULL DEFAULT TRUE,
                    notifications JSONB NOT NULL DEFAULT '[]',
                    last_updated TIMESTAMP WITH TIME ZONE
                )
            """)

            # Create custom messages table
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS twitch.custom_messages (
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    message TEXT NOT NULL,
                    is_embed BOOLEAN NOT NULL DEFAULT false,
                    PRIMARY KEY (guild_id, channel_id)
                )
            """)

            logger.info("Twitch database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            logger.error(traceback.format_exc())
            raise

    async def initialize(self):
        """Initialize the feed manager by loading subscriptions and active streams from database."""
        try:
            await self.setup_database()  # Ensure database tables exist
            await self.load_subscriptions()
            await self.load_active_streams()
            logger.info("Feed manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize feed manager: {e}")
            logger.error(traceback.format_exc())

    async def load_subscriptions(self):
        """Load subscriptions from database."""
        try:
            rows = await self.db.fetch("SELECT username, channel_id FROM twitch.subscriptions")
            
            # Group subscriptions by username
            for row in rows:
                username = row["username"]
                channel_id = row["channel_id"]
                
                if username not in self.subscriptions:
                    self.subscriptions[username] = set()
                self.subscriptions[username].add(channel_id)

                if username not in self.stream_tasks:
                    self.start_monitoring(username)

            logger.info(f"Loaded {len(self.subscriptions)} Twitch subscriptions")
        except Exception as e:
            logger.error(f"Failed to load subscriptions: {str(e)}")
            logger.error(traceback.format_exc())

    async def load_active_streams(self):
        """Load active streams from database."""
        try:
            rows = await self.db.fetch("""
                SELECT 
                    stream_id, username, title, game, viewer_count, 
                    thumbnail_url, started_at, is_live, notifications, 
                    last_updated 
                FROM twitch.active_streams 
                WHERE is_live = true
            """)
            
            for row in rows:
                stream_id = row["stream_id"]
                notifications = json.loads(row["notifications"]) if row["notifications"] else []
                
                stream_data = StreamData(
                    stream_id=stream_id,
                    username=row["username"],
                    title=row["title"],
                    game=row["game"],
                    viewer_count=row["viewer_count"],
                    thumbnail_url=row["thumbnail_url"],
                    started_at=row["started_at"],
                    is_live=row["is_live"],
                    notifications=[StreamNotification.from_dict(n) for n in notifications],
                    last_updated=row["last_updated"]
                )
                self.active_streams[stream_id] = stream_data

            logger.info(f"Loaded {len(self.active_streams)} active Twitch streams")
        except Exception as e:
            logger.error(f"Failed to load active streams: {str(e)}")
            logger.error(traceback.format_exc())

    async def save_active_stream(self, stream_id: str):
        """
        Save active stream to database.

        Args:
            stream_id: The ID of the stream to save
        """
        try:
            if stream_id in self.active_streams:
                stream_data = self.active_streams[stream_id]
                notifications = json.dumps([n.to_dict() for n in stream_data.notifications])
                
                await self.db.execute("""
                    INSERT INTO twitch.active_streams (
                        stream_id, username, title, game, viewer_count, 
                        thumbnail_url, started_at, is_live, notifications, 
                        last_updated
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (stream_id) DO UPDATE SET 
                        username = EXCLUDED.username,
                        title = EXCLUDED.title,
                        game = EXCLUDED.game,
                        viewer_count = EXCLUDED.viewer_count,
                        thumbnail_url = EXCLUDED.thumbnail_url,
                        started_at = EXCLUDED.started_at,
                        is_live = EXCLUDED.is_live,
                        notifications = EXCLUDED.notifications,
                        last_updated = EXCLUDED.last_updated
                """, 
                    stream_data.stream_id,
                    stream_data.username,
                    stream_data.title,
                    stream_data.game,
                    stream_data.viewer_count,
                    stream_data.thumbnail_url,
                    stream_data.started_at,
                    stream_data.is_live,
                    notifications,
                    stream_data.last_updated
                )
                logger.debug(f"Saved stream {stream_id} to database")
        except Exception as e:
            logger.error(f"Failed to save active stream {stream_id}: {str(e)}")
            logger.error(traceback.format_exc())

    def start_monitoring(self, username: str):
        """Start monitoring a Twitch stream."""
        if username in self.stream_tasks and not self.stream_tasks[username].done():
            return

        task = asyncio.create_task(self.monitor_stream(username))
        self.stream_tasks[username] = task
        logger.info(f"Started monitoring Twitch stream: {username}")

    def stop_monitoring(self, username: str):
        """Stop monitoring a Twitch stream."""
        if username in self.stream_tasks and not self.stream_tasks[username].done():
            self.stream_tasks[username].cancel()
            logger.info(f"Stopped monitoring Twitch stream: {username}")

    async def monitor_stream(self, username: str) -> None:
        """
        Monitor a Twitch stream for status changes with adaptive polling.

        Args:
            username: The Twitch username to monitor

        Implementation details:
        - Uses adaptive polling intervals based on stream status
        - Handles API errors with exponential backoff
        - Automatically cleans up when no subscribers remain
        """
        base_check_interval = 60  # Start with 60 seconds
        max_check_interval = 300  # Maximum 5 minutes
        current_interval = base_check_interval
        consecutive_errors = 0
        max_consecutive_errors = 5

        try:
            while True:
                try:
                    # Check if we still have subscribers
                    if (
                        username not in self.subscriptions
                        or not self.subscriptions[username]
                    ):
                        logger.info(
                            f"No more subscribers for {username}, stopping monitoring"
                        )
                        self.stop_monitoring(username)
                        return

                    # Get stream data from Twitch API
                    stream_data = await self.twitch_service.get_streams(
                        username=username
                    )

                    if not stream_data:
                        logger.warning(f"No stream data returned for {username}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(
                                f"Too many consecutive errors for {username}, increasing check interval"
                            )
                            current_interval = min(
                                current_interval * 2, max_check_interval
                            )
                        await asyncio.sleep(current_interval)
                        continue

                    # Reset error counter on successful API call
                    consecutive_errors = 0

                    # Process stream data
                    status = await self.process_stream_data(username, stream_data)

                    # Adjust polling interval based on stream status
                    if status == StreamStatus.LIVE:
                        # Stream is live, check more frequently
                        current_interval = base_check_interval
                    elif status == StreamStatus.OFFLINE:
                        # Stream is offline, check less frequently
                        current_interval = min(
                            current_interval * 1.5, max_check_interval
                        )

                except Exception as e:
                    logger.error(f"Error monitoring Twitch stream {username}: {str(e)}")
                    logger.error(traceback.format_exc())
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        current_interval = min(current_interval * 2, max_check_interval)

                await asyncio.sleep(current_interval)

        except asyncio.CancelledError:
            logger.info(f"Stream monitoring for {username} was cancelled")
        except Exception as e:
            logger.error(f"Fatal error in stream monitoring for {username}: {str(e)}")
            logger.error(traceback.format_exc())
            # Re-raise to ensure the error is properly handled
            raise

    async def process_stream_data(
        self, username: str, stream_data: StreamResponse
    ) -> StreamStatus:
        """
        Process stream data and determine stream status.

        Args:
            username: The username of the stream to process
            stream_data: The StreamResponse object from Twitch API

        Returns:
            StreamStatus: The current status of the stream
        """
        async with self.update_lock:
            try:
                if stream_data.stream:  # Use the stream property from StreamResponse
                    # Stream is live
                    stream = stream_data.stream
                    stream_id = stream.id

                    # Verify channel data
                    try:
                        user_data = await self.twitch_service.get_channel(
                            stream.user_login
                        )
                        if not user_data or not user_data.channel:
                            logger.error(
                                f"Invalid channel response for {username}: {user_data}"
                            )
                            return StreamStatus.OFFLINE
                    except Exception as e:
                        logger.error(f"Failed to get channel data for {username}: {e}")
                        return StreamStatus.OFFLINE

                    # Process stream data
                    if stream_id not in self.active_streams:
                        # New stream
                        self.active_streams[stream_id] = StreamData(
                            stream_id=stream_id,
                            username=stream.user_name,
                            title=stream.title or "No Title",
                            game=stream.game_name or "Unknown",
                            viewer_count=stream.viewer_count or 0,
                            thumbnail_url=(
                                stream.thumbnail_url.replace("{width}", "1280").replace(
                                    "{height}", "720"
                                )
                                if stream.thumbnail_url
                                else ""
                            ),
                            started_at=stream.started_at,
                            last_updated=datetime.now(timezone.utc),
                        )

                        await self.send_notifications(stream_id)
                        await self.save_active_stream(stream_id)
                        return StreamStatus.LIVE
                    else:
                        # Existing stream - check for significant updates
                        stream_obj = self.active_streams[stream_id]
                        stream_obj.title = stream.title or "No Title"
                        stream_obj.game = stream.game_name or "Unknown"
                        stream_obj.viewer_count = stream.viewer_count or 0
                        stream_obj.thumbnail_url = (
                            stream.thumbnail_url.replace("{width}", "1280").replace(
                                "{height}", "720"
                            )
                            if stream.thumbnail_url
                            else ""
                        )

                        if stream_obj.should_update_notification():
                            stream_obj.last_updated = datetime.now(timezone.utc)
                            await self.update_notifications(stream_id)
                            await self.save_active_stream(stream_id)
                            return StreamStatus.UPDATED

                        return StreamStatus.LIVE
                else:
                    # Stream is offline
                    for stream_id, stream_data in list(self.active_streams.items()):
                        if (
                            stream_data.username.lower() == username.lower()
                            and stream_data.is_live
                        ):
                            stream_data.is_live = False
                            await self.send_offline_notifications(stream_id)
                            await self.save_active_stream(stream_id)

                            # Remove stream data after a delay
                            await asyncio.sleep(300)  # 5 minutes delay
                            if stream_id in self.active_streams:
                                del self.active_streams[stream_id]
                                await self.db.execute(
                                    "DELETE FROM twitch.active_streams WHERE stream_id = $1",
                                    stream_id
                                )

                    return StreamStatus.OFFLINE
            except Exception as e:
                logger.error(f"Error processing stream data for {username}: {str(e)}")
                logger.error(traceback.format_exc())
                return StreamStatus.OFFLINE

    async def get_custom_message(self, guild_id: int, channel_id: int) -> Optional[Tuple[str, bool]]:
        """Get custom message for a channel if it exists."""
        result = await self.db.fetchrow("""
            SELECT message, is_embed 
            FROM twitch.custom_messages 
            WHERE guild_id = $1 AND channel_id = $2
        """, guild_id, channel_id)
        
        if result:
            return result["message"], result["is_embed"]
        return None

    async def format_message(self, message: str, stream: StreamData) -> str:
        """Format a message with stream data."""
        return message.format(
            streamer=stream.username,
            title=stream.title,
            game=stream.game,
            viewers=f"{stream.viewer_count:,}",
            url=f"https://twitch.tv/{stream.username}"
        )

    async def send_notifications(self, stream_id: str) -> None:
        """Send notifications for a stream that just went live."""
        if stream_id not in self.active_streams:
            logger.warning(
                f"Attempted to send notifications for unknown stream: {stream_id}"
            )
            return

        stream = self.active_streams[stream_id]
        username = stream.username.lower()

        if username not in self.subscriptions:
            logger.warning(f"No subscribers found for stream: {username}")
            return

        notification_failures = []
        for channel_id in self.subscriptions[username]:
            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    logger.warning(
                        f"Could not find Discord channel {channel_id} for stream {username}"
                    )
                    notification_failures.append(channel_id)
                    continue

                # Check for custom message
                custom_message = await self.get_custom_message(channel.guild.id, channel_id)
                
                if custom_message:
                    message_text, is_embed = custom_message
                    formatted_text = await self.format_message(message_text, stream)
                    
                    if is_embed:
                        message = await self.bot.send_embed(channel, formatted_text)
                    else:
                        message = await channel.send(formatted_text)
                else:
                    # Use default notification format
                    embed = self.create_live_embed(stream)
                    message = await channel.send(
                        content=f"🔴 **{stream.username}** is now live on Twitch!",
                        embed=embed,
                    )

                notification = StreamNotification(
                    channel_id=channel_id,
                    message_id=message.id,
                    last_notified=datetime.now(timezone.utc),
                )
                stream.notifications.append(notification)

            except discord.Forbidden:
                logger.error(
                    f"Bot lacks permissions to send messages in channel {channel_id}"
                )
                notification_failures.append(channel_id)
            except discord.HTTPException as e:
                logger.error(
                    f"HTTP error sending notification to channel {channel_id}: {str(e)}"
                )
                notification_failures.append(channel_id)
            except Exception as e:
                logger.error(
                    f"Failed to send stream notification to channel {channel_id}: {str(e)}"
                )
                logger.error(traceback.format_exc())
                notification_failures.append(channel_id)

        # Clean up failed notification channels
        if notification_failures:
            for channel_id in notification_failures:
                await self.unsubscribe(username, channel_id)
                logger.info(
                    f"Removed subscription for channel {channel_id} due to notification failures"
                )

    async def update_notifications(self, stream_id: str) -> None:
        """
        Update existing notifications for a stream.

        Args:
            stream_id: The ID of the stream to update notifications for
        """
        if stream_id not in self.active_streams:
            logger.warning(
                f"Attempted to update notifications for unknown stream: {stream_id}"
            )
            return

        stream = self.active_streams[stream_id]
        failed_notifications = []

        for notification in stream.notifications:
            try:
                channel = self.bot.get_channel(notification.channel_id)
                if not channel:
                    logger.warning(
                        f"Could not find Discord channel {notification.channel_id}"
                    )
                    failed_notifications.append(notification)
                    continue

                try:
                    message = (
                        await channel.fetch_message(notification.message_id)
                        if notification.message_id
                        else None
                    )

                    # Check for custom message
                    custom_message = await self.get_custom_message(channel.guild.id, notification.channel_id)
                    
                    if custom_message:
                        message_text, is_embed = custom_message
                        formatted_text = await self.format_message(message_text, stream)
                        
                        if message:
                            if is_embed:
                                await self.bot.send_embed(channel, formatted_text, message=message)
                            else:
                                await message.edit(content=formatted_text)
                        else:
                            # Create new message if original was deleted
                            if is_embed:
                                new_message = await self.bot.send_embed(channel, formatted_text)
                            else:
                                new_message = await channel.send(formatted_text)
                            notification.message_id = new_message.id
                    else:
                        # Use default notification format
                        embed = self.create_live_embed(stream)
                        if message:
                            await message.edit(
                                content=f"🔴 **{stream.username}** is live on Twitch! (Updated)",
                                embed=embed,
                            )
                        else:
                            # Create new message if original was deleted
                            new_message = await channel.send(
                                content=f"🔴 **{stream.username}** is still live on Twitch! (Updated)",
                                embed=embed,
                            )
                            notification.message_id = new_message.id

                    notification.last_notified = datetime.now(timezone.utc)

                except discord.NotFound:
                    # Message was deleted, create a new one
                    if custom_message:
                        message_text, is_embed = custom_message
                        formatted_text = await self.format_message(message_text, stream)
                        
                        if is_embed:
                            new_message = await self.bot.send_embed(channel, formatted_text)
                        else:
                            new_message = await channel.send(formatted_text)
                    else:
                        embed = self.create_live_embed(stream)
                        new_message = await channel.send(
                            content=f"🔴 **{stream.username}** is still live on Twitch! (Updated)",
                            embed=embed,
                        )
                    notification.message_id = new_message.id
                    notification.last_notified = datetime.now(timezone.utc)
                except discord.Forbidden:
                    logger.error(
                        f"Bot lacks permissions in channel {notification.channel_id}"
                    )
                    failed_notifications.append(notification)
                except discord.HTTPException as e:
                    logger.error(f"HTTP error updating notification: {str(e)}")
                    failed_notifications.append(notification)

            except Exception as e:
                logger.error(
                    f"Failed to update stream notification in channel {notification.channel_id}: {str(e)}"
                )
                logger.error(traceback.format_exc())
                failed_notifications.append(notification)

        # Remove failed notifications
        for failed in failed_notifications:
            stream.notifications.remove(failed)
            logger.info(f"Removed failed notification for channel {failed.channel_id}")

    async def send_offline_notifications(self, stream_id: str) -> None:
        """
        Send notifications that a stream has ended.

        Args:
            stream_id: The ID of the stream that ended

        Implementation:
        - Updates existing notification messages with offline status
        - Calculates and displays stream duration
        - Handles missing messages and channels gracefully
        - Cleans up notification data after sending
        """
        if stream_id not in self.active_streams:
            logger.warning(
                f"Attempted to send offline notifications for unknown stream: {stream_id}"
            )
            return

        stream = self.active_streams[stream_id]
        failed_notifications = []

        for notification in stream.notifications:
            try:
                channel = self.bot.get_channel(notification.channel_id)
                if not channel or not notification.message_id:
                    logger.warning(
                        f"Could not find Discord channel {notification.channel_id} or message {notification.message_id}"
                    )
                    failed_notifications.append(notification)
                    continue

                try:
                    message = await channel.fetch_message(notification.message_id)
                    if not message:
                        continue

                    # Calculate stream duration
                    duration = datetime.now(timezone.utc) - stream.started_at
                    hours, remainder = divmod(duration.total_seconds(), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    duration_str = (
                        f"{int(hours)}h {int(minutes)}m"
                        if hours > 0
                        else f"{int(minutes)}m {int(seconds)}s"
                    )

                    embed = self.create_offline_embed(stream, duration_str)

                    await message.edit(
                        content=f"⚫ **{stream.username}**'s Twitch stream has ended.",
                        embed=embed,
                    )
                except discord.NotFound:
                    # Message was deleted, don't create a new one for offline status
                    logger.info(
                        f"Message {notification.message_id} was deleted, skipping offline notification"
                    )
                    failed_notifications.append(notification)
                except discord.Forbidden:
                    logger.error(
                        f"Bot lacks permissions in channel {notification.channel_id}"
                    )
                    failed_notifications.append(notification)
                except discord.HTTPException as e:
                    logger.error(f"HTTP error sending offline notification: {str(e)}")
                    failed_notifications.append(notification)

            except Exception as e:
                logger.error(
                    f"Failed to send offline notification in channel {notification.channel_id}: {str(e)}"
                )
                logger.error(traceback.format_exc())
                failed_notifications.append(notification)

        # Clean up failed notifications
        for failed in failed_notifications:
            stream.notifications.remove(failed)
            logger.info(f"Removed failed notification for channel {failed.channel_id}")

    def create_live_embed(self, stream: StreamData) -> Embed:
        """
        Create an embed for a live stream notification.

        Args:
            stream: The StreamData object containing stream information

        Returns:
            Embed: A Discord embed with formatted stream information
        """
        embed = Embed(
            title=f"{stream.username} is now live on Twitch!",
            description=stream.title,
            url=f"https://twitch.tv/{stream.username}",
            color=0x6441A4,
            timestamp=stream.started_at,
        )

        embed.add_field(name="Game", value=stream.game or "No Game", inline=True)
        embed.add_field(name="Viewers", value=f"{stream.viewer_count:,}", inline=True)

        # Calculate stream uptime using timezone-aware datetimes
        now = datetime.now(timezone.utc)
        uptime = now - stream.started_at
        hours, remainder = divmod(uptime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = (
            f"{int(hours)}h {int(minutes)}m"
            if hours > 0
            else f"{int(minutes)}m {int(seconds)}s"
        )
        embed.add_field(name="Uptime", value=uptime_str, inline=True)

        # Set thumbnail to channel profile picture
        embed.set_thumbnail(
            url=f"https://static-cdn.jtvnw.net/jtv_user_pictures/{stream.username.lower()}-profile_image-300x300.png"
        )

        # Set preview image if available
        if stream.thumbnail_url:
            embed.set_image(url=stream.thumbnail_url)

        embed.set_footer(text="Started streaming")

        return embed

    def create_offline_embed(self, stream: StreamData, duration_str: str) -> Embed:
        """
        Create an embed for an offline stream notification.

        Args:
            stream: The StreamData object containing stream information
            duration_str: Formatted string of the stream's duration

        Returns:
            Embed: A Discord embed with formatted offline stream information
        """
        now = datetime.now(timezone.utc)
        embed = Embed(
            title=f"{stream.username}'s stream has ended",
            description=f"**Stream Title:** {stream.title}\n**Duration:** {duration_str}",
            url=f"https://twitch.tv/{stream.username}",
            color=0x6441A4,
            timestamp=now,
        )
        
        embed.add_field(name="Game", value=stream.game or "No Game", inline=True)
        embed.set_thumbnail(
            url=f"https://static-cdn.jtvnw.net/jtv_user_pictures/{stream.username.lower()}-profile_image-300x300.png"
        )
        embed.set_footer(text="Stream ended")

        return embed

    async def subscribe(self, username: str, channel_id: int) -> bool:
        """
        Subscribe a Discord channel to a Twitch stream.

        Args:
            username: The Twitch username to subscribe to
            channel_id: The Discord channel ID to send notifications to

        Returns:
            bool: True if subscription was successful, False otherwise

        Raises:
            Exception: If there's an error verifying the Twitch channel
        """
        username = username.lower()

        try:
            # Verify the Twitch channel exists
            channel_response = await self.twitch_service.get_channel(username)

            if isinstance(channel_response, int):
                logger.error(
                    f"Unexpected integer response from get_channel for {username}: {channel_response}"
                )
                return False

            if not hasattr(channel_response, "channel") or not channel_response.channel:
                logger.error(
                    f"Invalid channel response for {username}: {channel_response}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to verify Twitch channel {username}: {str(e)}")
            logger.error(traceback.format_exc())
            raise Exception(f"Failed to verify Twitch channel {username}") from e

        # Check if already subscribed
        if (
            username in self.subscriptions
            and channel_id in self.subscriptions[username]
        ):
            return False

        # Add subscription
        if username not in self.subscriptions:
            self.subscriptions[username] = set()
        self.subscriptions[username].add(channel_id)

        # Save to database
        try:
            await self.db.execute(
                "INSERT INTO twitch.subscriptions (username, channel_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                username, channel_id
            )
        except Exception as e:
            logger.error(f"Failed to save subscription to database: {str(e)}")
            # Remove from memory if database save fails
            self.subscriptions[username].discard(channel_id)
            raise

        # Start monitoring if not already
        self.start_monitoring(username)

        return True

    async def unsubscribe(self, username: str, channel_id: int) -> bool:
        """
        Unsubscribe a Discord channel from a Twitch stream.

        Args:
            username: The Twitch username to unsubscribe from
            channel_id: The Discord channel ID to stop notifications for

        Returns:
            bool: True if unsubscription was successful, False otherwise
        """
        username = username.lower()

        if (
            username not in self.subscriptions
            or channel_id not in self.subscriptions[username]
        ):
            return False

        # Remove subscription
        self.subscriptions[username].discard(channel_id)

        # Update database
        await self.db.execute(
            "DELETE FROM twitch.subscriptions WHERE username = $1 AND channel_id = $2",
            username, channel_id
        )

        # Stop monitoring if no more subscribers
        if not self.subscriptions[username]:
            self.subscriptions.pop(username)
            self.stop_monitoring(username)

        return True

    async def get_subscriptions(self, channel_id: int) -> List[str]:
        """
        Get all Twitch subscriptions for a Discord channel.

        Args:
            channel_id: The Discord channel ID to get subscriptions for

        Returns:
            List[str]: List of Twitch usernames the channel is subscribed to
        """
        try:
            rows = await self.db.fetch(
                "SELECT DISTINCT username FROM twitch.subscriptions WHERE channel_id = $1",
                channel_id
            )
            return [row["username"] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get subscriptions for channel {channel_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return []


class Feeds(commands.Cog):
    """Cog for handling feed services like Twitch streams."""

    def __init__(self, bot):
        self.bot = bot
        self.feed_manager = None
        self.ready = asyncio.Event()
        self.setup_task = asyncio.create_task(self.setup_feed_manager())

    async def setup_feed_manager(self):
        """Set up the feed manager."""
        try:
            self.feed_manager = FeedManager(self.bot)
            await self.feed_manager.initialize()
            self.ready.set()
            logger.info("Feed manager setup complete")
        except Exception as e:
            logger.error(f"Failed to set up feed manager: {e}")
            logger.error(traceback.format_exc())

    async def cog_load(self):
        """Called when the cog is loaded."""
        logger.info("Feeds cog loaded")

    def cog_unload(self):
        """Called when the cog is unloaded."""
        if self.feed_manager:
            for username, task in list(self.feed_manager.stream_tasks.items()):
                if not task.done():
                    task.cancel()

        if hasattr(self, "setup_task") and not self.setup_task.done():
            self.setup_task.cancel()

        logger.info("Feeds cog unloaded")

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info("Feeds cog ready")

    @commands.group(name="twitch", invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def twitch(self, ctx):
        """Manage Twitch stream subscriptions."""
        await ctx.send_help(ctx.command)

    @twitch.command(name="subscribe", aliases=["add", "sub"])
    @commands.has_permissions(manage_channels=True)
    async def twitch_subscribe(
        self, ctx, username: str, channel: Optional[discord.TextChannel] = None
    ):
        """Subscribe to a Twitch channel's stream notifications."""
        channel_obj = channel or ctx.channel
        await self.ready.wait()

        async with ctx.typing():
            try:
                success = await self.feed_manager.subscribe(username, channel_obj.id)
                if success:
                    await ctx.success(
                        f"Successfully subscribed to **{username}**'s Twitch streams!"
                    )
                else:
                    await ctx.fail(
                        f"Failed to subscribe to **{username}**. This username may already be subscribed in this channel or doesn't exist."
                    )
            except Exception as e:
                logger.error(f"Error subscribing to {username}: {e}")
                await ctx.fail(f"An error occurred while subscribing to **{username}**")

    @twitch.command(name="unsubscribe", aliases=["remove", "unsub"])
    @commands.has_permissions(manage_channels=True)
    async def twitch_unsubscribe(
        self, ctx, username: str, channel: Optional[discord.TextChannel] = None
    ):
        """Unsubscribe from a Twitch channel's stream notifications."""
        channel_obj = channel or ctx.channel
        await self.ready.wait()

        async with ctx.typing():
            try:
                success = await self.feed_manager.unsubscribe(username, channel_obj.id)
                if success:
                    await ctx.success(
                        f"Successfully unsubscribed from **{username}**'s Twitch streams."
                    )
                else:
                    await ctx.fail(
                        f"You are not subscribed to **{username}**'s Twitch streams in this channel."
                    )
            except Exception as e:
                logger.error(f"Error unsubscribing from {username}: {e}")
                await ctx.fail(f"An error occurred while unsubscribing from **{username}**")

    @twitch.command(name="list", aliases=["subscriptions", "subs"])
    async def twitch_list(self, ctx):
        """List all Twitch subscriptions for this channel."""
        await self.ready.wait()

        async with ctx.typing():
            try:
                subscriptions = await self.feed_manager.get_subscriptions(ctx.channel.id)

                if not subscriptions:
                    await ctx.info("This channel is not subscribed to any Twitch streams.")
                    return

                embed = Embed(
                    title="Twitch Subscriptions",
                    description=f"This channel is subscribed to {len(subscriptions)} Twitch streams:",
                    color=0x6441A4,
                )

                for i, username in enumerate(sorted(subscriptions), 1):
                    embed.add_field(
                        name=f"{i}. {username}",
                        value=f"[View Channel](https://twitch.tv/{username})",
                        inline=True,
                    )

                await ctx.send(embed=embed)
            except Exception as e:
                logger.error(f"Error listing subscriptions: {e}")
                await ctx.fail("An error occurred while fetching subscriptions")

    @app_commands.command(
        name="twitch", description="Manage Twitch stream subscriptions"
    )
    @app_commands.describe(
        action="The action to perform", username="The Twitch username"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Subscribe", value="subscribe"),
            app_commands.Choice(name="Unsubscribe", value="unsubscribe"),
            app_commands.Choice(name="List Subscriptions", value="list"),
        ]
    )
    @app_commands.default_permissions(manage_channels=True)
    async def twitch_slash(
        self,
        interaction: discord.Interaction,
        action: str,
        username: Optional[str] = None,
    ):
        """Slash command for managing Twitch subscriptions."""
        await self.ready.wait()

        if action == "list":
            try:
                subscriptions = await self.feed_manager.get_subscriptions(
                    interaction.channel_id
                )

                if not subscriptions:
                    await interaction.response.send_message(
                        "This channel is not subscribed to any Twitch streams.",
                        ephemeral=True,
                    )
                    return

                embed = Embed(
                    title="Twitch Subscriptions",
                    description=f"This channel is subscribed to {len(subscriptions)} Twitch streams:",
                    color=0x6441A4,
                )

                for i, username in enumerate(sorted(subscriptions), 1):
                    embed.add_field(
                        name=f"{i}. {username}",
                        value=f"[View Channel](https://twitch.tv/{username})",
                        inline=True,
                    )

                await interaction.response.send_message(embed=embed)
            except Exception as e:
                logger.error(f"Error listing subscriptions: {e}")
                await interaction.response.send_message(
                    "An error occurred while fetching subscriptions",
                    ephemeral=True
                )
            return

        if not username:
            await interaction.response.send_message(
                "Please provide a Twitch username.", ephemeral=True
            )
            return

        try:
            if action == "subscribe":
                success = await self.feed_manager.subscribe(
                    username, interaction.channel_id
                )

                if success:
                    await interaction.response.send_message(
                        f"Successfully subscribed to **{username}**'s Twitch streams!"
                    )
                else:
                    await interaction.response.send_message(
                        f"Failed to subscribe to **{username}**. This username may already be subscribed in this channel or doesn't exist.",
                        ephemeral=True,
                    )

            elif action == "unsubscribe":
                success = await self.feed_manager.unsubscribe(
                    username, interaction.channel_id
                )

                if success:
                    await interaction.response.send_message(
                        f"Successfully unsubscribed from **{username}**'s Twitch streams."
                    )
                else:
                    await interaction.response.send_message(
                        f"You are not subscribed to **{username}**'s Twitch streams in this channel.",
                        ephemeral=True,
                    )
        except Exception as e:
            logger.error(f"Error processing Twitch command: {e}")
            await interaction.response.send_message(
                "An error occurred while processing your request",
                ephemeral=True
            )

    @twitch.group(name="message", invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def twitch_message(self, ctx):
        """Manage custom Twitch live notification messages."""
        await ctx.send_help(ctx.command)

    @twitch_message.command(name="set")
    @commands.has_permissions(manage_channels=True)
    async def set_message(self, ctx, channel: Optional[discord.TextChannel] = None, *, code: str):
        """
        Set a custom message for Twitch live notifications.
        
        You can use the following variables in your message:
        {streamer} - The streamer's name
        {title} - Stream title
        {game} - Game being played
        {viewers} - Current viewer count
        {url} - Stream URL
        
        For embeds, use the embed parser format:
        {embed}
        {title: {streamer} is live!}
        {description: Playing {game}}
        {color: #6441A4}
        etc.
        """
        channel_obj = channel or ctx.channel
        is_embed = code.strip().startswith("{embed")

        try:
            if is_embed:
                # Validate embed code
                script = Script(code, ctx.author)
                await script.compile()

            # Save to database
            await self.bot.db.execute("""
                INSERT INTO twitch.custom_messages (guild_id, channel_id, message, is_embed)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, channel_id) 
                DO UPDATE SET message = EXCLUDED.message, is_embed = EXCLUDED.is_embed
            """, ctx.guild.id, channel_obj.id, code, is_embed)

            # Show preview
            if is_embed:
                preview = await self.bot.send_embed(ctx.channel, code.format(
                    streamer="ExampleStreamer",
                    title="Example Stream Title",
                    game="Example Game",
                    viewers="1,337",
                    url="https://twitch.tv/ExampleStreamer"
                ))
                await ctx.success(f"Custom embed message set for {channel_obj.mention}! Here's how it will look:")
            else:
                formatted = code.format(
                    streamer="ExampleStreamer",
                    title="Example Stream Title",
                    game="Example Game",
                    viewers="1,337",
                    url="https://twitch.tv/ExampleStreamer"
                )
                await ctx.send(formatted)
                await ctx.success(f"Custom text message set for {channel_obj.mention}! Preview shown above.")

        except Exception as e:
            await ctx.fail(f"Failed to set custom message: {str(e)}")

    @twitch_message.command(name="remove", aliases=["delete", "reset"])
    @commands.has_permissions(manage_channels=True)
    async def remove_message(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Remove the custom message for a channel and revert to default notifications."""
        channel_obj = channel or ctx.channel

        await self.bot.db.execute("""
            DELETE FROM twitch.custom_messages 
            WHERE guild_id = $1 AND channel_id = $2
        """, ctx.guild.id, channel_obj.id)

        await ctx.success(f"Removed custom message for {channel_obj.mention}. The channel will now use default notifications.")

    @twitch_message.command(name="show", aliases=["view", "preview"])
    @commands.has_permissions(manage_channels=True)
    async def show_message(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Show the current custom message for a channel."""
        channel_obj = channel or ctx.channel

        result = await self.bot.db.fetchrow("""
            SELECT message, is_embed 
            FROM twitch.custom_messages 
            WHERE guild_id = $1 AND channel_id = $2
        """, ctx.guild.id, channel_obj.id)

        if not result:
            await ctx.info(f"No custom message set for {channel_obj.mention}. Using default notifications.")
            return

        message, is_embed = result["message"], result["is_embed"]

        if is_embed:
            await ctx.send(f"Current embed code for {channel_obj.mention}:")
            await ctx.send(f"```\n{message}\n```")
            await ctx.send("Preview:")
            await self.bot.send_embed(ctx.channel, message.format(
                streamer="ExampleStreamer",
                title="Example Stream Title",
                game="Example Game",
                viewers="1,337",
                url="https://twitch.tv/ExampleStreamer"
            ))
        else:
            await ctx.send(f"Current message for {channel_obj.mention}:")
            await ctx.send(f"```\n{message}\n```")
            await ctx.send("Preview:")
            formatted = message.format(
                streamer="ExampleStreamer",
                title="Example Stream Title",
                game="Example Game",
                viewers="1,337",
                url="https://twitch.tv/ExampleStreamer"
            )
            await ctx.send(formatted)


async def setup(bot):
    """Set up the Feeds cog."""
    await bot.add_cog(Feeds(bot))
