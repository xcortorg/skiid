import { Metadata } from "next";
import { supabase } from "@/lib/supabase";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { formatDistanceToNow } from "date-fns";
import ImageActions from "@/app/components/ImageActions";

async function getImageDetails(host: string, path: string) {
  console.log("Debug - Host:", host);
  console.log("Debug - Original Path:", path);

  const cleanPath = path.replace(/\.json$/, "");
  console.log("Debug - Clean Path:", cleanPath);

  if (host.startsWith("upload.")) {
    const { data: image } = await supabase
      .from("uploads")
      .select("*, image_users!inner(*)")
      .eq("filename", cleanPath)
      .single();

    console.log("Debug - Upload image result:", image);
    return image;
  }

  console.log("Debug - Looking up user for host:", host);
  const { data: user } = await supabase
    .from("image_users")
    .select("id, subdomain")
    .eq("subdomain", host)
    .single();

  console.log("Debug - User lookup result:", user);

  if (!user) {
    console.log("Debug - No user found for host:", host);
    return null;
  }

  console.log(
    "Debug - Looking up image for user:",
    user.id,
    "path:",
    cleanPath
  );
  const { data: image } = await supabase
    .from("uploads")
    .select("*, image_users!inner(*)")
    .eq("user_id", user.id)
    .eq("filename", cleanPath)
    .single();

  console.log("Debug - Image lookup result:", image);
  return image;
}

export async function generateMetadata({ params }: any): Promise<Metadata> {
  const headersList = await headers();
  const host = headersList.get("host") || "";
  const path = params.slug.join("/");
  const image = await getImageDetails(host, path);

  if (!image) {
    console.log("Debug - Metadata - No image found, redirecting");
    redirect("https://emogir.ls");
  }

  const imageUrl = `https://r.emogir.ls/${image.filename}`;
  const oembedUrl = `https://${host}/oembed/${image.filename}.json`;

  return {
    openGraph: {
      images: [imageUrl],
    },
    twitter: {
      card: "summary_large_image",
      images: [imageUrl],
    },
    alternates: {
      types: {
        "application/json+oembed": oembedUrl,
      },
    },
  };
}

export default async function Page({ params }: any) {
  const headersList = await headers();
  const host = headersList.get("host") || "";
  const path = params.slug.join("/");

  if (path.endsWith(".json")) {
    return null;
  }

  const image = await getImageDetails(host, path);

  if (!image) {
    redirect("https://emogir.ls");
  }

  const uploadedAt = formatDistanceToNow(new Date(image.created_at), {
    addSuffix: true,
  });

  return (
    <div className="min-h-screen bg-darker text-white font-sans flex items-center justify-center">
      <div className="w-full max-w-5xl mx-auto p-6">
        <div className="bg-dark rounded-2xl overflow-hidden border border-white/5">
          <div className="relative aspect-video bg-black/20">
            <img
              src={`https://r.emogir.ls/${image.filename}`}
              alt={image.original_name}
              className="w-full h-auto"
            />
          </div>

          <div className="p-6 space-y-4 bg-darker/50">
            <div className="flex items-center justify-between">
              <h1 className="text-lg font-medium text-white/90">
                {image.original_name}
              </h1>
              <span className="text-sm text-white/60">
                Uploaded {uploadedAt}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="bg-black/20 rounded-lg p-4">
                <p className="text-sm text-white/60 mb-1">Size</p>
                <p className="text-white/90">
                  {(image.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <div className="bg-black/20 rounded-lg p-4">
                <p className="text-sm text-white/60 mb-1">Type</p>
                <p className="text-white/90">{image.mime_type}</p>
              </div>
              <div className="bg-black/20 rounded-lg p-4">
                <p className="text-sm text-white/60 mb-1">Dimensions</p>
                <p className="text-white/90">-</p>
              </div>
            </div>

            <ImageActions imageUrl={`https://r.emogir.ls/${image.filename}`} />
          </div>
        </div>
      </div>
    </div>
  );
}
