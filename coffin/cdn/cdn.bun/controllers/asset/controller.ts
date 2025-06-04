/*
  Author: cop-discord
  Email: cop@catgir.ls
  Discord: aiohttp
*/
// @ts-ignore

import { serve } from "bun";
import { v4 as uuid } from "uuid"; // Importing uuid from npm

const decodedAssets = {}; // Store decoded assets

// Function to handle GET requests for assets
export async function handleGetAssets(req) {
  const url = new URL(req.url);
  const file = url.pathname.split("/").pop(); // Extract the file name from the URL
  if (!file) {
    return new Response(JSON.stringify({ message: "Asset unavailable" }), {
        status: 404,
        headers: {
          "Content-Type": "application/json",
        },
      });
  }
  const fileName = file.includes(".") ? file.split(".")[0] : file; // Handle filename extraction

  const [data, contentType] = decodedAssets[fileName] || [null, null];

  if (data) {
    return new Response(data, {
      status: 200,
      headers: {
        "Content-Type": contentType, // Set the content type
      },
    });
  } else {
    return new Response(JSON.stringify({ message: "Asset unavailable" }), {
      status: 404,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }
}

// Function to handle POST requests for decoding images
export async function handleDecode(req) {
  const { image } = await req.json();
  if (!image) {
    return new Response("Image is required", { status: 400 });
  }

  const contentType = image.split(",")[0].split(":")[1].split(";")[0];
  const base64Str = image.split(",")[1];

  const binaryString = atob(base64Str); // Decode base64
  const len = binaryString.length;
  const bytes = new Uint8Array(len);

  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  const assetName = uuid(); // Generate a unique asset name
  decodedAssets[assetName] = [bytes, contentType]; // Store the asset

  return new Response(JSON.stringify({
    url: `https://cdn.coffin.bot/assets/${assetName}.${contentType.split("/")[1]}`,
  }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}
