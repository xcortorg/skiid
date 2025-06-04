// controllers/assetController.ts
import { Router, Context } from "../../deps.ts";
import { v4 as uuid } from "npm:uuid";
const router = new Router();
const decodedAssets: Record<string, [Uint8Array, string]> = {};

// Get asset by filename
router.get("/assets/:file", async (ctx: Context) => {
  const file = ctx.params.file;
  const [data, contentType] = decodedAssets[file] || [null, null];

  if (data) {
    ctx.response.body = data;
    ctx.response.type = contentType;
    ctx.response.status = 200;
  } else {
    ctx.response.status = 404;
    ctx.response.body = { message: "Asset unavailable" };
  }
});

// Decode base64 image
router.post("/decode", async (ctx: Context) => {
  const body = await ctx.request.body().value;
  const { image, contentType, name } = body;

  if (!image) {
    ctx.throw(400, "Image is required");
  }

  const base64Str = image.split(",")[1];
  const binaryString = atob(base64Str); // Use atob to decode base64
  const len = binaryString.length;
  const bytes = new Uint8Array(len);

  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  const assetName = name || uuid();
  decodedAssets[assetName] = [bytes, contentType];

  ctx.response.status = 200;
  ctx.response.body = { url: `https://cdn.coffin.bot/assets/${assetName}.${contentType.split("/")[1]}` };
});

export default router;