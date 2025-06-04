import { getServerSession } from "next-auth/next";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { validateAppearance } from "@/lib/validations";
import { AudioTrack } from "@/components/ui/appearance/appearance-form";
import { redis, incrementCounter } from "@/lib/redis";
import { isAccountRestricted } from "@/lib/account-status";
import { withMetrics } from "@/lib/api-wrapper";
import { Session } from "next-auth";

const MAX_UPDATES = 30;
const WINDOW_TIME = 300;
const ALLOWED_DOMAIN = "r.emogir.ls";
const DISCORD_INVITE_REGEX =
  /^(?:https?:\/\/)?(?:www\.)?discord(?:\.gg|(?:app)?\.com\/invite)\/([a-zA-Z0-9-]+)$/;

async function checkRateLimit(userId: string): Promise<{
  allowed: boolean;
  error?: string;
  remainingTime?: number;
}> {
  try {
    const key = `ratelimit:appearance:user:${userId}`;
    const attempts = await incrementCounter(key, WINDOW_TIME);

    if (attempts > MAX_UPDATES) {
      return {
        allowed: false,
        error: "Too many appearance updates. Please try again later.",
        remainingTime: WINDOW_TIME,
      };
    }

    return { allowed: true };
  } catch (error) {
    console.error("Rate limit error:", error);
    return { allowed: true };
  }
}

function validateAssetUrl(url: string | null): boolean {
  if (!url) return true;
  try {
    const parsedUrl = new URL(url);
    return parsedUrl.hostname === ALLOWED_DOMAIN;
  } catch {
    return false;
  }
}

function sanitizeBio(bio: string | null): string | null {
  if (!bio) return bio;
  return bio.replace(/[^\w\s.,!?-]/g, "").trim();
}

function validateBio(bio: string | null | undefined): {
  valid: boolean;
  error?: { code: string; message: string; field: string; value: number };
} {
  if (!bio) return { valid: true };

  const bioLength = bio.length;
  if (bioLength > 400) {
    return {
      valid: false,
      error: {
        code: "20018",
        message: "Bio must be 400 characters or less",
        field: "bio",
        value: bioLength,
      },
    };
  }
  return { valid: true };
}

async function checkUserStatus(userId: string): Promise<boolean> {
  const user = await db.user.findUnique({
    where: { id: userId },
    select: { accountStatus: true },
  });

  if (!user) return false;

  return (
    user.accountStatus === "ACTIVE" || user.accountStatus === "PENDING_REVIEW"
  );
}

