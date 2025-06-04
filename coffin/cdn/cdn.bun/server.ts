// @ts-ignore
import { serve } from "bun"; // Importing serve from Bun
import { attachment } from "./controllers/attachment/controller.ts"; // Import the attachment controller
import { handleGetAssets, handleDecode } from "./controllers/asset/controller.ts"; // Adjust the import path if necessary
// @ts-ignore
import { handleUpload, handleIdentifier } from "./controllers/upload/controller.ts"; // Adjust the import path if necessary

const PORT = 9000;


// Middleware to handle CORS
const corsMiddleware = async (req) => {
    const res = new Response("CORS Middleware", { status: 200 });
    res.headers.set("Access-Control-Allow-Origin", "*");
    res.headers.set("Access-Control-Allow-Methods", "GET, OPTIONS");
    return res;
};

// Main server function
const addCorsHeaders = (response) => {
    response.headers.set("Access-Control-Allow-Origin", "*"); // Allow all origins
    response.headers.set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"); // Allow specific methods
    response.headers.set("Access-Control-Allow-Headers", "Content-Type, Authorization"); // Allow specific headers
    return response;
};

// Middleware to handle CORS preflight requests
const handleOptions = () => {
    const response = new Response(null, { status: 204 }); // No content for OPTIONS
    return addCorsHeaders(response);
};

// Main server function
const server = serve({
    fetch: async (req) => {
        // Handle CORS preflight requests
        if (req.method === "OPTIONS") {
            return handleOptions();
        }

        // Handle other routes
        switch (req.method) {
            case "GET":
                if (req.url.includes("/assets")) {
                    return addCorsHeaders(await handleGetAssets(req));
                } else if (req.url.includes("/identifier")) {
                    return addCorsHeaders(await handleIdentifier(req));
                } else if (req.url.includes("/attachments/")) {
                    console.log(`handling request to ${req.url}`);
                    return addCorsHeaders(await attachment(req));
                }
                break;
            case "POST":
                if (req.url.includes("/upload")) {
                    return addCorsHeaders(await handleUpload(req));
                } else if (req.url.includes("/decode")) {
                    return addCorsHeaders(await handleDecode(req));
                }
                break;
            default:
                return addCorsHeaders(new Response("Method Not Allowed", { status: 405 }));
        }

        return addCorsHeaders(new Response("Not Found", { status: 404 }));
    },
    port: PORT, // Set your desired port
});

console.log(`Server running on http://localhost:${PORT}`);