__version__ = "1.1.1"

import json
import logging
import os
from typing import Any, Optional

import asyncpg
import orjson
from core.models import LogEntry
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from sanic import Sanic, response
from sanic.exceptions import NotFound

logger = logging.getLogger("sanic")
load_dotenv()


class Record(asyncpg.Record):
    def __getattr__(self, attr: str) -> Any:
        return self[attr]


if "URL_PREFIX" in os.environ:
    print("Using the legacy config var `URL_PREFIX`, rename it to `LOG_URL_PREFIX`")
    prefix = os.environ["URL_PREFIX"]
else:
    prefix = os.getenv("LOG_URL_PREFIX", "/logs")

if prefix == "NONE":
    prefix = ""


class Holder:
    def __init__(self):
        self.db = None

    def pool(self):
        return self.db


holder = Holder()
app = Sanic(__name__)
app.static("/static", "./static")

jinja_env = Environment(loader=FileSystemLoader("templates"))


def render_template(name, *args, **kwargs):
    template = jinja_env.get_template(name + ".html")
    return response.html(template.render(*args, **kwargs))


app.ctx.render_template = render_template

from pretend_redis import PretendRedis


@app.after_server_start
async def after_server_startup(app, loop):
    print("Connecting to database..")
    holder.db = await PretendRedis.from_url()
    await asyncpg.create_pool(
        host="127.0.0.1",
        port=5432,
        user="postgres",
        password="admin",
        database="pretend",
        record_class=Record,
    )
    print("Connected to database")


@app.exception(NotFound)
async def not_found(request, exc):
    return render_template("not_found")


@app.get("/")
async def index(request):
    return render_template("index")


@app.get(prefix + "/raw/<key>")
async def get_raw_logs_file(request, key):
    """Returns the plain text rendered log entry"""
    # if db == None: await after_server_startup(app)
    document = json.loads(
        await holder.db.fetchrow(
            """SELECT guild_id, channel_id, author, logs FROM logs WHERE key = $1""",
            key,
        )
    )
    if not document:
        raise NotFound
    #    document = dict(document)
    document["logs"].reverse()
    document["created_at"] = document["logs"][0]["timestamp"]
    document["creator"] = document["author"]
    document["messages"] = document["logs"]
    document["recipient"] = document["creator"]
    document.pop("logs")

    log_entry = LogEntry(app, document)

    return log_entry.render_plain_text()


import orjson


@app.get(prefix + "/<key>")
async def get_logs_file(request, key):
    """Returns the htndered log entry"""
    document = json.loads(await holder.db.get(key))
    await holder.db.fetchrow("""SELECT * FROM logs WHERE key = $1""", key)
    logger.warn(document)
    if isinstance(document, str):
        try:
            document = json.loads(document)
        except:
            pass
    logger.warn(type(document))
    if not document:
        raise NotFound
    #    document = dict(document)
    #   document['logs']=json.loads(document['logs'])['logs']
    document["key"] = key
    document["logs"].reverse()
    document["created_at"] = document["logs"][0]["timestamp"]
    document["creator"] = document["author"]
    document["creator"]["mod"] = True
    document.pop("author")
    document["messages"] = document["logs"]
    for log in document["messages"]:
        if isinstance(log, str):
            document["messages"].remove(log)
    document["open"] = True
    document["recipient"] = document["creator"]
    document.pop("logs")

    log_entry = LogEntry(app, dict(document))

    return log_entry.render_html()


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=os.getenv("PORT", 8000),
        debug=bool(os.getenv("DEBUG", False)),
    )
