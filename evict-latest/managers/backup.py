import gzip
import config
import asyncio
import logging
import ftplib
import subprocess

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, bot):
        self.bot = bot
        self.backup_dir = Path("backups")
        self.schemas_dir = self.backup_dir / "schemas"
        self.full_dir = self.backup_dir / "full"
        self.retention_days = 7
        
        self.backup_dir.mkdir(exist_ok=True)
        self.schemas_dir.mkdir(exist_ok=True)
        self.full_dir.mkdir(exist_ok=True)

    def _upload_to_bunny(self, local_path: Path, remote_path: str) -> bool:
        """
        Upload file to Bunny Storage via FTP.
        """
        try:
            with ftplib.FTP(config.AUTHORIZATION.BACKUPS.HOST, timeout=30) as ftp:
                ftp.login(config.AUTHORIZATION.BACKUPS.USER, config.AUTHORIZATION.BACKUPS.PASSWORD)
                
                current_path = ""
                for part in remote_path.split("/")[:-1]:
                    current_path += f"/{part}"
                    try:
                        ftp.mkd(current_path)
                    except:
                        pass

                with open(local_path, "rb") as file:
                    ftp.storbinary(f"STOR {remote_path}", file, blocksize=8192)
                
                log.info(f"Uploaded {local_path} to Bunny Storage")
                return True
        except Exception as e:
            log.error(f"Bunny Storage upload failed: {e}")
            return False

    async def _run_pg_dump(self, command: str) -> Optional[bytes]:
        """
        Execute pg_dump command and return output.
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                log.error(f"Backup failed: {stderr.decode()}")
                return None
            
            try:
                process.kill()
            except ProcessLookupError:
                pass
                
            return stdout
        except Exception as e:
            log.error(f"Backup error: {e}")
            if 'process' in locals():
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            return None

    async def create_schema_backup(self, timestamp: datetime) -> bool:
        """
        Create schema-only backup of all databases.
        """
        date_folder = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%H%M%S")
        filename = f"schemas_{time_str}.sql.gz"
        
        local_dir = self.schemas_dir / date_folder
        local_dir.mkdir(exist_ok=True)
        local_path = local_dir / filename

        command = (
            "PGPASSWORD=admin pg_dumpall -h localhost -U postgres "
            "--schema-only --clean --if-exists"
        )

        if data := await self._run_pg_dump(command):
            try:
                with gzip.open(local_path, 'wb') as f:
                    f.write(data)
                del data  
                
                remote_path = f"/schemas/{date_folder}/{filename}"
                success = self._upload_to_bunny(local_path, remote_path)
                
                if success:
                    log.info(f"Created schema backup: {filename}")
                    return True
            except Exception as e:
                log.error(f"Failed to write backup: {e}")
                if local_path.exists():
                    local_path.unlink()
        return False

    async def create_full_backup(self, timestamp: datetime) -> bool:
        """
        Create full backup of all databases.
        """
        date_folder = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%H%M%S")
        filename = f"full_{time_str}.sql.gz"
        
        local_dir = self.full_dir / date_folder
        local_dir.mkdir(exist_ok=True)
        local_path = local_dir / filename

        command = (
            "PGPASSWORD=admin pg_dumpall -h localhost -U postgres "
            "--clean --if-exists"
        )

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            with gzip.open(local_path, 'wb') as gz_file:
                while True:
                    chunk = await process.stdout.read(8192)  
                    if not chunk:
                        break
                    gz_file.write(chunk)
            
            stderr = await process.stderr.read()
            if process.returncode != 0:
                log.error(f"Backup failed: {stderr.decode()}")
                local_path.unlink()
                return False
                
            try:
                process.kill()
            except ProcessLookupError:
                pass
            
            success = await asyncio.get_event_loop().run_in_executor(
                None, 
                self._upload_to_bunny, 
                local_path, 
                f"/full/{date_folder}/{filename}"
            )
            
            if success:
                log.info(f"Created full backup: {filename}")
                return True
                
        except Exception as e:
            log.error(f"Backup error: {e}")
            if 'local_path' in locals() and local_path.exists():
                local_path.unlink()
            
        return False

    def cleanup_old_backups(self):
        """
        Remove backups older than retention period.
        """
        try:
            current_time = datetime.now(timezone.utc).timestamp()
            retention_seconds = self.retention_days * 24 * 60 * 60

            for directory in [self.schemas_dir, self.full_dir]:
                if not directory.exists():
                    continue
                    
                for date_dir in directory.iterdir():
                    if not date_dir.is_dir():
                        continue
                        
                    try:
                        for backup_file in date_dir.glob("*.sql.gz"):
                            try:
                                file_time = backup_file.stat().st_mtime
                                if current_time - file_time > retention_seconds:
                                    backup_file.unlink()
                                    log.info(f"Removed old backup: {backup_file.name}")
                            except (OSError, IOError) as e:
                                log.error(f"Error processing backup file {backup_file}: {e}")
                        
                        if not any(date_dir.iterdir()):
                            date_dir.rmdir()
                    except (OSError, IOError) as e:
                        log.error(f"Error processing date directory {date_dir}: {e}")
                        
        except Exception as e:
            log.error(f"Cleanup error: {e}")

    async def run_backup(self):
        """
        Run both schema and full backups.
        """
        timestamp = datetime.now(timezone.utc)
        schema_success = await self.create_schema_backup(timestamp)
        full_success = await self.create_full_backup(timestamp)
        
        if schema_success and full_success:
            self.cleanup_old_backups()
            return True
        return False 