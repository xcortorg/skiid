"use client";

import { useState, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AppearanceForm } from "@/components/ui/appearance/appearance-form";
import type { AppearanceState } from "@/components/ui/appearance/appearance-form";
import {
  IconDeviceMobile,
  IconPhoto,
  IconPalette,
  IconTypography,
  IconChartArea,
  IconLink,
  IconIcons,
  IconBrandDiscord,
  IconTerminal,
  IconMusic,
  IconActivity,
  IconUser,
  IconServer,
  IconSearch,
  IconX,
  IconSparkles,
  IconTemplate,
  IconCopy,
  IconClock,
} from "@tabler/icons-react";
import { useToast } from "@/components/ui/toast-provider";
import { DataCard } from "@/components/ui/data-card";
import { Select } from "@/components/ui/appearance/select";
import { ColorPicker } from "@/components/ui/appearance/color-picker";
import { AppearanceSelect } from "@/components/ui/appearance/select";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import type { IconProps } from "@tabler/icons-react";
import { FileInput } from "@/components/ui/appearance/file-input";
import { MediaUpload } from "@/components/ui/appearance/media-upload";
import { AudioTracksManager } from "@/components/ui/appearance/audio-tracks-manager";
import { AppearancePreview } from "@/components/appearance/preview";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Image from "next/image";
import { DecorationDialog } from "@/components/ui/appearance/decoration-dialog";
import { PreviewSection } from "@/components/appearance/PreviewSection";
import { Label } from "@/components/ui/label";
type LayoutType = "modern" | "console" | "femboy" | "discord";

