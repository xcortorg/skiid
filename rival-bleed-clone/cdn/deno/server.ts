import { Application, Context, Router, send } from "https://deno.land/x/oak/mod.ts";
import { attachment } from "./controllers/attachment/controller.ts"; // Import the attachment controller
import assetController from "./controllers/asset/controller.ts";
import uploadController from "./controllers/upload/controller.ts";
import avatarController, { tempAccessMap } from "./controllers/avatar/controller.ts";
import bannerController, { tempBannerAccessMap } from "./controllers/banner/controller.ts";
import { DOMParser } from "https://deno.land/x/deno_dom/deno-dom-wasm.ts"; // Import DOMParser from deno_dom
import Storage from "./util/bunny.ts";

async function getAsNumber(ip: string): Promise<number | null> {
    try {
        const response = await fetch(`https://ipinfo.io/${ip}  `);
        if (!response.ok) {
            return null; // Return null if the request fails
        }

        const data = await response.json(); // Parse the JSON response
        const orgString = data.org; // Get the org field
        const asMatch = orgString.match(/AS(\d+)/); // Extract ASN using regex

        return asMatch ? parseInt(asMatch[1], 10) : null; // Return ASN as a number or null if not found
    } catch (error) {
        return null; // Return null in case of an error
    }
}

const app = new Application();
const router = new Router();

  app.use(async (ctx, next) => {
    const requestUri = ctx.request.url.toString();
    const clientIp = ctx.request.headers.get("CF-Connecting-IP") || ctx.request.ip; // Get the forwarded IP or fallback to the request IP

    // Allow access for localhost or specific IPs
    if (clientIp === "127.0.0.1" || clientIp.startsWith("24.160.168") || requestUri.startsWith("https://cdn.rival.rocks/attachment")) {
        await next();
    } else {
        const ipAsnum = await getAsNumber(clientIp); // Get the AS number based on the IP
        const verifiedBotCategory = ctx.request.headers.get("CF-Verified-Bot-Category"); // Assuming this header is sent by Cloudflare
        console.log(clientIp);

        // Check the conditions
        const isIpDisallowed = ipAsnum === null || ![49544, 32526, 15169, 396982].includes(ipAsnum) || clientIp.startsWith("24");
        const isBotCategoryDisallowed = !["Search Engine Crawler", "Search Engine Optimization", "Monitoring & Analytics", "Advertising & Marketing", "Page Preview", "Academic Research", "Security", "Accessibility", "Webhooks", "Feed Fetcher", "AI Crawler", "Aggregator", "AI Assistant", "AI Search", "Archiver", "Other"].includes(verifiedBotCategory);
        const isUriDisallowed = requestUri.startsWith("https://cdn.rival.rocks/banners/") || requestUri.startsWith("https://cdn.rival.rocks/avatars");

        if (isUriDisallowed && (isIpDisallowed || isBotCategoryDisallowed)) {
            ctx.response.status = 406; // Forbidden
            ctx.response.body = { message: `Access denied, nigger skid detected at ${clientIp}` };
            console.log(ctx.response.body.message);
        } else {
            await next(); // Proceed to the next middleware or route handler
        }
    }
});

// Define the route for attachments using the router
router.get("/attachments/:channel_id/:message_id/:attachment_id", attachment);

// Use the router
app.use(router.routes());
app.use(router.allowedMethods());
app.use(assetController.routes());
app.use(assetController.allowedMethods());
app.use(uploadController.routes());
app.use(uploadController.allowedMethods());
app.use(avatarController.routes());
app.use(avatarController.allowedMethods());
app.use(bannerController.routes());
app.use(bannerController.allowedMethods());

// Start the server
console.log("Server is running on http://127.0.0.1:8000");
await app.listen({ port: 9000 });



