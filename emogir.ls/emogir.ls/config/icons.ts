const CDN_BASE = "https://r.emogir.ls/assets/icons/svg";

export interface IconConfig {
  id: string;
  name: string;
  url: string;
  urlPrefix: string;
  category: string;
  iconUrl: string;
  type: "cdn";
}

export const SOCIAL_ICONS: IconConfig[] = [
  // Social
  {
    id: "x",
    name: "Twitter/X",
    url: "twitter.com",
    urlPrefix: "twitter.com/",
    category: "Social",
    iconUrl: `${CDN_BASE}/x.svg`,
    type: "cdn",
  },
  {
    id: "instagram",
    name: "Instagram",
    url: "instagram.com",
    urlPrefix: "instagram.com/",
    category: "Social",
    iconUrl: `${CDN_BASE}/instagram.svg`,
    type: "cdn",
  },
  {
    id: "threads",
    name: "Threads",
    url: "threads.net",
    urlPrefix: "threads.net/@",
    category: "Social",
    iconUrl: `${CDN_BASE}/threads.svg`,
    type: "cdn",
  },
  {
    id: "tiktok",
    name: "TikTok",
    url: "tiktok.com",
    urlPrefix: "tiktok.com/@",
    category: "Social",
    iconUrl: `${CDN_BASE}/tiktok.svg`,
    type: "cdn",
  },
  {
    id: "facebook",
    name: "Facebook",
    url: "facebook.com",
    urlPrefix: "facebook.com/",
    category: "Social",
    iconUrl: `${CDN_BASE}/facebook.svg`,
    type: "cdn",
  },
  {
    id: "snapchat",
    name: "Snapchat",
    url: "snapchat.com",
    urlPrefix: "snapchat.com/add/",
    category: "Social",
    iconUrl: `${CDN_BASE}/snapchat.svg`,
    type: "cdn",
  },

  // Content & Streaming
  {
    id: "youtube",
    name: "YouTube",
    url: "youtube.com",
    urlPrefix: "youtube.com/@",
    category: "Content",
    iconUrl: `${CDN_BASE}/youtube.svg`,
    type: "cdn",
  },
  {
    id: "twitch",
    name: "Twitch",
    url: "twitch.tv",
    urlPrefix: "twitch.tv/",
    category: "Content",
    iconUrl: `${CDN_BASE}/twitch.svg`,
    type: "cdn",
  },
  {
    id: "spotify",
    name: "Spotify",
    url: "spotify.com",
    urlPrefix: "open.spotify.com/user/",
    category: "Content",
    iconUrl: `${CDN_BASE}/spotify.svg`,
    type: "cdn",
  },

  // Gaming
  {
    id: "steam",
    name: "Steam",
    url: "steamcommunity.com",
    urlPrefix: "steamcommunity.com/id/",
    category: "Gaming",
    iconUrl: `${CDN_BASE}/steam.svg`,
    type: "cdn",
  },
  {
    id: "xbox",
    name: "Xbox",
    url: "xbox.com",
    urlPrefix: "xbox.com/profile/",
    category: "Gaming",
    iconUrl: `${CDN_BASE}/xbox.svg`,
    type: "cdn",
  },

  // Professional
  {
    id: "linkedin",
    name: "LinkedIn",
    url: "linkedin.com",
    urlPrefix: "linkedin.com/in/",
    category: "Professional",
    iconUrl: `${CDN_BASE}/linkedin.svg`,
    type: "cdn",
  },
  {
    id: "github",
    name: "GitHub",
    url: "github.com",
    urlPrefix: "github.com/",
    category: "Professional",
    iconUrl: `${CDN_BASE}/github.svg`,
    type: "cdn",
  },
  {
    id: "email",
    name: "Email",
    url: "mailto:",
    urlPrefix: "mailto:",
    category: "Professional",
    iconUrl: `${CDN_BASE}/email.svg`,
    type: "cdn",
  },

  // Communication
  {
    id: "discord",
    name: "Discord",
    url: "discord.gg",
    urlPrefix: "discord.gg/",
    category: "Communication",
    iconUrl: `${CDN_BASE}/discord.svg`,
    type: "cdn",
  },
  {
    id: "telegram",
    name: "Telegram",
    url: "t.me",
    urlPrefix: "t.me/",
    category: "Communication",
    iconUrl: `${CDN_BASE}/telegram.svg`,
    type: "cdn",
  },
  {
    id: "skype",
    name: "Skype",
    url: "skype.com",
    urlPrefix: "skype:",
    category: "Communication",
    iconUrl: `${CDN_BASE}/skype.svg`,
    type: "cdn",
  },
  {
    id: "wechat",
    name: "WeChat",
    url: "wechat",
    urlPrefix: "wechat:",
    category: "Communication",
    iconUrl: `${CDN_BASE}/wechat.svg`,
    type: "cdn",
  },

  // Payment
  {
    id: "paypal",
    name: "PayPal",
    url: "paypal.me",
    urlPrefix: "paypal.me/",
    category: "Payment",
    iconUrl: `${CDN_BASE}/paypal.svg`,
    type: "cdn",
  },
  {
    id: "bitcoin",
    name: "Bitcoin",
    url: "bitcoin:",
    urlPrefix: "bitcoin:",
    category: "Payment",
    iconUrl: `${CDN_BASE}/bitcoin.svg`,
    type: "cdn",
  },

  // Other
  {
    id: "mastodon",
    name: "Mastodon",
    url: "mastodon.social",
    urlPrefix: "@",
    category: "Other",
    iconUrl: `${CDN_BASE}/mastodon.svg`,
    type: "cdn",
  },
  {
    id: "bluesky",
    name: "Bluesky",
    url: "bsky.app",
    urlPrefix: "bsky.app/",
    category: "Other",
    iconUrl: `${CDN_BASE}/bluesky.svg`,
    type: "cdn",
  },
  {
    id: "lastfm",
    name: "Last.fm",
    url: "last.fm",
    urlPrefix: "last.fm/user/",
    category: "Other",
    iconUrl: `${CDN_BASE}/lastfm.svg`,
    type: "cdn",
  },
  {
    id: "reddit",
    name: "Reddit",
    url: "reddit.com",
    urlPrefix: "reddit.com/u/",
    category: "Other",
    iconUrl: `${CDN_BASE}/reddit.svg`,
    type: "cdn",
  },
  {
    id: "pinterest",
    name: "Pinterest",
    url: "pinterest.com",
    urlPrefix: "pinterest.com/",
    category: "Other",
    iconUrl: `${CDN_BASE}/pinterest.svg`,
    type: "cdn",
  },
  {
    id: "tumblr",
    name: "Tumblr",
    url: "tumblr.com",
    urlPrefix: "tumblr.com/",
    category: "Other",
    iconUrl: `${CDN_BASE}/tumblr.svg`,
    type: "cdn",
  },
];

export const CATEGORIES = Array.from(
  new Set(SOCIAL_ICONS.map((icon) => icon.category)),
);
