"use client";

import { DiscordData } from "@/app/types/discord";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { IconExternalLink } from "@tabler/icons-react";
import { motion } from "framer-motion";
import { useToast } from "@/components/ui/toast-provider";
import Link from "next/link";

type ColorValue =
  | `#${string}`
  | `rgb(${string})`
  | `rgba(${string})`
  | `hsl(${string})`
  | `hsla(${string})`
  | string;

const isValidColor = (color: string): boolean => {
  const colorPatterns = [
    /^#([A-Fa-f0-9]{3}){1,2}$/,
    /^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$/,
    /^rgba\(\s*\d+\\s*,\s*\d+\s*,\s*\d+\s*,\s*[0-1]?\.?\d*\s*\)$/,
    /^hsl\(\s*\d+\s*,\s*\d+%?\s*,\s*\d+%?\s*\)$/,
    /^hsla\(\s*\d+\s*,\s*\d+%?\s*,\s*\d+%?\s*,\s*[0-1]?\.?\d*\s*\)$/,
    /^(text|bg|border)-.+$/,
  ];

  return colorPatterns.some((pattern) => pattern.test(color));
};

const safeColor = (
  color: ColorValue | undefined,
  defaultColor: string,
): string => {
  if (!color) return defaultColor;
  return isValidColor(color) ? color : defaultColor;
};

interface UserData {
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

interface LayoutOneProps {
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

export default function LayoutOne({
  userData,
  discordData,
  slug,
  theme = {},
}: LayoutOneProps) {
  const { toast } = useToast();
  const [visible, setVisible] = useState(true);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(`https://emogir.ls/@${slug}`);
      toast({
        title: "Copied",
        description: `emogir.ls/@${slug}`,
        variant: "success",
      });
    } catch (err) {}
  };

  const formatDuration = (startDate: Date) => {
    const diff = new Date().getTime() - startDate.getTime();
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    return `${hours}h ${minutes}m`;
  };

