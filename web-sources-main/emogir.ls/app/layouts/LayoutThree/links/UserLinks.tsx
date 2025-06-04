import { motion } from "framer-motion";
import { IconExternalLink } from "@tabler/icons-react";
import React from "react";
import {
  FaTwitch,
  FaTiktok,
  FaGithub,
  FaSnapchat,
  FaReddit,
  FaPinterest,
  FaInstagram,
  FaTwitter,
  FaYoutube,
  FaTelegram,
  FaDiscord,
  FaLinkedin,
  FaMedium,
  FaSpotify,
  FaSoundcloud,
  FaBehance,
  FaDribbble,
  FaPatreon,
  FaEtsy,
  FaKickstarterK,
  FaImdb,
  FaVimeo,
  FaFlickr,
  FaGoodreads,
  FaLastfm,
  FaSteam,
  FaXbox,
  FaPlaystation,
  FaAmazon,
  FaWhatsapp,
  FaSkype,
  FaSlack,
  FaWeibo,
  FaLine,
  FaVk,
  FaGlobe,
  FaEnvelope,
} from "react-icons/fa";
import { SiKofi, SiBuymeacoffee, SiCashapp, SiVenmo } from "react-icons/si";
import { FaThreads, FaXTwitter } from "react-icons/fa6";
import { IconType } from "react-icons";

const getIcon = (type: string, url: string) => {
  if (!type) {
    return getFallbackIconFromUrl(url);
  }

  switch (type.toLowerCase()) {
    case "twitter":
      return FaXTwitter;
    case "github":
      return FaGithub;
    case "instagram":
      return FaInstagram;
    case "pinterest":
      return FaPinterest;
    case "reddit":
      return FaReddit;
    case "snapchat":
      return FaSnapchat;
    case "tiktok":
      return FaTiktok;
    case "twitch":
      return FaTwitch;
    case "youtube":
      return FaYoutube;
    case "telegram":
      return FaTelegram;
    case "discord":
      return FaDiscord;
    case "linkedin":
      return FaLinkedin;
    case "medium":
      return FaMedium;
    case "spotify":
      return FaSpotify;
    case "soundcloud":
      return FaSoundcloud;
    case "behance":
      return FaBehance;
    case "dribbble":
      return FaDribbble;
    case "patreon":
      return FaPatreon;
    case "etsy":
      return FaEtsy;
    case "kickstarter":
      return FaKickstarterK;
    case "imdb":
      return FaImdb;
    case "vimeo":
      return FaVimeo;
    case "flickr":
      return FaFlickr;
    case "goodreads":
      return FaGoodreads;
    case "lastfm":
      return FaLastfm;
    case "steam":
      return FaSteam;
    case "xbox":
      return FaXbox;
    case "playstation":
      return FaPlaystation;
    case "amazon":
      return FaAmazon;
    case "whatsapp":
      return FaWhatsapp;
    case "skype":
      return FaSkype;
    case "slack":
      return FaSlack;
    case "weibo":
      return FaWeibo;
    case "line":
      return FaLine;
    case "vk":
      return FaVk;
    case "threads":
      return FaThreads;
    case "kofi":
      return SiKofi;
    case "buymeacoffee":
      return SiBuymeacoffee;
    case "cashapp":
      return SiCashapp;
    case "venmo":
      return SiVenmo;
    case "twitter":
      return FaTwitter;
    default:
      return getFallbackIconFromUrl(url);
  }
};

