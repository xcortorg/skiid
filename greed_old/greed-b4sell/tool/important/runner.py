from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional, TypeVar, cast
from functools import wraps

from discord.ext import commands
from watchfiles import Change, awatch

T = TypeVar("T")

class RebootRunner:
    """Manages cog reloading and file change watching for a Discord bot."""

    def __init__(
        self,
        client: commands.Bot,
        path: str = "commands",
        debug: bool = True,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        default_logger: bool = True,
        preload: bool = False,
        auto_commit: bool = False,
        colors: bool = True,
    ) -> None:
        self.client = client
        self.path = Path(path).resolve()
        self.debug = debug
        self.loop = loop or asyncio.get_event_loop()
        self.default_logger = default_logger
        self.preload = preload
        self.auto_commit = auto_commit
        self.started = False
        self.colors = colors
        self._setup_logger()
        self._pending_changes: dict[str, Change] = {}
        self._debounce_timer: Optional[asyncio.Task[None]] = None
        self._debounce_delay: float = 1.0

    def _setup_logger(self) -> None:
        """Configures the logger."""
        self.logger = logging.getLogger("RebootRunner")
        if self.default_logger:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

    @staticmethod
    def get_cog_name(file_path: Path) -> str:
        """Extracts the cog name from a file path."""
        return file_path.stem

    def get_dotted_path(self, file_path: Path) -> str:
        """Generates the dotted module path for a cog.

        If file is in a subdirectory, returns the path to the parent directory module
        Otherwise returns the path to the file directly.
        """
        try:
            relative_path = file_path.relative_to(self.path.parent)
            parts = relative_path.parts
            return f"{parts[0]}.{parts[1]}" if len(parts) > 2 else ".".join(relative_path.with_suffix("").parts)
        except ValueError:
            raise ValueError(f"Invalid path: {file_path} not within {self.path.parent}")

    async def start(self) -> bool:
        """Initializes the cog watcher."""
        if self.started:
            self.logger.warning("Watcher already started")
            return False
        if not self.path.exists() or not self.path.is_dir():
            self.logger.error(f"Directory {self.path} does not exist or is not valid")
            return False

        if self.preload:
            await self._preload_cogs()

        if self.debug or not __debug__:
            self.logger.info(f"Watching directory: {self.path}")
            self.loop.create_task(self._watch_cogs())

        self.started = True
        return True

    async def _watch_cogs(self) -> None:
        """Monitors the directory for file changes and handles reloads."""
        async for changes in awatch(self.path):
            for change_type, file_path in changes:
                file_path = Path(file_path)
                if ".git" in str(file_path) or file_path.suffix != ".py" or "custom" in file_path.parts:
                    continue

                self._pending_changes[str(file_path)] = change_type

                if self._debounce_timer and not self._debounce_timer.done():
                    self._debounce_timer.cancel()

                self._debounce_timer = self.loop.create_task(self._process_pending_changes())

    async def _process_pending_changes(self) -> None:
        """Process batched changes after debounce delay."""
        try:
            await asyncio.sleep(self._debounce_delay)

            if await self._is_git_operation():
                self.logger.debug("Ignoring changes from git operation")
                self._pending_changes.clear()
                return

            processed_paths = set()
            for file_path_str, change_type in self._pending_changes.items():
                file_path = Path(file_path_str)
                if str(file_path) in processed_paths:
                    continue

                try:
                    cog_path = self.get_dotted_path(file_path)
                    self.logger.debug(f"Processing cog path '{cog_path}' from file '{file_path}'")

                    if change_type == Change.deleted:
                        await self._unload_cog(cog_path)
                    elif change_type == Change.added:
                        await self._load_cog(cog_path)
                    elif change_type == Change.modified:
                        await self._reload_cog(cog_path)

                    processed_paths.add(str(file_path))
                except Exception as e:
                    self.logger.error(f"Error processing change {change_type} for {file_path}: {e}")

            self._pending_changes.clear()

        except Exception as e:
            self.logger.error(f"Error in processing pending changes: {e}")
            self._pending_changes.clear()

    async def _is_git_operation(self) -> bool:
        """Check if there's an ongoing git operation."""
        try:
            git_dir = self.path / ".git"
            if git_dir.exists():
                lock_files = [git_dir / name for name in ("index.lock", "HEAD.lock", "refs.lock")]
                exists_results = await asyncio.gather(*[self.loop.run_in_executor(None, lock.exists) for lock in lock_files])
                return any(exists_results)
        except Exception:
            pass
        return False

    async def _preload_cogs(self) -> None:
        """Loads all cogs on startup."""
        self.logger.info("Preloading cogs...")
        try:
            files = await self.loop.run_in_executor(None, lambda: list(self.path.rglob("*.py")))
            self.logger.debug(f"Found {len(files)} potential cog files")
            
            valid_files = [file for file in files if not file.name.startswith("_") and "custom" not in file.parts]
            for batch in [valid_files[i:i + 10] for i in range(0, len(valid_files), 10)]:
                await asyncio.gather(*[self._load_cog(self.get_dotted_path(file)) for file in batch])
                
        except Exception as e:
            self.logger.error(f"Error during cog preloading: {e}")

    async def _load_cog(self, cog_path: str) -> None:
        """Loads a cog."""
        if "custom" in cog_path:
            return
            
        try:
            await self.client.load_extension(cog_path)
            self.logger.info(f"Loaded cog: {cog_path}")
        except commands.ExtensionAlreadyLoaded:
            self.logger.info(f"Cog already loaded: {cog_path}")
        except commands.ExtensionFailed as e:
            self.logger.error(f"Failed to load cog {cog_path}: {e}")

    async def _unload_cog(self, cog_path: str) -> None:
        """Unloads a cog."""
        try:
            await self.client.unload_extension(cog_path)
            self.logger.info(f"Unloaded cog: {cog_path}")
        except commands.ExtensionNotLoaded:
            self.logger.warning(f"Cog not loaded: {cog_path}")

    async def _reload_cog(self, cog_path: str) -> None:
        """Reloads a cog."""
        if "custom" in cog_path:
            return
            
        if self.auto_commit:
            await self._auto_commit_changes()
            
        try:
            await self.client.reload_extension(cog_path)
            self.logger.info(f"Reloaded cog: {cog_path}")
        except commands.ExtensionNotLoaded:
            self.logger.info(f"Cog not loaded, loading instead: {cog_path}")
            await self._load_cog(cog_path)
        except commands.ExtensionFailed as e:
            self.logger.error(f"Failed to reload cog {cog_path}: {e}")

    async def _auto_commit_changes(self) -> None:
        """Automatically commits changes using git."""
        try:
            self.logger.info("Performing git commit")
            commands = [
                ("git", "add", "."),
                ("git", "commit", "-m", "Auto commit"),
                ("git", "push", "--force"),
            ]

            for cmd in commands:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0 and stderr:
                    self.logger.warning(f"Git command {cmd[0]} failed: {stderr.decode()}")
                    return

            self.logger.info("Successfully committed and pushed changes")
        except Exception as e:
            self.logger.error(f"Git commit failed: {e}")


def watch(**kwargs: Any) -> Callable[[Callable[[commands.Bot], Coroutine[Any, Any, T]]], Callable[[commands.Bot], Coroutine[Any, Any, T]]]:
    """Decorator for initializing and starting a RebootRunner."""

    def decorator(func: Callable[[commands.Bot], Coroutine[Any, Any, T]]) -> Callable[[commands.Bot], Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(client: commands.Bot) -> T:
            runner = RebootRunner(client, **kwargs)
            await runner.start()
            return await func(client)

        return wrapper

    return decorator
