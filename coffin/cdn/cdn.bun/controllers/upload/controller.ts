/*
  Author: cop-discord
  Email: cop@catgir.ls
  Discord: aiohttp
*/
// @ts-ignore
import { v4 as uuid } from "uuid"; // Importing uuid from npm
const AI_ASSETS = {}; // Store uploaded assets

// Upload file
export async function handleUpload(req) {
  const body = await req.formData(); // Use formData to handle file uploads
  const file = body.get("file"); // Assuming the file input name is "file"
  const imageHash = uuid();

  if (file) {
    const arrayBuffer = await file.arrayBuffer(); // Read the file as an ArrayBuffer
    AI_ASSETS[imageHash] = { content_type: file.type, data: new Uint8Array(arrayBuffer)};
    return new Response(JSON.stringify({ Hash: imageHash, url: `https://cdn.coffin.bot/identifier/${imageHash}` }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } else {
    return new Response(JSON.stringify({ error: "No file uploaded" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }
};

// Get uploaded file by identifier
export async function handleIdentifier(req) {
  const url = new URL(req.url);
  const identifier = url.pathname.split("/").pop(); // Extract identifier from the URL

  if (!identifier) {
    return new Response(JSON.stringify({ error: "Identifier not found" }), {status: 404});
  }
  
  const asset = AI_ASSETS[identifier];

  if (asset) {
      return new Response(asset.data, {
          status: 200,
          headers: { "Content-Type": asset.content_type },
      });
  } else {
      return new Response(JSON.stringify({ error: `No Asset found under identifier ${identifier}` }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
      });
  }
}
