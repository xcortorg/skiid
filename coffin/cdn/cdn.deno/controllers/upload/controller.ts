// controllers/uploadController.ts
import { Router, Context } from "../../deps.ts";
import { v4 as uuid } from "npm:uuid";

const router = new Router();
const AI_ASSETS: Record<string, { content_type: string; data: Uint8Array }> = {};

// Upload file
router.post("/upload", async (ctx: Context) => {
  const body = ctx.request.body();
  const file = await body.value.read();
  const imageHash = uuid();

  if (file && file.content) {
    AI_ASSETS[imageHash] = { content_type: file.content.type, data: await Deno.readAll(file.content) };
    ctx.response.status = 200;
    ctx.response.body = { Hash: imageHash, url: `https://cdn.coffin.bot/uploads/${imageHash}` };
  } else {
    ctx.throw(400, "No file uploaded");
  }
});

// Get uploaded file by identifier
router.get("/uploads/:identifier", async (ctx: Context) => {
  const identifier = ctx.params.identifier;
  const asset = AI_ASSETS[identifier];

  if (asset) {
    ctx.response.body = asset.data;
    ctx.response.type = asset.content_type;
    ctx.response.status = 200;
  } else {
    ctx.response.status = 404;
    ctx.response.body = { error: `No Asset found under identifier ${identifier}` };
  }
});

export default router;