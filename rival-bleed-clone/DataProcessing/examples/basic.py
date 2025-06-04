from DataProcessing import ServiceManager
from asyncio import run
import orjson


async def test():
    query = "purple"
    safe = True
    redis = None  # redis implementation here lol
    manager = ServiceManager(redis)
    search_results = await manager.bing.search(query, safe)
    image_results = await manager.bing.image_search(query, safe)
    with open("search.json", "wb") as file:
        file.write(orjson.dumps(search_results.dict()))

    with open("image.json", "wb") as file:
        file.write(orjson.dumps(image_results.dict()))


run(test())
