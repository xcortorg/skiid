import os
import orjson
from piper.download import get_voices
from asyncio import sleep, Lock, ensure_future
from collections import defaultdict
from pathlib import Path
from tuuid import tuuid
from fast_string_match import closest_match
from pydantic import BaseModel
from typing import Optional, Union
from logging import getLogger
from tool.worker import offloaded
from cashews import cache
from contextlib import suppress
from .translate import translate

cache.setup("mem://")
logger = getLogger(__name__)

BASE_DIR = "greed"


@offloaded
def execute(command: str, filename: str) -> str:
    import subprocess
    import os
    import time

    total = 0.000
    subprocess.run(command, shell=True, check=True)
    passed = True
    while not os.path.isfile(filename):
        sleep_time = 0.001
        time.sleep(sleep_time)
        total += sleep_time
        if sleep_time >= 2.000:
            passed = False
            break
    if not passed:
        raise TypeError("could not execute that TTS query")
    return filename


@offloaded
def read_file(filepath: str, mode: str) -> Union[str, bytes]:
    with open(filepath, mode) as file:
        data = file.read()
    return data


class TTSModel(BaseModel):
    model: str
    config: str
    name: str
    language: str
    level: str


class TTS:
    def __init__(self):
        self.models = {}
        self.lock = defaultdict(Lock)
        self.model_storage = None

    def get_model_names(self):
        return [str(p) for p in Path("/root/tts_models/").iterdir() if p.is_dir()]

    def get_models(self):
        models = []
        for m in [
            str(p) for p in Path("/root/tts_models").glob("*onnx") if not p.is_dir()
        ]:
            name, level, language = self.get_name(m)
            models.append(
                TTSModel(
                    **{
                        "model": m,
                        "config": f"{m}.json",
                        "name": name,
                        "language": language,
                        "level": level,
                    }
                )
            )
        self.model_storage = models
        return models

    def _find_model_named(self, name: str, language: str = "en_US", level: str = "low"):
        if self.model_storage is None:
            self.get_models()
        models = {m.name: m for m in self.model_storage}
        close = []
        exact = [
            m
            for m in self.model_storage
            if m.name == name and m.language == language and m.level == level
        ]
        if len(exact) > 0:
            return exact[0]
        if match := closest_match(name, list(models.keys())):
            for model in self.model_storage:
                if (
                    model.name == match
                    and model.language == language
                    and model.level == level
                ):
                    return match
                else:
                    if model.name == match and model.language == language:
                        close.append(model)
        if len(close) > 0:
            return close[0]
        else:
            raise ValueError("No model found for that query")

    def get_voice(self, name: str, language: str = "en_US", level: str = "low"):
        m = self._find_model_named(name, language, level)
        return f"{m.language}-{m.name}-{m.level}"

    def get_name(self, path: str):
        obj = path.split("-", 1)
        language = obj[0].split("/")[-1]
        name, level = obj[1].split("-")
        level = level.split(".", 1)[0]
        return name, level, language

    async def get_model_names_all(self):
        return orjson.loads(await read_file("/root/tts_models/voices.json", "rb"))

    def get_model_files(self, name: str):
        p = [m for m in Path("/root/tts_models").iterdir()]
        if "/root/tts_models" in name:
            f = [d for d in Path(name).iterdir()]
        else:
            f = [d for d in Path(f"/root/tts_models/{name}/{p[0]}").iterdir()]
        return [str(k) for k in Path(f[0]).iterdir() if "onnx" in str(k)]

    def download_models(self):
        return get_voices(download_dir="/root/tts_models", update_voices=True)

    async def delete_soon(self, fp: str, ttl: int = 100) -> bool:
        async def delete(fp: str, ttl: int):
            await sleep(ttl)
            with suppress(FileNotFoundError):
                os.remove(fp)
            return True

        ensure_future(delete(fp, ttl))
        return True

    async def tts_api(self, name: str, language: str, level: str, text: str):
        _ = await self.tts(name, language, level, text)
        await self.delete_soon(_)
        return _

    async def load_model(self, name: str):
        files = self.get_model_files(name)
        config = None
        model = None
        for file in files:
            if file.endswith(".json"):
                config = file
            else:
                model = file
        self.models[name] = {"model": model, "config": config}
        return self.models[name]

    def find_model(self, name: str, level: str = "low", language: str = "en_US"):
        return f"{language}-{name}-{level}"

    async def tts(self, name: str, language: str, level: str, text: str):
        model = self.get_voice(name, language, level)
        return await self.do_tts(model, text)

    async def do_tts(
        self, model: str, text: str, output_dir: Optional[str] = "/data/tts"
    ):
        output_dir = f"/root/{BASE_DIR}{output_dir}"
        if "/root/tts_models/" not in model:
            model = f"/root/tts_models/{model}"
        if ".onnx" not in model:
            model = f"{model}.onnx"
        filename = f"{output_dir}/{tuuid()}.mp3"
        cmd = f"""echo '{text}' | piper \
  --model /root/tts_models/en_US-amy-low.onnx \
  --output_file {filename}"""
        return await execute(cmd, filename)