export default function AppearancePage() {
  const { toast } = useToast();
  const [state, setState] = useState<AppearanceState>({
    selectedLayout: "modern",
    profile: {
      displayName: "",
      bio: "",
      avatar: null,
      banner: null,
      decoration: null,
    },
    layout: {
      style: "modern",
    },
    container: {
      backgroundUrl: null,
      backdropBlur: "8px",
      borderWidth: "1px",
      borderRadius: "12px",
      glowIntensity: "0.3",
      glassEffect: true,
      backgroundColor: "#030303",
      borderColor: "#1a1a1a",
      glowColor: "#ff3379",
    },
    avatar: {
      size: "96px",
      borderWidth: "2px",
      borderColor: "#ff3379",
      borderRadius: "50%",
      glowColor: "#ff3379",
      glowIntensity: "0.3",
      showBorder: true,
      alignment: "left",
    },
    text: {
      titleColor: "#ffffff",
      titleSize: "24px",
      titleWeight: "600",
      usernameColor: "#999999",
      usernameSize: "16px",
      bioColor: "#cccccc",
      bioSize: "14px",
      bioTextEffectEnabled: false,
      bioTextEffect: "typewriter",
      bioTextEffectSpeed: 50,
    },
    links: {
      backgroundColor: "#1a1a1a",
      borderColor: "#333333",
      hoverColor: "#2a2a2a",
      gap: "8px",
      hoverTextColor: "#ffffff",
      textSize: "14px",
      iconSize: "20px",
      iconBgColor: "#333333",
      iconBorderRadius: "8px",
      primaryTextColor: "#ffffff",
      secondaryTextColor: "#999999",
      iconColor: "#ffffff",
      iconBgEnabled: true,
      compactMode: false,
      disableBackground: false,
      disableHover: false,
      disableBorder: false,
    },
    discord: {
      presenceAvatarSize: "32px",
      presenceSecondaryColor: "#999999",
      presenceBgColor: "#1a1a1a",
      presenceBorderColor: "#333333",
      presenceTextColor: "#ffffff",
      guildAvatarSize: "48px",
      guildBgColor: "#1a1a1a",
      guildBorderColor: "#333333",
      guildTitleColor: "#ffffff",
      guildButtonBgColor: "#333333",
      guildButtonHoverColor: "#444444",
      serverInvite: "",
      activityTextColor: "#ffffff",
      activityBgColor: "#000000",
      activityBorderStyle: "solid",
      activityLayout: "compact",
      animationsEnabled: true,
      statusIndicatorSize: "10px",
      statusIndicatorEnabled: true,
      activityDisplayType: "BOTH",
      activityCompactMode: false,
    },
    effects: {
      clickEnabled: true,
      clickText: "click",
      clickColor: "#ff3379",
      gradientEnabled: false,
      gradientColors: ["#ff3379", "#ff6b3d"],
      gradientType: "linear",
      gradientDirection: "to-right",
      tiltDisabled: false,
    },
    stats: {
      enabled: true,
      color: "#ffffff",
      bgColor: "#1a1a1a",
    },
    typography: {
      font: "inter",
      size: "md",
      weight: "normal",
    },
    terminal: {
      fontFamily: "monospace",
      cursorStyle: "block",
      cursorColor: "#00ff00",
      cursorBlinkSpeed: "normal",
      typingSpeed: 50,
      promptSymbol: "$",
      headerControls: true,
      statusBarEnabled: true,
      lineNumbersEnabled: true,
    },
    theme: {
      accentColor: "#ff3379",
      primaryColor: "#ffffff",
      secondaryColor: "#999999",
      backgroundColor: "#000000",
      borderColor: "#1a1a1a",
      textColor: "#ffffff",
      glowColor: "#ff3379",
    },
    audio: {
      tracks: [],
      playerEnabled: false,
    },
    lastfm: {
      enabled: true,
      compactMode: false,
      showScrobbles: true,
      showTabs: true,
      maxTracks: 4,
      themeColor: "#f43f5e",
      bgColor: "rgba(0,0,0,0.4)",
      textColor: "#ffffff",
      secondaryColor: "rgba(255,255,255,0.6)",
    },
    embedColor: "#f2108a",
  });

  const [isLoading, setIsLoading] = useState(false);
  const [selectedLayout, setSelectedLayout] = useState<LayoutType>("modern");
  const [uploading, setUploading] = useState(false);

  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const mainTabParam = searchParams.get("tab") || "general";
  const subTabParam = searchParams.get("subtab") || "profile";

  const [activeMainTab, setActiveMainTab] = useState(mainTabParam);
  const [activeSubTab, setActiveSubTab] = useState(subTabParam);

  const updateTabParams = useCallback(
    (tab: string, subtab?: string) => {
      const params = new URLSearchParams(searchParams);
      params.set("tab", tab);
      if (subtab) {
        params.set("subtab", subtab);
      }
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const handleMainTabChange = (tab: string) => {
    setActiveMainTab(tab);
    let defaultSubtab = "profile";
    if (tab === "typography") defaultSubtab = "typography";
    if (tab === "discord") defaultSubtab = "activity";
    if (tab === "links") defaultSubtab = "links";
    if (tab === "effects") defaultSubtab = "effects";
    if (tab === "extras") defaultSubtab = "stats";
    if (tab === "integrations") defaultSubtab = "integrations";

    setActiveSubTab(defaultSubtab);
    updateTabParams(tab, defaultSubtab);
  };

  const handleSubTabChange = (subtab: string) => {
    setActiveSubTab(subtab);
    updateTabParams(activeMainTab, subtab);
  };

  useEffect(() => {
    setActiveMainTab(mainTabParam);
    setActiveSubTab(subTabParam);
  }, [mainTabParam, subTabParam]);

  useEffect(() => {
    const fetchAppearance = async () => {
      try {
        const [appearanceResponse, linksResponse] = await Promise.all([
          fetch("/api/appearance"),
          fetch("/api/links/style"),
        ]);

        const appearanceData = await appearanceResponse.json();

        if (appearanceData) {
          setState((prev) => ({
            ...prev,
            profile: {
              displayName: appearanceData.displayName || "",
              bio: appearanceData.bio || "",
              avatar: appearanceData.avatar || null,
              banner: appearanceData.banner || null,
              decoration: appearanceData.avatarDecoration || null,
            },
            layout: {
              style: appearanceData.layoutStyle || "modern",
            },
            container: {
              backgroundUrl: appearanceData.backgroundUrl || null,
              backdropBlur: appearanceData.containerBackdropBlur || "8px",
              borderWidth: appearanceData.containerBorderWidth || "1px",
              borderRadius: appearanceData.containerBorderRadius || "12px",
              glowIntensity: appearanceData.containerGlowIntensity || "0.3",
              glassEffect: appearanceData.glassEffect || true,
              backgroundColor:
                appearanceData.containerBackgroundColor || "#030303",
              borderColor: appearanceData.containerBorderColor || "#1a1a1a",
              glowColor: appearanceData.containerGlowColor || "#ff3379",
            },
            avatar: {
              size: appearanceData.avatarSize || "96px",
              borderWidth: appearanceData.avatarBorderWidth || "2px",
              borderColor: appearanceData.avatarBorderColor || "#ff3379",
              borderRadius: appearanceData.avatarBorderRadius || "50%",
              glowColor: appearanceData.avatarGlowColor || "#ff3379",
              glowIntensity: appearanceData.avatarGlowIntensity || "0.3",
              showBorder: appearanceData.avatarShowBorder || true,
              alignment: appearanceData.avatarAlignment || "left",
            },
            text: {
              titleColor: appearanceData.titleColor || "#ffffff",
              titleSize: appearanceData.titleSize || "24px",
              titleWeight: appearanceData.titleWeight || "600",
              usernameColor: appearanceData.usernameColor || "#999999",
              usernameSize: appearanceData.usernameSize || "16px",
              bioColor: appearanceData.bioColor || "#cccccc",
              bioSize: appearanceData.bioSize || "14px",
              bioTextEffectEnabled:
                appearanceData.bioTextEffectEnabled ?? false,
              bioTextEffect: appearanceData.bioTextEffect || "typewriter",
              bioTextEffectSpeed: appearanceData.bioTextEffectSpeed || 50,
            },
            links: {
              backgroundColor: appearanceData.linksBackgroundColor || "#1a1a1a",
              hoverColor: appearanceData.linksHoverColor || "#2a2a2a",
              borderColor: appearanceData.linksBorderColor || "#333333",
              gap: appearanceData.linksGap || "8px",
              primaryTextColor:
                appearanceData.linksPrimaryTextColor || "#ffffff",
              secondaryTextColor:
                appearanceData.linksSecondaryTextColor || "#999999",
              hoverTextColor: appearanceData.linksHoverTextColor || "#ffffff",
              textSize: appearanceData.linksTextSize || "14px",
              iconSize: appearanceData.linksIconSize || "20px",
              iconColor: appearanceData.linksIconColor || "#ffffff",
              iconBgColor: appearanceData.linksIconBgColor || "#333333",
              iconBorderRadius: appearanceData.linksIconBorderRadius || "8px",
              iconBgEnabled: appearanceData.linksIconBgEnabled ?? true,
              compactMode: appearanceData.linksCompactMode || false,
              disableBackground: appearanceData.linksDisableBackground || false,
              disableHover: appearanceData.linksDisableHover || false,
              disableBorder: appearanceData.linksDisableBorder || false,
            },
            discord: {
              presenceAvatarSize:
                appearanceData.discordPresenceAvatarSize || "32px",
              presenceSecondaryColor:
                appearanceData.discordPresenceSecondaryColor || "#999999",
              presenceBgColor:
                appearanceData.discordPresenceBgColor || "#1a1a1a",
              presenceBorderColor:
                appearanceData.discordPresenceBorderColor || "#333333",
              presenceTextColor:
                appearanceData.discordPresenceTextColor || "#ffffff",
              guildAvatarSize: appearanceData.discordGuildAvatarSize || "48px",
              guildBgColor: appearanceData.discordGuildBgColor || "#1a1a1a",
              guildBorderColor:
                appearanceData.discordGuildBorderColor || "#333333",
              guildTitleColor:
                appearanceData.discordGuildTitleColor || "#ffffff",
              guildButtonBgColor:
                appearanceData.discordGuildButtonBgColor || "#333333",
              guildButtonHoverColor:
                appearanceData.discordGuildButtonHoverColor || "#444444",
              serverInvite: appearanceData.discordServerInvite || "",
              activityTextColor:
                appearanceData.discordActivityTextColor || "#ffffff",
              activityBgColor:
                appearanceData.discordActivityBgColor || "#000000",
              activityBorderStyle:
                appearanceData.discordActivityBorderStyle || "solid",
              activityLayout: appearanceData.discordActivityLayout || "compact",
              animationsEnabled:
                appearanceData.discordAnimationsEnabled || true,
              statusIndicatorSize:
                appearanceData.discordStatusIndicatorSize || "10px",
              statusIndicatorEnabled:
                appearanceData.discordStatusIndicatorEnabled ?? true,
              activityDisplayType:
                appearanceData.discordActivityDisplayType || "BOTH",
              activityCompactMode:
                appearanceData.discordActivityCompactMode || false,
            },
            effects: {
              clickEnabled: appearanceData.clickEffectEnabled,
              clickText: appearanceData.clickEffectText || "click",
              clickColor: appearanceData.clickEffectColor || "#ff3379",
              gradientEnabled: appearanceData.gradientEnabled || false,
              gradientColors: appearanceData.gradientColors
                ? JSON.parse(appearanceData.gradientColors)
                : ["#ff3379", "#ff6b3d"],
              gradientType: appearanceData.gradientType || "linear",
              gradientDirection: appearanceData.gradientDirection || "to-right",
              tiltDisabled: appearanceData.tiltDisabled || false,
            },
            stats: {
              enabled: appearanceData.statsEnabled || true,
              color: appearanceData.statsColor || "#ffffff",
              bgColor: appearanceData.statsBgColor || "#1a1a1a",
            },
            typography: {
              font: appearanceData.font || "inter",
              size: appearanceData.fontSize || "md",
              weight: appearanceData.fontWeight || "normal",
            },
            terminal: {
              fontFamily: appearanceData.terminalFontFamily || "monospace",
              cursorStyle: appearanceData.terminalCursorStyle || "block",
              cursorColor: appearanceData.terminalCursorColor || "#00ff00",
              cursorBlinkSpeed:
                appearanceData.terminalCursorBlinkSpeed || "normal",
              typingSpeed: appearanceData.terminalTypingSpeed || 50,
              promptSymbol: appearanceData.terminalPromptSymbol || "$",
              headerControls: appearanceData.terminalHeaderControls || true,
              statusBarEnabled: appearanceData.terminalStatusBarEnabled || true,
              lineNumbersEnabled:
                appearanceData.terminalLineNumbersEnabled || true,
            },
            theme: {
              accentColor: appearanceData.themeAccentColor || "#ff3379",
              primaryColor: appearanceData.themePrimaryColor || "#ffffff",
              secondaryColor: appearanceData.themeSecondaryColor || "#999999",
              backgroundColor: appearanceData.themeBackgroundColor || "#000000",
              borderColor: appearanceData.themeBorderColor || "#1a1a1a",
              textColor: appearanceData.themeTextColor || "#ffffff",
              glowColor: appearanceData.themeGlowColor || "#ff3379",
            },
            audio: {
              tracks: appearanceData.audioTracks || [],
              playerEnabled: appearanceData.audioPlayerEnabled ?? false,
            },
            lastfm: {
              enabled: appearanceData.lastfmEnabled ?? true,
              compactMode: appearanceData.lastfmCompactMode ?? false,
              showScrobbles: appearanceData.lastfmShowScrobbles ?? true,
              showTabs: appearanceData.lastfmShowTabs ?? true,
              maxTracks: appearanceData.lastfmMaxTracks || 4,
              themeColor: appearanceData.lastfmThemeColor || "#f43f5e",
              bgColor: appearanceData.lastfmBgColor || "rgba(0,0,0,0.4)",
              textColor: appearanceData.lastfmTextColor || "#ffffff",
              secondaryColor:
                appearanceData.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
            },
            embedColor: appearanceData.embedColor || "#f2108a",
          }));
        }
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to load appearance settings",
          variant: "error",
        });
      }
    };

    fetchAppearance();
  }, []);

  const handleChange = (path: string, value: any) => {
    setState((prev) => {
      const newState = { ...prev };
      const keys = path.split(".");
      let current: any = newState;

      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) {
          current[keys[i]] = {};
        }
        current = current[keys[i]];
      }

      current[keys[keys.length - 1]] = value;

      console.log(`Updating ${path} to:`, value);
      console.log("New state:", newState);

      return newState;
    });
  };

  const handleSave = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/appearance", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audioPlayerEnabled: state.audio.playerEnabled,
          audioTracks: state.audio.tracks,
          displayName: state.profile.displayName,
          bio: state.profile.bio,
          avatar: state.profile.avatar,
          banner: state.profile.banner,
          layoutStyle: state.layout.style,
          containerBackdropBlur: state.container.backdropBlur,
          containerBorderWidth: state.container.borderWidth,
          containerBorderRadius: state.container.borderRadius,
          containerGlowIntensity: state.container.glowIntensity,
          glassEffect: state.container.glassEffect,
          backgroundUrl: state.container.backgroundUrl,
          avatarSize: state.avatar.size,
          avatarBorderWidth: state.avatar.borderWidth,
          avatarBorderColor: state.avatar.borderColor,
          avatarBorderRadius: state.avatar.borderRadius,
          avatarGlowColor: state.avatar.glowColor,
          avatarGlowIntensity: state.avatar.glowIntensity,
          avatarShowBorder: state.avatar.showBorder,
          avatarAlignment: state.avatar.alignment,
          titleColor: state.text.titleColor,
          titleSize: state.text.titleSize,
          titleWeight: state.text.titleWeight,
          usernameColor: state.text.usernameColor,
          usernameSize: state.text.usernameSize,
          bioColor: state.text.bioColor,
          bioSize: state.text.bioSize,
          discordPresenceAvatarSize: state.discord.presenceAvatarSize,
          discordPresenceSecondaryColor: state.discord.presenceSecondaryColor,
          discordGuildAvatarSize: state.discord.guildAvatarSize,
          discordGuildTitleColor: state.discord.guildTitleColor,
          discordGuildButtonBgColor: state.discord.guildButtonBgColor,
          discordGuildButtonHoverColor: state.discord.guildButtonHoverColor,
          clickEffectEnabled: state.effects.clickEnabled,
          clickEffectText: state.effects.clickText,
          clickEffectColor: state.effects.clickColor,
          gradientEnabled: state.effects.gradientEnabled,
          gradientColors: JSON.stringify(state.effects.gradientColors),
          gradientType: state.effects.gradientType,
          gradientDirection: state.effects.gradientDirection,
          statsEnabled: state.stats.enabled,
          font: state.typography.font,
          fontSize: state.typography.size,
          fontWeight: state.typography.weight,
          terminalFontFamily: state.terminal.fontFamily,
          terminalCursorStyle: state.terminal.cursorStyle,
          terminalCursorColor: state.terminal.cursorColor,
          terminalCursorBlinkSpeed: state.terminal.cursorBlinkSpeed,
          terminalTypingSpeed: state.terminal.typingSpeed,
          terminalPromptSymbol: state.terminal.promptSymbol,
          terminalHeaderControls: state.terminal.headerControls,
          terminalStatusBarEnabled: state.terminal.statusBarEnabled,
          terminalLineNumbersEnabled: state.terminal.lineNumbersEnabled,
          themeAccentColor: state.theme.accentColor,
          themePrimaryColor: state.theme.primaryColor,
          themeSecondaryColor: state.theme.secondaryColor,
          themeBackgroundColor: state.theme.backgroundColor,
          themeBorderColor: state.theme.borderColor,
          themeTextColor: state.theme.textColor,
          themeGlowColor: state.theme.glowColor,
          tiltDisabled: state.effects.tiltDisabled,
          discordServerInvite: state.discord.serverInvite,
          linksBackgroundColor: state.links.backgroundColor,
          linksHoverColor: state.links.hoverColor,
          linksBorderColor: state.links.borderColor,
          linksGap: state.links.gap,
          linksPrimaryTextColor: state.links.primaryTextColor,
          linksSecondaryTextColor: state.links.secondaryTextColor,
          linksHoverTextColor: state.links.hoverTextColor,
          linksTextSize: state.links.textSize,
          linksIconSize: state.links.iconSize,
          linksIconColor: state.links.iconColor,
          linksIconBgColor: state.links.iconBgColor,
          linksIconBorderRadius: state.links.iconBorderRadius,
          linksIconBgEnabled: state.links.iconBgEnabled,
          linksCompactMode: state.links.compactMode,
          discordActivityTextColor: state.discord.activityTextColor,
          discordActivityBgColor: state.discord.activityBgColor,
          discordActivityBorderStyle: state.discord.activityBorderStyle,
          discordActivityLayout: state.discord.activityLayout,
          discordAnimationsEnabled: state.discord.animationsEnabled,
          discordStatusIndicatorSize: state.discord.statusIndicatorSize,
          discordStatusIndicatorEnabled: state.discord.statusIndicatorEnabled,
          bioTextEffectEnabled: state.text.bioTextEffectEnabled,
          bioTextEffect: state.text.bioTextEffect,
          bioTextEffectSpeed: state.text.bioTextEffectSpeed,
          avatarDecoration: state.profile.decoration,
          lastfmEnabled: state.lastfm.enabled,
          lastfmCompactMode: state.lastfm.compactMode,
          lastfmShowScrobbles: state.lastfm.showScrobbles,
          lastfmShowTabs: state.lastfm.showTabs,
          lastfmMaxTracks: state.lastfm.maxTracks,
          lastfmThemeColor: state.lastfm.themeColor,
          lastfmBgColor: state.lastfm.bgColor,
          lastfmTextColor: state.lastfm.textColor,
          lastfmSecondaryColor: state.lastfm.secondaryColor,
          embedColor: state.embedColor,
          discordActivityCompactMode: state.discord.activityCompactMode,
          discordActivityDisplayType: state.discord.activityDisplayType,
          statsColor: state.stats.color,
          statsBgColor: state.stats.bgColor,
          discordPresenceBgColor: state.discord.presenceBgColor,
          discordPresenceBorderColor: state.discord.presenceBorderColor,
          discordPresenceTextColor: state.discord.presenceTextColor,
          discordGuildBgColor: state.discord.guildBgColor,
          discordGuildBorderColor: state.discord.guildBorderColor,
          containerBackgroundColor: state.container.backgroundColor,
          containerBorderColor: state.container.borderColor,
          containerGlowColor: state.container.glowColor,
        }),
      });

      const linkStyleResponse = await fetch("/api/links/style", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          backgroundColor: state.links.backgroundColor,
          hoverColor: state.links.hoverColor,
          borderColor: state.links.borderColor,
          gap: state.links.gap,
          primaryTextColor: state.links.primaryTextColor,
          secondaryTextColor: state.links.secondaryTextColor,
          hoverTextColor: state.links.hoverTextColor,
          textSize: state.links.textSize,
          iconSize: state.links.iconSize,
          iconColor: state.links.iconColor,
          iconBgColor: state.links.iconBgColor,
          iconBorderRadius: state.links.iconBorderRadius,
          iconBgEnabled: state.links.iconBgEnabled,
          compactMode: state.links.compactMode,
        }),
      });

      if (!response.ok || !linkStyleResponse.ok) {
        const data = await response.json();
        const linkData = !linkStyleResponse.ok
          ? await linkStyleResponse.json()
          : null;

        if (data.errors) {
          data.errors.forEach((error: any) => {
            toast({
              title: "Error",
              description: `${error.message} [${error.code}]${
                error.value ? ` - Received: ${error.value}` : ""
              }`,
              variant: "error",
            });
          });
          return;
        }
        if (linkData?.errors) {
          linkData.errors.forEach((error: any) => {
            toast({
              title: "Error",
              description: `${error.message} [${error.code}]${
                error.value ? ` - Received: ${error.value}` : ""
              }`,
              variant: "error",
            });
          });
          return;
        }
        throw new Error();
      }

      toast({
        title: "Success",
        description: "Appearance settings saved successfully",
        variant: "success",
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to save appearance settings",
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const isSettingSupportedByLayout = (section: string): boolean => {
    const baseFeatures = [
      "container",
      "profile",
      "theme",
      "avatar",
      "text",
      "links",
      "effects",
      "stats",
      "typography",
      "layout",
    ];

    const layoutSpecialFeatures: Record<LayoutType, string[]> = {
      modern: [],
      console: ["terminal"],
      femboy: ["theme colors"],
      discord: ["discord presence", "discord guild"],
    };

    if (baseFeatures.includes(section.toLowerCase())) {
      return true;
    }

    return layoutSpecialFeatures[selectedLayout].includes(
      section.toLowerCase()
    );
  };

  const renderSettingCard = (
    title: string,
    icon: React.ComponentType<IconProps>,
    children: React.ReactNode
  ) => {
    const isSupported = isSettingSupportedByLayout(title.toLowerCase());

    return (
      <DataCard
        title={title}
        icon={icon}
        style={{
          backgroundColor: state.theme.backgroundColor,
          borderColor: state.theme.borderColor,
          color: state.theme.textColor,
        }}
      >
        <div className={cn("relative", !isSupported && "opacity-50")}>
          {!isSupported && (
            <div className="absolute inset-0 backdrop-blur-sm z-10 flex items-center justify-center">
              <div className="bg-black/80 px-4 py-2 rounded-lg text-sm">
                Not available in {selectedLayout} layout
              </div>
            </div>
          )}
          {children}
        </div>
      </DataCard>
    );
  };

  const [decorationDialogOpen, setDecorationDialogOpen] = useState(false);

  const handleDecorationSelect = (decoration: string) => {
    setState((prev) => ({
      ...prev,
      profile: {
        ...prev.profile,
        decoration,
      },
    }));
    setDecorationDialogOpen(false);
  };

  const [previewLink, setPreviewLink] = useState<string | null>(null);
  const [previewTimeRemaining, setPreviewTimeRemaining] = useState(0);

  return (
    <div className="flex flex-col lg:flex-row gap-6">
      <div className="w-full lg:flex-1 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Appearance</h1>
          <Button
            text="Save Changes"
            onClick={handleSave}
            loading={isLoading}
          />
        </div>

        <DataCard title="Layout Type" icon={IconDeviceMobile}>
          <div className="p-4 space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { id: "modern", label: "Modern", icon: IconDeviceMobile },
                {
                  id: "console",
                  label: "Console",
                  icon: IconTerminal,
                  disabled: true,
                },
                {
                  id: "femboy",
                  label: "Femboy",
                  icon: IconPalette,
                  disabled: true,
                },
                {
                  id: "discord",
                  label: "Discord",
                  icon: IconBrandDiscord,
                  disabled: true,
                },
              ].map((layout) => (
                <button
                  key={layout.id}
                  onClick={() => {
                    if (!layout.disabled) {
                      setSelectedLayout(layout.id as LayoutType);
                      setState((prev) => ({
                        ...prev,
                        layout: {
                          ...prev.layout,
                          style: layout.id,
                        },
                      }));
                    }
                  }}
                  disabled={layout.disabled}
                  className={cn(
                    "p-4 rounded-lg border-2 transition-all",
                    layout.disabled && "opacity-50 cursor-not-allowed",
                    selectedLayout === layout.id
                      ? "border-primary bg-primary/10"
                      : "border-primary/10 hover:border-primary/30"
                  )}
                >
                  <div className="flex flex-col items-center gap-2">
                    <layout.icon size={24} />
                    <span className="text-sm">{layout.label}</span>
                    {layout.disabled && (
                      <span className="text-xs text-white/60">Coming soon</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
            <p className="text-sm text-white/60">
              Note: Currently only the Modern layout is available.
            </p>
          </div>
        </DataCard>

        <div className="flex flex-col">
          <div className="flex flex-wrap justify-start mb-6 border-b border-gray-800 w-full overflow-x-auto">
            {[
              { id: "general", label: "General", icon: IconPhoto },
              { id: "typography", label: "Typography", icon: IconTypography },
              { id: "discord", label: "Discord", icon: IconBrandDiscord },
              { id: "links", label: "Links", icon: IconLink },
              { id: "effects", label: "Effects", icon: IconPalette },
              { id: "extras", label: "Extras", icon: IconChartArea },
              { id: "integrations", label: "Integrations", icon: IconMusic },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => handleMainTabChange(tab.id)}
                className={`flex items-center gap-2 px-4 sm:px-6 py-3 transition-all relative text-left whitespace-nowrap ${
                  activeMainTab === tab.id
                    ? "text-primary"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                <tab.icon
                  size={16}
                  className={activeMainTab === tab.id ? "text-primary" : ""}
                />
                <span className="hidden sm:inline">{tab.label}</span>
                {activeMainTab === tab.id && (
                  <div className="absolute bottom-0 left-0 w-full h-0.5 bg-primary" />
                )}
              </button>
            ))}
          </div>

          <div className="flex gap-6">
            {activeMainTab === "general" && (
              <div className="w-full">
                <div className="mb-6">
                  <div className="flex flex-wrap gap-2">
                    {[
                      { id: "profile", label: "Profile", icon: IconPhoto },
                      { id: "banner", label: "Banner", icon: IconPhoto },
                      { id: "theme", label: "Theme", icon: IconPalette },
                      { id: "avatar", label: "Avatar", icon: IconPhoto },
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => handleSubTabChange(tab.id)}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all ${
                          activeSubTab === tab.id
                            ? "bg-primary/10 text-primary"
                            : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
                        }`}
                      >
                        <tab.icon
                          size={18}
                          className={
                            activeSubTab === tab.id ? "text-primary" : ""
                          }
                        />
                        <span className="hidden sm:inline">{tab.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {activeSubTab === "profile" && (
                  <DataCard title="Profile" icon={IconPhoto}>
                    <div className="flex gap-4 items-start p-4">
                      <div className="relative">
                        <FileInput
                          accept="image/jpeg,image/png,image/webp"
                          value={state.profile.avatar}
                          disabled={uploading}
                          onValueChange={async (file) => {
                            if (!file) {
                              setState((prev) => ({
                                ...prev,
                                profile: { ...prev.profile, avatar: null },
                              }));
                              return;
                            }

                            try {
                              setUploading(true);
                              const formData = new FormData();
                              formData.append("file", file);

                              const response = await fetch(
                                "/api/upload/avatar",
                                {
                                  method: "POST",
                                  body: formData,
                                }
                              );

                              if (!response.ok)
                                throw new Error("Upload failed");

                              const data = await response.json();
                              setState((prev) => ({
                                ...prev,
                                profile: {
                                  ...prev.profile,
                                  avatar: data.url,
                                },
                              }));
                              toast({
                                title: "Success",
                                description: "Avatar uploaded successfully",
                                variant: "success",
                              });
                            } catch (error) {
                              toast({
                                title: "Error",
                                description: "Failed to upload avatar",
                                variant: "error",
                              });
                              console.error(error);
                            } finally {
                              setUploading(false);
                            }
                          }}
                        />
                      </div>
                      <div className="flex-1 space-y-3">
                        <input
                          type="text"
                          placeholder="Display Name"
                          className="w-full bg-black/20 border border-primary/10 rounded-lg px-3 py-2 text-sm"
                          value={state.profile.displayName}
                          onChange={(e) =>
                            handleChange("profile.displayName", e.target.value)
                          }
                        />
                        <textarea
                          placeholder="Bio"
                          rows={2}
                          className="w-full bg-black/20 border border-primary/10 rounded-lg px-3 py-2 text-sm resize-none"
                          value={state.profile.bio}
                          onChange={(e) =>
                            handleChange("profile.bio", e.target.value)
                          }
                        />
                      </div>
                    </div>
                  </DataCard>
                )}

                {activeSubTab === "banner" && selectedLayout === "modern" && (
                  <DataCard title="Banner" icon={IconPhoto} className="w-full">
                    <div className="p-4">
                      <MediaUpload
                        type="banner"
                        value={state.profile.banner}
                        onChange={(url) => handleChange("profile.banner", url)}
                      />
                    </div>
                  </DataCard>
                )}

                {activeSubTab === "theme" && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                    {renderSettingCard(
                      "Theme",
                      IconPalette,
                      <div className="p-4 space-y-4">
                        <ColorPicker
                          label="Brand Color"
                          value={state.theme.glowColor}
                          onChange={(color) =>
                            handleChange("theme.glowColor", color)
                          }
                        />
                        <ColorPicker
                          label="Background"
                          value={state.theme.backgroundColor}
                          onChange={(color) =>
                            handleChange("theme.backgroundColor", color)
                          }
                        />
                        <ColorPicker
                          label="Text Color"
                          value={state.text.titleColor}
                          onChange={(color) =>
                            handleChange("text.titleColor", color)
                          }
                        />
                        <ColorPicker
                          label="Border Color"
                          value={state.theme.borderColor}
                          onChange={(color) =>
                            handleChange("theme.borderColor", color)
                          }
                        />
                        <ColorPicker
                          label="Embed Color"
                          value={state.embedColor}
                          onChange={(color) =>
                            handleChange("embedColor", color)
                          }
                        />
                      </div>
                    )}

                    <DataCard title="Background" icon={IconPhoto}>
                      <div className="p-4 space-y-4">
                        <MediaUpload
                          type="background"
                          value={state.container.backgroundUrl}
                          onChange={(url) =>
                            handleChange("container.backgroundUrl", url)
                          }
                        />
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={state.container.glassEffect}
                            onCheckedChange={(value) =>
                              handleChange("container.glassEffect", value)
                            }
                          />
                          <label>Enable glass effect</label>
                        </div>
                      </div>
                    </DataCard>
                  </div>
                )}

                {activeSubTab === "avatar" && (
                  <DataCard title="Avatar" icon={IconPhoto} className="w-full">
                    <div className="p-4 space-y-4">
                      <Select
                        label="Roundness"
                        value={state.avatar.borderRadius}
                        onChange={(value) =>
                          handleChange("avatar.borderRadius", value)
                        }
                        options={[
                          { label: "Large", value: "50%" },
                          { label: "Medium", value: "25%" },
                          { label: "Small", value: "12.5%" },
                        ]}
                      />
                      <Select
                        label="Alignment"
                        value={state.avatar.alignment || "left"}
                        onChange={(value) =>
                          handleChange("avatar.alignment", value)
                        }
                        options={[
                          { label: "Left", value: "left" },
                          { label: "Center", value: "center" },
                          { label: "Right", value: "right" },
                        ]}
                      />

                      <div className="space-y-2">
                        <label className="text-sm font-medium">
                          Avatar Decoration
                        </label>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setDecorationDialogOpen(true)}
                            className="flex-1 flex items-center justify-between px-3 py-2 bg-black/20 border border-primary/10 rounded-lg text-sm"
                          >
                            <span>
                              {state.profile.decoration
                                ? state.profile.decoration
                                    .replace(".png", "")
                                    .split("_")
                                    .map(
                                      (word) =>
                                        word.charAt(0).toUpperCase() +
                                        word.slice(1)
                                    )
                                    .join(" ")
                                : "No decoration"}
                            </span>
                            <div className="flex items-center gap-2">
                              {state.profile.decoration && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleChange("profile.decoration", null);
                                  }}
                                  className="p-1 hover:bg-white/10 rounded-full"
                                >
                                  <IconX size={14} />
                                </button>
                              )}
                              <span className="text-xs text-white/60">
                                Select
                              </span>
                            </div>
                          </button>
                        </div>

                        {state.profile.decoration && (
                          <div className="relative w-24 h-24 mx-auto mt-4">
                            <div
                              className="w-24 h-24 overflow-hidden rounded-full"
                              style={{
                                borderRadius:
                                  state.avatar.borderRadius || "50%",
                              }}
                            >
                              {state.profile.avatar && (
                                <Image
                                  src={state.profile.avatar}
                                  alt="Avatar"
                                  width={96}
                                  height={96}
                                  className="w-full h-full object-cover"
                                />
                              )}
                            </div>
                            <Image
                              src={`/decorations/${state.profile.decoration}`}
                              alt="Decoration"
                              width={96}
                              height={96}
                              className="absolute -inset-0 w-full h-full scale-[1.2] pointer-events-none"
                            />
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <Switch
                          checked={state.avatar.showBorder}
                          onCheckedChange={(checked) =>
                            handleChange("avatar.showBorder", checked)
                          }
                        />
                        <label>Show Border</label>
                      </div>
                      {state.avatar.showBorder && (
                        <>
                          <Select
                            label="Border Width"
                            value={state.avatar.borderWidth}
                            onChange={(value) =>
                              handleChange("avatar.borderWidth", value)
                            }
                            options={[
                              { label: "Thin", value: "1px" },
                              { label: "Medium", value: "2px" },
                              { label: "Thick", value: "3px" },
                            ]}
                          />
                          <ColorPicker
                            label="Border Color"
                            value={state.avatar.borderColor}
                            onChange={(color) =>
                              handleChange("avatar.borderColor", color)
                            }
                          />
                          <ColorPicker
                            label="Glow Color"
                            value={state.avatar.glowColor}
                            onChange={(color) =>
                              handleChange("avatar.glowColor", color)
                            }
                          />
                          <Select
                            label="Glow Intensity"
                            value={state.avatar.glowIntensity}
                            onChange={(value) =>
                              handleChange("avatar.glowIntensity", value)
                            }
                            options={[
                              { label: "None", value: "0" },
                              { label: "Low", value: "0.3" },
                              { label: "Medium", value: "0.6" },
                              { label: "High", value: "0.9" },
                            ]}
                          />
                        </>
                      )}
                    </div>
                  </DataCard>
                )}
              </div>
            )}

            {activeMainTab === "typography" && (
              <div className="w-full">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                  {renderSettingCard(
                    "Typography",
                    IconTypography,
                    <div className="p-4 space-y-4">
                      <AppearanceSelect
                        label="Font"
                        value={state.typography.font}
                        onChange={(value) =>
                          handleChange("typography.font", value)
                        }
                        options={[
                          { label: "Satoshi", value: "satoshi" },
                          { label: "Inter", value: "inter" },
                          { label: "Outfit", value: "outfit" },
                          { label: "Space Grotesk", value: "space-grotesk" },
                          {
                            label: "Plus Jakarta Sans",
                            value: "plus-jakarta-sans",
                          },
                          { label: "Sora", value: "sora" },
                        ]}
                      />
                      <Select
                        label="Size"
                        value={state.typography.size}
                        onChange={(value) =>
                          handleChange("typography.size", value)
                        }
                        options={[
                          { label: "Small", value: "sm" },
                          { label: "Medium", value: "md" },
                          { label: "Large", value: "lg" },
                        ]}
                      />
                      <Select
                        label="Weight"
                        value={state.typography.weight}
                        onChange={(value) =>
                          handleChange("typography.weight", value)
                        }
                        options={[
                          { label: "Normal", value: "normal" },
                          { label: "Medium", value: "medium" },
                          { label: "Bold", value: "bold" },
                        ]}
                      />
                    </div>
                  )}

                  <DataCard title="Text" icon={IconTypography}>
                    <div className="p-4 space-y-4">
                      <ColorPicker
                        label="Title Color"
                        value={state.text.titleColor}
                        onChange={(color) =>
                          handleChange("text.titleColor", color)
                        }
                      />
                      <Select
                        label="Title Size"
                        value={state.text.titleSize}
                        onChange={(value) =>
                          handleChange("text.titleSize", value)
                        }
                        options={[
                          { label: "Small", value: "20px" },
                          { label: "Medium", value: "24px" },
                          { label: "Large", value: "28px" },
                        ]}
                      />
                      <ColorPicker
                        label="Bio Color"
                        value={state.text.bioColor}
                        onChange={(color) =>
                          handleChange("text.bioColor", color)
                        }
                      />
                      <Select
                        label="Bio Size"
                        value={state.text.bioSize}
                        onChange={(value) =>
                          handleChange("text.bioSize", value)
                        }
                        options={[
                          { label: "Small", value: "12px" },
                          { label: "Medium", value: "14px" },
                          { label: "Large", value: "16px" },
                        ]}
                      />
                      <div className="space-y-4 border-t border-white/10 pt-4">
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={state.text.bioTextEffectEnabled}
                            onCheckedChange={(value) =>
                              handleChange("text.bioTextEffectEnabled", value)
                            }
                          />
                          <label>Enable Bio Text Effect</label>
                        </div>

                        {state.text.bioTextEffectEnabled && (
                          <>
                            <Select
                              label="Effect Type"
                              value={state.text.bioTextEffect}
                              onChange={(value) =>
                                handleChange("text.bioTextEffect", value)
                              }
                              options={[
                                { label: "Typewriter", value: "typewriter" },
                                { label: "Binary", value: "binary" },
                                { label: "Glitch", value: "glitch" },
                              ]}
                            />

                            <div className="space-y-2">
                              <label className="text-sm font-medium">
                                Effect Speed
                              </label>
                              <input
                                type="range"
                                min="10"
                                max="200"
                                value={state.text.bioTextEffectSpeed}
                                onChange={(e) =>
                                  handleChange(
                                    "text.bioTextEffectSpeed",
                                    parseInt(e.target.value)
                                  )
                                }
                                className="w-full h-2 bg-black/20 rounded-lg appearance-none cursor-pointer accent-primary [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:appearance-none [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-primary [&::-moz-range-thumb]:border-0"
                              />
                              <div className="flex justify-between text-xs text-white/60">
                                <span>Fast</span>
                                <span>Slow</span>
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  </DataCard>
                </div>
              </div>
            )}

            {selectedLayout === "modern" && activeMainTab === "discord" && (
              <div className="w-full">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <DataCard title="Discord Activity" icon={IconActivity}>
                    <div className="p-4 space-y-4">
                      <h3 className="text-sm font-medium">Activity</h3>

                      <Select
                        label="Display Type"
                        value={state.discord.activityDisplayType || "BOTH"}
                        onChange={(value) =>
                          handleChange("discord.activityDisplayType", value)
                        }
                        options={[
                          { label: "Show Both", value: "BOTH" },
                          {
                            label: "Discord Info Only",
                            value: "DISCORD_INFO_ONLY",
                          },
                          {
                            label: "Presence Info Only",
                            value: "PRESENCE_INFO_ONLY",
                          },
                        ]}
                      />

                      <div className="flex items-center gap-2">
                        <Switch
                          checked={state.discord.statusIndicatorEnabled ?? true}
                          onCheckedChange={(value) =>
                            handleChange(
                              "discord.statusIndicatorEnabled",
                              value
                            )
                          }
                        />
                        <label>Show Status Indicator</label>
                      </div>
                      <ColorPicker
                        label="Text Color"
                        value={state.discord.activityTextColor}
                        onChange={(color) =>
                          handleChange("discord.activityTextColor", color)
                        }
                      />
                      <ColorPicker
                        label="Background Color"
                        value={state.discord.activityBgColor}
                        onChange={(color) =>
                          handleChange("discord.activityBgColor", color)
                        }
                      />
                      <Select
                        label="Border Style"
                        value={state.discord.activityBorderStyle}
                        onChange={(value) =>
                          handleChange("discord.activityBorderStyle", value)
                        }
                        options={[
                          { label: "Solid", value: "solid" },
                          { label: "Dashed", value: "dashed" },
                          { label: "Dotted", value: "dotted" },
                        ]}
                      />
                      <Select
                        label="Layout"
                        value={state.discord.activityLayout}
                        onChange={(value) =>
                          handleChange("discord.activityLayout", value)
                        }
                        options={[
                          { label: "Compact", value: "compact" },
                          { label: "Cozy", value: "cozy" },
                        ]}
                      />
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={state.discord.animationsEnabled}
                          onCheckedChange={(value) =>
                            handleChange("discord.animationsEnabled", value)
                          }
                        />
                        <label>Enable Animations</label>
                      </div>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div className="space-y-0.5">
                            <Label>Compact Activity</Label>
                            <p className="text-sm text-muted-foreground">
                              Display Discord activity in a more compact format
                            </p>
                          </div>
                          <Switch
                            checked={state.discord.activityCompactMode}
                            onCheckedChange={(checked) =>
                              handleChange(
                                "discord.activityCompactMode",
                                checked
                              )
                            }
                          />
                        </div>
                      </div>
                    </div>
                  </DataCard>

                  <DataCard title="Discord Presence" icon={IconUser}>
                    <div className="p-4 space-y-4">
                      <h3 className="text-sm font-medium">Presence</h3>
                      <ColorPicker
                        label="Background Color"
                        value={state.discord.presenceBgColor}
                        onChange={(color) =>
                          handleChange("discord.presenceBgColor", color)
                        }
                      />
                      <ColorPicker
                        label="Border Color"
                        value={state.discord.presenceBorderColor}
                        onChange={(color) =>
                          handleChange("discord.presenceBorderColor", color)
                        }
                      />
                      <Select
                        label="Avatar Size"
                        value={state.discord.presenceAvatarSize}
                        onChange={(value) =>
                          handleChange("discord.presenceAvatarSize", value)
                        }
                        options={[
                          { label: "Small", value: "34px" },
                          { label: "Medium", value: "46px" },
                          { label: "Large", value: "60px" },
                        ]}
                      />
                      <Select
                        label="Status Indicator Size"
                        value={state.discord.statusIndicatorSize}
                        onChange={(value) =>
                          handleChange("discord.statusIndicatorSize", value)
                        }
                        options={[
                          { label: "Small", value: "8px" },
                          { label: "Medium", value: "10px" },
                          { label: "Large", value: "12px" },
                        ]}
                      />
                      <ColorPicker
                        label="Text Color"
                        value={state.discord.presenceTextColor}
                        onChange={(color) =>
                          handleChange("discord.presenceTextColor", color)
                        }
                      />
                      <ColorPicker
                        label="Secondary Text Color"
                        value={state.discord.presenceSecondaryColor}
                        onChange={(color) =>
                          handleChange("discord.presenceSecondaryColor", color)
                        }
                      />
                    </div>
                  </DataCard>

                  <DataCard title="Discord Server" icon={IconServer}>
                    <div className="p-4 space-y-4">
                      <h3 className="text-sm font-medium">Server</h3>
                      <ColorPicker
                        label="Background Color"
                        value={state.discord.guildBgColor}
                        onChange={(color) =>
                          handleChange("discord.guildBgColor", color)
                        }
                      />
                      <ColorPicker
                        label="Border Color"
                        value={state.discord.guildBorderColor}
                        onChange={(color) =>
                          handleChange("discord.guildBorderColor", color)
                        }
                      />
                      <Select
                        label="Avatar Size"
                        value={state.discord.guildAvatarSize}
                        onChange={(value) =>
                          handleChange("discord.guildAvatarSize", value)
                        }
                        options={[
                          { label: "Small", value: "40px" },
                          { label: "Medium", value: "48px" },
                          { label: "Large", value: "56px" },
                        ]}
                      />
                      <ColorPicker
                        label="Title Color"
                        value={state.discord.guildTitleColor}
                        onChange={(color) =>
                          handleChange("discord.guildTitleColor", color)
                        }
                      />
                      <ColorPicker
                        label="Button Background"
                        value={state.discord.guildButtonBgColor}
                        onChange={(color) =>
                          handleChange("discord.guildButtonBgColor", color)
                        }
                      />
                      <ColorPicker
                        label="Button Hover"
                        value={state.discord.guildButtonHoverColor}
                        onChange={(color) =>
                          handleChange("discord.guildButtonHoverColor", color)
                        }
                      />
                      <div className="space-y-2">
                        <label className="text-sm font-medium">
                          Server Invite
                        </label>
                        <input
                          type="text"
                          placeholder="discord.gg/your-invite"
                          className="w-full bg-black/20 border border-primary/10 rounded-lg px-3 py-2 text-sm"
                          value={state.discord.serverInvite}
                          onChange={(e) =>
                            handleChange("discord.serverInvite", e.target.value)
                          }
                        />
                      </div>
                    </div>
                  </DataCard>
                </div>
              </div>
            )}

            {activeMainTab === "links" && (
              <div className="w-full">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                  <DataCard title="Links" icon={IconLink}>
                    <div className="p-4 space-y-4">
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={state.links.compactMode}
                          onCheckedChange={(value) =>
                            handleChange("links.compactMode", value)
                          }
                        />
                        <label>Compact Mode</label>
                      </div>

                      <div className="flex items-center gap-2">
                        <Switch
                          checked={state.links.iconBgEnabled}
                          onCheckedChange={(value) => {
                            console.log("Setting iconBgEnabled to:", value);
                            handleChange("links.iconBgEnabled", value);
                          }}
                        />
                        <label>Show Icon Background</label>
                      </div>

                      {state.links.compactMode && (
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={state.links.disableBackground}
                            onCheckedChange={(value) => {
                              handleChange("links.disableBackground", value);
                            }}
                          />
                          <label>Disable Background</label>
                        </div>
                      )}

                      <div className="flex items-center gap-2">
                        <Switch
                          checked={!state.links.disableHover}
                          onCheckedChange={(value) =>
                            handleChange("links.disableHover", !value)
                          }
                        />
                        <label>Show Hover Effect</label>
                      </div>

                      <div className="flex items-center gap-2">
                        <Switch
                          checked={!state.links.disableBorder}
                          onCheckedChange={(value) =>
                            handleChange("links.disableBorder", !value)
                          }
                        />
                        <label>Show Border</label>
                      </div>

                      {(!state.links.disableBackground ||
                        !state.links.compactMode) && (
                        <ColorPicker
                          label="Background Color"
                          value={state.links.backgroundColor}
                          onChange={(color) =>
                            handleChange("links.backgroundColor", color)
                          }
                        />
                      )}

                      {!state.links.disableHover && (
                        <ColorPicker
                          label="Hover Color"
                          value={state.links.hoverColor}
                          onChange={(color) =>
                            handleChange("links.hoverColor", color)
                          }
                        />
                      )}

                      {!state.links.disableBorder && (
                        <ColorPicker
                          label="Border Color"
                          value={state.links.borderColor}
                          onChange={(color) =>
                            handleChange("links.borderColor", color)
                          }
                        />
                      )}

                      <Select
                        label="Gap"
                        value={state.links.gap}
                        onChange={(value) => handleChange("links.gap", value)}
                        options={[
                          { label: "Small", value: "4px" },
                          { label: "Medium", value: "8px" },
                          { label: "Large", value: "12px" },
                        ]}
                      />

                      <ColorPicker
                        label="Primary Text Color"
                        value={state.links.primaryTextColor}
                        onChange={(color) =>
                          handleChange("links.primaryTextColor", color)
                        }
                      />
                      <ColorPicker
                        label="Secondary Text Color"
                        value={state.links.secondaryTextColor}
                        onChange={(color) =>
                          handleChange("links.secondaryTextColor", color)
                        }
                      />
                      <ColorPicker
                        label="Hover Text Color"
                        value={state.links.hoverTextColor}
                        onChange={(color) =>
                          handleChange("links.hoverTextColor", color)
                        }
                      />
                      <Select
                        label="Text Size"
                        value={state.links.textSize}
                        onChange={(value) =>
                          handleChange("links.textSize", value)
                        }
                        options={[
                          { label: "Small", value: "12px" },
                          { label: "Medium", value: "14px" },
                          { label: "Large", value: "16px" },
                        ]}
                      />
                    </div>
                  </DataCard>

                  <DataCard title="Link Icons" icon={IconIcons}>
                    <div className="p-4 space-y-4">
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={state.links.iconBgEnabled}
                          onCheckedChange={(value) =>
                            handleChange("links.iconBgEnabled", value)
                          }
                        />
                        <label>Show Icon Background</label>
                      </div>
                      <Select
                        label="Icon Size"
                        value={state.links.iconSize}
                        onChange={(value) =>
                          handleChange("links.iconSize", value)
                        }
                        options={[
                          { label: "Small", value: "16px" },
                          { label: "Medium", value: "20px" },
                          { label: "Large", value: "24px" },
                        ]}
                      />
                      <ColorPicker
                        label="Icon Color"
                        value={state.links.iconColor}
                        onChange={(color) =>
                          handleChange("links.iconColor", color)
                        }
                      />
                      {state.links.iconBgEnabled && (
                        <>
                          <ColorPicker
                            label="Icon Background"
                            value={state.links.iconBgColor}
                            onChange={(color) =>
                              handleChange("links.iconBgColor", color)
                            }
                          />
                          <Select
                            label="Icon Border Radius"
                            value={state.links.iconBorderRadius}
                            onChange={(value) =>
                              handleChange("links.iconBorderRadius", value)
                            }
                            options={[
                              { label: "None", value: "0px" },
                              { label: "Small", value: "4px" },
                              { label: "Medium", value: "8px" },
                              { label: "Large", value: "12px" },
                              { label: "Full", value: "9999px" },
                            ]}
                          />
                        </>
                      )}
                    </div>
                  </DataCard>
                </div>
              </div>
            )}

            {activeMainTab === "effects" && (
              <div className="w-full">
                <div className="space-y-6 w-full">
                  <DataCard title="Effects" icon={IconPalette}>
                    <div className="p-4 space-y-4">
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={state.effects.clickEnabled}
                          onCheckedChange={(value) =>
                            handleChange("effects.clickEnabled", value)
                          }
                        />
                        <label>Click Effect</label>
                      </div>
                      {state.effects.clickEnabled && (
                        <>
                          <input
                            type="text"
                            placeholder="Click Text"
                            className="w-full bg-black/20 border border-primary/10 rounded-lg px-3 py-2 text-sm"
                            value={state.effects.clickText}
                            onChange={(e) =>
                              handleChange("effects.clickText", e.target.value)
                            }
                          />
                          <ColorPicker
                            label="Click Color"
                            value={state.effects.clickColor}
                            onChange={(color) =>
                              handleChange("effects.clickColor", color)
                            }
                          />
                        </>
                      )}
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={state.effects.gradientEnabled}
                          onCheckedChange={(value) =>
                            handleChange("effects.gradientEnabled", value)
                          }
                        />
                        <label>Gradient Effect</label>
                      </div>
                      {state.effects.gradientEnabled && (
                        <>
                          <Select
                            label="Gradient Type"
                            value={state.effects.gradientType}
                            onChange={(value) =>
                              handleChange("effects.gradientType", value)
                            }
                            options={[
                              { label: "Linear", value: "linear" },
                              { label: "Radial", value: "radial" },
                            ]}
                          />
                          <Select
                            label="Direction"
                            value={state.effects.gradientDirection}
                            onChange={(value) =>
                              handleChange("effects.gradientDirection", value)
                            }
                            options={[
                              { label: "To Right", value: "to-right" },
                              { label: "To Bottom", value: "to-bottom" },
                              { label: "To Left", value: "to-left" },
                              { label: "To Top", value: "to-top" },
                            ]}
                          />
                        </>
                      )}
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={state.effects.tiltDisabled}
                          onCheckedChange={(value) =>
                            handleChange("effects.tiltDisabled", value)
                          }
                        />
                        <label>Disable Tilt Effect</label>
                      </div>
                    </div>
                  </DataCard>

                  {selectedLayout === "console" && (
                    <DataCard title="Terminal" icon={IconTerminal}>
                      <div className="p-4 space-y-4">
                        <input
                          type="text"
                          placeholder="Font Family"
                          className="w-full bg-black/20 border border-primary/10 rounded-lg px-3 py-2 text-sm"
                          value={state.terminal.fontFamily}
                          onChange={(e) =>
                            handleChange("terminal.fontFamily", e.target.value)
                          }
                        />
                        <Select
                          label="Cursor Style"
                          value={state.terminal.cursorStyle}
                          onChange={(value) =>
                            handleChange("terminal.cursorStyle", value)
                          }
                          options={[
                            { label: "Block", value: "block" },
                            { label: "Underline", value: "underline" },
                            { label: "Bar", value: "bar" },
                          ]}
                        />
                        <ColorPicker
                          label="Cursor Color"
                          value={state.terminal.cursorColor}
                          onChange={(color) =>
                            handleChange("terminal.cursorColor", color)
                          }
                        />
                        <Select
                          label="Cursor Blink Speed"
                          value={state.terminal.cursorBlinkSpeed}
                          onChange={(value) =>
                            handleChange("terminal.cursorBlinkSpeed", value)
                          }
                          options={[
                            { label: "Slow", value: "slow" },
                            { label: "Normal", value: "normal" },
                            { label: "Fast", value: "fast" },
                          ]}
                        />
                        <input
                          type="text"
                          placeholder="Prompt Symbol"
                          className="w-full bg-black/20 border border-primary/10 rounded-lg px-3 py-2 text-sm"
                          value={state.terminal.promptSymbol}
                          onChange={(e) =>
                            handleChange(
                              "terminal.promptSymbol",
                              e.target.value
                            )
                          }
                        />
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={state.terminal.headerControls}
                            onCheckedChange={(value) =>
                              handleChange("terminal.headerControls", value)
                            }
                          />
                          <label>Show Header Controls</label>
                        </div>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={state.terminal.statusBarEnabled}
                            onCheckedChange={(value) =>
                              handleChange("terminal.statusBarEnabled", value)
                            }
                          />
                          <label>Show Status Bar</label>
                        </div>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={state.terminal.lineNumbersEnabled}
                            onCheckedChange={(value) =>
                              handleChange("terminal.lineNumbersEnabled", value)
                            }
                          />
                          <label>Show Line Numbers</label>
                        </div>
                      </div>
                    </DataCard>
                  )}

                  {selectedLayout === "discord" && (
                    <DataCard title="Discord" icon={IconBrandDiscord}>
                      <div className="p-4 space-y-8">
                        <div className="space-y-4">
                          <h3 className="text-sm font-medium">Activity</h3>
                          <ColorPicker
                            label="Text Color"
                            value={state.discord.activityTextColor}
                            onChange={(color) =>
                              handleChange("discord.activityTextColor", color)
                            }
                          />
                          <ColorPicker
                            label="Background Color"
                            value={state.discord.activityBgColor}
                            onChange={(color) =>
                              handleChange("discord.activityBgColor", color)
                            }
                          />
                          <Select
                            label="Border Style"
                            value={state.discord.activityBorderStyle}
                            onChange={(value) =>
                              handleChange("discord.activityBorderStyle", value)
                            }
                            options={[
                              { label: "Solid", value: "solid" },
                              { label: "Dashed", value: "dashed" },
                              { label: "Dotted", value: "dotted" },
                            ]}
                          />
                          <Select
                            label="Layout"
                            value={state.discord.activityLayout}
                            onChange={(value) =>
                              handleChange("discord.activityLayout", value)
                            }
                            options={[
                              { label: "Compact", value: "compact" },
                              { label: "Cozy", value: "cozy" },
                            ]}
                          />
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={state.discord.animationsEnabled}
                              onCheckedChange={(value) =>
                                handleChange("discord.animationsEnabled", value)
                              }
                            />
                            <label>Enable Animations</label>
                          </div>
                        </div>

                        <div className="space-y-4 mt-6">
                          <h3 className="text-sm font-medium">Presence</h3>
                          <ColorPicker
                            label="Background Color"
                            value={state.discord.presenceBgColor}
                            onChange={(color) =>
                              handleChange("discord.presenceBgColor", color)
                            }
                          />
                          <ColorPicker
                            label="Border Color"
                            value={state.discord.presenceBorderColor}
                            onChange={(color) =>
                              handleChange("discord.presenceBorderColor", color)
                            }
                          />
                          <Select
                            label="Avatar Size"
                            value={state.discord.presenceAvatarSize}
                            onChange={(value) =>
                              handleChange("discord.presenceAvatarSize", value)
                            }
                            options={[
                              { label: "Small", value: "34px" },
                              { label: "Medium", value: "46px" },
                              { label: "Large", value: "60px" },
                            ]}
                          />
                          <Select
                            label="Status Indicator Size"
                            value={state.discord.statusIndicatorSize}
                            onChange={(value) =>
                              handleChange("discord.statusIndicatorSize", value)
                            }
                            options={[
                              { label: "Small", value: "8px" },
                              { label: "Medium", value: "10px" },
                              { label: "Large", value: "12px" },
                            ]}
                          />
                          <ColorPicker
                            label="Text Color"
                            value={state.discord.presenceTextColor}
                            onChange={(color) =>
                              handleChange("discord.presenceTextColor", color)
                            }
                          />
                          <ColorPicker
                            label="Secondary Text Color"
                            value={state.discord.presenceSecondaryColor}
                            onChange={(color) =>
                              handleChange(
                                "discord.presenceSecondaryColor",
                                color
                              )
                            }
                          />
                        </div>

                        <div className="space-y-4 mt-6">
                          <h3 className="text-sm font-medium">Server</h3>
                          <ColorPicker
                            label="Background Color"
                            value={state.discord.guildBgColor}
                            onChange={(color) =>
                              handleChange("discord.guildBgColor", color)
                            }
                          />
                          <ColorPicker
                            label="Border Color"
                            value={state.discord.guildBorderColor}
                            onChange={(color) =>
                              handleChange("discord.guildBorderColor", color)
                            }
                          />
                          <Select
                            label="Avatar Size"
                            value={state.discord.guildAvatarSize}
                            onChange={(value) =>
                              handleChange("discord.guildAvatarSize", value)
                            }
                            options={[
                              { label: "Small", value: "40px" },
                              { label: "Medium", value: "48px" },
                              { label: "Large", value: "56px" },
                            ]}
                          />
                          <ColorPicker
                            label="Title Color"
                            value={state.discord.guildTitleColor}
                            onChange={(color) =>
                              handleChange("discord.guildTitleColor", color)
                            }
                          />
                          <ColorPicker
                            label="Button Background"
                            value={state.discord.guildButtonBgColor}
                            onChange={(color) =>
                              handleChange("discord.guildButtonBgColor", color)
                            }
                          />
                          <ColorPicker
                            label="Button Hover"
                            value={state.discord.guildButtonHoverColor}
                            onChange={(color) =>
                              handleChange(
                                "discord.guildButtonHoverColor",
                                color
                              )
                            }
                          />
                          <div className="space-y-2">
                            <label className="text-sm font-medium">
                              Server Invite
                            </label>
                            <input
                              type="text"
                              placeholder="discord.gg/your-invite"
                              className="w-full bg-black/20 border border-primary/10 rounded-lg px-3 py-2 text-sm"
                              value={state.discord.serverInvite}
                              onChange={(e) =>
                                handleChange(
                                  "discord.serverInvite",
                                  e.target.value
                                )
                              }
                            />
                          </div>
                        </div>
                      </div>
                    </DataCard>
                  )}
                </div>
              </div>
            )}

            {activeMainTab === "extras" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <DataCard title="Stats" icon={IconChartArea}>
                  <div className="p-4 space-y-4">
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={state.stats.enabled}
                        onCheckedChange={(value: boolean) =>
                          handleChange("stats.enabled", value)
                        }
                      />
                      <label>Show Stats</label>
                    </div>

                    {state.stats.enabled && (
                      <>
                        <ColorPicker
                          label="Stats Text Color"
                          value={state.stats.color}
                          onChange={(color) =>
                            handleChange("stats.color", color)
                          }
                        />
                        <ColorPicker
                          label="Stats Background Color"
                          value={state.stats.bgColor}
                          onChange={(color) =>
                            handleChange("stats.bgColor", color)
                          }
                        />
                      </>
                    )}
                  </div>
                </DataCard>

                <DataCard title="Audio Player" icon={IconMusic}>
                  <div className="p-4 space-y-4">
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={state.audio.playerEnabled}
                        onCheckedChange={(value) =>
                          handleChange("audio.playerEnabled", value)
                        }
                      />
                      <label>Show Audio Player</label>
                    </div>

                    <AudioTracksManager
                      tracks={state.audio.tracks}
                      playerEnabled={state.audio.playerEnabled}
                      onTracksChange={(tracks) =>
                        handleChange("audio.tracks", tracks)
                      }
                      onPlayerEnabledChange={(enabled) =>
                        handleChange("audio.playerEnabled", enabled)
                      }
                    />
                    <p className="text-sm text-white/60">
                      These tracks will be available for playback on your
                      profile page.
                    </p>
                  </div>
                </DataCard>
              </div>
            )}

            {activeMainTab === "integrations" && (
              <div className="w-full">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                  <DataCard title="Last.fm Integration" icon={IconMusic}>
                    <div className="p-4 space-y-4">
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={state.lastfm.enabled}
                          onCheckedChange={(value) =>
                            handleChange("lastfm.enabled", value)
                          }
                        />
                        <label>Show Last.fm Widget</label>
                      </div>

                      {state.lastfm.enabled && (
                        <>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={state.lastfm.compactMode}
                              onCheckedChange={(value) =>
                                handleChange("lastfm.compactMode", value)
                              }
                            />
                            <label>Compact Mode</label>
                          </div>

                          <div className="flex items-center gap-2">
                            <Switch
                              checked={state.lastfm.showScrobbles}
                              onCheckedChange={(value) =>
                                handleChange("lastfm.showScrobbles", value)
                              }
                            />
                            <label>Show Scrobble Count</label>
                          </div>

                          {!state.lastfm.compactMode && (
                            <div className="flex items-center gap-2">
                              <Switch
                                checked={state.lastfm.showTabs}
                                onCheckedChange={(value) =>
                                  handleChange("lastfm.showTabs", value)
                                }
                              />
                              <label>Show Tabs (Recent/Top)</label>
                            </div>
                          )}

                          <Select
                            label="Maximum Tracks"
                            value={state.lastfm.maxTracks?.toString() || "4"}
                            onChange={(value) =>
                              handleChange("lastfm.maxTracks", parseInt(value))
                            }
                            options={[
                              { label: "2 Tracks", value: "2" },
                              { label: "3 Tracks", value: "3" },
                              { label: "4 Tracks", value: "4" },
                              { label: "5 Tracks", value: "5" },
                            ]}
                          />

                          <ColorPicker
                            label="Theme Color"
                            value={state.lastfm.themeColor || "#f43f5e"}
                            onChange={(color) =>
                              handleChange("lastfm.themeColor", color)
                            }
                          />

                          <ColorPicker
                            label="Background Color"
                            value={state.lastfm.bgColor || "rgba(0,0,0,0.4)"}
                            onChange={(color) =>
                              handleChange("lastfm.bgColor", color)
                            }
                          />

                          <ColorPicker
                            label="Text Color"
                            value={state.lastfm.textColor || "#ffffff"}
                            onChange={(color) =>
                              handleChange("lastfm.textColor", color)
                            }
                          />

                          <ColorPicker
                            label="Secondary Text Color"
                            value={
                              state.lastfm.secondaryColor ||
                              "rgba(255,255,255,0.6)"
                            }
                            onChange={(color) =>
                              handleChange("lastfm.secondaryColor", color)
                            }
                          />
                        </>
                      )}
                    </div>
                  </DataCard>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="hidden lg:block w-[450px] sticky top-6">
        <div className="space-y-4">
          <div className="bg-black/20 border border-primary/10 rounded-lg overflow-hidden">
            <div className="p-4 border-b border-primary/10 flex items-center justify-between">
              <h3 className="text-sm font-medium flex items-center gap-2">
                <IconSparkles size={16} className="text-primary" />
                Preview Options
              </h3>
            </div>

            <PreviewSection state={state} />
          </div>

          <div className="bg-black/20 border border-primary/10 rounded-lg overflow-hidden backdrop-blur-sm">
            <div className="p-4 border-b border-primary/10 flex items-center justify-between">
              <h3 className="text-sm font-medium flex items-center gap-2">
                <IconPalette size={16} className="text-primary" />
                Browse Templates
              </h3>
              <span className="text-xs px-2 py-1 bg-primary/20 text-primary rounded-full">
                Coming Soon
              </span>
            </div>

            <div className="p-6 flex flex-col items-center justify-center min-h-[200px] opacity-60">
              <div className="text-center space-y-4 max-w-xs mx-auto filter blur-[0.5px]">
                <IconTemplate size={48} className="mx-auto text-primary/30" />
                <h3 className="text-lg font-medium">Ready-made designs</h3>
                <p className="text-sm text-white/60">
                  Choose from a variety of professionally designed templates to
                  quickly style your profile.
                </p>
                <Button
                  text="Browse Templates"
                  className="w-full"
                  disabled={true}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <DecorationDialog
        open={decorationDialogOpen}
        onOpenChange={setDecorationDialogOpen}
        currentAvatar={state.profile.avatar}
        currentDecoration={state.profile.decoration}
        onSelect={handleDecorationSelect}
      />
    </div>
  );
}
