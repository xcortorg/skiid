"use client";

import {
  motion,
  useMotionValue,
  useTransform,
  useSpring,
  AnimatePresence,
} from "framer-motion";
import {
  Gamepad2,
  Music,
  Pause,
  Play,
  ExternalLink as IconExternalLink,
  Globe as IconGlobe,
  SkipBack,
  SkipForward,
  Clock,
  BarChart2,
  Disc,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import Image from "next/image";
import React from "react";
import { useEffect, useState } from "react";
import {
  FaGithub,
  FaGlobe,
  FaInstagram,
  FaPinterest,
  FaReddit,
  FaSnapchat,
  FaTiktok,
  FaTwitch,
  FaTwitter,
  FaYoutube,
} from "react-icons/fa";

import { DiscordGuild } from "./LayoutThree/guild/DiscordGuild";
import { UserLinks } from "./LayoutThree/links/UserLinks";
import { useToast } from "@/components/ui/toast-provider";
import { LayoutThreeProps } from "@/app/types/LayoutThree";

const statusColors = {
  online: "bg-green-500",
  idle: "bg-yellow-500",
  dnd: "bg-red-500",
  offline: "bg-gray-500",
} as const;

function getElementColor(colors: any, element: string) {
  const elementColor = colors.elements[element];
  if (elementColor.type === "linear") {
    return elementColor.color;
  } else {
    return `linear-gradient(to right, ${elementColor.colors
      .map((c: any) => `${c.color} ${c.position}%`)
      .join(", ")})`;
  }
}

function formatBio(bio: string): string {
  if (!bio) return "";

  const newlineCount = (bio.match(/\n/g) || []).length;

  let formattedBio = bio;

  if (newlineCount > 10) {
    formattedBio = bio.replace(/\n{2,}/g, "\n");

    if ((formattedBio.match(/\n/g) || []).length > 10) {
      const lines = formattedBio.split("\n");
      formattedBio = lines.slice(0, 10).join("\n");

      if (lines.length > 10) {
        formattedBio += "\n...";
      }
    }
  }

  if (formattedBio.length > 550) {
    formattedBio = formattedBio.substring(0, 547) + "...";
  }

  return formattedBio;
}

const safeColor = (color: string | undefined, defaultColor: string): string => {
  if (!color) return defaultColor;
  return color;
};

const flickerAnimation = `
    @keyframes textFlicker {
        0% { opacity: 1; }
        50% { opacity: 0.3; }
        100% { opacity: 1; }
    }
`;

const pulseAnimation = `
    @keyframes textPulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
`;

const bounceAnimation = `
    @keyframes textBounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
`;

const formatTrackTitle = (title: string) => {
  return title.replace(/\.(mp3|wav|mpeg|ogg|m4a|flac)$/i, "");
};

const calculateSpotifyProgress = (start: number, end: number) => {
  const now = Date.now() / 1000;
  const total = end - start;
  const current = now - start;
  return Math.min((current / total) * 100, 100);
};

const getFontFamily = (font: string) => {
  switch (font) {
    case "inter":
      return "var(--font-inter)";
    case "outfit":
      return "var(--font-outfit)";
    case "space-grotesk":
      return "var(--font-space-grotesk)";
    case "plus-jakarta-sans":
      return "var(--font-plus-jakarta-sans)";
    case "sora":
      return "var(--font-sora)";
    case "satoshi":
    default:
      return "inherit";
  }
};

const BioText = ({
  text,
  effect,
  speed,
  style,
  isBlurred,
}: {
  text: string;
  effect: string;
  speed: number;
  style: React.CSSProperties;
  isBlurred: boolean;
}) => {
  const [displayText, setDisplayText] = useState("");
  const fullText = text.replace(/<[^>]*>/g, "").trim();

  const containerStyle = {
    ...style,
    minHeight: "20px",
    display: "block",
    position: "relative" as const,
  };

  useEffect(() => {
    if (isBlurred) {
      setDisplayText("");
      return;
    }

    if (effect === "typewriter") {
      let currentLength = 0;
      let isTyping = true;

      const typewriter = () => {
        if (isTyping) {
          if (currentLength < fullText.length) {
            setDisplayText(fullText.slice(0, currentLength + 1));
            currentLength++;
            setTimeout(typewriter, speed);
          } else {
            setTimeout(() => {
              isTyping = false;
              typewriter();
            }, 1000);
          }
        } else {
          if (currentLength > 0) {
            setDisplayText(fullText.slice(0, currentLength - 1));
            currentLength--;
            setTimeout(typewriter, speed);
          } else {
            setTimeout(() => {
              isTyping = true;
              typewriter();
            }, 1000);
          }
        }
      };

      typewriter();
      return () => {
        currentLength = isTyping ? fullText.length : 0;
      };
    }

    if (effect === "binary") {
      let currentLength = 0;
      let isRevealing = true;

      const binary = () => {
        if (isRevealing) {
          if (currentLength < fullText.length) {
            setDisplayText((prev) => {
              const binaryPart = Array(fullText.length - currentLength)
                .fill(0)
                .map(() => (Math.random() > 0.5 ? "1" : "0"))
                .join("");
              return fullText.slice(0, currentLength + 1) + binaryPart;
            });
            currentLength++;
            setTimeout(binary, speed);
          } else {
            setTimeout(() => {
              isRevealing = false;
              binary();
            }, 1000);
          }
        } else {
          if (currentLength > 0) {
            setDisplayText((prev) => {
              const binaryPart = Array(currentLength)
                .fill(0)
                .map(() => (Math.random() > 0.5 ? "1" : "0"))
                .join("");
              return binaryPart + fullText.slice(currentLength);
            });
            currentLength--;
            setTimeout(binary, speed);
          } else {
            setTimeout(() => {
              isRevealing = true;
              binary();
            }, 1000);
          }
        }
      };

      binary();
      return () => {
        currentLength = isRevealing ? fullText.length : 0;
      };
    }

    if (effect === "glitch") {
      let currentLength = 0;
      let isRevealing = true;
      const glitchChars = "!@#$%^&*()_+-=[]{}|;:,.<>?";

      const glitch = () => {
        if (isRevealing) {
          if (currentLength < fullText.length) {
            setDisplayText((prev) => {
              const glitchPart = Array(fullText.length - currentLength)
                .fill(0)
                .map(
                  () =>
                    glitchChars[Math.floor(Math.random() * glitchChars.length)]
                )
                .join("");
              return fullText.slice(0, currentLength + 1) + glitchPart;
            });
            currentLength++;
            setTimeout(glitch, speed);
          } else {
            setTimeout(() => {
              isRevealing = false;
              glitch();
            }, 1000);
          }
        } else {
          if (currentLength > 0) {
            setDisplayText((prev) => {
              const glitchPart = Array(currentLength)
                .fill(0)
                .map(
                  () =>
                    glitchChars[Math.floor(Math.random() * glitchChars.length)]
                )
                .join("");
              return glitchPart + fullText.slice(currentLength);
            });
            currentLength--;
            setTimeout(glitch, speed);
          } else {
            setTimeout(() => {
              isRevealing = true;
              glitch();
            }, 1000);
          }
        }
      };

      glitch();
      return () => {
        currentLength = isRevealing ? fullText.length : 0;
      };
    }

    setDisplayText(fullText);
  }, [text, effect, speed, isBlurred]);

  return <div style={containerStyle}>{displayText || "\u00A0"}</div>;
};

const LastFmStats = ({
  username,
  theme,
}: {
  username: string;
  theme?: any;
}) => {
  const [lastfmData, setLastfmData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"recent" | "top">("recent");

  const isCompact = theme?.lastfmCompactMode || false;

  useEffect(() => {
    const fetchLastFmData = async () => {
      try {
        const response = await fetch(`/api/lastfm?slug=${username}`);
        if (!response.ok) {
          throw new Error("Failed to fetch Last.fm data");
        }
        const data = await response.json();
        setLastfmData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    if (username) {
      fetchLastFmData();
    }
  }, [username]);

  if (loading) {
    return (
      <div className="mt-6 p-4 bg-white/[0.02] rounded-xl border border-white/5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-white/10 animate-pulse"></div>
            <div className="h-4 w-24 bg-white/10 rounded animate-pulse"></div>
          </div>
          <div className="h-8 w-32 bg-white/5 rounded-full animate-pulse"></div>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-md bg-white/5 animate-pulse"></div>
              <div className="flex-1 space-y-2">
                <div className="h-3 w-3/4 bg-white/10 rounded animate-pulse"></div>
                <div className="h-2 w-1/2 bg-white/5 rounded animate-pulse"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (
    error ||
    !lastfmData ||
    (!lastfmData.recentTracks?.length && !lastfmData.topTracks?.length)
  ) {
    return (
      <div
        className="mt-6 overflow-hidden bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-xl border border-white/10"
        style={{ background: theme?.lastfmBgColor || "rgba(0,0,0,0.4)" }}
      >
        <div className="p-4 flex flex-col items-center justify-center text-center">
          <div
            className="w-12 h-12 rounded-full bg-pink-500/20 flex items-center justify-center mb-3"
            style={{
              backgroundColor: `${theme?.lastfmThemeColor || "#f43f5e"}20`,
            }}
          >
            <Music
              className="w-6 h-6 text-pink-400"
              style={{ color: theme?.lastfmThemeColor || "#f43f5e" }}
            />
          </div>
          <h3
            className="text-sm font-medium mb-1"
            style={{ color: theme?.lastfmTextColor || "#ffffff" }}
          >
            No Last.fm Data
          </h3>
          <p
            className="text-xs max-w-[250px]"
            style={{
              color: theme?.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
            }}
          >
            No recent tracks found. The user may not have connected their
            Last.fm account or hasn't scrobbled any tracks recently. You can
            connect Last.fm as an Integration in your Emogir.ls settings.
          </p>
          <a
            href="https://www.last.fm/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-1 text-xs mt-4 py-2 px-4 rounded-md bg-white/5 hover:bg-white/10 transition-colors"
            style={{
              color: theme?.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
            }}
          >
            Learn about Last.fm
            <IconExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    );
  }

  const recentTracks =
    lastfmData.recentTracks?.slice(0, theme?.lastfmMaxTracks || 4) || [];
  const topTracks =
    lastfmData.topTracks?.slice(0, theme?.lastfmMaxTracks || 4) || [];
  const nowPlaying = recentTracks[0]?.["@attr"]?.nowplaying === "true";
  const userInfo = lastfmData.userInfo || {};

  const formatNumber = (num: number) => {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  };

  const timeAgo = (timestamp: number) => {
    const now = new Date();
    const trackDate = new Date(timestamp * 1000);
    const diffMs = now.getTime() - trackDate.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;
    if (diffDay < 7) return `${diffDay}d ago`;
    return trackDate.toLocaleDateString();
  };

  if (isCompact) {
    return (
      <div
        className="mt-6 overflow-hidden bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-xl border border-white/10"
        style={{ background: theme?.lastfmBgColor || "rgba(0,0,0,0.4)" }}
      >
        <div className="p-3 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className="w-6 h-6 rounded-full bg-pink-500/20 flex items-center justify-center"
              style={{
                backgroundColor: `${theme?.lastfmThemeColor || "#f43f5e"}20`,
              }}
            >
              <Music
                className="w-3 h-3 text-pink-400"
                style={{ color: theme?.lastfmThemeColor || "#f43f5e" }}
              />
            </div>
            <h3
              className="text-xs font-medium text-white/90"
              style={{ color: theme?.lastfmTextColor || "#ffffff" }}
            >
              Last.fm
            </h3>
          </div>

          {theme?.lastfmShowScrobbles !== false && (
            <div className="flex items-center gap-1">
              <span
                className="text-[10px] text-white/60"
                style={{
                  color: theme?.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
                }}
              >
                {userInfo.playcount &&
                  `${formatNumber(parseInt(userInfo.playcount))} scrobbles`}
              </span>
            </div>
          )}
        </div>

        <div className="p-2">
          <div className="space-y-2">
            {recentTracks.map((track: any, index: number) => (
              <a
                key={index}
                href={track.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`flex items-center gap-2 p-1.5 rounded-lg transition-colors group ${index === 0 && nowPlaying
                    ? "relative overflow-hidden"
                    : "hover:bg-white/5"
                  }`}
                style={
                  index === 0 && nowPlaying
                    ? {
                      background: `linear-gradient(90deg, ${theme?.lastfmThemeColor || "#f43f5e"
                        }15, transparent)`,
                      borderLeft: `2px solid ${theme?.lastfmThemeColor || "#f43f5e"
                        }`,
                    }
                    : {}
                }
              >
                {index === 0 && nowPlaying && (
                  <div
                    className="absolute top-0 left-0 h-full w-1"
                    style={{
                      backgroundColor: theme?.lastfmThemeColor || "#f43f5e",
                    }}
                  ></div>
                )}
                <div className="relative min-w-[32px]">
                  {track.image && track.image[1]["#text"] ? (
                    <img
                      src={track.image[1]["#text"]}
                      alt={track.name}
                      className="w-8 h-8 rounded-md object-cover"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-md bg-white/5 flex items-center justify-center">
                      <Music className="w-3 h-3 text-white/40" />
                    </div>
                  )}

                  {index === 0 && nowPlaying && (
                    <div
                      className="absolute -top-1 -right-1 w-3 h-3 rounded-full flex items-center justify-center"
                      style={{
                        backgroundColor: theme?.lastfmThemeColor || "#f43f5e",
                      }}
                    >
                      <span className="relative flex h-1.5 w-1.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-white"></span>
                        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-white"></span>
                      </span>
                    </div>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p
                    className="text-xs font-medium truncate"
                    style={{ color: theme?.lastfmTextColor || "#ffffff" }}
                  >
                    {track.name}
                  </p>
                  <p
                    className="text-[10px] truncate"
                    style={{
                      color:
                        theme?.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
                    }}
                  >
                    {track.artist["#text"]}
                  </p>
                </div>
              </a>
            ))}
          </div>

          <a
            href={`https://www.last.fm/user/${lastfmData.username}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-1 text-[10px] text-white/50 hover:text-white/80 transition-colors mt-2 py-1 rounded-md bg-white/5 hover:bg-white/10"
            style={{
              color: theme?.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
            }}
          >
            View on Last.fm
            <IconExternalLink className="w-2 h-2" />
          </a>
        </div>
      </div>
    );
  }

  return (
    <div
      className="mt-6 overflow-hidden bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-xl border border-white/10"
      style={{ background: theme?.lastfmBgColor || "rgba(0,0,0,0.4)" }}
    >
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div
              className="w-10 h-10 rounded-full bg-pink-500/20 flex items-center justify-center"
              style={{
                backgroundColor: `${theme?.lastfmThemeColor || "#f43f5e"}20`,
              }}
            >
              <Music
                className="w-5 h-5 text-pink-400"
                style={{ color: theme?.lastfmThemeColor || "#f43f5e" }}
              />
            </div>
            <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-black flex items-center justify-center">
              <Disc className="w-3 h-3 text-white/80" />
            </div>
          </div>
          <div>
            <h3
              className="text-sm font-medium text-white/90"
              style={{ color: theme?.lastfmTextColor || "#ffffff" }}
            >
              Last.fm
            </h3>
            {theme?.lastfmShowScrobbles !== false && (
              <p
                className="text-xs text-white/60"
                style={{
                  color: theme?.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
                }}
              >
                {userInfo.playcount &&
                  `${formatNumber(parseInt(userInfo.playcount))} scrobbles`}
              </p>
            )}
          </div>
        </div>

        {theme?.lastfmShowTabs !== false && (
          <div className="flex items-center bg-black/20 rounded-full p-1">
            <button
              onClick={() => setActiveTab("recent")}
              className={`px-3 py-1 text-xs rounded-full transition-colors ${activeTab === "recent"
                  ? "bg-white/10 text-white"
                  : "text-white/60 hover:text-white/80"
                }`}
              style={{
                backgroundColor:
                  activeTab === "recent"
                    ? "rgba(255,255,255,0.1)"
                    : "transparent",
                color:
                  activeTab === "recent"
                    ? theme?.lastfmTextColor || "#ffffff"
                    : theme?.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
              }}
            >
              Recent
            </button>
            <button
              onClick={() => setActiveTab("top")}
              className={`px-3 py-1 text-xs rounded-full transition-colors ${activeTab === "top"
                  ? "bg-white/10 text-white"
                  : "text-white/60 hover:text-white/80"
                }`}
              style={{
                backgroundColor:
                  activeTab === "top" ? "rgba(255,255,255,0.1)" : "transparent",
                color:
                  activeTab === "top"
                    ? theme?.lastfmTextColor || "#ffffff"
                    : theme?.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
              }}
            >
              Top Tracks
            </button>
          </div>
        )}
      </div>

      <div className="p-4">
        <div className="space-y-3">
          {(activeTab === "recent" ? recentTracks : topTracks).map(
            (track: any, index: number) => (
              <a
                key={index}
                href={track.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`flex items-center gap-3 p-2 rounded-lg transition-colors group ${activeTab === "recent" && index === 0 && nowPlaying
                    ? "relative overflow-hidden"
                    : "hover:bg-white/5"
                  }`}
                style={
                  activeTab === "recent" && index === 0 && nowPlaying
                    ? {
                      background: `linear-gradient(90deg, ${theme?.lastfmThemeColor || "#f43f5e"
                        }15, transparent)`,
                      borderLeft: `2px solid ${theme?.lastfmThemeColor || "#f43f5e"
                        }`,
                    }
                    : {}
                }
              >
                {activeTab === "recent" && index === 0 && nowPlaying && (
                  <div
                    className="absolute top-0 left-0 h-full w-1"
                    style={{
                      backgroundColor: theme?.lastfmThemeColor || "#f43f5e",
                    }}
                  ></div>
                )}
                <div className="relative min-w-[48px]">
                  {track.image && track.image[2]["#text"] ? (
                    <img
                      src={track.image[2]["#text"]}
                      alt={track.name}
                      className="w-12 h-12 rounded-md object-cover"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-md bg-white/5 flex items-center justify-center">
                      <Music className="w-5 h-5 text-white/40" />
                    </div>
                  )}

                  <div className="absolute inset-0 bg-black/40 rounded-md opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                    <Play className="w-6 h-6 text-white fill-white" />
                  </div>

                  {activeTab === "recent" && index === 0 && nowPlaying && (
                    <div
                      className="absolute -top-1 -right-1 w-3 h-3 rounded-full flex items-center justify-center"
                      style={{
                        backgroundColor: theme?.lastfmThemeColor || "#f43f5e",
                      }}
                    >
                      <span className="relative flex h-1.5 w-1.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-white"></span>
                        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-white"></span>
                      </span>
                    </div>
                  )}

                  {activeTab === "top" && (
                    <div
                      className="absolute -top-1 -left-1 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold"
                      style={{
                        backgroundColor: theme?.lastfmThemeColor || "#f43f5e",
                      }}
                    >
                      {index + 1}
                    </div>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p
                      className="text-sm font-medium truncate"
                      style={{ color: theme?.lastfmTextColor || "#ffffff" }}
                    >
                      {track.name}
                    </p>
                  </div>
                  <p
                    className="text-xs truncate"
                    style={{
                      color:
                        theme?.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
                    }}
                  >
                    {track.artist["#text"]}
                  </p>

                  {activeTab === "recent" ? (
                    <div className="flex items-center gap-1 mt-1">
                      <Clock className="w-3 h-3 text-white/40" />
                      <p
                        className="text-[10px] text-white/40"
                        style={{
                          color: `${theme?.lastfmSecondaryColor ||
                            "rgba(255,255,255,0.6)"
                            }99`,
                        }}
                      >
                        {nowPlaying && index === 0
                          ? "Now playing"
                          : track.date
                            ? timeAgo(parseInt(track.date.uts))
                            : ""}
                      </p>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1 mt-1">
                      <BarChart2 className="w-3 h-3 text-white/40" />
                      <p
                        className="text-[10px] text-white/40"
                        style={{
                          color: `${theme?.lastfmSecondaryColor ||
                            "rgba(255,255,255,0.6)"
                            }99`,
                        }}
                      >
                        {track.playcount
                          ? `${formatNumber(parseInt(track.playcount))} plays`
                          : ""}
                      </p>
                    </div>
                  )}
                </div>
              </a>
            )
          )}
        </div>

        <a
          href={`https://www.last.fm/user/${lastfmData.username}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-1 text-xs text-white/50 hover:text-white/80 transition-colors mt-4 py-2 rounded-md bg-white/5 hover:bg-white/10"
          style={{
            color: theme?.lastfmSecondaryColor || "rgba(255,255,255,0.6)",
          }}
        >
          View full profile on Last.fm
          <IconExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
};

export default function LayoutThree({
  userData,
  discordData,
  slug,
  theme,
}: LayoutThreeProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [linkModal, setLinkModal] = useState<{ isOpen: boolean; url: string }>({
    isOpen: false,
    url: "",
  });
  const [currentActivity, setCurrentActivity] = useState(0);
  const [isBlurred, setIsBlurred] = useState(true);
  const [volume, setVolume] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [currentTrack, setCurrentTrack] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audio] = useState(() =>
    typeof window !== "undefined" ? new Audio() : null
  );
  const [hasStartedPlaying, setHasStartedPlaying] = useState(false);
  const [userInteracted, setUserInteracted] = useState(false);
  const [visible, setVisible] = useState(true);
  const [guildData, setGuildData] = useState<any>(null);
  const [isPlayerCollapsed, setIsPlayerCollapsed] = useState(false);

  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useTransform(y, [-300, 300], [10, -10]);
  const rotateY = useTransform(x, [-300, 300], [-10, 10]);

  const progress = useSpring(0, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001,
  });

  const nonCustomActivities =
    userData.presence?.activities?.filter(
      (activity) => activity.type !== "ActivityType.custom"
    ) || [];

  useEffect(() => {
    setTimeout(() => { }, 500);
  }, []);

  useEffect(() => {
    if (audio && userData?.audio?.url && !isBlurred) {
      audio.volume = 0.5;
      setVolume(0.5);
      audio.play();
    }
  }, [isBlurred, userData?.audio?.url]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.handleExternalLink = (element: HTMLAnchorElement) => {
        const url = element.getAttribute("data-url");
        if (url) {
          setLinkModal({ isOpen: true, url });
        }
      };
    }
  }, []);

  useEffect(() => {
    if (userData) {
      setLoading(false);
    }
  }, [userData]);

  useEffect(() => {
    if (!audio) {
      return;
    }

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      progress.set((audio.currentTime / (audio.duration || 1)) * 100);
    };

    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("timeupdate", handleTimeUpdate);

    if (
      userData.audioTracks?.[currentTrack]?.url &&
      audio.src !== userData.audioTracks[currentTrack].url
    ) {
      audio.src = userData.audioTracks[currentTrack].url;
      audio.load();
    }

    return () => {
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
    };
  }, [currentTrack, userData.audioTracks, audio]);

  useEffect(() => {
    if (!audio || !userInteracted) return;

    if (!isBlurred) {
      audio
        .play()
        .then(() => {
          setIsPlaying(true);
        })
        .catch((err) => {
          console.error("Play error:", err);
          setIsPlaying(false);
        });
    }
  }, [isBlurred, userInteracted, audio]);

  const togglePlay = () => {
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => console.error("Play error:", err));
    }
  };

  useEffect(() => {
    const handleUserInteraction = () => {
      setUserInteracted(true);
      document.removeEventListener("click", handleUserInteraction);
      document.removeEventListener("keydown", handleUserInteraction);
      document.removeEventListener("touchstart", handleUserInteraction);
    };

    document.addEventListener("click", handleUserInteraction);
    document.addEventListener("keydown", handleUserInteraction);
    document.addEventListener("touchstart", handleUserInteraction);

    return () => {
      document.removeEventListener("click", handleUserInteraction);
      document.removeEventListener("keydown", handleUserInteraction);
      document.removeEventListener("touchstart", handleUserInteraction);
    };
  }, []);

  const playNextTrack = () => {
    if (!userData.audioTracks) return;

    const nextTrack = (currentTrack + 1) % userData.audioTracks.length;
    setCurrentTrack(nextTrack);

    if (audio) {
      audio.src = userData.audioTracks[nextTrack].url;
      audio.load();
      audio
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => console.error("Play error:", err));
    }
  };

  const playPreviousTrack = () => {
    if (!userData.audioTracks) return;

    const prevTrack =
      currentTrack === 0 ? userData.audioTracks.length - 1 : currentTrack - 1;
    setCurrentTrack(prevTrack);

    if (audio) {
      audio.src = userData.audioTracks[prevTrack].url;
      audio.load();
      audio
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => console.error("Play error:", err));
    }
  };

  useEffect(() => {
    if (!audio) return;

    const handleEnded = () => {
      playNextTrack();
    };

    audio.addEventListener("ended", handleEnded);

    return () => {
      audio.removeEventListener("ended", handleEnded);
    };
  }, [audio, currentTrack, userData.audioTracks]);

  useEffect(() => {
    if (typeof navigator === "undefined" || !navigator.mediaSession) return;

    const updateMetadata = () => {
      if (!userData.audioTracks?.[currentTrack]) return;

      navigator.mediaSession.metadata = new MediaMetadata({
        title: formatTrackTitle(
          userData.audioTracks[currentTrack].title ?? "Unknown Track"
        ),
        artist: userData.user.name ?? "Unknown Artist",
        artwork: userData.audioTracks[currentTrack].icon
          ? [
            {
              src: userData.audioTracks[currentTrack].icon!,
              sizes: "512x512",
              type: "image/jpeg",
            },
          ]
          : undefined,
      });
    };

    updateMetadata();

    navigator.mediaSession.setActionHandler("play", () => {
      if (audio) {
        audio
          .play()
          .then(() => setIsPlaying(true))
          .catch((err) => console.error("Play error:", err));
      }
    });

    navigator.mediaSession.setActionHandler("pause", () => {
      if (audio) {
        audio.pause();
        setIsPlaying(false);
      }
    });

    navigator.mediaSession.setActionHandler("previoustrack", () => {
      playPreviousTrack();
    });

    navigator.mediaSession.setActionHandler("nexttrack", () => {
      playNextTrack();
    });

    return () => {
      if (navigator.mediaSession) {
        navigator.mediaSession.setActionHandler("play", null);
        navigator.mediaSession.setActionHandler("pause", null);
        navigator.mediaSession.setActionHandler("previoustrack", null);
        navigator.mediaSession.setActionHandler("nexttrack", null);
      }
    };
  }, [currentTrack, audio, userData.audioTracks]);

  useEffect(() => {
    const fetchGuildData = async () => {
      const inviteUrl =
        theme?.discordServerInvite || userData.discord_guild?.invite_url;

      if (inviteUrl) {
        const inviteCode = inviteUrl.split("/").pop();
        try {
          const response = await fetch(
            `https://discord.com/api/v9/invites/${inviteCode}?with_counts=true`
          );
          const data = await response.json();
          setGuildData({
            id: data.guild.id,
            name: data.guild.name,
            icon: data.guild.icon,
            description: data.guild.description,
            presence_count: data.approximate_presence_count,
            member_count: data.approximate_member_count,
            invite_url: inviteUrl,
          });
        } catch (error) {
          console.error("Failed to fetch guild data:", error);
        }
      }
    };

    fetchGuildData();
  }, [userData.discord_guild?.invite_url, theme?.discordServerInvite]);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (theme?.tiltDisabled) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const centerX = rect.x + rect.width / 2;
    const centerY = rect.y + rect.height / 2;
    x.set(e.clientX - centerX);
    y.set(e.clientY - centerY);
  };

  const handleMouseLeave = () => {
    if (theme?.tiltDisabled) return;

    x.set(0);
    y.set(0);
  };

  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-4"
        style={{
          background: "rgb(0 0 0 / 0.95)",
        }}
      >
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="w-full max-w-[700px] rounded-xl overflow-hidden bg-black"
        >
          <div className="h-24 sm:h-32 md:h-48 bg-gradient-to-br from-zinc-900 to-black animate-pulse" />

          <div className="p-4 sm:p-6">
            <div className="relative -mt-12 sm:-mt-16 px-2 sm:px-6">
              <div className="flex flex-col sm:flex-row sm:items-end gap-4">
                <div className="relative mx-auto sm:mx-0">
                  <div className="w-24 h-24 sm:w-32 sm:h-32 rounded-full bg-zinc-900 animate-pulse" />
                </div>

                <div className="flex-1 text-center sm:text-left space-y-2">
                  <div className="h-8 w-48 bg-zinc-900 rounded animate-pulse" />
                  <div className="h-4 w-32 bg-zinc-900/50 rounded animate-pulse" />
                </div>
              </div>

              <div className="mt-6 space-y-4">
                <div className="h-32 bg-zinc-900/20 rounded-xl animate-pulse" />
                <div className="h-24 bg-zinc-900/20 rounded-xl animate-pulse" />
                <div className="h-24 bg-zinc-900/20 rounded-xl animate-pulse" />
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    );
  }

  if (!userData) return null;

  const customStatus = userData.presence?.activities?.find(
    (activity) => activity.type === "ActivityType.custom" && activity.state
  );

  if (typeof window !== "undefined") {
    window.handleExternalLink = (element: HTMLAnchorElement) => {
      const url = element.getAttribute("data-url");
      if (url) {
        setLinkModal({ isOpen: true, url });
      }
    };
  }

  const getActivityIcon = (type: string) => {
    switch (type) {
      case "ActivityType.listening":
        return <Music className="w-4 h-4" />;
      case "ActivityType.playing":
        return <Gamepad2 className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const activity = userData.presence?.activities?.[currentActivity];

  const getAnimationStyle = () => {
    const textConfig =
      typeof theme?.blurScreen?.text === "string"
        ? {}
        : theme?.blurScreen?.text || {};
    const type = textConfig.animation?.type || "none";
    const speed = textConfig.animation?.speed || "normal";
    const intensity = textConfig.animation?.intensity || "medium";

    const speeds = {
      slow: "3s",
      normal: "2s",
      fast: "1s",
    };

    switch (type) {
      case "flicker":
        return {
          animation: `textFlicker ${speeds[speed]} infinite`,
          style: flickerAnimation,
        };
      case "pulse":
        return {
          animation: `textPulse ${speeds[speed]} infinite`,
          style: pulseAnimation,
        };
      case "bounce":
        return {
          animation: `textBounce ${speeds[speed]} ease-in-out infinite`,
          style: bounceAnimation,
        };
      default:
        return { animation: "", style: "" };
    }
  };

  const animationData = getAnimationStyle();

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  return (
    <div
      style={{
        fontFamily: getFontFamily(theme?.typography?.font || "default"),
      }}
    >
      <style jsx global>{`
        ${animationData.style}
      `}</style>

      {theme?.clickEffectEnabled && (
        <div
          className={`fixed inset-0 z-50 flex items-center justify-center transition-opacity duration-1000 ease-in-out cursor-pointer
            ${visible ? "opacity-100" : "opacity-0 pointer-events-none"}
          `}
          style={{
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            backdropFilter: `blur(16px)`,
            WebkitBackdropFilter: `blur(16px)`,
          }}
          onClick={() => {
            setVisible(false);
            setIsBlurred(false);
            setUserInteracted(true);
          }}
        >
          <span
            className="text-2xl font-medium tracking-wider"
            style={{
              color: theme?.clickEffectColor || "#FFFFFF",
            }}
          >
            {theme?.clickEffectText || "[ click ]"}
          </span>
        </div>
      )}

      {userData.audioPlayerEnabled && userData.audioTracks?.length > 0 && (
        <>
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-[95vw] sm:w-auto">
            <AnimatePresence mode="wait">
              <motion.div
                key={isPlayerCollapsed ? "collapsed" : "expanded"}
                initial={{
                  opacity: 0,
                  y: 20,
                  scale: isPlayerCollapsed ? 0.95 : 1,
                }}
                animate={{
                  opacity: 1,
                  y: 0,
                  scale: 1,
                  backdropFilter: `blur(${isPlayerCollapsed ? 5 : 12}px)`,
                  WebkitBackdropFilter: `blur(${isPlayerCollapsed ? 5 : 12}px)`,
                }}
                exit={{
                  opacity: 0,
                  y: 10,
                  scale: isPlayerCollapsed ? 1 : 0.95,
                }}
                transition={{
                  duration: 0.3,
                  ease: [0.22, 1, 0.36, 1],
                }}
                className={`bg-black/80 backdrop-blur-md ${isPlayerCollapsed
                    ? "rounded-full p-2 px-3"
                    : "rounded-full p-3 px-4"
                  } flex items-center gap-3 shadow-lg w-full ${isPlayerCollapsed ? "sm:w-auto" : "sm:w-[400px]"
                  }`}
                style={{
                  borderColor: safeColor(
                    theme?.container?.borderColor,
                    "rgba(255, 255, 255, 0.1)"
                  ),
                  borderWidth: "1px",
                }}
              >
                <div
                  className={`${isPlayerCollapsed ? "w-8 h-8" : "w-8 h-8 sm:w-10 sm:h-10"
                    } relative cursor-pointer`}
                  onClick={() => setIsPlayerCollapsed(!isPlayerCollapsed)}
                >
                  {userData.audioTracks[currentTrack]?.icon ? (
                    <img
                      src={userData.audioTracks[currentTrack].icon}
                      alt="Track artwork"
                      className={`${isPlayerCollapsed
                          ? "w-8 h-8"
                          : "w-8 h-8 sm:w-10 sm:h-10"
                        } rounded-full object-cover flex-shrink-0`}
                    />
                  ) : (
                    <div
                      className={`${isPlayerCollapsed
                          ? "w-8 h-8"
                          : "w-8 h-8 sm:w-10 sm:h-10"
                        } rounded-full bg-white/10 flex items-center justify-center flex-shrink-0`}
                    >
                      <Music
                        className={`${isPlayerCollapsed
                            ? "w-4 h-4"
                            : "w-4 h-4 sm:w-5 sm:h-5"
                          } text-white/60`}
                      />
                    </div>
                  )}

                  {isPlayerCollapsed && isPlaying && (
                    <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full flex items-center justify-center bg-green-500">
                      <span className="relative flex h-1.5 w-1.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-white"></span>
                        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-white"></span>
                      </span>
                    </div>
                  )}
                </div>

                <motion.div
                  className="flex flex-col flex-1 min-w-0"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: isPlayerCollapsed ? 0 : 1 }}
                  transition={{ duration: 0.2 }}
                  style={{ display: isPlayerCollapsed ? "none" : "flex" }}
                >
                  {!isPlayerCollapsed && (
                    <>
                      <span className="text-sm text-white font-medium truncate">
                        {userData.audioTracks[currentTrack]?.title
                          ? formatTrackTitle(
                            userData.audioTracks[currentTrack].title
                          )
                          : "Unknown Track"}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-white/60">
                          {formatTime(currentTime)}
                        </span>
                        <div className="relative flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
                          <motion.div
                            className="absolute inset-0 bg-white/60"
                            style={{ width: progress }}
                          />
                        </div>
                        <span className="text-xs text-white/60">
                          {formatTime(duration)}
                        </span>
                      </div>
                    </>
                  )}
                </motion.div>

                <motion.div
                  className="flex items-center gap-1 sm:gap-2 flex-shrink-0"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: isPlayerCollapsed ? 0 : 1 }}
                  transition={{ duration: 0.2 }}
                  style={{ display: isPlayerCollapsed ? "none" : "flex" }}
                >
                  {!isPlayerCollapsed && (
                    <>
                      <button
                        onClick={playPreviousTrack}
                        className="p-1 sm:p-1.5 rounded-full hover:bg-white/10 transition-colors"
                      >
                        <SkipBack className="w-3 h-3 sm:w-4 sm:h-4 text-white" />
                      </button>

                      <button
                        onClick={togglePlay}
                        className="p-1.5 sm:p-2 rounded-full hover:bg-white/10 transition-colors"
                      >
                        {isPlaying ? (
                          <Pause className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                        ) : (
                          <Play className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                        )}
                      </button>

                      <button
                        onClick={playNextTrack}
                        className="p-1 sm:p-1.5 rounded-full hover:bg-white/10 transition-colors"
                      >
                        <SkipForward className="w-3 h-3 sm:w-4 sm:h-4 text-white" />
                      </button>
                    </>
                  )}
                </motion.div>

                {isPlayerCollapsed && (
                  <motion.button
                    onClick={togglePlay}
                    className="p-1.5 rounded-full hover:bg-white/10 transition-colors"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.2 }}
                  >
                    {isPlaying ? (
                      <Pause className="w-4 h-4 text-white" />
                    ) : (
                      <Play className="w-4 h-4 text-white" />
                    )}
                  </motion.button>
                )}

                <motion.button
                  onClick={() => setIsPlayerCollapsed(!isPlayerCollapsed)}
                  className="p-1 rounded-full hover:bg-white/10 transition-colors"
                  whileHover={{ backgroundColor: "rgba(255, 255, 255, 0.1)" }}
                  whileTap={{ scale: 0.95 }}
                >
                  {isPlayerCollapsed ? (
                    <ChevronUp className="w-3 h-3 text-white/60" />
                  ) : (
                    <ChevronDown className="w-3 h-3 text-white/60" />
                  )}
                </motion.button>
              </motion.div>
            </AnimatePresence>
          </div>
        </>
      )}

      <div className="min-h-screen w-full flex items-center justify-center p-4 relative">
        <div className="fixed inset-0 z-0">
          {userData.background_url?.endsWith(".mp4") ? (
            <video
              autoPlay
              loop
              muted
              playsInline
              controls={false}
              className="fixed inset-0 w-full h-full object-cover"
              style={{ backgroundColor: "rgb(0, 0, 0)" }}
            >
              <source src={userData.background_url} type="video/mp4" />
            </video>
          ) : (
            <div
              className="fixed inset-0"
              style={{
                background: userData.background_url
                  ? `url(${userData.background_url}) center/cover no-repeat`
                  : theme?.containerBackgroundColor || "rgb(0 0 0 / 0.95)",
              }}
            />
          )}
        </div>

        <motion.div
          className="w-[800px] max-w-[95vw] relative z-10"
          style={{
            backgroundColor: safeColor(
              theme?.container?.backgroundColor,
              "rgba(0, 0, 0, 0.4)"
            ),
            backdropFilter: `blur(${theme?.container?.backdropBlur || "16px"})`,
            borderColor: safeColor(
              theme?.container?.borderColor,
              "rgba(255, 255, 255, 0.1)"
            ),
            borderWidth: theme?.container?.borderWidth || "1px",
            borderRadius: theme?.container?.borderRadius || "32px",
            boxShadow: theme?.container?.glowColor
              ? `0 0 ${theme?.container?.glowIntensity || "40px"} ${theme.container.glowColor
              }`
              : undefined,
            ...(theme?.tiltDisabled
              ? {}
              : {
                rotateX,
                rotateY,
              }),
            transition: "all 0.15s ease",
            transformStyle: "preserve-3d",
            perspective: 1000,
            overflow: "hidden",
          }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <div className="relative">
            <div className={`h-24 sm:h-32 md:h-48 relative overflow-hidden`}>
              {userData?.user?.banner &&
                (userData.user.banner.endsWith(".mp4") ? (
                  <video
                    src={userData.user.banner}
                    autoPlay
                    loop
                    muted
                    playsInline
                    controls={false}
                    className="absolute inset-0 w-full h-full object-cover"
                  />
                ) : (
                  <Image
                    src={userData.user.banner}
                    alt="Profile banner"
                    fill
                    className="object-cover"
                    priority
                  />
                ))}
            </div>

            {/* <div className="absolute top-4 right-4">
              <button
                onClick={() => {
                  setLinkModal({
                    isOpen: true,
                    url:
                      "/login?callbackUrl=" +
                      encodeURIComponent(window.location.href),
                  });
                }}
                className="p-2 rounded-lg bg-black/20 backdrop-blur-sm hover:bg-black/30 transition-colors group"
              >
                <AlertTriangle className="w-5 h-5 text-red-500 group-hover:text-red-400" />
              </button>
            </div> */}

            <div
              className={`${userData.glass_effect ? "bg-black/50" : "bg-black"
                } p-6`}
            >
              <div className="relative -mt-16 sm:-mt-16 px-2 sm:px-6">
                <div
                  className={`flex flex-col ${theme?.avatarAlignment === "center"
                      ? "items-center sm:items-center"
                      : theme?.avatarAlignment === "right"
                        ? "items-center sm:items-end"
                        : "items-center sm:items-start"
                    } ${theme?.avatarAlignment === "center"
                      ? "sm:flex-col sm:gap-3"
                      : theme?.avatarAlignment === "right"
                        ? "sm:flex-row-reverse sm:items-end"
                        : "sm:flex-row sm:items-end"
                    } gap-4`}
                >
                  <div className="relative">
                    <div
                      className="w-28 h-28 sm:w-32 sm:h-32 overflow-hidden"
                      style={{
                        borderRadius: theme?.avatarBorderRadius || "50%",
                        ...(theme?.avatarShowBorder && {
                          borderWidth: theme?.avatarBorderWidth || "2px",
                          borderColor: theme?.avatarBorderColor || "#ff3379",
                          borderStyle: "solid",
                          boxShadow: theme?.avatarGlowColor
                            ? `0 0 ${theme?.avatarGlowIntensity || "0.3"} ${theme.avatarGlowColor
                            }`
                            : undefined,
                        }),
                      }}
                    >
                      {userData.user.avatar && (
                        <Image
                          src={userData.user.avatar}
                          alt={userData.user.name}
                          width={128}
                          height={128}
                          unoptimized
                          className="relative object-cover w-28 h-28 sm:w-32 sm:h-32"
                          style={{ aspectRatio: "1/1", zIndex: 1 }}
                        />
                      )}
                    </div>
                    {userData.user.avatar_decoration_data?.asset ? (
                      <Image
                        src={`https://cdn.discordapp.com/avatar-decoration-presets/${userData.user.avatar_decoration_data.asset}.png?size=256&passthrough=true`}
                        alt=""
                        width={128}
                        height={128}
                        unoptimized
                        className="absolute -inset-0 w-full h-full scale-[1.2] pointer-events-none"
                        style={{ zIndex: 2 }}
                      />
                    ) : (
                      theme?.avatarDecoration && (
                        <Image
                          src={`/decorations/${theme.avatarDecoration}`}
                          alt=""
                          width={128}
                          height={128}
                          unoptimized
                          className="absolute -inset-0 w-full h-full scale-[1.2] pointer-events-none"
                          style={{ zIndex: 2 }}
                        />
                      )
                    )}
                  </div>

                  <div
                    className={`flex-1 text-center ${theme?.avatarAlignment === "center"
                        ? "sm:text-center"
                        : theme?.avatarAlignment === "right"
                          ? "sm:text-right sm:mb-1"
                          : "sm:text-left sm:mb-1"
                      }`}
                  >
                    <div
                      className={`flex flex-col ${theme?.avatarAlignment === "center"
                          ? "sm:items-center"
                          : theme?.avatarAlignment === "right"
                            ? "sm:items-end"
                            : "sm:items-start"
                        } gap-2`}
                    >
                      <h1
                        style={{
                          color: safeColor(theme?.titleColor, "white"),
                          fontSize: theme?.titleSize || "1.5rem",
                          fontWeight: theme?.titleWeight || "600",
                          fontFamily: getFontFamily(
                            theme?.typography?.font || "default"
                          ),
                        }}
                      >
                        {userData.user.name}
                      </h1>

                      {userData.badges && userData.badges.length > 0 && (
                        <div className="flex items-center justify-center gap-[5px] bg-white/[0.05] border-[2px] border-white/[0.04] rounded-[25px] py-[6px] px-[10px]">
                          {userData.badges.map((badge) => (
                            <div
                              key={badge}
                              className="group relative flex items-center transition-all duration-200 hover:scale-110"
                            >
                              <Image
                                src={`/badges/${badge.toLowerCase()}.svg`}
                                alt={badge}
                                width={
                                  badge.toLowerCase() === "og" ||
                                    badge.toLowerCase() === "verified" ||
                                    badge.toLowerCase() === "owner"
                                    ? 20
                                    : 16
                                }
                                height={
                                  badge.toLowerCase() === "og" ||
                                    badge.toLowerCase() === "verified"
                                    ? 20
                                    : 16
                                }
                                className="brightness-0 invert"
                              />
                              <span
                                className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1 px-2 py-1 text-xs font-medium rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap bg-black/80 text-white"
                              >
                                {badge.replace("_", " ")}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {userData.bio && (
                  <div className="mt-6 p-4 bg-white/[0.02] rounded-xl border border-white/5">
                    <div className="text-white/80 flex items-center gap-1">
                      <div
                        className="whitespace-pre-line"
                        style={{
                          ...(userData.colors.elements.bio.type === "gradient"
                            ? {
                              background: getElementColor(
                                userData.colors,
                                "bio"
                              ),
                              WebkitBackgroundClip: "text",
                              WebkitTextFillColor: "transparent",
                              backgroundClip: "text",
                            }
                            : {
                              color: theme?.bioColor || "white",
                              fontSize: theme?.bioSize || "14px",
                            }),
                        }}
                      >
                        {theme?.bioTextEffectEnabled ? (
                          <BioText
                            text={formatBio(userData.bio)}
                            effect={theme?.bioTextEffect || "typewriter"}
                            speed={theme?.bioTextEffectSpeed || 50}
                            style={{
                              color: theme?.bioColor || "white",
                              fontSize: theme?.bioSize || "14px",
                            }}
                            isBlurred={isBlurred}
                          />
                        ) : (
                          formatBio(userData.bio)
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {(theme?.discordActivityDisplayType === "BOTH" || 
                  theme?.discordActivityDisplayType === "DISCORD_INFO_ONLY" ||
                  theme?.discordActivityDisplayType === "PRESENCE_INFO_ONLY") && 
                  (discordData?.detailed?.user || nonCustomActivities.length > 0) && (
                  <div className="mt-4">
                    {theme?.discordActivityCompactMode && nonCustomActivities.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {(theme?.discordActivityDisplayType === "BOTH" || 
                          theme?.discordActivityDisplayType === "DISCORD_INFO_ONLY") &&
                          discordData?.detailed?.user && (
                          <div className="p-4 rounded-xl border" style={{
                            backgroundColor: theme?.discordPresenceBgColor || "rgba(255, 255, 255, 0.02)",
                            borderColor: theme?.discordPresenceBorderColor || "rgba(255, 255, 255, 0.05)",
                          }}>
                            <div className="flex items-start gap-3">
                              <div className="relative flex-shrink-0">
                                <Image
                                  src={`https://cdn.discordapp.com/avatars/${discordData.detailed.user.id}/${discordData.detailed.user.avatar}.png?size=128`}
                                  alt={discordData.detailed.user.username}
                                  width={48}
                                  height={48}
                                  className="rounded-full"
                                  style={{
                                    width: theme?.discordPresenceAvatarSize || "48px",
                                    height: theme?.discordPresenceAvatarSize || "48px",
                                  }}
                                  unoptimized
                                />
                                {theme?.discordStatusIndicatorEnabled !== false && (
                                  <div
                                    className={`absolute w-3.5 h-3.5 rounded-full border-2 ${statusColors[(userData.presence?.status as keyof typeof statusColors) || "offline"]
                                      }`}
                                    style={{
                                      borderColor: theme?.discordPresenceBgColor || "rgba(255, 255, 255, 0.02)",
                                      bottom: "-2px",
                                      right: "-2px"
                                    }}
                                  />
                                )}
                              </div>
                              <div className="flex-1 min-w-0 -mt-1">
                                <div className="flex flex-col">
                                  <div className="flex items-center gap-2">
                                    <div
                                      className="font-semibold truncate flex items-center gap-1.5"
                                      style={{
                                        color:
                                          theme?.discordPresenceTextColor ||
                                          "rgba(255, 255, 255, 0.95)",
                                        fontSize: "1.1rem",
                                      }}
                                    >
                                      {discordData.detailed.user.global_name ||
                                        discordData.detailed.user.username}
                                      {discordData.detailed?.badges && (
                                        <div className="flex items-center gap-1.5">
                                          {discordData.detailed.badges.map(
                                            (badge) => (
                                              <img
                                                key={badge.id}
                                                src={`https://cdn.discordapp.com/badge-icons/${badge.icon}.png`}
                                                alt={badge.description}
                                                className="w-5 h-5"
                                                title={badge.description}
                                              />
                                            )
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                  <div
                                    className="text-sm truncate opacity-90"
                                    style={{
                                      color:
                                        theme?.discordPresenceSecondaryColor ||
                                        "rgba(255, 255, 255, 0.6)",
                                    }}
                                  >
                                    @{discordData.detailed.user.username}
                                  </div>

                                  {(theme?.discordActivityDisplayType === "BOTH" ||
                                    theme?.discordActivityDisplayType === "DISCORD_INFO_ONLY") &&
                                    customStatus &&
                                    customStatus.state && (
                                      <div
                                        className="mt-2 flex items-center gap-2"
                                        style={{
                                          color:
                                            theme?.discordPresenceSecondaryColor ||
                                            "rgba(255, 255, 255, 0.7)",
                                        }}
                                      >
                                        {customStatus.emoji && (
                                          <img
                                            src={
                                              customStatus.emoji.url ||
                                              `https://cdn.discordapp.com/emojis/${customStatus.emoji.id}.png`
                                            }
                                            alt={customStatus.emoji.name}
                                            className="w-4 h-4"
                                          />
                                        )}
                                        <span className="text-sm">{customStatus.state}</span>
                                      </div>
                                    )}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                        {(theme?.discordActivityDisplayType === "BOTH" || 
                          theme?.discordActivityDisplayType === "PRESENCE_INFO_ONLY") && (
                          <div className="p-4 rounded-xl border" style={{
                            backgroundColor: theme?.discordPresenceBgColor || "rgba(255, 255, 255, 0.02)",
                            borderColor: theme?.discordPresenceBorderColor || "rgba(255, 255, 255, 0.05)",
                          }}>
                            <motion.div
                              initial={theme?.discordAnimationsEnabled !== false ? { opacity: 0, y: 20 } : false}
                              animate={theme?.discordAnimationsEnabled !== false ? { opacity: 1, y: 0 } : false}
                            >
                              {nonCustomActivities.length > 0 ? (
                                <div className={`flex ${theme?.discordActivityLayout === "cozy"
                                  ? "flex-col gap-4"
                                  : "flex-col sm:flex-row"
                                } items-start sm:items-center justify-between w-full gap-4`}>
                                  {nonCustomActivities[currentActivity]?.name ===
                                    "Spotify" ? (
                                    <div className="flex items-center gap-3 w-full">
                                      {nonCustomActivities[currentActivity]
                                        ?.large_image && (
                                          <Image
                                            src={
                                              nonCustomActivities[currentActivity]
                                                ?.large_image
                                            }
                                            alt="Album cover"
                                            width={60}
                                            height={68}
                                            className="rounded-md"
                                            style={{
                                              width:
                                                theme?.discordPresenceAvatarSize ||
                                                "60px",
                                              height:
                                                theme?.discordPresenceAvatarSize ||
                                                "68px",
                                            }}
                                            unoptimized
                                          />
                                        )}
                                      <div className="flex-1 min-w-0 sm:min-w-0">
                                        <div
                                          className="flex items-center gap-2"
                                          style={{
                                            color:
                                              theme?.discordPresenceSecondaryColor ||
                                              "rgba(255, 255, 255, 0.6)",
                                          }}
                                        >
                                          <Music className="w-4 h-4" />
                                          <span className="text-sm">
                                            Listening to Spotify
                                          </span>
                                        </div>
                                        <p
                                          className="text-sm truncate"
                                          style={{
                                            color:
                                              theme?.discordActivityTextColor ||
                                              "white",
                                          }}
                                        >
                                          {nonCustomActivities[currentActivity]
                                            ?.details || "Unknown Track"}
                                        </p>
                                        <p
                                          className="text-xs truncate"
                                          style={{
                                            color:
                                              theme?.discordPresenceSecondaryColor ||
                                              "rgba(255, 255, 255, 0.6)",
                                          }}
                                        >
                                          {nonCustomActivities[currentActivity]
                                            ?.state || "Unknown Artist"}
                                        </p>
                                        {nonCustomActivities[currentActivity]
                                          ?.timestamps?.start &&
                                          nonCustomActivities[currentActivity]
                                            ?.timestamps?.end && (
                                            <div className="mt-2 pr-2">
                                              <div className="h-1 bg-white/10 rounded-full w-full overflow-hidden">
                                                <motion.div
                                                  className="h-full bg-green-500"
                                                  initial={{
                                                    width: `${calculateSpotifyProgress(
                                                      nonCustomActivities[
                                                        currentActivity
                                                      ]?.timestamps.start,
                                                      nonCustomActivities[
                                                        currentActivity
                                                      ]?.timestamps.end
                                                    )}%`,
                                                  }}
                                                  animate={{ width: "100%" }}
                                                  transition={{
                                                    duration:
                                                      nonCustomActivities[
                                                        currentActivity
                                                      ]?.timestamps.end -
                                                      Date.now() / 1000,
                                                    repeat: 0,
                                                    ease: "linear",
                                                  }}
                                                />
                                              </div>
                                            </div>
                                          )}
                                      </div>
                                    </div>
                                  ) : (
                                    <>
                                      {nonCustomActivities[currentActivity]
                                        ?.large_image && (
                                          <Image
                                            src={
                                              nonCustomActivities[currentActivity]
                                                ?.large_image
                                            }
                                            alt={
                                              nonCustomActivities[currentActivity]
                                                ?.large_text || "Activity image"
                                            }
                                            unoptimized
                                            width={60}
                                            height={60}
                                            className="rounded-md"
                                            style={{
                                              width:
                                                theme?.discordPresenceAvatarSize ||
                                                "60px",
                                              height:
                                                theme?.discordPresenceAvatarSize ||
                                                "60px",
                                            }}
                                          />
                                        )}
                                      <div>
                                        <div
                                          className="flex items-center gap-2"
                                          style={{
                                            color:
                                              theme?.discordPresenceSecondaryColor ||
                                              "rgba(255, 255, 255, 0.6)",
                                          }}
                                        >
                                          {getActivityIcon(
                                            nonCustomActivities[currentActivity]
                                              ?.type
                                          )}
                                          <span className="text-sm">
                                            {
                                              nonCustomActivities[currentActivity]
                                                ?.name
                                            }
                                          </span>
                                        </div>
                                        <p
                                          style={{
                                            color:
                                              theme?.discordActivityTextColor ||
                                              "white",
                                          }}
                                        >
                                          {
                                            nonCustomActivities[currentActivity]
                                              ?.details
                                          }
                                        </p>
                                        <p
                                          className="text-xs"
                                          style={{
                                            color:
                                              theme?.discordPresenceSecondaryColor ||
                                              "rgba(255, 255, 255, 0.6)",
                                          }}
                                        >
                                          {
                                            nonCustomActivities[currentActivity]
                                              ?.state
                                          }
                                        </p>
                                      </div>
                                    </>
                                  )}
                                </div>
                              ) : (
                                <div className="flex items-center gap-3 text-sm" style={{
                                  color: theme?.discordPresenceSecondaryColor || "rgba(255, 255, 255, 0.6)"
                                }}>
                                  <Gamepad2 className="w-4 h-4" />
                                  <span>Not playing anything</span>
                                </div>
                              )}
                            </motion.div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="p-4 rounded-xl border" style={{
                        backgroundColor: theme?.discordPresenceBgColor || "rgba(255, 255, 255, 0.02)",
                        borderColor: theme?.discordPresenceBorderColor || "rgba(255, 255, 255, 0.05)",
                      }}>
                        <div className="space-y-4">
                          {(theme?.discordActivityDisplayType === "BOTH" || 
                            theme?.discordActivityDisplayType === "DISCORD_INFO_ONLY") &&
                            discordData?.detailed?.user && (
                            <div className="flex items-start gap-3">
                              <div className="relative flex-shrink-0">
                                <Image
                                  src={`https://cdn.discordapp.com/avatars/${discordData.detailed.user.id}/${discordData.detailed.user.avatar}.png?size=128`}
                                  alt={discordData.detailed.user.username}
                                  width={48}
                                  height={48}
                                  className="rounded-full"
                                  style={{
                                    width: theme?.discordPresenceAvatarSize || "48px",
                                    height: theme?.discordPresenceAvatarSize || "48px",
                                  }}
                                  unoptimized
                                />
                                {theme?.discordStatusIndicatorEnabled !== false && (
                                  <div
                                    className={`absolute w-3.5 h-3.5 rounded-full border-2 ${statusColors[(userData.presence?.status as keyof typeof statusColors) || "offline"]
                                      }`}
                                    style={{
                                      borderColor: theme?.discordPresenceBgColor || "rgba(255, 255, 255, 0.02)",
                                      bottom: "-2px",
                                      right: "-2px"
                                    }}
                                  />
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex flex-col gap-1">
                                  <div
                                    className="font-semibold truncate flex items-center gap-1.5"
                                    style={{
                                      color:
                                        theme?.discordPresenceTextColor ||
                                        "rgba(255, 255, 255, 0.95)",
                                      fontSize: "1.1rem",
                                    }}
                                  >
                                    {discordData.detailed.user.global_name || discordData.detailed.user.username}
                                    {discordData.detailed?.badges && (
                                      <div className="flex items-center gap-1.5">
                                        {discordData.detailed.badges.map((badge) => (
                                          <img
                                            key={badge.id}
                                            src={`https://cdn.discordapp.com/badge-icons/${badge.icon}.png`}
                                            alt={badge.description}
                                            className="w-5 h-5"
                                            title={badge.description}
                                          />
                                        ))}
                                      </div>
                                    )}
                                  </div>

                                  <div
                                    className="text-sm truncate"
                                    style={{
                                      color:
                                        theme?.discordPresenceSecondaryColor ||
                                        "rgba(255, 255, 255, 0.6)",
                                    }}
                                  >
                                    @{discordData.detailed.user.username}
                                  </div>

                                  {(theme?.discordActivityDisplayType === "BOTH" ||
                                    theme?.discordActivityDisplayType === "DISCORD_INFO_ONLY") &&
                                    customStatus &&
                                    customStatus.state && (
                                      <div
                                        className="flex items-center gap-2"
                                        style={{
                                          color:
                                            theme?.discordPresenceSecondaryColor ||
                                            "rgba(255, 255, 255, 0.7)",
                                        }}
                                      >
                                        {customStatus.emoji && (
                                          <img
                                            src={
                                              customStatus.emoji.url ||
                                              `https://cdn.discordapp.com/emojis/${customStatus.emoji.id}.png`
                                            }
                                            alt={customStatus.emoji.name}
                                            className="w-4 h-4"
                                          />
                                        )}
                                        <span className="text-sm">{customStatus.state}</span>
                                      </div>
                                    )}
                                </div>
                              </div>
                            </div>
                          )}

                          {(theme?.discordActivityDisplayType === "BOTH" || 
                            theme?.discordActivityDisplayType === "PRESENCE_INFO_ONLY") &&
                            nonCustomActivities.length > 0 && (
                            <motion.div>
                              <div
                                className={`flex ${theme?.discordActivityLayout === "cozy"
                                    ? "flex-col gap-4"
                                    : "flex-col sm:flex-row"
                                  } items-start sm:items-center justify-between w-full gap-4`}
                              >
                                <div className="flex items-center gap-4 w-full">
                                  {nonCustomActivities[currentActivity]?.name ===
                                    "Spotify" ? (
                                    <div className="flex items-center gap-3 w-full">
                                      {nonCustomActivities[currentActivity]
                                        ?.large_image && (
                                          <Image
                                            src={
                                              nonCustomActivities[currentActivity]
                                                ?.large_image
                                            }
                                            alt="Album cover"
                                            width={60}
                                            height={68}
                                            className="rounded-md"
                                            style={{
                                              width:
                                                theme?.discordPresenceAvatarSize ||
                                                "60px",
                                              height:
                                                theme?.discordPresenceAvatarSize ||
                                                "68px",
                                            }}
                                            unoptimized
                                          />
                                        )}
                                      <div className="flex-1 min-w-0 sm:min-w-0">
                                        <div
                                          className="flex items-center gap-2"
                                          style={{
                                            color:
                                              theme?.discordPresenceSecondaryColor ||
                                              "rgba(255, 255, 255, 0.6)",
                                          }}
                                        >
                                          <Music className="w-4 h-4" />
                                          <span className="text-sm">
                                            Listening to Spotify
                                          </span>
                                        </div>
                                        <p
                                          className="text-sm truncate"
                                          style={{
                                            color:
                                              theme?.discordActivityTextColor ||
                                              "white",
                                          }}
                                        >
                                          {nonCustomActivities[currentActivity]
                                            ?.details || "Unknown Track"}
                                        </p>
                                        <p
                                          className="text-xs truncate"
                                          style={{
                                            color:
                                              theme?.discordPresenceSecondaryColor ||
                                              "rgba(255, 255, 255, 0.6)",
                                          }}
                                        >
                                          {nonCustomActivities[currentActivity]
                                            ?.state || "Unknown Artist"}
                                        </p>
                                        {nonCustomActivities[currentActivity]
                                          ?.timestamps?.start &&
                                          nonCustomActivities[currentActivity]
                                            ?.timestamps?.end && (
                                            <div className="mt-2 pr-2">
                                              <div className="h-1 bg-white/10 rounded-full w-full overflow-hidden">
                                                <motion.div
                                                  className="h-full bg-green-500"
                                                  initial={{
                                                    width: `${calculateSpotifyProgress(
                                                      nonCustomActivities[
                                                        currentActivity
                                                      ]?.timestamps.start,
                                                      nonCustomActivities[
                                                        currentActivity
                                                      ]?.timestamps.end
                                                    )}%`,
                                                  }}
                                                  animate={{ width: "100%" }}
                                                  transition={{
                                                    duration:
                                                      nonCustomActivities[
                                                        currentActivity
                                                      ]?.timestamps.end -
                                                      Date.now() / 1000,
                                                    repeat: 0,
                                                    ease: "linear",
                                                  }}
                                                />
                                              </div>
                                            </div>
                                          )}
                                      </div>
                                    </div>
                                  ) : (
                                    <>
                                      {nonCustomActivities[currentActivity]
                                        ?.large_image && (
                                          <Image
                                            src={
                                              nonCustomActivities[currentActivity]
                                                ?.large_image
                                            }
                                            alt={
                                              nonCustomActivities[currentActivity]
                                                ?.large_text || "Activity image"
                                            }
                                            unoptimized
                                            width={60}
                                            height={60}
                                            className="rounded-md"
                                            style={{
                                              width:
                                                theme?.discordPresenceAvatarSize ||
                                                "60px",
                                              height:
                                                theme?.discordPresenceAvatarSize ||
                                                "60px",
                                            }}
                                          />
                                        )}
                                      <div>
                                        <div
                                          className="flex items-center gap-2"
                                          style={{
                                            color:
                                              theme?.discordPresenceSecondaryColor ||
                                              "rgba(255, 255, 255, 0.6)",
                                          }}
                                        >
                                          {getActivityIcon(
                                            nonCustomActivities[currentActivity]
                                              ?.type
                                          )}
                                          <span className="text-sm">
                                            {
                                              nonCustomActivities[currentActivity]
                                                ?.name
                                            }
                                          </span>
                                        </div>
                                        <p
                                          style={{
                                            color:
                                              theme?.discordActivityTextColor ||
                                              "white",
                                          }}
                                        >
                                          {
                                            nonCustomActivities[currentActivity]
                                              ?.details
                                          }
                                        </p>
                                        <p
                                          className="text-xs"
                                          style={{
                                            color:
                                              theme?.discordPresenceSecondaryColor ||
                                              "rgba(255, 255, 255, 0.6)",
                                          }}
                                        >
                                          {
                                            nonCustomActivities[currentActivity]
                                              ?.state
                                          }
                                        </p>
                                      </div>
                                    </>
                                  )}
                                </div>

                                {nonCustomActivities.length > 1 && (
                                  <div className="flex items-center gap-2 w-full sm:w-auto justify-center sm:justify-start">
                                    {nonCustomActivities.map((_, index) => (
                                      <button
                                        key={index}
                                        onClick={() => setCurrentActivity(index)}
                                        className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${index === currentActivity ? "w-3" : ""
                                          }`}
                                        style={{
                                          backgroundColor:
                                            index === currentActivity
                                              ? theme?.discordActivityTextColor ||
                                              "rgba(255, 255, 255, 0.6)"
                                              : "rgba(255, 255, 255, 0.2)",
                                        }}
                                      />
                                    ))}
                                  </div>
                                )}
                              </div>
                            </motion.div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-6">
                  {guildData && (
                    <DiscordGuild guildData={guildData} theme={theme || {}} />
                  )}
                </div>

                {userData.links?.length > 0 && (
                  <UserLinks
                    links={userData.links.map((link) => ({
                      id: link.id,
                      title: link.type,
                      type: link.type,
                      url: link.url,
                      clicks: link.clicks,
                      position: link.position,
                      enabled: link.enabled,
                      iconUrl: link.iconUrl,
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
                    }))}
                    theme={{
                      ...theme,
                      linksCompactMode: theme?.linksCompactMode ?? false,
                      linksIconBgEnabled: theme?.linksIconBgEnabled ?? true,
                      linksDisableBackground:
                        theme?.linksDisableBackground ?? false,
                      linksDisableHover: theme?.linksDisableHover ?? false,
                      linksDisableBorder: theme?.linksDisableBorder ?? false,
                    }}
                  />
                )}

                {theme?.lastfmEnabled && (
                  <LastFmStats username={slug} theme={theme} />
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {linkModal.isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            backdropFilter: `blur(16px)`,
            WebkitBackdropFilter: `blur(16px)`,
          }}
        >
          <div className="bg-white p-8 rounded-xl max-w-[95vw] max-h-[95vh] overflow-auto">
            <h2 className="text-2xl font-bold mb-4">Login Required</h2>
            <p>
              You need to be logged in to access this link. Please log in and
              try again.
            </p>
            <button
              onClick={() => {
                setLinkModal({ isOpen: false, url: "" });
              }}
              className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
            >
              Log In
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

declare global {
  interface Window {
    handleExternalLink: (element: HTMLAnchorElement) => void;
  }
}