const getFallbackIconFromUrl = (url: string): IconType => {
  if (!url) return FaGlobe;

  const urlLower = url.toLowerCase();

  if (
    urlLower.includes("mailto:") ||
    urlLower.includes("email") ||
    urlLower.includes("mail")
  ) {
    return FaEnvelope;
  }

  if (urlLower.includes("instagram.com")) return FaInstagram;
  if (urlLower.includes("twitter.com") || urlLower.includes("x.com"))
    return FaXTwitter;
  if (urlLower.includes("github.com")) return FaGithub;
  if (urlLower.includes("tiktok.com")) return FaTiktok;
  if (urlLower.includes("twitch.tv")) return FaTwitch;
  if (urlLower.includes("youtube.com") || urlLower.includes("youtu.be"))
    return FaYoutube;
  if (urlLower.includes("pinterest.com")) return FaPinterest;
  if (urlLower.includes("reddit.com")) return FaReddit;
  if (urlLower.includes("snapchat.com")) return FaSnapchat;
  if (urlLower.includes("telegram.me") || urlLower.includes("t.me"))
    return FaTelegram;
  if (urlLower.includes("discord.gg") || urlLower.includes("discord.com"))
    return FaDiscord;
  if (urlLower.includes("linkedin.com")) return FaLinkedin;
  if (urlLower.includes("medium.com")) return FaMedium;
  if (urlLower.includes("spotify.com")) return FaSpotify;
  if (urlLower.includes("soundcloud.com")) return FaSoundcloud;
  if (urlLower.includes("behance.net")) return FaBehance;
  if (urlLower.includes("dribbble.com")) return FaDribbble;
  if (urlLower.includes("patreon.com")) return FaPatreon;
  if (urlLower.includes("etsy.com")) return FaEtsy;
  if (urlLower.includes("kickstarter.com")) return FaKickstarterK;
  if (urlLower.includes("imdb.com")) return FaImdb;
  if (urlLower.includes("vimeo.com")) return FaVimeo;
  if (urlLower.includes("flickr.com")) return FaFlickr;
  if (urlLower.includes("goodreads.com")) return FaGoodreads;
  if (urlLower.includes("last.fm")) return FaLastfm;
  if (
    urlLower.includes("steamcommunity.com") ||
    urlLower.includes("steampowered.com")
  )
    return FaSteam;
  if (urlLower.includes("xbox.com")) return FaXbox;
  if (urlLower.includes("playstation.com")) return FaPlaystation;
  if (urlLower.includes("amazon.")) return FaAmazon;
  if (urlLower.includes("wa.me") || urlLower.includes("whatsapp.com"))
    return FaWhatsapp;
  if (urlLower.includes("skype.com")) return FaSkype;
  if (urlLower.includes("slack.com")) return FaSlack;
  if (urlLower.includes("weibo.com")) return FaWeibo;
  if (urlLower.includes("line.me")) return FaLine;
  if (urlLower.includes("vk.com")) return FaVk;
  if (urlLower.includes("ko-fi.com")) return SiKofi;
  if (urlLower.includes("buymeacoffee.com")) return SiBuymeacoffee;
  if (urlLower.includes("cash.app")) return SiCashapp;
  if (urlLower.includes("venmo.com")) return SiVenmo;

  return FaGlobe;
};

const safeColor = (color: string | undefined, defaultColor: string): string => {
  if (!color) return defaultColor;
  return color;
};

interface Link {
  type: string;
  url: string;
  enabled: boolean;
  backgroundColor?: string;
  borderColor?: string;
  hoverColor?: string;
  iconBgColor?: string;
  iconBorderRadius?: string;
  iconColor?: string;
  textSize?: string;
  primaryTextColor?: string;
  secondaryTextColor?: string;
  title: string;
  hoverTextColor?: string;
}

interface UserLinksProps {
  links: Link[];
  theme: any;
}

const getIconSizeClass = (size: string | undefined): string => {
  switch (size) {
    case "16px":
      return "w-4 h-4";
    case "20px":
      return "w-5 h-5";
    case "24px":
      return "w-6 h-6";
    default:
      return "w-5 h-5";
  }
};

