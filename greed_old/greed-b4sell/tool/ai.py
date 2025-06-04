from gpt4all import GPT4All as GPT
from asyncio import run
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from aiohttp import ClientSession
from orjson import loads


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
                    self.models = [Model(**model) for model in loads(await f.read())]
        if not return_raw:
            return {model.name: model.filename for model in self.models}
        return self.models

    async def get_model(self, name: str):
        models = await self.get_all_models()
        if name not in models.keys() and name not in models.values():
            raise ValueError("Invalid model name.")
        return models[name] if "." not in name else name


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
        async with session.head(url) as request:
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
        if model_name not in self.models:
            self.models[model_name] = GPT(n_threads=50, model_name=model_name)
        gpt = self.models[model_name]
        text = await run(gpt.generate, input)
        return AIResponse(text=text, time_elapsed=get_timestamp() - time_started)


async def test(input: str, model: str):
    response = await AI().generate_response(input, model)
    logger.info(response)
    return response


if __name__ == "__main__":
    run(
        test(
            "do black people have the same rights as white people",
            "gpt4all-falcon-newbpe-q4_0.gguf",
        )
    )
