import {
  IconBrandTwitter,
  IconBrandInstagram,
  IconBrandTiktok,
  IconBrandYoutube,
  IconBrandTwitch,
  IconBrandSpotify,
  IconBrandOnlyfans,
  IconBrandLinkedin,
  IconBrandGithub,
  IconBrandFacebook,
  IconBrandSnapchat,
  IconBrandDiscord,
  IconBrandTelegram,
  IconBrandPatreon,
  IconBrandKickstarter,
  IconBrandCashapp,
  IconBrandPaypal,
  IconWorld,
  IconMail,
  IconBrandX,
  IconBrandThreads,
} from "@tabler/icons-react";
import { IconProps } from "@tabler/icons-react";

export interface PresetLink {
  id: string;
  name: string;
  urlPrefix: string;
  category: string;
  icon: React.ComponentType<IconProps>;
}

export const PRESET_LINKS: PresetLink[] = [
  // unused for now
];

export const CATEGORIES = Array.from(
  new Set(PRESET_LINKS.map((link) => link.category)),
);
