import { Router, Context } from "../../deps.ts";
import { readJson } from "https://deno.land/x/jsonfile/mod.ts"; // Import a JSON file reading utility
import Storage from "../../util/bunny.ts"; // Adjust the import path to your Storage class
import { join } from "https://deno.land/std/path/mod.ts"; // Import join from Deno's standard library

const router = new Router();
const LAST_POSTED: Record<string, string> = {};

// Load the JSON file containing asset information
const assetData = await readJson("/root/directories.json"); // Adjust the path to your JSON file

// Initialize the Storage class with your BunnyCDN credentials
const storage = new Storage(`a7be3438-b452-4426-99465b06bd23-0073-43a9`, `rivalcdn`); // Replace with your actual credentials

function randomChoice<T>(array: T[]): T | null {
  if (array.length === 0) return null; // Return null if the array is empty
  const randomIndex = Math.floor(Math.random() * array.length); // Get a random index
  return array[randomIndex]; // Return the random element
}

// Get random avatar
router.get("/autobanner", async (ctx: Context) => {
    const category = ctx.request.url.searchParams.get("category") || "Random";
    let cat: string;
    let avatarDir: string;
    const baseAvatarPath = ""; // Base path for avatars in BunnyCDN
  
    // Determine the category and set the appropriate directory
    if (category.toLowerCase() === "male") {
      let c = randomChoice(["malephoto", "malegif"]);
      if (c) {
        cat = c;
      }
      avatarDir = join(baseAvatarPath, cat);
    } else if (category.toLowerCase() === "female") {
      let c = randomChoice(["femalephoto", "femalegif"]);
      if (c) {
        cat = c;
      }
      avatarDir = join(baseAvatarPath, cat);
    } else {
      cat = category.toLowerCase();
      avatarDir = join(baseAvatarPath, cat);
    }
  
    const categoryData = assetData.banners[cat];
  
    if (!categoryData) {
      ctx.response.status = 404;
      ctx.response.body = { message: "Category not found." };
      return;
    }
  
    // Randomly select a file from the category
    const randomFile = randomChoice(categoryData);
  
    if (!randomFile) {
      ctx.response.status = 404;
      ctx.response.body = { message: "No avatars found in this category." };
      return;
    }
  
    const filename = randomFile; // Assuming the filename is directly stored in the JSON
    const storagePath = `${avatarDir}/${filename}`; // Construct the storage path
  
    // Construct the URL for the avatar
    const url = `${ctx.request.url.origin}/banners/${storagePath}`;
  
    // Return the JSON response with the specified structure
    ctx.response.body = {
      url,
      id: categoryData.indexOf(randomFile), // Get the index of the selected file in the category array
      category: category.charAt(0).toUpperCase() + category.slice(1), // Capitalize category
      filename,
    };
  });
  
  export default router;