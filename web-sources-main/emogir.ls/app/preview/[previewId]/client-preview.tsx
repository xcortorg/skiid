// @ts-nocheck
"use client";

import { useState, useEffect } from "react";
import LayoutOne from "../../layouts/LayoutOne";
import LayoutTwo from "../../layouts/LayoutTwo";
import LayoutThree from "../../layouts/LayoutThree";
import LayoutConsole from "../../layouts/LayoutConsole";
import LayoutFemboy from "../../layouts/LayoutFemboy";
import { DiscordData } from "@/types/slugs";
import { notFound } from "next/navigation";
import {
  LayoutConsoleProps,
  LayoutFemboyProps,
  LayoutThreeProps,
  LayoutOneProps,
  LayoutTwoProps,
} from "@/types/slugs";

enum LayoutType {
  One = 1,
  Two = 2,
  Three = 3,
  Console = 4,
  Femboy = 5,
}

const getLayoutType = (layoutStyle: string): LayoutType => {
  switch (layoutStyle) {
    case "one":
      return LayoutType.One;
    case "two":
      return LayoutType.Two;
    case "three":
      return LayoutType.Three;
    case "console":
      return LayoutType.Console;
    case "femboy":
      return LayoutType.Femboy;
    case "modern":
      return LayoutType.Three;
    default:
      return LayoutType.Three;
  }
};

