/*
  Author: cop-discord
  Email: cop@catgir.ls
  Discord: aiohttp
*/
// @ts-ignore


import { v4 as uuid } from "uuid"; // Importing uuid from npm

// Attachment handler function
export const attachment = async (req) => {
  const url = new URL(req.url);
  const { channel_id, message_id, attachment_id } = url.pathname.split("/").slice(-3); // Extract parameters from the URL

  // Construct the new URL based on the original request URL
  const fetchUrl = url.href
    .replace("http://127.0.0.1:9000", "https://cdn.coffin.bot")
    .replace("cdn.coffin.bot", "cdn.discordapp.com").replace("http://localhost:9000", "https://cdn.discordapp.com");

  let response;

  try {
    const fetchResponse = await fetch(fetchUrl); // Use the built-in fetch
    const contentType = fetchResponse.headers.get("content-type");

    if (contentType === "text/plain;charset=UTF-8" || contentType === "text/plain") {
      response = { message: "Asset expired or not found" };
      return new Response(JSON.stringify(response), {
        status: 404,
        headers: {
          "Content-Type": contentType,
        },
      });
    } else {
      const body = await fetchResponse.arrayBuffer();
      return new Response(body, {
        status: 200,
        headers: {
          "Content-Type": contentType || "application/octet-stream",
        },
      });
    }
  } catch (error) {
    console.error("Error fetching the attachment:", error);
    return new Response(JSON.stringify({ message: "Internal Server Error" }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }
};