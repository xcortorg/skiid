// controllers/assetController.ts
import { Router, Context } from "../../deps.ts";
import { v4 as uuid } from "npm:uuid";
import { Context } from "https://deno.land/x/oak/mod.ts";
const router = new Router();
const decodedAssets: Record<string, [Uint8Array, string]> = {};

router.get("/assets/:file", async (ctx: Context) => {
  console.log(decodedAssets);
  
  const file = ctx.params.file;
  
  // Correctly handle the filename extraction
  const fileName = file.includes(".") ? file.split(".")[0] : file; // Use includes instead of "in"

  const [data, contentType] = decodedAssets[fileName] || [null, null];

  if (data) {
    ctx.response.body = data;
    ctx.response.type = contentType; // Set the content type
    ctx.response.status = 200; // Respond with 200 OK
  } else {
    ctx.response.status = 404; // Respond with 404 Not Found
    ctx.response.body = { message: "Asset unavailable" }; // Message for the client
  }
});
// Decode base64 image
router.post("/decode", async (ctx: Context) => {
  const { image } = await ctx.request.body.json();
  if (!image) {
    ctx.throw(400, "Image is required");
  }
  const contentType = image.split(",")[0].split(":")[1].split(";")[0];
  const base64Str = image.split(",")[1];

  const binaryString = atob(base64Str); // Use atob to decode base64
  const len = binaryString.length;
  const bytes = new Uint8Array(len);

  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  const assetName = name || uuid();
  console.log(`${image} - ${contentType} ${name}`);
  decodedAssets[assetName] = [bytes, contentType];
  console.log(assetName);

  ctx.response.status = 200;
  ctx.response.body = { url: `https://cdn.rival.rocks/assets/${assetName}.${contentType.split("/")[1]}` };
});

export default router;