async function handleGET(request: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const isActive = await checkUserStatus(session.user.id);
    if (!isActive) {
      return NextResponse.json(
        { error: "This account has been suspended" },
        { status: 403 }
      );
    }

    const appearance = await db.appearance.findUnique({
      where: { userId: session.user.id },
      select: {
        id: true,
        userId: true,
        displayName: true,
        bio: true,
        avatar: true,
        banner: true,
        audioPlayerEnabled: true,
        audioTracks: {
          select: {
            id: true,
            url: true,
            title: true,
            icon: true,
            order: true,
            appearanceId: true,
            createdAt: true,
            updatedAt: true,
          },
          orderBy: {
            order: "asc",
          },
          take: 3,
        },
        layoutStyle: true,
        containerBackgroundColor: true,
        containerBackdropBlur: true,
        containerBorderColor: true,
        containerBorderWidth: true,
        containerBorderRadius: true,
        containerGlowColor: true,
        containerGlowIntensity: true,
        glassEffect: true,
        backgroundUrl: true,
        embedColor: true,
        avatarSize: true,
        avatarShowBorder: true,
        avatarBorderWidth: true,
        avatarBorderColor: true,
        avatarBorderRadius: true,
        avatarGlowColor: true,
        avatarGlowIntensity: true,
        avatarAlignment: true,
        titleColor: true,
        titleSize: true,
        titleWeight: true,
        usernameColor: true,
        usernameSize: true,
        bioColor: true,
        bioSize: true,
        linksBackgroundColor: true,
        linksHoverColor: true,
        linksBorderColor: true,
        linksGap: true,
        linksPrimaryTextColor: true,
        linksSecondaryTextColor: true,
        linksHoverTextColor: true,
        linksTextSize: true,
        linksIconSize: true,
        linksIconColor: true,
        linksIconBgColor: true,
        linksIconBorderRadius: true,
        linksCompactMode: true,
        linksDisableBackground: true,
        linksDisableHover: true,
        linksDisableBorder: true,
        discordPresenceBgColor: true,
        discordPresenceBorderColor: true,
        discordPresenceAvatarSize: true,
        discordPresenceTextColor: true,
        discordPresenceSecondaryColor: true,
        discordGuildBgColor: true,
        discordGuildBorderColor: true,
        discordGuildAvatarSize: true,
        discordGuildTitleColor: true,
        discordGuildButtonBgColor: true,
        discordGuildButtonHoverColor: true,
        clickEffectEnabled: true,
        clickEffectText: true,
        clickEffectColor: true,
        gradientEnabled: true,
        gradientColor: true,
        gradientType: true,
        gradientDirection: true,
        statsEnabled: true,
        statsColor: true,
        statsBgColor: true,
        font: true,
        fontSize: true,
        fontWeight: true,
        terminalFontFamily: true,
        terminalCursorStyle: true,
        terminalCursorColor: true,
        terminalCursorBlinkSpeed: true,
        terminalTypingSpeed: true,
        terminalPromptSymbol: true,
        terminalHeaderControls: true,
        terminalStatusBarEnabled: true,
        terminalLineNumbersEnabled: true,
        themeAccentColor: true,
        themePrimaryColor: true,
        themeSecondaryColor: true,
        themeBackgroundColor: true,
        tiltDisabled: true,
        discordServerInvite: true,
        linksIconBgEnabled: true,
        bioTextEffectEnabled: true,
        bioTextEffect: true,
        bioTextEffectSpeed: true,
        avatarDecoration: true,
        discordStatusIndicatorEnabled: true,
        lastfmEnabled: true,
        lastfmCompactMode: true,
        lastfmShowScrobbles: true,
        lastfmShowTabs: true,
        lastfmMaxTracks: true,
        lastfmThemeColor: true,
        lastfmBgColor: true,
        lastfmTextColor: true,
        lastfmSecondaryColor: true,
        discordActivityDisplayType: true,
        discordActivityCompactMode: true,
      },
    });

    if (!appearance) {
      return NextResponse.json(
        { error: "Appearance not found" },
        { status: 404 }
      );
    }

    const response = NextResponse.json(appearance);
    response.headers.set("x-user-id", session.user.id);
    return response;
  } catch (error) {
    console.error("Error fetching appearance:", error);
    return NextResponse.json(
      { error: "Failed to fetch appearance" },
      { status: 500 }
    );
  }
}

