import { notFound } from "next/navigation";
import { db } from "@/lib/db";
import ClientPreview from "./client-preview";

export const dynamic = "force-dynamic";
export const revalidate = 0;

async function getPreviewData(previewId: string) {
  const preview = await db.appearancePreview.findUnique({
    where: {
      id: previewId,
    },
  });

  if (!preview) return null;

  const user = await db.user.findUnique({
    where: {
      id: preview.userId,
    },
    select: {
      id: true,
      username: true,
      name: true,
      bio: true,
      image: true,
      links: true,
      appearance: {
        select: {
          lastfmEnabled: true,
          lastfmCompactMode: true,
          lastfmShowScrobbles: true,
          lastfmShowTabs: true,
          lastfmMaxTracks: true,
          lastfmThemeColor: true,
          lastfmBgColor: true,
          lastfmTextColor: true,
          lastfmSecondaryColor: true,
        },
      },
      iconSettings: {
        select: {
          backgroundColor: true,
          size: true,
          borderRadius: true,
          borderColor: true,
          glowColor: true,
          glowIntensity: true,
        },
      },
    },
  });

  if (!preview || preview.expiresAt < new Date()) {
    return null;
  }

  return {
    preview,
    user,
  };
}

export default async function PreviewPage({
  params,
}: {
  params: Promise<{ previewId: string }>;
}) {
  const resolvedParams = await params;
  const data = await getPreviewData(resolvedParams.previewId);

  if (!data) {
    notFound();
  }

  const { preview, user } = data;
  const previewData = preview.previewData as any;

  return <ClientPreview previewData={previewData} userData={user} />;
}
