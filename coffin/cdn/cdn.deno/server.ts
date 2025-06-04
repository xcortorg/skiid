/*
  Author: cop-discord
  Email: cop@catgir.ls
  Discord: aiohttp
*/
// @ts-ignore
import { Application, Context, Router, send } from "https://deno.land/x/oak/mod.ts";
import { attachment } from "./controllers/attachment/controller.ts";
import assetController from "./controllers/asset/controller.ts";
import uploadController from "./controllers/upload/controller.ts";

const app = new Application();
const router = new Router();

// Middleware to handle CORS
app.use(async (ctx, next) => {
  ctx.response.headers.set("Access-Control-Allow-Origin", "*");
  ctx.response.headers.set("Access-Control-Allow-Methods", "GET, OPTIONS");
  await next();
});


// Attachment Router
router.get("/attachments/:channel_id/:message_id/:attachment_id", attachment);

// Routers
app.use(router.routes());
app.use(router.allowedMethods());
app.use(assetController.routes());
app.use(assetController.allowedMethods());
app.use(uploadController.routes());
app.use(uploadController.allowedMethods());

console.log("Server is running on http://127.0.0.1:9000");
await app.listen({ port: 9000 });