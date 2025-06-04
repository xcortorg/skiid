import { db } from "@/lib/db";
import ClientPage from "./client-page";
import { Metadata, Viewport } from "next";

function formatBioForMetadata(bio: string | null): string {
  if (!bio) return "View my profile on emogir.ls";

  let formatted = bio;
  const newlineCount = (formatted.match(/\n/g) || []).length;

  if (newlineCount > 3) {
    formatted = formatted.replace(/\n{2,}/g, "\n");

    if ((formatted.match(/\n/g) || []).length > 3) {
      const lines = formatted.split("\n");
      formatted = lines.slice(0, 3).join(" ");
    }
  }

  formatted = formatted.replace(/\n/g, " ");

  if (formatted.length > 160) {
    formatted = formatted.substring(0, 157) + "...";
  }

  return formatted;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const resolvedParams = await params;
  const sanitizedSlug = decodeURIComponent(resolvedParams.slug).replace(
    /^@/,
    ""
  );
  console.log("Generating metadata for slug:", sanitizedSlug);

  if (sanitizedSlug.includes(".")) {
    return {};
  }

  const userStatus = await db.user.findUnique({
    where: { username: sanitizedSlug },
    select: {
      accountStatus: true,
    },
  });

  if (
    !userStatus ||
    ["BANNED", "DISABLED", "RESTRICTED"].includes(userStatus.accountStatus)
  ) {
    return {
      title: "emogir.ls",
      description: "Create your own customizable profile page",
    };
  }

  const user = await db.user.findUnique({
    where: { username: sanitizedSlug },
    select: {
      name: true,
      bio: true,
      appearance: {
        select: {
          displayName: true,
          bio: true,
          embedColor: true,
        },
      },
    },
  });

  console.log("Found user:", user);

  if (!user) {
    console.log("No user found for slug:", sanitizedSlug);
    return {
      title: "Not Found | emogir.ls",
      description: "Profile not found",
    };
  }

  const title = `${
    user.appearance?.displayName || user.name || sanitizedSlug
  } | emogir.ls`;

  const rawDescription = user.appearance?.bio || user.bio || null;
  const description = formatBioForMetadata(rawDescription);

  console.log("Generated metadata:", { title, description });

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      images: [`https://emogir.ls/api/og?slug=${sanitizedSlug}`],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [`https://emogir.ls/api/og?slug=${sanitizedSlug}`],
    },
  };
}

export async function generateViewport({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Viewport> {
  const resolvedParams = await params;
  const sanitizedSlug = decodeURIComponent(resolvedParams.slug).replace(
    /^@/,
    ""
  );

  const user = await db.user.findUnique({
    where: { username: sanitizedSlug },
    select: {
      appearance: {
        select: {
          embedColor: true,
        },
      },
    },
  });

  return {
    themeColor: user?.appearance?.embedColor || "#f2108a",
  };
}

export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const resolvedParams = await params;
  const sanitizedSlug = decodeURIComponent(resolvedParams.slug).replace(
    /^@/,
    ""
  );
  return <ClientPage slug={sanitizedSlug} />;
}
