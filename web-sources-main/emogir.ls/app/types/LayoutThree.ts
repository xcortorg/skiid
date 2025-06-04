import { DiscordData } from "@/app/types/discord";

export interface LayoutThreeProps {
  userData: {
    user: {
      id: string;
      name: string;
      avatar: string;
      banner: string | null;
      created_at: string;
      avatar_decoration_data?: {
        asset: string;
      };
    };
    colors: {
      profile: {
        type: "linear" | "gradient";
        linear_color: string;
        gradient_colors: Array<{
          color: string;
          position: number;
        }>;
      };
      elements: {
        [key: string]: {
          type: "linear" | "gradient";
          color?: string;
          colors?: Array<{
            color: string;
            position: number;
          }>;
        };
      };
    };
    presence: {
      status: string;
      activities: Array<{
        name: string;
        type: string;
        details: string;
        state: string;
        emoji?: {
          name: string;
          id?: string;
          url?: string;
          unicode?: string;
        };
        application_id?: string;
        large_image?: string;
        small_image?: string;
        large_text?: string;
        small_text?: string;
        album_cover_url?: string;
        track_url?: string;
        duration?: number;
        start?: number;
        end?: number;
        timestamps?: {
          start: number;
          end: number;
        };
      }>;
    };

    bio: string;
    background_url: string | null;
    glass_effect: boolean;
    discord_guild?: {
      id: string;
      name: string;
      icon: string;
      description?: string;
      presence_count: number;
      member_count: number;
      invite_url: string;
    };
    click: {
      enabled: boolean;
      text: string;
    };
    audio?: {
      url: string;
      title?: string;
    };
    links: Array<{
      id: string;
      type: string;
      url: string;
      clicks: number;
      position: number;
      enabled: boolean;
      iconUrl: string;
      backgroundColor: string;
      hoverColor: string;
      borderColor: string;
      gap: string;
      primaryTextColor: string;
      secondaryTextColor: string;
      hoverTextColor: string;
      textSize: string;
      iconSize: string;
      iconColor: string;
      iconBgColor: string;
      iconBorderRadius: string;
    }>;
    audioTracks: Array<{
      url: string;
      title?: string;
      icon?: string;
    }>;
    audioPlayerEnabled: boolean;
    clickEffectEnabled: boolean;
    clickEffectColor: string;
    clickEffectText: string;
    badges?: Array<string>;
  };
  discordData: DiscordData | null;
  slug: string;
  theme?: {
    discordActivityCompactMode: string;
    discordStatusIndicatorEnabled: boolean;
    avatarDecoration: string;
    avatarAlignment: string;
    clickEffectEnabled: boolean;
    clickEffectColor: string;
    clickEffectText: string;
    layoutStyle: string;
    background_url: string;
    audioPlayerEnabled: boolean;
    audioTracks: Array<{
      id: string;
      url: string;
      title: string;
      icon: string;
      order: number;
    }>;
    containerBorderColor?: string;
    containerBackgroundColor?: string;
    linksIconColor?: string;
    tiltDisabled?: boolean;
    discordServerInvite?: string;
    container?: {
      backgroundColor?: string;
      backdropBlur?: string;
      borderColor?: string;
      borderWidth?: string;
      borderRadius?: string;
      glowColor?: string;
      glowIntensity?: string;
    };
    avatar?: {
      size?: string;
      borderWidth?: string;
      borderColor?: string;
      borderRadius?: string;
    };
    banner?: {
      height?: string;
      overlay?: string;
    };
    text?: {
      name?: {
        color?: string;
        size?: string;
        weight?: string;
      };
      bio?: {
        color?: string;
        size?: string;
      };
      status?: {
        color?: string;
        backgroundColor?: string;
      };
    };
    activity?: {
      backgroundColor?: string;
      borderColor?: string;
      textColor?: string;
      secondaryColor?: string;
      progressBar?: {
        backgroundColor?: string;
        fillColor?: string;
      };
    };
    socialIcons?: {
      backgroundColor?: string;
      hoverColor?: string;
      iconColor?: string;
      size?: string;
      borderRadius?: string;
    };
    discord?: {
      guild?: {
        backgroundColor?: string;
        borderColor?: string;
        avatar?: {
          size?: string;
          borderRadius?: string;
        };
        title?: {
          color?: string;
          size?: string;
          weight?: string;
        };
        badge?: {
          backgroundColor?: string;
          textColor?: string;
        };
        description?: {
          color?: string;
        };
        stats?: {
          color?: string;
          dotColor?: {
            online?: string;
            offline?: string;
          };
        };
        button?: {
          backgroundColor?: string;
          hoverColor?: string;
          textColor?: string;
        };
      };
    };
    links?: {
      backgroundColor?: string;
      hoverColor?: string;
      borderColor?: string;
      gap?: string;
      icon?: {
        backgroundColor?: string;
        size?: string;
        borderRadius?: string;
        color?: string;
        borderColor?: string;
        glow?: {
          color?: string;
          intensity?: string;
        };
      };
      text?: {
        primaryColor?: string;
        secondaryColor?: string;
        hoverColor?: string;
        size?: string;
      };
    };
    blurScreen?: {
      enabled?: boolean;
      text?: {
        content?: string;
        color?: string;
        size?: string;
        weight?: string;
        letterSpacing?: string;
        animation?: {
          type?: "none" | "flicker" | "pulse" | "bounce";
          speed?: "slow" | "normal" | "fast";
          intensity?: "light" | "medium" | "strong";
        };
      };
      backdrop?: {
        blur?: string;
        opacity?: string;
        color?: string;
      };
    };
    bioColor?: string;
    bioSize?: string;
    typography?: {
      font?: string;
      size?: string;
      weight?: string;
    };
    titleColor?: string;
    titleSize?: string;
    titleWeight?: string;
    avatarBorderRadius?: string;
    avatarShowBorder?: boolean;
    avatarBorderWidth?: string;
    avatarBorderColor?: string;
    avatarGlowColor?: string;
    avatarGlowIntensity?: string;
    discordPresenceBgColor?: string;
    discordPresenceBorderColor?: string;
    discordPresenceTextColor?: string;
    discordStatusIndicatorSize?: string;
    discordActivityBgColor?: string;
    discordActivityBorderStyle?: string;
    discordActivityTextColor?: string;
    discordPresenceSecondaryColor?: string;
    discordPresenceAvatarSize?: string;
    discordAnimationsEnabled?: boolean;
    discordActivityLayout?: string;
    discordActivityDisplayType?: "BOTH" | "DISCORD_INFO_ONLY" | "PRESENCE_INFO_ONLY";
    bioTextEffectEnabled?: boolean;
    bioTextEffect?: "typewriter" | "binary" | "glitch";
    bioTextEffectSpeed?: number;
    linksCompactMode?: boolean;
    linksIconBgEnabled?: boolean;
    linksDisableBackground?: boolean;
    linksDisableHover?: boolean;
    linksDisableBorder?: boolean;
    lastfmEnabled?: boolean;
    lastfmCompactMode?: boolean;
    lastfmShowScrobbles?: boolean;
    lastfmShowTabs?: boolean;
    lastfmMaxTracks?: number;
    lastfmThemeColor?: string;
    lastfmBgColor?: string;
    lastfmTextColor?: string;
    lastfmSecondaryColor?: string;
  };
}
