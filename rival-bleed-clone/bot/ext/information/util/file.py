from pyogg import VorbisFile
from aiohttp import ClientSession
from mutagen import File as MFile
from typing import Optional, Any, Dict, List, Union
from discord import File, Client, Message, TextChannel
from lib.worker import offloaded
from typing_extensions import Self, NoReturn
from pydub import AudioSegment
import subprocess
import asyncio
import os


async def wait_for_file(filepath: str, timeout: float) -> bool:
    async def file_exists():
        while not os.path.isfile(filepath):
            await asyncio.sleep(0.001)  # Check every second
        return True

    try:
        await asyncio.wait_for(file_exists(), timeout)
        return True
    except asyncio.TimeoutError:
        return False


def delete_file(filepath: str):
    try:
        os.remove(filepath)
    except Exception:
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
    # audio = AudioSegment.from_mp3(filepath)
    output_path = filepath.replace(".mp3", ".ogg")
    command = f"ffmpeg -i {filepath} -c:a libvorbis -q:a 5 -y {output_path}"  # f"ffmpeg -i {filepath} -c:a libopus -b:a 16k -ar 48000 -ac 1 -application voip -y {output_path}"
    subprocess.run(command, shell=True, check=True)
    return output_path


class FileProcessing:
    def __init__(self: Self, bot: Client):
        self.bot = bot

    async def attachment(self, channel: TextChannel, filePath: str) -> dict:
        url = f"https://discord.com/api/v10/channels/{channel.id}/attachments"
        headers = {"Authorization": f"Bot {os.environ['TOKEN']}"}
        payload = {
            "files": [
                {
                    "filename": "voice-message.ogg",
                    "file_size": VorbisFile(filePath).buffer_length,
                    "id": "2",  # was 6
                }
            ]
        }

        async with ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["attachments"][0]
                    else:
                        response_text = await response.text()
                        raise Exception(f"Attachment Error: {response_text}")
            except Exception as e:
                raise Exception(f"Attachment Exception: {e}")

    async def upload_to_cloud(self, upload_url: str, filePath: str) -> bool:
        headers = {"Content-Type": "audio/ogg"}
        await wait_for_file(filePath, 10)
        async with ClientSession() as session:
            try:
                data = await read_file(filePath)
                async with session.put(
                    upload_url, data=data, headers=headers
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        response_text = await response.text()
                        raise Exception(
                            f"Cloud Upload Error: {response_text}:{response.status}"
                        )
            except Exception as e:
                raise Exception(f"Cloud Upload Exception: {e}")

    async def upload_to_discord(self, channel: TextChannel, filePath: str) -> tuple:
        if not filePath.endswith(".ogg"):
            output_path = filePath.replace(".mp3", ".ogg")
            delete_file(output_path)
            filePath = await mp3_to_ogg(filePath)
            await asyncio.sleep(0.05)
            await wait_for_file(filePath, 3)
        try:
            attachment_info = await self.attachment(channel, filePath)
            success = await self.upload_to_cloud(
                attachment_info["upload_url"], filePath
            )

            if success:
                url = f"https://discord.com/api/v10/channels/{channel.id}/messages"
                headers = {
                    "Authorization": f"Bot {self.bot.config['token']}",
                    "content-type": "application/json",
                }
                payload = {
                    "content": "",
                    "channel_id": str(channel.id),
                    "type": 0,
                    "flags": 8192,
                    "attachments": [
                        {
                            "id": "0",  # attachment_info['id'],
                            "filename": attachment_info["upload_filename"].split("/")[
                                1
                            ],
                            "uploaded_filename": attachment_info["upload_filename"],
                            "duration_secs": MFile(filePath).info.length,
                            "waveform": "FzYACgAAAAAAACQAAAAAAAA=",  # "KBkKDRAKGBIWcnZ+o1xub6GUX6CITm0b"
                        }
                    ],
                }
                try:
                    os.remove(filePath)
                except Exception:
                    pass
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
