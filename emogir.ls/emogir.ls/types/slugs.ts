// Default

export interface DiscordData {
  type: number;
  code: string;
  guild?: {
    id: string;
    name: string;
    icon: string;
    description: string | null;
    features: string[];
    verification_level: number;
    premium_subscription_count: number;
  };
  approximate_member_count: number;
  approximate_presence_count: number;
  presence?: {
    user: {
      id: string;
      username: string;
      avatar: string;
      discriminator: string;
      status: "online" | "idle" | "dnd" | "offline";
    };
    activities?: {
      name: string;
      type: number;
      application_id?: string;
      state?: string;
      details?: string;
      timestamps?: {
        start?: number;
        end?: number;
      };
      assets?: {
        large_image?: string;
        large_text?: string;
        small_image?: string;
        small_text?: string;
      };
    }[];
  };
}

// Layout Console

export interface ConsoleTheme {
  container?: {
    backgroundColor?: string;
    textColor?: string;
    fontFamily?: string;
    cursorColor?: string;
    borderColor?: string;
    glassEffect?: boolean;
    blur?: string;
  };
  header?: {
    show?: boolean;
    title?: string;
    controls?: {
      show?: boolean;
      color1?: string;
      color2?: string;
      color3?: string;
    };
    borderColor?: string;
  };
  prompt?: {
    user?: string;
    symbol?: string;
    userColor?: string;
    pathColor?: string;
    symbolColor?: string;
  };
  cursor?: {
    style?: "block" | "line" | "underscore";
    blinkSpeed?: "slow" | "normal" | "fast";
    color?: string;
  };
  text?: {
    commands?: {
      color?: string;
      prefix?: string;
    };
    success?: {
      color?: string;
      prefix?: string;
    };
    error?: {
      color?: string;
      prefix?: string;
    };
    info?: {
      color?: string;
      prefix?: string;
    };
    links?: {
      color?: string;
      hoverColor?: string;
    };
  };
  animation?: {
    typingSpeed?: number;
    initialDelay?: number;
    lineDelay?: number;
    enabled?: boolean;
  };
  window?: {
    title?: string;
    titleAlignment?: "left" | "center" | "right";
    resizable?: boolean;
    minWidth?: number;
    minHeight?: number;
    defaultSize?: { width: number; height: number };
  };
  statusBar?: {
    show?: boolean;
    height?: number;
    backgroundColor?: string;
    textColor?: string;
    items?: {
      time?: boolean;
      systemInfo?: boolean;
      customText?: string;
    };
  };
  lineNumbers?: {
    show?: boolean;
    color?: string;
    backgroundColor?: string;
    width?: number;
  };
  tabs?: {
    show?: boolean;
    items?: string[];
    activeTab?: number;
    backgroundColor?: string;
    activeColor?: string;
    textColor?: string;
  };
}

export interface LayoutConsoleProps {
  userData: {
    username: string;
    displayName: string;
    bio: string;
    avatar: string;
    links: {
      id: number;
      title: string;
      url: string;
      iconUrl: string;
      clicks: number;
    }[];
    location?: string;
    timezone?: string;
    languages?: string[];
    skills?: string[];
    projects?: {
      name: string;
      description: string;
      url?: string;
    }[];
  };
  discordData: DiscordData | null;
  slug: string;
  theme?: ConsoleTheme;
}

// Layout Femboy

export interface LayoutFemboyProps {
  userData: {
    username: string;
    displayName: string;
    bio: string;
    avatar: string;
    links: {
      id: number;
      title: string;
      url: string;
      iconUrl: string;
      clicks: number;
    }[];
  };
  discordData: DiscordData | null;
  theme?: {
    primaryColor?: string;
    secondaryColor?: string;
    accentColor?: string;
    backgroundColor?: string;
  };
}

// Layout One

type ColorValue =
  | `#${string}`
  | `rgb(${string})`
  | `rgba(${string})`
  | `hsl(${string})`
  | `hsla(${string})`
  | string;

export interface UserData {
  username: string;
  displayName: string;
  bio: string;
  avatar: string;
  links: {
    id: number;
    title: string;
    url: string;
    iconUrl: string;
    clicks: number;
  }[];
}

export interface LayoutOneProps {
  userData: UserData;
  discordData: DiscordData | null;
  slug: string;
  theme?: {
    avatar?: {
      size?: string;
      borderWidth?: string;
      borderColor?: ColorValue;
      borderRadius?: string;
    };
    text?: {
      title?: {
        color?: ColorValue;
        size?: string;
        weight?: string;
      };
      username?: {
        color?: ColorValue;
      };
      bio?: {
        color?: ColorValue;
      };
    };
    button?: {
      backgroundColor?: ColorValue;
      textColor?: ColorValue;
    };
    discord?: {
      presence?: {
        backgroundColor?: ColorValue;
        borderColor?: ColorValue;
        avatar?: {
          size?: string;
          borderRadius?: string;
        };
        username?: {
          color?: ColorValue;
          secondaryColor?: ColorValue;
        };
        separator?: {
          color?: ColorValue;
          labelColor?: ColorValue;
          labelBg?: ColorValue;
        };
      };
      guild?: {
        backgroundColor?: ColorValue;
        borderColor?: ColorValue;
        avatar?: {
          size?: string;
          borderRadius?: string;
        };
        title?: {
          color?: ColorValue;
          size?: string;
          weight?: string;
        };
        button?: {
          backgroundColor?: ColorValue;
          hoverColor?: ColorValue;
        };
      };
    };
    links?: {
      backgroundColor?: ColorValue;
      hoverColor?: ColorValue;
      borderColor?: ColorValue;
      icon?: {
        backgroundColor?: ColorValue;
        size?: string;
        borderRadius?: string;
      };
      text?: {
        primaryColor?: ColorValue;
        secondaryColor?: ColorValue;
        hoverColor?: ColorValue;
      };
    };
    blurScreen?: {
      enabled?: boolean;
      backgroundColor?: ColorValue;
      textColor?: ColorValue;
      blur?: string;
      duration?: string;
      text?:
        | string
        | {
            content?: string;
            color?: ColorValue;
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
        color?: ColorValue;
      };
    };
  };
}

