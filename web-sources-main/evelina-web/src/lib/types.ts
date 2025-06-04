export interface TeamMember {
  user_id: string;
  rank: string;
  socials: string | {
    custom?: string;
    github?: string;
    discord?: string;
    tiktok?: string;
    spotify?: string;
    youtube?: string;
    instagram?: string;
    snapchat?: string;
    steam?: string;
    soundcloud?: string;
  };
  user_data?: {
    activity?: {
      details: string;
      emoji: string;
      image: string;
      name: string;
      state: string;
    };
    avatar: string;
    banner: string;
    banner_color?: string;
    user: string;
  };
}