async function handlePUT(request: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const isActive = await checkUserStatus(session.user.id);
    if (!isActive) {
      return NextResponse.json(
        { error: "This account has been suspended" },
        { status: 403 }
      );
    }

    const isRestricted = await isAccountRestricted(session.user.id);
    if (isRestricted) {
      return NextResponse.json(
        { error: "Account is currently restricted" },
        { status: 403 }
      );
    }

    const rateLimitCheck = await checkRateLimit(session.user.id);
    if (!rateLimitCheck.allowed) {
      return NextResponse.json(
        {
          error: rateLimitCheck.error,
          blocked: true,
          remainingTime: rateLimitCheck.remainingTime,
        },
        { status: 429 }
      );
    }

    const body = await request.json();

    const bioValidation = validateBio(body.bio);
    if (!bioValidation.valid) {
      return NextResponse.json(
        {
          code: "40002",
          message: "Validation failed",
          errors: [bioValidation.error],
        },
        { status: 400 }
      );
    }

    const urlValidationErrors = [];

    if (!validateAssetUrl(body.avatar)) {
      urlValidationErrors.push({
        code: "20010",
        message: "Avatar URL must be from r.emogir.ls",
        field: "avatar",
        value: body.avatar,
      });
    }

    if (!validateAssetUrl(body.banner)) {
      urlValidationErrors.push({
        code: "20011",
        message: "Banner URL must be from r.emogir.ls",
        field: "banner",
        value: body.banner,
      });
    }

    if (!validateAssetUrl(body.backgroundUrl)) {
      urlValidationErrors.push({
        code: "20012",
        message: "Background URL must be from r.emogir.ls",
        field: "backgroundUrl",
        value: body.backgroundUrl,
      });
    }

    if (body.audioTracks?.length > 0) {
      body.audioTracks.forEach((track: any, index: number) => {
        if (!validateAssetUrl(track.url)) {
          urlValidationErrors.push({
            code: "20013",
            message: "Audio URL must be from r.emogir.ls",
            field: `audioTracks[${index}].url`,
            value: track.url,
          });
        }
        if (!validateAssetUrl(track.icon)) {
          urlValidationErrors.push({
            code: "20014",
            message: "Audio icon URL must be from r.emogir.ls",
            field: `audioTracks[${index}].icon`,
            value: track.icon,
          });
        }
      });
    }

    if (
      body.discordServerInvite &&
      !DISCORD_INVITE_REGEX.test(body.discordServerInvite)
    ) {
      urlValidationErrors.push({
        code: "20015",
        message: "Invalid Discord invite URL format",
        field: "discordServerInvite",
        value: body.discordServerInvite,
      });
    }

    if (urlValidationErrors.length > 0) {
      return NextResponse.json(
        {
          code: "40002",
          message: "Validation failed",
          errors: urlValidationErrors,
        },
        { status: 400 }
      );
    }

    if (body.audioTracks?.length > 3) {
      return NextResponse.json(
        {
          code: "40002",
          message: "Validation failed",
          errors: [
            {
              code: "20016",
              message: "Maximum of 3 audio tracks allowed",
              field: "audioTracks",
              value: body.audioTracks.length,
            },
          ],
        },
        { status: 400 }
      );
    }

    const currentAppearance = await db.appearance.findUnique({
      where: { userId: session.user.id },
      select: { layoutStyle: true },
    });

    body.layoutStyle = currentAppearance?.layoutStyle
      ? body.layoutStyle
      : body.layoutStyle === "modern"
      ? "modern"
      : "modern";

    const validationErrors = validateAppearance(body);
    if (validationErrors.length > 0) {
      return NextResponse.json(
        {
          code: "40002",
          message: "Validation failed",
          errors: validationErrors,
        },
        { status: 400 }
      );
    }

    const audioTracks: AudioTrack[] = body.audioTracks || [];

    const updateData = {
      displayName: body.displayName,
      bio: sanitizeBio(body.bio),
      audioPlayerEnabled: body.audioPlayerEnabled ?? true,
      layoutStyle: body.layoutStyle,
      containerBackgroundColor: body.containerBackgroundColor,
      containerBackdropBlur: body.containerBackdropBlur,
      containerBorderColor: body.containerBorderColor,
      containerBorderWidth: body.containerBorderWidth,
      containerBorderRadius: body.containerBorderRadius,
      containerGlowColor: body.containerGlowColor,
      containerGlowIntensity: body.containerGlowIntensity,
      glassEffect: body.glassEffect,
      backgroundUrl: body.backgroundUrl ?? null,
      avatarDecoration: body.avatarDecoration,
      embedColor: body.embedColor || "#f2108a",

      avatarSize: "96px",
      avatarShowBorder: body.avatarShowBorder,
      avatarBorderWidth: body.avatarBorderWidth,
      avatarBorderColor: body.avatarBorderColor,
      avatarBorderRadius: body.avatarBorderRadius,
      avatarGlowColor: body.avatarGlowColor,
      avatarGlowIntensity: body.avatarGlowIntensity,
      avatarAlignment: body.avatarAlignment || "left",

      titleColor: body.titleColor,
      titleSize: body.titleSize,
      titleWeight: body.titleWeight,
      usernameColor: body.usernameColor,
      usernameSize: body.usernameSize,
      bioColor: body.bioColor,
      bioSize: body.bioSize,

      linksBackgroundColor: body.linksBackgroundColor,
      linksHoverColor: body.linksHoverColor,
      linksBorderColor: body.linksBorderColor,
      linksGap: body.linksGap,
      linksPrimaryTextColor: body.linksPrimaryTextColor,
      linksSecondaryTextColor: body.linksSecondaryTextColor,
      linksHoverTextColor: body.linksHoverTextColor,
      linksTextSize: body.linksTextSize,
      linksIconSize: body.linksIconSize,
      linksIconColor: body.linksIconColor,
      linksIconBgColor: body.linksIconBgColor,
      linksIconBorderRadius: body.linksIconBorderRadius,
      linksCompactMode: body.linksCompactMode ?? false,
      linksIconBgEnabled: body.linksIconBgEnabled ?? true,
      linksDisableBackground: body.linksDisableBackground ?? false,
      linksDisableHover: body.linksDisableHover ?? false,
      linksDisableBorder: body.linksDisableBorder ?? false,

      discordPresenceBgColor: body.discordPresenceBgColor,
      discordPresenceBorderColor: body.discordPresenceBorderColor,
      discordPresenceAvatarSize: body.discordPresenceAvatarSize,
      discordPresenceTextColor: body.discordPresenceTextColor,
      discordPresenceSecondaryColor: body.discordPresenceSecondaryColor,
      discordGuildBgColor: body.discordGuildBgColor,
      discordGuildBorderColor: body.discordGuildBorderColor,
      discordGuildAvatarSize: body.discordGuildAvatarSize,
      discordGuildTitleColor: body.discordGuildTitleColor,
      discordGuildButtonBgColor: body.discordGuildButtonBgColor,
      discordGuildButtonHoverColor: body.discordGuildButtonHoverColor,

      clickEffectEnabled: body.clickEffectEnabled,
      clickEffectText: body.clickEffectText,
      clickEffectColor: body.clickEffectColor,
      gradientEnabled: body.gradientEnabled,
      gradientColor: body.gradientColor,
      gradientType: body.gradientType,
      gradientDirection: body.gradientDirection,

      statsEnabled: body.statsEnabled,
      statsColor: body.statsColor,
      statsBgColor: body.statsBgColor,

      font: body.font,
      fontSize: body.fontSize,
      fontWeight: body.fontWeight,

      terminalFontFamily: body.terminalFontFamily,
      terminalCursorStyle: body.terminalCursorStyle,
      terminalCursorColor: body.terminalCursorColor,
      terminalCursorBlinkSpeed: body.terminalCursorBlinkSpeed,
      terminalTypingSpeed: body.terminalTypingSpeed,
      terminalPromptSymbol: body.terminalPromptSymbol,
      terminalHeaderControls: body.terminalHeaderControls,
      terminalStatusBarEnabled: body.terminalStatusBarEnabled,
      terminalLineNumbersEnabled: body.terminalLineNumbersEnabled,

      themeAccentColor: body.themeAccentColor,
      themePrimaryColor: body.themePrimaryColor,
      themeSecondaryColor: body.themeSecondaryColor,
      themeBackgroundColor: body.themeBackgroundColor,

      tiltDisabled: body.tiltDisabled ?? false,
      discordServerInvite: body.discordServerInvite,
      banner: body.banner ?? null,
      bioTextEffectEnabled: body.bioTextEffectEnabled ?? false,
      bioTextEffect: body.bioTextEffect || "typewriter",
      bioTextEffectSpeed: body.bioTextEffectSpeed || 50,
      discordStatusIndicatorEnabled:
        body.discordStatusIndicatorEnabled ?? false,

      lastfmEnabled: body.lastfmEnabled ?? false,
      lastfmCompactMode: body.lastfmCompactMode ?? false,
      lastfmShowScrobbles: body.lastfmShowScrobbles ?? true,
      lastfmShowTabs: body.lastfmShowTabs ?? true,
      lastfmMaxTracks: body.lastfmMaxTracks ?? 4,
      lastfmThemeColor: body.lastfmThemeColor ?? "#f43f5e",
      lastfmBgColor: body.lastfmBgColor ?? "rgba(0,0,0,0.4)",
      lastfmTextColor: body.lastfmTextColor ?? "#ffffff",
      lastfmSecondaryColor:
        body.lastfmSecondaryColor ?? "rgba(255,255,255,0.6)",
      discordActivityDisplayType: body.discordActivityDisplayType || "BOTH",
      discordActivityCompactMode: body.discordActivityCompactMode ?? false,
    };

    try {
      let appearance = await db.appearance.findUnique({
        where: { userId: session.user.id },
      });

      if (!appearance) {
        appearance = await db.appearance.create({
          data: {
            userId: session.user.id,
            ...updateData,
          },
        });
      } else {
        appearance = await db.appearance.update({
          where: { id: appearance.id },
          data: updateData,
        });
      }

      await db.audioTrack.deleteMany({
        where: { appearanceId: appearance.id },
      });

      if (body.audioTracks?.length > 0) {
        const existingTracks = await db.audioTrack.findMany({
          where: { appearanceId: appearance.id },
        });

        // @ts-ignore
        const iconMap = new Map(
          existingTracks.map((track) => [track.id, track.icon])
        );

        await db.audioTrack.createMany({
          data: body.audioTracks
            .slice(0, 3)
            .map((track: any, index: number) => ({
              appearanceId: appearance.id,
              url: track.url,
              title: track.title || "",
              icon: track.icon || iconMap.get(track.id) || null,
              order: index,
            })),
        });
      }

      const responseData = {
        ...appearance,
        audioTracks,
      };

      const response = NextResponse.json(responseData);
      response.headers.set("x-user-id", session.user.id);
      return response;
    } catch (dbError) {
      console.error("Database error:", dbError);
      throw dbError;
    }
  } catch (error) {
    console.error("Error in PUT /api/appearance:", error);
    return NextResponse.json(
      {
        code: "50001",
        message: "Internal server error",
        errors: [
          {
            code: "50001",
            message:
              error instanceof Error
                ? error.message
                : "An unexpected error occurred",
            field: "server",
          },
        ],
      },
      { status: 500 }
    );
  }
}

