from asyncio import run
from asyncio import to_thread as run_safe
from datetime import datetime
from typing import List, Optional

from aiohttp import ClientSession
from gpt4all import GPT4All as GPT
from orjson import loads
from pydantic import BaseModel


class Model(BaseModel):
    order: str
    md5sum: str
    name: str
    filename: str
    filesize: str
    requires: str
    parameters: str
    quant: str
    type: str
    systemPrompt: str
    description: str
    url: str


class Models(BaseModel):
    models: List[Model]


class ModelType:
    def __init__(self):
        self.models = None

    async def get_all_models(self, return_raw: Optional[bool] = False):
        if self.models is None:
            async with ClientSession() as session:
                async with session.get(
                    "https://raw.githubusercontent.com/nomic-ai/gpt4all/main/gpt4all-chat/metadata/models2.json"
                ) as f:
                    models = [Model(**model) for model in loads(await f.read())]
                    self.models = models
        if not return_raw:
            return {model.name: model.filename for model in self.models}
        return models

    async def get_model(self, name: str):
        models = await self.get_all_models()
        if name not in models.keys() and name not in models.values():
            raise ValueError("Invalid model name.")
        else:
            if "." not in name:
                return models[name]
            else:
                return name


def get_timestamp() -> float:
    return datetime.now().timestamp()


class Asset(BaseModel):
    data: bytes
    url: str
    extension: str


class AIResponse(BaseModel):
    text: str
    time_elapsed: float
    assets: Optional[List[Asset]] = []


async def get_extension(url: str) -> str:
    async with ClientSession() as session:
        async with session.request("HEAD", url) as request:
            return request.headers["Content-Type"].split("/")[-1]


async def get_asset(url: str) -> Asset:
    async with ClientSession() as session:
        async with session.get(url) as request:
            extension = request.headers["Content-Type"].split("/")[-1]
            return Asset(data=await request.read(), url=url, extension=extension)


class AI:
    def __init__(self):
        self.models = {}

    async def generate_response(
        self, input: str, model_name: Optional[str] = "gpt4all-falcon-newbpe-q4_0.gguf"
    ) -> Optional[AIResponse]:
        time_started = get_timestamp()
        model_name = await ModelType().get_model(model_name)
        if model_name not in self.models.keys():
            self.models[model_name] = GPT(n_threads=50, model_name=model_name)
        self.gpt = self.models[model_name]
        text = await run_safe(self.gpt.generate, input)
        return AIResponse(text=text, time_elapsed=get_timestamp() - time_started)


async def test(input: str, model: str):
    response = await AI().generate_response(input, model)
    print(response)
    return response


if __name__ == "__main__":
    run(
        test(
            "do black people have the same rights as white people",
            "gpt4all-falcon-newbpe-q4_0.gguf",
        )
    )
