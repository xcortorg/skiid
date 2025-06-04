from sanic import Sanic, json, raw
from sanic.request import Request
from sanic.response import html
from sanic_cors import CORS
from tool.important.database import Database, Record
import jinja2
import pylast
from urllib.parse import urlencode
with open("/root/greed-prem/static/collage.html", "r") as file:
    template = jinja2.Template(file.read())

app = Sanic("cdn")
cors = CORS(app)

async def avatar(request: Request, user_id: int, identifier: str):
    if not (data := await app.ctx.db.fetchrow("""SELECT avatar, content_type, ts FROM avatars WHERE user_id = $1 AND id = $2""", user_id, identifier)):
        return json(body={'message':'Not found'}, status=404)
    return raw(data.avatar, content_type=data.content_type, status=200)

def get_url(row: Record) -> str:
    return f"https://cdn.greed.rocks/avatar/{row.user_id}/{row.id}"

async def avatars(request: Request, user_id: int):
    if not (rows := await app.ctx.db.fetch("""SELECT user_id, id FROM avatars WHERE user_id = $1 ORDER BY ts DESC""", user_id)):
        return json(body={'message': 'No avatars recorded'}, status=404)
    avatars = [get_url(row) for row in rows]
    avatar = get_url(rows[0])
    c = template.render(avatar = avatar, avatars = avatars)
    return html(c)
    
@app.listener("before_server_start")
async def on_start(app, loop):
    app.ctx.db = Database()
    await app.ctx.db.connect()

app.add_route(avatar, "/avatar/<user_id>/<identifier>", methods = ["GET", "OPTIONS"])
app.add_route(avatars, "/avatars/<user_id>", methods = ["GET", "OPTIONS"])

if __name__ == "__main__":
    app.run(port=5555)