  const getAnimationStyle = () => {
    const textConfig =
      typeof theme.blurScreen?.text === "string"
        ? {}
        : theme.blurScreen?.text || {};
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
  const textConfig =
    typeof theme.blurScreen?.text === "string"
      ? {}
      : theme.blurScreen?.text || {};

  return (
    <>
      <style jsx global>{`
        ${animationData.style}
      `}</style>

      {theme.blurScreen?.enabled && (
        <div
          className={`fixed inset-0 z-50 flex items-center justify-center transition-opacity duration-1000 ease-in-out cursor-pointer
            ${visible ? "opacity-100" : "opacity-0 pointer-events-none"}
          `}
          style={{
            backgroundColor: safeColor(
              theme.blurScreen.backdrop?.color,
              "rgba(0, 0, 0, 0.8)",
            ),
            backdropFilter: `blur(${
              theme.blurScreen.backdrop?.blur || "16px"
            })`,
            WebkitBackdropFilter: `blur(${
              theme.blurScreen.backdrop?.blur || "16px"
            })`,
          }}
          onClick={() => setVisible(false)}
        >
          <span
            className={`
              ${textConfig.size || "text-2xl"}
              ${textConfig.weight || "font-medium"}
              ${textConfig.letterSpacing || "tracking-wider"}
            `}
            style={{
              color: safeColor(textConfig.color, "#ffffff"),
              animation: animationData.animation,
            }}
          >
            {typeof theme.blurScreen.text === "string"
              ? theme.blurScreen.text
              : theme.blurScreen.text?.content || "[ click ]"}
          </span>
        </div>
      )}

      <div className="min-h-screen w-full max-w-2xl mx-auto px-4 py-8 md:py-16">
        <div className="relative space-y-6">
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="relative">
              <img
                src={userData.avatar}
                alt={userData.displayName}
                className={`
                  ${theme.avatar?.size || "w-24 h-24"}
                  ${theme.avatar?.borderRadius || "rounded-full"}
                  ${theme.avatar?.borderWidth || "border-2"}
                  ${safeColor(theme.avatar?.borderColor, "border-primary")}
                  object-cover
                `}
              />
              <div
                className={`absolute bottom-0 right-0 w-6 h-6 rounded-full border-4 border-background
                ${
                  discordData?.presence?.activities?.[0]?.state === "online"
                    ? "bg-green-500"
                    : discordData?.presence?.activities?.[0]?.state === "idle"
                      ? "bg-yellow-500"
                      : discordData?.presence?.activities?.[0]?.state === "dnd"
                        ? "bg-red-500"
                        : "bg-gray-500"
                }`}
              />
            </div>

            <div>
              <h1
                className={`
                ${theme.text?.title?.size || "text-2xl"}
                ${theme.text?.title?.weight || "font-bold"}
                ${safeColor(theme.text?.title?.color, "text-white")}
              `}
              >
                {userData.displayName}
              </h1>
              <p
                className={safeColor(
                  theme.text?.username?.color,
                  "text-white/60",
                )}
              >
                @{userData.username}
              </p>
            </div>
            <p
              className={safeColor(theme.text?.bio?.color, "text-white/80")}
              style={{ maxWidth: "28rem" }}
            >
              {userData.bio}
            </p>
            <div className="flex space-x-2">
              <Button
                text="copy url"
                className={`!text-sm ${safeColor(
                  theme.button?.backgroundColor,
                  "bg-primary",
                )} ${safeColor(theme.button?.textColor, "text-white")}`}
                onClick={copyToClipboard}
              />
            </div>
          </div>

          {discordData?.presence && (
            <div
              className={`
              ${safeColor(
                theme.discord?.presence?.backgroundColor,
                "bg-black/40",
              )}
              backdrop-blur-sm border
              ${safeColor(
                theme.discord?.presence?.borderColor,
                "border-primary/10",
              )}
              rounded-xl p-5
            `}
            >
              <div className="flex items-center gap-3">
                <img
                  src={`https://cdn.discordapp.com/avatars/442626774841556992/e18f44d77f1a91c939ba827a964c9f05.webp?size=128`}
                  alt="Discord Avatar"
                  className={`
                    ${safeColor(
                      theme.discord?.presence?.avatar?.size,
                      "w-12 h-12",
                    )}
                    ${safeColor(
                      theme.discord?.presence?.avatar?.borderRadius,
                      "rounded-lg",
                    )}
                    object-cover
                  `}
                />
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`font-medium ${safeColor(
                        theme.discord?.presence?.username?.color,
                        "text-white",
                      )}`}
                    >
                      {discordData.presence.user.username}
                    </span>
                  </div>
                  <span
                    className={`text-sm ${safeColor(
                      theme.discord?.presence?.username?.secondaryColor,
                      "text-white/60",
                    )}`}
                  >
                    @{discordData.presence.user.username.toLowerCase()}
                  </span>
                </div>
              </div>

              {discordData.presence.activities?.[0] && (
                <>
                  <div className="relative my-4">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-white/[0.08]" />
                    </div>
                    <div className="relative flex justify-center text-center">
                      <span className="bg-black/40 px-3 text-[11px] font-medium tracking-wider text-white/20 backdrop-blur-sm">
                        PLAYING
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <img
                      src={`https://cdn.discordapp.com/app-icons/363445589247131668/f2b60e350a2097289b3b0b877495e55f.webp?size=160&keep_aspect_ratio=false`}
                      alt="Activity icon"
                      className="w-12 h-12 rounded-lg"
                    />
                    <div className="flex flex-col">
                      <span className="text-[13px] font-medium text-white/80">
                        {discordData.presence.activities[0].name}
                      </span>
                      {discordData.presence.activities[0].timestamps?.start && (
                        <span className="text-xs text-white/50">
                          {formatDuration(
                            new Date(
                              discordData.presence.activities[0].timestamps.start,
                            ),
                          )}{" "}
                          elapsed
                        </span>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {discordData?.guild && (
            <div
              className={`
              ${safeColor(theme.discord?.guild?.backgroundColor, "bg-black/40")}
              border
              ${safeColor(
                theme.discord?.guild?.borderColor,
                "border-primary/10",
              )}
              rounded-lg p-6 space-y-4
            `}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <img
                    src={`https://cdn.discordapp.com/icons/${discordData.guild.id}/${discordData.guild.icon}.png`}
                    alt={discordData.guild.name}
                    className={`
                      ${theme.discord?.guild?.avatar?.size || "w-16 h-16"}
                      ${
                        theme.discord?.guild?.avatar?.borderRadius ||
                        "rounded-full"
                      }
                    `}
                  />
                  <div>
                    <h3
                      className={`
                      ${theme.discord?.guild?.title?.size || "text-xl"}
                      ${theme.discord?.guild?.title?.weight || "font-bold"}
                      ${safeColor(
                        theme.discord?.guild?.title?.color,
                        "text-white",
                      )}
                    `}
                    >
                      {discordData.guild.name}
                    </h3>
                    <div className="text-white/60 flex items-center gap-2">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                        {discordData.approximate_presence_count.toLocaleString()}{" "}
                        online
                      </span>
                      <span>•</span>
                      <span>
                        {(
                          discordData.approximate_member_count -
                          discordData.approximate_presence_count
                        ).toLocaleString()}{" "}
                        offline
                      </span>
                    </div>
                  </div>
                </div>
                <Button
                  text="Join Server"
                  className={`
                    !text-sm
                    ${safeColor(
                      theme.discord?.guild?.button?.backgroundColor,
                      "bg-[#5865F2]",
                    )}
                    ${safeColor(
                      theme.discord?.guild?.button?.hoverColor,
                      "hover:bg-[#4752C4]",
                    )}
                  `}
                  onClick={() =>
                    window.open("https://discord.gg/emogirls", "_blank")
                  }
                />
              </div>
              {discordData.guild.description && (
                <p className="text-white/80">{discordData.guild.description}</p>
              )}
            </div>
          )}

          <div className="space-y-3">
            {userData.links.map((link, index) => (
              <motion.a
                key={link.id}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`
                  flex items-center justify-between p-4
                  ${safeColor(theme.links?.backgroundColor, "bg-black/40")}
                  ${safeColor(theme.links?.hoverColor, "hover:bg-black/60")}
                  backdrop-blur-sm border
                  ${safeColor(theme.links?.borderColor, "border-primary/10")}
                  rounded-lg transition-all group
                `}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`
                    ${safeColor(
                      theme.links?.icon?.backgroundColor,
                      "bg-black/20",
                    )}
                    ${safeColor(theme.links?.icon?.size, "w-10 h-10")}
                    ${safeColor(theme.links?.icon?.borderRadius, "rounded-lg")}
                    flex items-center justify-center
                  `}
                  >
                    <img
                      src={link.iconUrl}
                      alt={link.title}
                      className={`
                        ${safeColor(theme.links?.icon?.size, "w-5 h-5")}
                        ${safeColor(
                          theme.links?.icon?.size,
                          "brightness-0 invert",
                        )}
                      `}
                    />
                  </div>
                  <div className="flex flex-col items-start">
                    <span
                      className={`
                      ${safeColor(
                        theme.links?.text?.primaryColor,
                        "text-white",
                      )}
                      font-medium text-sm group-hover:text-primary transition-colors
                    `}
                    >
                      {link.title}
                    </span>
                    <span
                      className={`
                      ${safeColor(
                        theme.links?.text?.secondaryColor,
                        "text-white/40",
                      )}
                      text-xs
                    `}
                    >
                      {link.clicks.toLocaleString()} clicks
                    </span>
                  </div>
                </div>
                <IconExternalLink
                  className={`
                    ${safeColor(theme.links?.text?.hoverColor, "text-primary")}
                    w-4 h-4 transition-colors
                  `}
                />
              </motion.a>
            ))}
          </div>

          <div className="pt-8 text-center">
            <Link
              href="/"
              className="text-white/40 hover:text-primary transition-colors text-sm"
            >
              powered by emogir.ls
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