// Layout Three

export interface LayoutThreeProps {
  userData: {
    user: {
      id: string;
      name: string;
      avatar: string;
      banner: string | null;
      created_at: string;
    };
    badges: string[];
    colors: {
      profile: {
        type: "linear" | "gradient";
        linear_color: string;
        gradient_colors: any[];
      };
      elements: {
        [key: string]: {
          type: "linear" | "gradient";
          color?: string;
        };
      };
    };
    presence: {
      status: string;
      activities: any[];
    };
    discord_guild: {
      invite_url: string;
    };
    bio: string;
    background_url: string | null;
    glass_effect: boolean;
    audioPlayerEnabled: boolean;
    audioTracks: Array<{
      id: string;
      url: string;
      title: string;
      icon: string;
      order: number;
    }>;
    click: {
      enabled: boolean;
      text: string;
    };
    links: Array<{
      type: string;
      url: string;
      enabled: boolean;
    }>;
    theme: {
      effects: {
        tiltDisabled: boolean;
      };
      containerBackgroundColor: string;
      containerBackdropBlur: string;
      containerBorderColor: string;
      containerBorderWidth: string;
      containerBorderRadius: string;
      containerGlowColor: string;
      containerGlowIntensity: string;
      avatarSize: string;
      avatarBorderWidth: string;
      avatarBorderColor: string;
      avatarBorderRadius: string;
      avatarGlowColor: string;
      avatarGlowIntensity: string;
      titleColor: string;
      titleSize: string;
      titleWeight: string;
      usernameColor: string;
      usernameSize: string;
      bioColor: string;
      bioSize: string;
      linksBackgroundColor: string;
      linksHoverColor: string;
      linksBorderColor: string;
      linksGap: string;
      linksPrimaryTextColor: string;
      linksSecondaryTextColor: string;
      linksHoverTextColor: string;
      linksTextSize: string;
      linksIconSize: string;
      linksIconColor: string;
      linksIconBgColor: string;
      linksIconBorderRadius: string;
      font: string;
      fontSize: string;
      fontWeight: string;
      discordPresenceBgColor: string;
      discordPresenceBorderColor: string;
      discordPresenceAvatarSize: string;
      discordPresenceTextColor: string;
      discordPresenceSecondaryColor: string;
      discordGuildBgColor: string;
      discordGuildBorderColor: string;
      discordGuildAvatarSize: string;
      discordGuildTitleColor: string;
      discordGuildButtonBgColor: string;
      discordGuildButtonHoverColor: string;
      discordServerInvite: string;
    };
  };
  discordData: DiscordData | null;
  slug: string;
}

// Layout Two

export interface LayoutTwoProps {
  userData: UserData;
  discordData: DiscordData | null;
  slug: string;
  theme?: {
    container?: {
      backgroundColor?: ColorValue;
      backdropBlur?: string;
      borderColor?: ColorValue;
      borderWidth?: string;
      borderRadius?: string;
      glowColor?: ColorValue;
      glowIntensity?: string;
    };
    avatar?: {
      size?: string;
      borderWidth?: string;
      borderColor?: ColorValue;
      borderRadius?: string;
      glow?: {
        color?: ColorValue;
        intensity?: string;
      };
    };
    text?: {
      title?: {
        color?: ColorValue;
        size?: string;
        weight?: string;
      };
      username?: {
        color?: ColorValue;
        size?: string;
      };
      bio?: {
        color?: ColorValue;
        size?: string;
      };
    };
    badges?: {
      size?: string;
      gap?: string;
    };
    stats?: {
      color?: ColorValue;
      iconColor?: ColorValue;
      size?: string;
    };
    discord?: {
      presence?: {
        backgroundColor?: ColorValue;
        borderColor?: ColorValue;
        avatar?: {
          size?: string;
          borderRadius?: string;
        };
        text?: {
          primaryColor?: ColorValue;
          secondaryColor?: ColorValue;
        };
      };
      guild?: {
        backgroundColor?: ColorValue;
        borderColor?: ColorValue;
        avatar?: {
          size?: string;
          borderRadius?: string;
        };
        text?: {
          primaryColor?: ColorValue;
          secondaryColor?: ColorValue;
        };
        button?: {
          backgroundColor?: ColorValue;
          textColor?: ColorValue;
          hoverColor?: ColorValue;
        };
      };
    };
    links?: {
      backgroundColor?: ColorValue;
      hoverColor?: ColorValue;
      borderColor?: ColorValue;
      gap?: string;
      icon?: {
        backgroundColor?: ColorValue;
        borderColor?: ColorValue;
        size?: string;
        borderRadius?: string;
        color?: ColorValue;
        glow?: {
          color?: ColorValue;
          intensity?: string;
        };
      };
      text?: {
        primaryColor?: ColorValue;
        secondaryColor?: ColorValue;
        hoverColor?: ColorValue;
        size?: string;
      };
    };
    blurScreen?: {
      enabled?: boolean;
      text?:
        | string
        | {
            content?: string;
            color?: ColorValue;
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
        color?: ColorValue;
      };
    };
  };
}
