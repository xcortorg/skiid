import { Context } from "https://deno.land/x/oak/mod.ts";

export const attachment = async (ctx: Context) => {
  const { channel_id, message_id, attachment_id } = ctx.params;
  let response;

  const url = ctx.request.url.href
    .replace("http://127.0.0.1:8000", "https://cdn.coffin.bot")
    .replace("cdn.coffin.bot", "cdn.discordapp.com");

  try {
    const fetchResponse = await fetch(url); // Use the built-in fetch
    const contentType = fetchResponse.headers.get("content-type");

    if (contentType === "text/plain;charset=UTF-8" || contentType === "text/plain") {
      response = { message: "Asset expired or not found" };
      ctx.response.status = 404;
      ctx.response.headers.set("Content-Type", contentType);
      ctx.response.body = await fetchResponse.arrayBuffer();
    } else {
      ctx.response.status = 200;
      ctx.response.headers.set("Content-Type", contentType || "application/octet-stream");
      ctx.response.body = await fetchResponse.arrayBuffer();
    }
  } catch (error) {
    console.error("Error fetching the attachment:", error);
    ctx.response.status = 500;
    ctx.response.body = { message: "Internal Server Error" };
  }
};