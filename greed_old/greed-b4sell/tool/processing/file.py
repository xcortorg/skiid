from pyogg import VorbisFile
from aiohttp import ClientSession
from mutagen import File as MFile
from typing import Any
from discord import Client, Message, TextChannel
from tool.worker import offloaded
import subprocess
from typing_extensions import Self
import asyncio
import os


async def wait_for_file(filepath: str, timeout: float) -> bool:
    async def file_exists():
        while not os.path.isfile(filepath):
            await asyncio.sleep(0.001)
        return True

    try:
        await asyncio.wait_for(file_exists(), timeout)
        return True
    except asyncio.TimeoutError:
        return False


def delete_file(filepath: str):
    try:
        os.remove(filepath)
    except OSError:
        pass
    return True


@offloaded
def save_file(filepath: str, data: bytes) -> str:
    with open(filepath, "wb") as file:
        file.write(data)
    return filepath


@offloaded
def read_file(filepath: str, mode: str = "rb", **kwargs: Any) -> Any:
    with open(filepath, mode, **kwargs) as file:
        data = file.read()
    return data


@offloaded
def mp3_to_ogg(filepath: str) -> str:
    output_path = filepath.replace(".mp3", ".ogg")
    command = f"ffmpeg -i {filepath} -c:a libvorbis -q:a 5 -y {output_path}"
    subprocess.run(command, shell=True, check=True)
    return output_path


class FileProcessing:
    def __init__(self: Self, bot: Client):
        self.bot = bot
        self.token = self.bot.config["token"]

    async def attachment(self, channel: TextChannel, filePath: str) -> dict:
        url = f"https://discord.com/api/v9/channels/{channel.id}/attachments"
        headers = {"Authorization": f"Bot {self.token}"}
        payload = {
            "files": [
                {
                    "filename": "voice-message.ogg",
                    "file_size": VorbisFile(filePath).buffer_length,
                    "id": "2",
                }
            ]
        }

        async with ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["attachments"][0]
                else:
                    response_text = await response.text()
                    raise Exception(f"Attachment Error: {response_text}")

    async def upload_to_cloud(self, upload_url: str, filePath: str) -> bool:
        headers = {"Content-Type": "audio/ogg"}
        async with ClientSession() as session:
            data = await read_file(filePath)
            async with session.put(upload_url, data=data, headers=headers) as response:
                if response.status == 200:
                    return True
                else:
                    response_text = await response.text()
                    raise Exception(f"Cloud Upload Error: {response_text}")

    async def upload_to_discord(self, channel: TextChannel, filePath: str) -> tuple:
        if not filePath.endswith(".ogg"):
            output_path = filePath.replace(".mp3", ".ogg")
            delete_file(output_path)
            filePath = await mp3_to_ogg(filePath)
            await wait_for_file(filePath, 3)
        try:
            attachment_info = await self.attachment(channel, filePath)
            success = await self.upload_to_cloud(
                attachment_info["upload_url"], filePath
            )

            if success:
                url = f"https://discord.com/api/v9/channels/{channel.id}/messages"
                headers = {
                    "Authorization": f"Bot {self.token}",
                    "content-type": "application/json",
                }
                payload = {
                    "content": "",
                    "channel_id": str(channel.id),
                    "type": 0,
                    "flags": 8192,
                    "attachments": [
                        {
                            "id": "0",
                            "filename": attachment_info["upload_filename"].split("/")[
                                1
                            ],
                            "uploaded_filename": attachment_info["upload_filename"],
                            "duration_secs": MFile(filePath).info.length,
                            "waveform": "FzYACgAAAAAAACQAAAAAAAA=",
                        }
                    ],
                }

                async with ClientSession() as session:
                    async with session.post(
                        url, headers=headers, json=payload
                    ) as response:
                        if response.status == 200:
                            return True, Message(
                                state=self.bot._connection,
                                channel=channel,
                                data=await response.json(),
                            )
                        else:
                            response_json = await response.json()
                            return False, response_json
        except Exception as e:
            raise Exception(f"Discord Upload Exception: {e}")
