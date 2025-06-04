import asyncio
import logging
from pathlib import Path
from typing import Optional
import ftplib
import subprocess

log = logging.getLogger(__name__)

def run_pg_dump(command: str) -> Optional[bytes]:
    """
    Execute pg_dump command in a separate process.
    """
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            log.error(f"Backup failed: {stderr.decode()}")
            return None
            
        return stdout
    except Exception as e:
        log.error(f"Backup error: {e}")
        return None 

def process_bunny_upload(local_path: Path, remote_path: str, bunny_host: str, bunny_user: str, bunny_pass: str) -> bool:
    """
    Process Bunny Storage upload in a separate process.
    """
    try:
        with ftplib.FTP(bunny_host) as ftp:
            ftp.login(bunny_user, bunny_pass)
            
            current_path = ""
            for part in remote_path.split("/")[:-1]:
                current_path += f"/{part}"
                try:
                    ftp.mkd(current_path)
                except:
                    pass

            with open(local_path, "rb") as file:
                ftp.storbinary(f"STOR {remote_path}", file)
            
            log.info(f"Uploaded {local_path} to Bunny Storage")
            return True
    
    except Exception as e:
        log.error(f"Bunny Storage upload failed: {e}")
        return False 