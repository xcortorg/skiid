import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { compare } from "bcrypt";
import { withMetrics } from "@/lib/api-wrapper";

async function handleGET(
  req: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const resolvedParams = await params;

    const userCheck = await db.user.findUnique({
      where: { username: resolvedParams.slug },
      select: {
        pinEnabled: true,
        pinHash: true,
        accountStatus: true,
      },
    });

    if (!userCheck) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    if (
      userCheck.accountStatus === "BANNED" ||
      userCheck.accountStatus === "DISABLED" ||
      userCheck.accountStatus === "RESTRICTED"
    ) {
      return NextResponse.json(
        {
          error: "This account has been suspended",
          status: userCheck.accountStatus,
        },
        { status: 403 }
      );
    }

    if (userCheck.pinEnabled) {
      const url = new URL(req.url);
      const pin = url.searchParams.get("pin");

      if (!pin) {
        return NextResponse.json(
          {
            error: "PIN required",
            pinProtected: true,
          },
          { status: 403 }
        );
      }

      const isValidPin = await compare(pin, userCheck.pinHash!);
      if (!isValidPin) {
        return NextResponse.json(
          {
            error: "Invalid PIN",
            pinProtected: true,
          },
          { status: 403 }
        );
      }
    }

    const user = await db.user.findUnique({
      where: { username: resolvedParams.slug },
      select: {
        id: true,
        username: true,
        name: true,
        image: true,
        createdAt: true,
        pageTitle: true,
        seoDescription: true,
        badges: true,
        appearance: {
          select: {
            avatar: true,
            avatarDecoration: true,
            bio: true,
            banner: true,
            layoutStyle: true,
            backgroundUrl: true,
            audioPlayerEnabled: true,
            audioTracks: {
              take: 3,
              select: {
                id: true,
                url: true,
                title: true,
                icon: true,
                order: true,
              },
              orderBy: {
                order: "asc",
              },
            },
            containerBackgroundColor: true,
            containerBackdropBlur: true,
            containerBorderColor: true,
            containerBorderWidth: true,
            containerBorderRadius: true,
            containerGlowColor: true,
            containerGlowIntensity: true,
            glassEffect: true,

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
            linksIconBgEnabled: true,
            linksCompactMode: true,
            linksDisableBackground: true,
            linksDisableHover: true,
            linksDisableBorder: true,

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

            discordActivityTextColor: true,
            discordActivityBgColor: true,
            discordActivityBorderStyle: true,
            discordStatusIndicatorSize: true,
            discordActivityLayout: true,
            discordAnimationsEnabled: true,
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

            tiltDisabled: true,
            discordServerInvite: true,

            displayName: true,
            bioTextEffectEnabled: true,
            bioTextEffect: true,
            bioTextEffectSpeed: true,
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
            embedColor: true,
            discordActivityDisplayType: true,
            discordActivityCompactMode: true,
          },
        },
        links: {
          take: 5,
          where: { enabled: true },
          orderBy: { position: "asc" },
          select: {
            id: true,
            title: true,
            url: true,
            clicks: true,
            position: true,
            enabled: true,
            iconUrl: true,
            backgroundColor: true,
            hoverColor: true,
            borderColor: true,
            gap: true,
            primaryTextColor: true,
            secondaryTextColor: true,
            hoverTextColor: true,
            textSize: true,
            iconSize: true,
            iconColor: true,
            iconBgColor: true,
            iconBorderRadius: true,
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

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    if (user.appearance) {
      user.appearance.clickEffectEnabled = true;
      user.appearance.audioTracks = user.appearance.audioTracks?.slice(0, 3);
    }
    if (user.links) {
      user.links = user.links.slice(0, 5);
    }

    return NextResponse.json({
      id: user.id,
      user: {
        name: user.appearance?.displayName || user.name || user.username,
        username: user.username,
      },
      badges: user.badges,
      bio: user.appearance?.bio || null,
      avatar: user.appearance?.avatar || null,
      avatarDecoration: user.appearance?.avatarDecoration || null,
      banner: user.appearance?.banner || null,
      createdAt: user.createdAt,
      pageTitle: user.pageTitle,
      seoDescription: user.seoDescription,
      appearance: {
        layoutStyle: user.appearance?.layoutStyle,
        backgroundUrl: user.appearance?.backgroundUrl,
        audioPlayerEnabled: user.appearance?.audioPlayerEnabled,
        audioTracks: user.appearance?.audioTracks || [],
        containerBackgroundColor: user.appearance?.containerBackgroundColor,
        containerBackdropBlur: user.appearance?.containerBackdropBlur,
        containerBorderColor: user.appearance?.containerBorderColor,
        containerBorderWidth: user.appearance?.containerBorderWidth,
        containerBorderRadius: user.appearance?.containerBorderRadius,
        containerGlowColor: user.appearance?.containerGlowColor,
        containerGlowIntensity: user.appearance?.containerGlowIntensity,
        glassEffect: user.appearance?.glassEffect,

        avatarSize: user.appearance?.avatarSize,
        avatarShowBorder: user.appearance?.avatarShowBorder,
        avatarBorderWidth: user.appearance?.avatarShowBorder
          ? user.appearance?.avatarBorderWidth
          : "0px",
        avatarBorderColor: user.appearance?.avatarBorderColor,
        avatarBorderRadius: user.appearance?.avatarBorderRadius,
        avatarGlowColor: user.appearance?.avatarGlowColor,
        avatarGlowIntensity: user.appearance?.avatarGlowIntensity,
        avatarAlignment: user.appearance?.avatarAlignment || "left",

        titleColor: user.appearance?.titleColor,
        titleSize: user.appearance?.titleSize,
        titleWeight: user.appearance?.titleWeight,
        usernameColor: user.appearance?.usernameColor,
        usernameSize: user.appearance?.usernameSize,
        bioColor: user.appearance?.bioColor,
        bioSize: user.appearance?.bioSize,

        linksBackgroundColor: user.appearance?.linksBackgroundColor,
        linksHoverColor: user.appearance?.linksHoverColor,
        linksBorderColor: user.appearance?.linksBorderColor,
        linksGap: user.appearance?.linksGap,
        linksPrimaryTextColor: user.appearance?.linksPrimaryTextColor,
        linksSecondaryTextColor: user.appearance?.linksSecondaryTextColor,
        linksHoverTextColor: user.appearance?.linksHoverTextColor,
        linksTextSize: user.appearance?.linksTextSize,
        linksIconSize: user.appearance?.linksIconSize,
        linksIconColor: user.appearance?.linksIconColor,
        linksIconBgColor: user.appearance?.linksIconBgColor,
        linksIconBorderRadius: user.appearance?.linksIconBorderRadius,
        linksIconBgEnabled: user.appearance?.linksIconBgEnabled ?? true,
        linksCompactMode: user.appearance?.linksCompactMode ?? false,
        linksDisableBackground:
          user.appearance?.linksDisableBackground ?? false,
        linksDisableHover: user.appearance?.linksDisableHover ?? false,
        linksDisableBorder: user.appearance?.linksDisableBorder ?? false,

        clickEffectEnabled: true,
        clickEffectText: user.appearance?.clickEffectText || "[ click ]",
        clickEffectColor: user.appearance?.clickEffectColor || "#ff3379",

        gradientEnabled: user.appearance?.gradientEnabled,
        gradientColor: user.appearance?.gradientColor,
        gradientType: user.appearance?.gradientType,
        gradientDirection: user.appearance?.gradientDirection,

        statsEnabled: user.appearance?.statsEnabled,
        statsColor: user.appearance?.statsColor,
        statsBgColor: user.appearance?.statsBgColor,

        font: user.appearance?.font,
        fontSize: user.appearance?.fontSize,
        fontWeight: user.appearance?.fontWeight,

        terminalFontFamily: user.appearance?.terminalFontFamily,
        terminalCursorStyle: user.appearance?.terminalCursorStyle,
        terminalCursorColor: user.appearance?.terminalCursorColor,
        terminalCursorBlinkSpeed: user.appearance?.terminalCursorBlinkSpeed,
        terminalTypingSpeed: user.appearance?.terminalTypingSpeed,
        terminalPromptSymbol: user.appearance?.terminalPromptSymbol,
        terminalHeaderControls: user.appearance?.terminalHeaderControls,
        terminalStatusBarEnabled: user.appearance?.terminalStatusBarEnabled,
        terminalLineNumbersEnabled: user.appearance?.terminalLineNumbersEnabled,

        themeAccentColor: user.appearance?.themeAccentColor,
        themePrimaryColor: user.appearance?.themePrimaryColor,
        themeSecondaryColor: user.appearance?.themeSecondaryColor,
        themeBackgroundColor: user.appearance?.themeBackgroundColor,

        discordActivityTextColor: user.appearance?.discordActivityTextColor,
        discordActivityBgColor: user.appearance?.discordActivityBgColor,
        discordActivityBorderStyle: user.appearance?.discordActivityBorderStyle,
        discordStatusIndicatorSize: user.appearance?.discordStatusIndicatorSize,
        discordActivityLayout: user.appearance?.discordActivityLayout,
        discordAnimationsEnabled: user.appearance?.discordAnimationsEnabled,
        discordPresenceBgColor: user.appearance?.discordPresenceBgColor,
        discordPresenceBorderColor: user.appearance?.discordPresenceBorderColor,
        discordPresenceAvatarSize: user.appearance?.discordPresenceAvatarSize,
        discordPresenceTextColor: user.appearance?.discordPresenceTextColor,
        discordPresenceSecondaryColor:
          user.appearance?.discordPresenceSecondaryColor,
        discordGuildBgColor: user.appearance?.discordGuildBgColor,
        discordGuildBorderColor: user.appearance?.discordGuildBorderColor,
        discordGuildAvatarSize: user.appearance?.discordGuildAvatarSize,
        discordGuildTitleColor: user.appearance?.discordGuildTitleColor,
        discordGuildButtonBgColor: user.appearance?.discordGuildButtonBgColor,
        discordGuildButtonHoverColor:
          user.appearance?.discordGuildButtonHoverColor,

        tiltDisabled: user.appearance?.tiltDisabled,
        discordServerInvite: user.appearance?.discordServerInvite,

        bioTextEffectEnabled: user.appearance?.bioTextEffectEnabled ?? false,
        bioTextEffect: user.appearance?.bioTextEffect || "typewriter",
        bioTextEffectSpeed: user.appearance?.bioTextEffectSpeed || 50,
        avatarDecoration: user.appearance?.avatarDecoration || null,
        discordStatusIndicatorEnabled:
          user.appearance?.discordStatusIndicatorEnabled ?? false,

        lastfmEnabled: user.appearance?.lastfmEnabled === true,
        lastfmCompactMode: user.appearance?.lastfmCompactMode ?? false,
        lastfmShowScrobbles: user.appearance?.lastfmShowScrobbles ?? true,
        lastfmShowTabs: user.appearance?.lastfmShowTabs ?? true,
        lastfmMaxTracks: user.appearance?.lastfmMaxTracks ?? 4,
        lastfmThemeColor: user.appearance?.lastfmThemeColor || "#f43f5e",
        lastfmBgColor: user.appearance?.lastfmBgColor || "rgba(0,0,0,0.4)",
        lastfmTextColor: user.appearance?.lastfmTextColor || "#ffffff",
        lastfmSecondaryColor:
          user.appearance?.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
        embedColor: user.appearance?.embedColor || "#f2108a",
        discordActivityDisplayType: user.appearance?.discordActivityDisplayType || "BOTH",
        discordActivityCompactMode: user.appearance?.discordActivityCompactMode ?? false,
      },
      links: user.links.map((link) => ({
        ...link,
        backgroundColor: link.backgroundColor,
        hoverColor: link.hoverColor,
        borderColor: link.borderColor,
        gap: link.gap,
        primaryTextColor: link.primaryTextColor,
        secondaryTextColor: link.secondaryTextColor,
        hoverTextColor: link.hoverTextColor,
        textSize: link.textSize,
        iconSize: link.iconSize,
        iconColor: link.iconColor,
        iconBgColor: link.iconBgColor,
        iconBorderRadius: link.iconBorderRadius,
      })),
      iconSettings: user.iconSettings,
    });
  } catch (error) {
    console.error("Error fetching profile:", error);
    return NextResponse.json(
      { error: "Failed to fetch profile" },
      { status: 500 }
    );
  }
}

export const GET = withMetrics(handleGET);
