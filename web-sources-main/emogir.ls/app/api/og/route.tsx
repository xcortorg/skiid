import { ImageResponse } from "next/og";

export const runtime = "edge";

function sanitizeBio(bio: string | null): string {
  if (!bio) return "";

  const newlineCount = (bio.match(/\n/g) || []).length;

  let cleaned = bio;

  if (newlineCount > 3) {
    cleaned = bio.replace(/\n{2,}/g, "\n");

    const reducedNewlineCount = (cleaned.match(/\n/g) || []).length;
    if (reducedNewlineCount > 5) {
      cleaned = cleaned.replace(/\n+/g, " ");
    }
  }

  return cleaned.length > 120 ? cleaned.substring(0, 117) + "..." : cleaned;
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const slug = searchParams.get("slug")?.replace("@", "");

    if (!slug) {
      return new Response("Missing slug parameter", { status: 400 });
    }

    const response = await fetch(`https://emogir.ls/api/profile/${slug}`);
    if (!response.ok) {
      return new Response("User not found", { status: 404 });
    }

    const userData = await response.json();

    const rawBio = userData.bio || userData.appearance?.bio || "";
    const sanitizedBio = sanitizeBio(rawBio);

    const user = {
      name: userData.user?.name || userData.name || slug,
      bio: sanitizedBio,
      image: userData.avatar,
    };

    return new ImageResponse(
      (
        <div
          style={{
            height: "100%",
            width: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "#0A0A0A",
            padding: "40px 60px",
            gap: "24px",
          }}
        >
          <div style={{ position: "relative", display: "flex" }}>
            {user.image && (
              <img
                src={user.image}
                alt={user.name || ""}
                style={{
                  width: "160px",
                  height: "160px",
                  borderRadius: "80px",
                }}
              />
            )}
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "16px",
            }}
          >
            <h1 style={{ fontSize: "48px", color: "white", margin: 0 }}>
              {user.name || ""}
            </h1>
            {user.bio && (
              <p
                style={{
                  fontSize: "24px",
                  color: "rgba(255, 255, 255, 0.8)",
                  margin: 0,
                  maxWidth: "600px",
                  textAlign: "center",
                  lineHeight: "1.4",
                  whiteSpace: "pre-line",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {user.bio}
              </p>
            )}
          </div>
          <div
            style={{ position: "absolute", bottom: "40px", display: "flex" }}
          >
            <p
              style={{
                fontSize: "20px",
                color: "rgba(255, 255, 255, 0.6)",
                margin: 0,
              }}
            >
              emogir.ls/@{slug}
            </p>
          </div>
        </div>
      ),
      {
        width: 1200,
        height: 630,
      },
    );
  } catch (e) {
    console.error(e);
    return new Response("Failed to generate image", { status: 500 });
  }
}
