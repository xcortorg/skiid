interface DiscordBadge {
  id: string;
  description: string;
  icon: string;
  link: string;
}

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
  detailed?: {
    user: {
      id: string;
      username: string;
      global_name: string;
      avatar: string;
      avatar_decoration_data: null | {
        asset: string;
        sku_id: string;
        expires_at: string | null;
      };
      discriminator: string;
      public_flags: number;
      banner: string | null;
      banner_color: string | null;
      accent_color: string | null;
      bio: string;
    };
    badges: {
      id: string;
      description: string;
      icon: string;
      link: string;
    }[];
    connected_accounts: any[];
    premium_type: number;
    premium_since: string;
    user_profile: any;
    guild_badges: any[];
    mutual_guilds: any[];
    cached: boolean;
    cache_time: number;
  };
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

export interface DetailedDiscordData {
  data: {
    user: {
      id: string;
      username: string;
      global_name: string;
      avatar: string;
      avatar_decoration_data?: {
        asset: string;
        sku_id: string;
        expires_at: null | string;
      };
    };
  };
  cached: boolean;
  cache_time: number;
}