async function handlePOST(request: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const isActive = await checkUserStatus(session.user.id);
    if (!isActive) {
      return NextResponse.json(
        { error: "This account has been suspended" },
        { status: 403 }
      );
    }

    const isRestricted = await isAccountRestricted(session.user.id);
    if (isRestricted) {
      return NextResponse.json(
        { error: "Account is currently restricted" },
        { status: 403 }
      );
    }

    const rateLimitCheck = await checkRateLimit(session.user.id);
    if (!rateLimitCheck.allowed) {
      return NextResponse.json(
        {
          error: rateLimitCheck.error,
          blocked: true,
          remainingTime: rateLimitCheck.remainingTime,
        },
        { status: 429 }
      );
    }

    const data = await request.json();

    const bioValidation = validateBio(data.profile.bio);
    if (!bioValidation.valid) {
      return NextResponse.json(
        {
          code: "40002",
          message: "Validation failed",
          errors: [bioValidation.error],
        },
        { status: 400 }
      );
    }

    await db.appearance.upsert({
      where: {
        userId: session.user.id,
      },
      create: {
        userId: session.user.id,
        avatar: data.profile.avatar,
        banner: data.profile.banner,
        bio: sanitizeBio(data.profile.bio),
        glassEffect: data.container.glassEffect,
        themePrimaryColor: data.colors.primary,
        themeSecondaryColor: data.colors.secondary,
        audioTracks: {
          create: data.audio.tracks.map((track: any, index: number) => ({
            url: track.url,
            title: track.title,
            icon: track.icon,
            order: index,
          })),
        },
        bioTextEffectEnabled: data.text?.bioTextEffectEnabled ?? false,
        bioTextEffect: data.text?.bioTextEffect || "typewriter",
        bioTextEffectSpeed: data.text?.bioTextEffectSpeed || 50,
        avatarDecoration: data.avatarDecoration,
        discordStatusIndicatorEnabled:
          data.discord?.statusIndicatorEnabled ?? false,
        embedColor: data.profile.embedColor || "#f2108a",
        discordActivityDisplayType: data.discord?.activityDisplayType || "BOTH",
        discordActivityCompactMode: data.discord?.activityCompactMode ?? false,
      },
      update: {
        avatar: data.profile.avatar,
        banner: data.profile.banner,
        bio: sanitizeBio(data.profile.bio),
        glassEffect: data.container.glassEffect,
        themePrimaryColor: data.colors.primary,
        themeSecondaryColor: data.colors.secondary,
        audioTracks: {
          create: data.audio.tracks.map((track: any, index: number) => ({
            url: track.url,
            title: track.title,
            icon: track.icon,
            order: index,
          })),
        },
        bioTextEffectEnabled: data.text?.bioTextEffectEnabled ?? false,
        bioTextEffect: data.text?.bioTextEffect || "typewriter",
        bioTextEffectSpeed: data.text?.bioTextEffectSpeed || 50,
        avatarDecoration: data.avatarDecoration,
        discordStatusIndicatorEnabled:
          data.discord?.statusIndicatorEnabled ?? false,
        embedColor: data.profile.embedColor || "#f2108a",
        discordActivityDisplayType: data.discord?.activityDisplayType || "BOTH",
        discordActivityCompactMode: data.discord?.activityCompactMode ?? false,
      },
    });

    const response = NextResponse.json({ success: true });
    response.headers.set("x-user-id", session.user.id);
    return response;
  } catch (error) {
    console.error("Appearance update error:", error);
    return NextResponse.json(
      { error: "Failed to update appearance" },
      { status: 500 }
    );
  }
}

export const GET = withMetrics(handleGET);
export const PUT = withMetrics(handlePUT);
export const POST = withMetrics(handlePOST);