const transformUserDataForLayout = (
  userData: any,
  discordData: DiscordData | null,
  layoutType: LayoutType,
  previewData: any
) => {
  const baseUserData = {
    username: userData?.username || "",
    displayName: userData?.name || "",
    bio: userData?.bio || "",
    avatar: userData?.image || "",
    links: (userData?.links || []).map((link: any) => ({
      id: link.id || "",
      title: link.type || "",
      url: link.url || "",
      enabled: link.enabled || false,
      clicks: 0,
      position: 0,
      iconUrl: `https://r.emogir.ls/assets/icons/svg/${(
        link.type || "default"
      ).toLowerCase()}.svg`,
      backgroundColor: userData.appearance?.linksBackgroundColor,
      hoverColor: userData.appearance?.linksHoverColor,
      borderColor: userData.appearance?.linksBorderColor,
      gap: userData.appearance?.linksGap,
      primaryTextColor: userData.appearance?.linksPrimaryTextColor,
      secondaryTextColor: userData.appearance?.linksSecondaryTextColor,
      hoverTextColor: userData.appearance?.linksHoverTextColor,
      textSize: userData.appearance?.linksTextSize,
      iconSize: userData.appearance?.linksIconSize,
      iconColor: userData.appearance?.linksIconColor,
      iconBgColor: userData.appearance?.linksIconBgColor,
      iconBorderRadius: userData.appearance?.linksIconBorderRadius,
    })),
  };

  switch (layoutType) {
    case LayoutType.Console:
      return {
        ...baseUserData,
        location: userData?.location,
        timezone: userData?.timezone,
        languages: userData?.languages || [],
        skills: userData?.skills || [],
        projects: userData?.projects || [],
      };

    case LayoutType.Three:
      return {
        user: {
          id: userData?.id || "",
          name: previewData.profile?.displayName || userData?.name || "",
          avatar: previewData.profile?.avatar || userData?.image || null,
          banner: previewData.profile?.banner || null,
          created_at: userData?.createdAt || new Date().toISOString(),
        },
        links: (userData?.links || []).map((link: any) => ({
          id: link.id || "",
          title: link.type || "",
          url: link.url || "",
          enabled: link.enabled || false,
          clicks: 0,
          position: 0,
          iconUrl: `https://r.emogir.ls/assets/icons/svg/${(
            link.type || "default"
          ).toLowerCase()}.svg`,
          backgroundColor: previewData.links?.backgroundColor,
          hoverColor: previewData.links?.hoverColor,
          borderColor: previewData.links?.borderColor,
          gap: previewData.links?.gap,
          primaryTextColor: previewData.links?.primaryTextColor,
          secondaryTextColor: previewData.links?.secondaryTextColor,
          hoverTextColor: previewData.links?.hoverTextColor,
          textSize: previewData.links?.textSize,
          iconSize: previewData.links?.iconSize,
          iconColor: previewData.links?.iconColor,
          iconBgColor: previewData.links?.iconBgColor,
          iconBorderRadius: previewData.links?.iconBorderRadius,
        })),
        bio: previewData.profile?.bio || userData?.bio || "",
        effects: {
          tiltDisabled: previewData.effects?.tiltDisabled || false,
          clickEnabled: previewData.effects?.clickEnabled || false,
          clickText: previewData.effects?.clickText || "click",
          clickColor: previewData.effects?.clickColor || "#ffffff",
          gradientEnabled: previewData.effects?.gradientEnabled || false,
          gradientType: previewData.effects?.gradientType || "linear",
          gradientColors: previewData.effects?.gradientColors || [],
          gradientDirection:
            previewData.effects?.gradientDirection || "to-right",
        },
        background_url: previewData.container?.backgroundUrl || null,
        glass_effect: previewData.container?.glassEffect || false,
        audioPlayerEnabled: previewData.audio?.playerEnabled || false,
        audioTracks: previewData.audio?.tracks || [],
        click: {
          enabled: previewData.effects?.clickEnabled || false,
          text: previewData.effects?.clickText || "click",
        },
        clickEffectEnabled: previewData.effects?.clickEnabled || false,
        clickEffectColor: previewData.effects?.clickColor || "#ffffff",
        clickEffectText: previewData.effects?.clickText || "click",
        avatarDecoration: previewData.profile?.decoration || null,
        theme: previewData,
      };

    case LayoutType.Two:
      return {
        ...baseUserData,
        theme: {
          containerBackgroundColor:
            userData?.appearance?.containerBackgroundColor || "#141010",
          containerBackdropBlur:
            userData?.appearance?.containerBackdropBlur || "8px",
          containerBorderColor:
            userData?.appearance?.containerBorderColor || "#1a1a1a",
          containerBorderWidth:
            userData?.appearance?.containerBorderWidth || "1px",
          containerBorderRadius:
            userData?.appearance?.containerBorderRadius || "12px",
          containerGlowColor:
            userData?.appearance?.containerGlowColor || "#ff3379",
          containerGlowIntensity:
            userData?.appearance?.containerGlowIntensity || "0.3",
          avatarSize: userData?.appearance?.avatarSize || "96px",
          avatarBorderWidth: userData?.appearance?.avatarBorderWidth || "2px",
          avatarBorderColor:
            userData?.appearance?.avatarBorderColor || "#ff3379",
          avatarBorderRadius: userData?.appearance?.avatarBorderRadius || "50%",
          avatarGlowColor: userData?.appearance?.avatarGlowColor || "#ff3379",
          avatarGlowIntensity:
            userData?.appearance?.avatarGlowIntensity || "0.3",
          titleColor: userData?.appearance?.titleColor || "#ffffff",
          titleSize: userData?.appearance?.titleSize || "24px",
          titleWeight: userData?.appearance?.titleWeight || "600",
          usernameColor: userData?.appearance?.usernameColor || "#999999",
          usernameSize: userData?.appearance?.usernameSize || "16px",
          bioColor: userData?.appearance?.bioColor || "#cccccc",
          bioSize: userData?.appearance?.bioSize || "14px",
          backgroundUrl: userData?.appearance?.backgroundUrl || null,
          glassEffect: userData?.appearance?.glassEffect || false,
        },
      };

    case LayoutType.One:
      return {
        ...baseUserData,
        theme: {
          containerBackgroundColor:
            userData?.appearance?.containerBackgroundColor || "#141010",
          containerBackdropBlur:
            userData?.appearance?.containerBackdropBlur || "8px",
          containerBorderColor:
            userData?.appearance?.containerBorderColor || "#1a1a1a",
          containerBorderWidth:
            userData?.appearance?.containerBorderWidth || "1px",
          containerBorderRadius:
            userData?.appearance?.containerBorderRadius || "12px",
          containerGlowColor:
            userData?.appearance?.containerGlowColor || "#ff3379",
          containerGlowIntensity:
            userData?.appearance?.containerGlowIntensity || "0.3",
          avatarSize: userData?.appearance?.avatarSize || "96px",
          avatarBorderWidth: userData?.appearance?.avatarBorderWidth || "2px",
          avatarBorderColor:
            userData?.appearance?.avatarBorderColor || "#ff3379",
          avatarBorderRadius: userData?.appearance?.avatarBorderRadius || "50%",
          avatarGlowColor: userData?.appearance?.avatarGlowColor || "#ff3379",
          avatarGlowIntensity:
            userData?.appearance?.avatarGlowIntensity || "0.3",
          titleColor: userData?.appearance?.titleColor || "#ffffff",
          titleSize: userData?.appearance?.titleSize || "24px",
          titleWeight: userData?.appearance?.titleWeight || "600",
          usernameColor: userData?.appearance?.usernameColor || "#999999",
          usernameSize: userData?.appearance?.usernameSize || "16px",
          bioColor: userData?.appearance?.bioColor || "#cccccc",
          bioSize: userData?.appearance?.bioSize || "14px",
          backgroundUrl: userData?.appearance?.backgroundUrl || null,
          glassEffect: userData?.appearance?.glassEffect || false,
        },
      };

    case LayoutType.Femboy:
      return {
        ...baseUserData,
        theme: {
          containerBackgroundColor:
            userData?.appearance?.containerBackgroundColor || "#141010",
          containerBackdropBlur:
            userData?.appearance?.containerBackdropBlur || "8px",
          containerBorderColor:
            userData?.appearance?.containerBorderColor || "#1a1a1a",
          containerBorderWidth:
            userData?.appearance?.containerBorderWidth || "1px",
          containerBorderRadius:
            userData?.appearance?.containerBorderRadius || "12px",
          containerGlowColor:
            userData?.appearance?.containerGlowColor || "#ff3379",
          containerGlowIntensity:
            userData?.appearance?.containerGlowIntensity || "0.3",
          avatarSize: userData?.appearance?.avatarSize || "96px",
          avatarBorderWidth: userData?.appearance?.avatarBorderWidth || "2px",
          avatarBorderColor:
            userData?.appearance?.avatarBorderColor || "#ff3379",
          avatarBorderRadius: userData?.appearance?.avatarBorderRadius || "50%",
          avatarGlowColor: userData?.appearance?.avatarGlowColor || "#ff3379",
          avatarGlowIntensity:
            userData?.appearance?.avatarGlowIntensity || "0.3",
          titleColor: userData?.appearance?.titleColor || "#ffffff",
          titleSize: userData?.appearance?.titleSize || "24px",
          titleWeight: userData?.appearance?.titleWeight || "600",
          usernameColor: userData?.appearance?.usernameColor || "#999999",
          usernameSize: userData?.appearance?.usernameSize || "16px",
          bioColor: userData?.appearance?.bioColor || "#cccccc",
          bioSize: userData?.appearance?.bioSize || "14px",
          backgroundUrl: userData?.appearance?.backgroundUrl || null,
          glassEffect: userData?.appearance?.glassEffect || false,
        },
      };

    default:
      return baseUserData;
  }
};