export const UserLinks = ({ links, theme }: UserLinksProps) => {
  const normalizedTheme = {
    linksBackgroundColor:
      theme.linksBackgroundColor || theme.links?.backgroundColor,
    linksBorderColor: theme.linksBorderColor || theme.links?.borderColor,
    linksGap: theme.linksGap || theme.links?.gap,
    linksHoverColor: theme.linksHoverColor || theme.links?.hoverColor,
    linksHoverTextColor:
      theme.linksHoverTextColor || theme.links?.text?.hoverColor,
    linksIconBgColor:
      theme.linksIconBgColor || theme.links?.icon?.backgroundColor,
    linksIconBorderRadius:
      theme.linksIconBorderRadius || theme.links?.icon?.borderRadius,
    linksIconColor: theme.linksIconColor || theme.links?.icon?.color,
    linksIconSize: theme.linksIconSize || theme.links?.icon?.size,
    linksPrimaryTextColor:
      theme.linksPrimaryTextColor || theme.links?.text?.primaryColor,
    linksSecondaryTextColor:
      theme.linksSecondaryTextColor || theme.links?.text?.secondaryColor,
    linksTextSize: theme.linksTextSize || theme.links?.text?.size,
    linksIconBgEnabled: theme.linksIconBgEnabled ?? true,
    linksCompactMode: theme.linksCompactMode ?? false,
    linksDisableBackground: theme.linksDisableBackground ?? false,
    linksDisableHover: theme.linksDisableHover ?? false,
    linksDisableBorder: theme.linksDisableBorder ?? false,
  };

  if (normalizedTheme.linksCompactMode) {
    return (
      <div className="mt-6 flex flex-wrap justify-center gap-4">
        {links.map((link, index) => (
          <motion.a
            key={index}
            href={
              link.url.includes("mailto:")
                ? link.url.replace("https://mailto:", "mailto:")
                : link.url.startsWith("http")
                ? link.url
                : `https://${link.url}`
            }
            target={link.url.startsWith("mailto:") ? "_self" : "_blank"}
            rel="noopener noreferrer"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-center justify-center p-3 rounded-lg transition-all"
            style={{
              backgroundColor:
                normalizedTheme.linksDisableBackground === true
                  ? "transparent"
                  : link.backgroundColor ||
                    normalizedTheme.linksBackgroundColor,
              borderColor:
                normalizedTheme.linksDisableBorder === true
                  ? "transparent"
                  : link.borderColor || normalizedTheme.linksBorderColor,
              borderWidth:
                normalizedTheme.linksDisableBorder === true ? "0" : "1px",
            }}
            onMouseOver={(e) => {
              if (!normalizedTheme.linksDisableHover) {
                e.currentTarget.style.backgroundColor =
                  link.hoverColor || normalizedTheme.linksHoverColor;
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor =
                normalizedTheme.linksDisableBackground === true
                  ? "transparent"
                  : link.backgroundColor ||
                    normalizedTheme.linksBackgroundColor;
            }}
            title={link.title}
          >
            <div
              className={`flex items-center justify-center ${getIconSizeClass(
                normalizedTheme.linksIconSize
              )} ${normalizedTheme.linksIconBgEnabled ? "rounded-lg" : ""}`}
              style={{
                backgroundColor: normalizedTheme.linksIconBgEnabled
                  ? link.iconBgColor || normalizedTheme.linksIconBgColor
                  : "transparent",
                borderRadius: normalizedTheme.linksIconBgEnabled
                  ? link.iconBorderRadius ||
                    normalizedTheme.linksIconBorderRadius
                  : "0",
                padding: normalizedTheme.linksIconBgEnabled ? "8px" : "0",
              }}
            >
              {React.createElement(getIcon(link.type, link.url), {
                className: getIconSizeClass(normalizedTheme.linksIconSize),
                style: {
                  color: link.iconColor || normalizedTheme.linksIconColor,
                },
              })}
            </div>
          </motion.a>
        ))}
      </div>
    );
  }

  return (
    <div className="mt-6 flex flex-col gap-2">
      {links.map((link, index) => (
        <motion.a
          key={index}
          href={
            link.url.includes("mailto:")
              ? link.url.replace("https://mailto:", "mailto:")
              : link.url.startsWith("http")
              ? link.url
              : `https://${link.url}`
          }
          target={link.url.startsWith("mailto:") ? "_self" : "_blank"}
          rel="noopener noreferrer"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          className="flex items-center justify-between p-4 backdrop-blur-sm rounded-lg transition-all"
          style={{
            backgroundColor:
              link.backgroundColor || normalizedTheme.linksBackgroundColor,
            borderColor: link.borderColor || normalizedTheme.linksBorderColor,
            borderWidth: "1px",
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.backgroundColor =
              link.hoverColor || normalizedTheme.linksHoverColor;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor =
              link.backgroundColor || normalizedTheme.linksBackgroundColor;
          }}
        >
          <div className="flex items-center gap-3">
            <div
              className={`flex items-center justify-center ${getIconSizeClass(
                normalizedTheme.linksIconSize
              )} ${normalizedTheme.linksIconBgEnabled ? "rounded-lg" : ""}`}
              style={{
                backgroundColor: normalizedTheme.linksIconBgEnabled
                  ? link.iconBgColor || normalizedTheme.linksIconBgColor
                  : "transparent",
                borderRadius: normalizedTheme.linksIconBgEnabled
                  ? link.iconBorderRadius ||
                    normalizedTheme.linksIconBorderRadius
                  : "0",
                padding: normalizedTheme.linksIconBgEnabled ? "8px" : "0",
              }}
            >
              {React.createElement(getIcon(link.type, link.url), {
                className: getIconSizeClass(normalizedTheme.linksIconSize),
                style: {
                  color: link.iconColor || normalizedTheme.linksIconColor,
                },
              })}
            </div>
            <div className="flex flex-col">
              <span
                className={
                  link.textSize || normalizedTheme.linksTextSize || "text-sm"
                }
                style={{
                  color:
                    link.primaryTextColor ||
                    normalizedTheme.linksPrimaryTextColor,
                }}
              >
                {link.title}
              </span>
              <span
                className="text-xs"
                style={{
                  color:
                    link.secondaryTextColor ||
                    normalizedTheme.linksSecondaryTextColor,
                }}
              >
                {link.url}
              </span>
            </div>
          </div>
          <IconExternalLink
            className="w-4 h-4"
            style={{
              color: link.hoverTextColor || normalizedTheme.linksHoverTextColor,
            }}
          />
        </motion.a>
      ))}
    </div>
  );
};
