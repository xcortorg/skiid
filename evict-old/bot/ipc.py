import os

import asyncpg
from cashews import cache
from discord.ext.ipc import Client
from dotenv import load_dotenv
from quart import Quart, jsonify, request
from quart_cors import cors

cache.setup("mem://")

load_dotenv()


class Evict(Quart):
    def init(self, *args, kwargs):
        super().__init__(*args, **kwargs)
        self.ipc = Client(
            secret_key="Ng\\_3QEVfjN)U/1=FQz`58c%B4m3|&",
            standard_port=6060,
            do_multicast=False,
        )

    async def startup(self):
        self.pool = await asyncpg.create_pool(
            port="5432",
            database="evict",
            user="postgres",
            host="localhost",
            password="admin",
        )

    async def shutdown(self):
        await self.pool.close()


app = Evict(__name__)
app = cors(
    app,
    allow_origin="*",
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.after_request
async def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.before_serving
async def before_serving():
    await app.startup()


@app.after_serving
async def after_serving():
    await app.shutdown()


@app.errorhandler(404)
async def handle_not_found(error: str = "Resource not found"):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(400)
async def handle_bad_request(error: str = "Bad Request"):
    return jsonify({"error": "Bad request"}), 400


@app.route("/bad-request", methods=["POST"])
async def bad_request(error: str = "Bad Request"):
    if not request.is_json:
        raise bad_request()
    data = await request.json
    return jsonify({"message": "Received data", "data": data})


@app.route("/status")
@cache(ttl="5s", key="status")
async def status():
    try:
        resp = await app.ipc.request("status")
    except Exception as e:
        app.ipc = Client(
            secret_key="Ng\\_3QEVfjN)U/1=FQz`58c%B4m3|&",
            standard_port=6060,
            do_multicast=False,
        )
        resp = await app.ipc.request("status")
    return jsonify(resp.response)


if __name__ == "__main__":
    app.run(port=5000)