export default function ClientPreview({
  previewData,
  userData,
}: {
  previewData: any;
  userData: any;
}) {
  const [discordData, setDiscordData] = useState<DiscordData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDiscordData = async () => {
      try {
        if (userData?.id) {
          const discordResponse = await fetch(
            `/api/account/discord/${userData.id}`
          );
          if (discordResponse.ok) {
            const discordData = await discordResponse.json();
            if (discordData?.id) {
              setDiscordData(discordData);
            }
          }
        }
      } catch (error) {
        console.error("Error fetching Discord data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchDiscordData();
  }, [userData]);

  if (loading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black/90">
        <div className="relative flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-full border-4 border-white/10 border-t-white/90 animate-spin" />
          <div className="text-white/60 text-sm font-medium animate-pulse">
            Loading preview...
          </div>
        </div>
      </div>
    );
  }

  if (!previewData) {
    notFound();
  }

  const layoutType = getLayoutType(previewData.selectedLayout || "three");

  const layoutThreeData = {
    user: {
      id: userData?.id || "",
      name: previewData.profile?.displayName || userData?.name || "",
      avatar: previewData.profile?.avatar || userData?.image || null,
      banner: previewData.profile?.banner || null,
      created_at: userData?.createdAt || new Date().toISOString(),
    },
    badges: userData?.badges || [],
    colors: {
      profile: {
        type: previewData.effects?.gradientEnabled ? "gradient" : "linear",
        linear_color: previewData.theme?.accentColor || "#ff3379",
        gradient_colors: previewData.effects?.gradientColors || [],
      },
      elements: {
        status: {
          type: "linear",
          color: previewData.theme?.accentColor || "#ff3379",
        },
        bio: {
          type: "linear",
          color: previewData.text?.bioColor || "#ffffff",
        },
      },
    },
    presence: {
      status: userData?.presence?.status || "offline",
      activities: userData?.presence?.activities || [],
    },
    discord_guild: {
      invite_url: previewData.discord?.serverInvite,
    },
    bio: previewData.profile?.bio || userData?.bio || "",
    background_url: previewData.container?.backgroundUrl || null,
    glass_effect: previewData.container?.glassEffect || false,
    audioPlayerEnabled: previewData.audio?.playerEnabled || false,
    audioTracks: previewData.audio?.tracks || [],
    click: {
      enabled: previewData.effects?.clickEnabled || false,
      text: previewData.effects?.clickText || "click",
    },
    clickEffectEnabled: previewData.effects?.clickEnabled || false,
    clickEffectColor: previewData.effects?.clickColor || "#ffffff",
    clickEffectText: previewData.effects?.clickText || "click",
    links: (userData?.links || []).map((link: any) => ({
      id: link.id || "",
      title: link.type || "",
      url: link.url || "",
      enabled: link.enabled || false,
      clicks: 0,
      position: 0,
      iconUrl: `https://r.emogir.ls/assets/icons/svg/${(
        link.type || "default"
      ).toLowerCase()}.svg`,
      backgroundColor: previewData.links?.backgroundColor,
      hoverColor: previewData.links?.hoverColor,
      borderColor: previewData.links?.borderColor,
      gap: previewData.links?.gap,
      primaryTextColor: previewData.links?.primaryTextColor,
      secondaryTextColor: previewData.links?.secondaryTextColor,
      hoverTextColor: previewData.links?.hoverTextColor,
      textSize: previewData.links?.textSize,
      iconSize: previewData.links?.iconSize,
      iconColor: previewData.links?.iconColor,
      iconBgColor: previewData.links?.iconBgColor,
      iconBorderRadius: previewData.links?.iconBorderRadius,
    })),
    theme: {
      effects: {
        clickEnabled: previewData.effects?.clickEnabled || false,
        clickText: previewData.effects?.clickText || "click",
        clickColor: previewData.effects?.clickColor || "#ff3379",
        gradientEnabled: previewData.effects?.gradientEnabled || false,
        gradientType: previewData.effects?.gradientType || "linear",
        gradientColors: previewData.effects?.gradientColors || [
          "#ff3379",
          "#ff6b3d",
        ],
        gradientDirection: previewData.effects?.gradientDirection || "to-right",
        tiltDisabled: previewData.effects?.tiltDisabled || false,
      },
      text: previewData.text || {},
      audio: previewData.audio || {},
      links: previewData.links || {},
      stats: previewData.stats || {},
      theme: previewData.theme || {},
      avatar: previewData.avatar || {},
      lastfm: previewData.lastfm || {},
      layout: previewData.layout || {},
      discord: previewData.discord || {},
      profile: previewData.profile || {},
      terminal: previewData.terminal || {},
      container: previewData.container || {},
      typography: previewData.typography || {},
      selectedLayout: previewData.selectedLayout || "modern",
    },
    avatarDecoration: previewData.profile?.decoration || null,
  };

  return (
    <div>
      <div className="fixed top-0 left-0 right-0 bg-black/80 p-3 z-50 flex items-center justify-between">
        <div className="text-sm">
          <span className="text-primary font-medium">Preview Mode</span>
          <span className="text-white/60 ml-2">
            This is a temporary preview of your appearance changes
          </span>
        </div>
        <div className="text-xs text-white/60">
          Close this tab when finished
        </div>
      </div>

      <div className="pt-14">
        {layoutType === LayoutType.Three && (
          <LayoutThree
            // @ts-ignore
            userData={layoutThreeData}
            discordData={discordData}
            slug={userData.username}
            theme={{
              layoutStyle: previewData.layout?.style || "modern",
              background_url: previewData.container?.backgroundUrl,
              audioPlayerEnabled: previewData.audio?.playerEnabled,
              audioTracks: previewData.audio?.tracks,
              containerBackgroundColor: previewData.theme?.backgroundColor,
              containerBackdropBlur: previewData.container?.backdropBlur,
              containerBorderColor: previewData.container?.borderColor,
              containerBorderWidth: previewData.container?.borderWidth,
              containerBorderRadius: previewData.container?.borderRadius,
              containerGlowColor: previewData.container?.glowColor,
              containerGlowIntensity: previewData.container?.glowIntensity,
              glassEffect: previewData.container?.glassEffect,
              avatarSize: previewData.avatar?.size,
              avatarShowBorder: previewData.avatar?.showBorder,
              avatarBorderWidth: previewData.avatar?.borderWidth,
              avatarBorderColor: previewData.avatar?.borderColor,
              avatarBorderRadius: previewData.avatar?.borderRadius,
              avatarGlowColor: previewData.avatar?.glowColor,
              avatarGlowIntensity: previewData.avatar?.glowIntensity,
              avatarAlignment: previewData.avatar?.alignment,
              titleColor: previewData.text?.titleColor,
              titleSize: previewData.text?.titleSize,
              titleWeight: previewData.text?.titleWeight,
              usernameColor: previewData.text?.usernameColor,
              usernameSize: previewData.text?.usernameSize,
              bioColor: previewData.text?.bioColor,
              bioSize: previewData.text?.bioSize,
              linksBackgroundColor: previewData.links?.backgroundColor,
              linksHoverColor: previewData.links?.hoverColor,
              linksBorderColor: previewData.links?.borderColor,
              linksGap: previewData.links?.gap,
              linksPrimaryTextColor: previewData.links?.primaryTextColor,
              linksSecondaryTextColor: previewData.links?.secondaryTextColor,
              linksHoverTextColor: previewData.links?.hoverTextColor,
              linksTextSize: previewData.links?.textSize,
              linksIconSize: previewData.links?.iconSize,
              linksIconColor: previewData.links?.iconColor,
              linksIconBgColor: previewData.links?.iconBgColor,
              linksIconBorderRadius: previewData.links?.iconBorderRadius,
              linksIconBgEnabled: previewData.links?.iconBgEnabled,
              linksCompactMode: previewData.links?.compactMode,
              linksDisableBackground: previewData.links?.disableBackground,
              linksDisableHover: previewData.links?.disableHover,
              linksDisableBorder: previewData.links?.disableBorder,
              tiltDisabled: previewData.effects?.tiltDisabled,
              clickEffectEnabled: previewData.effects?.clickEnabled,
              clickEffectText: previewData.effects?.clickText,
              clickEffectColor: previewData.effects?.clickColor,
              bioTextEffectEnabled: previewData.text?.bioTextEffectEnabled,
              bioTextEffect: previewData.text?.bioTextEffect,
              bioTextEffectSpeed: previewData.text?.bioTextEffectSpeed,
              discordPresenceAvatarSize:
                previewData.discord?.presenceAvatarSize,
              discordPresenceSecondaryColor:
                previewData.discord?.presenceSecondaryColor,
              discordPresenceTextColor: previewData.discord?.presenceTextColor,
              discordPresenceBgColor: previewData.discord?.presenceBgColor,
              discordPresenceBorderColor:
                previewData.discord?.presenceBorderColor,
              discordGuildAvatarSize: previewData.discord?.guildAvatarSize,
              discordGuildTitleColor: previewData.discord?.guildTitleColor,
              discordGuildButtonBgColor:
                previewData.discord?.guildButtonBgColor,
              discordGuildButtonHoverColor:
                previewData.discord?.guildButtonHoverColor,
              discordServerInvite: previewData.discord?.serverInvite,
              discordStatusIndicatorEnabled:
                previewData.discord?.statusIndicatorEnabled,
              discordStatusIndicatorSize:
                previewData.discord?.statusIndicatorSize,
              discordActivityLayout: previewData.discord?.activityLayout,
              discordActivityTextColor: previewData.discord?.activityTextColor,
              discordActivityBgColor: previewData.discord?.activityBgColor,
              discordActivityBorderStyle:
                previewData.discord?.activityBorderStyle,
              discordAnimationsEnabled: previewData.discord?.animationsEnabled,
              lastfmEnabled: previewData.lastfm?.enabled ?? false,
              lastfmCompactMode: previewData.lastfm?.compactMode ?? false,
              lastfmShowScrobbles: previewData.lastfm?.showScrobbles ?? true,
              lastfmShowTabs: previewData.lastfm?.showTabs ?? true,
              lastfmMaxTracks: previewData.lastfm?.maxTracks ?? 4,
              lastfmThemeColor: previewData.lastfm?.themeColor || "#f43f5e",
              lastfmBgColor: previewData.lastfm?.bgColor || "rgba(0,0,0,0.4)",
              lastfmTextColor: previewData.lastfm?.textColor || "#ffffff",
              lastfmSecondaryColor: previewData.lastfm?.secondaryColor || "rgba(255,255,255,0.6)",
            }}
          />
        )}
        {layoutType === LayoutType.Console && (
          <LayoutConsole
            userData={
              transformUserDataForLayout(
                { ...userData, appearance: previewData },
                discordData,
                layoutType,
                previewData
              ) as LayoutConsoleProps["userData"]
            }
            discordData={discordData}
            slug={userData.username}
            theme={previewData}
          />
        )}
        {layoutType === LayoutType.Femboy && (
          <LayoutFemboy
            userData={
              transformUserDataForLayout(
                { ...userData, appearance: previewData },
                discordData,
                layoutType,
                previewData
              ) as LayoutFemboyProps["userData"]
            }
            discordData={discordData}
            theme={previewData}
          />
        )}
        {layoutType === LayoutType.Two && (
          <LayoutTwo
            userData={
              transformUserDataForLayout(
                { ...userData, appearance: previewData },
                discordData,
                layoutType,
                previewData
              ) as LayoutTwoProps["userData"]
            }
            discordData={discordData}
            slug={userData.username}
            theme={previewData}
          />
        )}
        {layoutType === LayoutType.One && (
          <LayoutOne
            userData={
              transformUserDataForLayout(
                { ...userData, appearance: previewData },
                discordData,
                layoutType,
                previewData
              ) as LayoutOneProps["userData"]
            }
            discordData={discordData}
            slug={userData.username}
            theme={previewData}
          />
        )}
      </div>
    </div>
  );
}
