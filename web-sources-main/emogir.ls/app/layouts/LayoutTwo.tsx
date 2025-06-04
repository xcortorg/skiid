"use client";

import { useEffect, useState } from "react";
import { JetBrains_Mono } from "next/font/google";
import { motion, useMotionValue, useTransform } from "framer-motion";
import { DiscordData } from "@/app/types/discord";

const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"] });

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
    /^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[0-1]?\.?\d*\s*\)$/,
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

interface LayoutTwoProps {
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

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: -20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: "easeOut",
    },
  },
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

const TypingText = ({ userData }: { userData: UserData }) => {
  const [text, setText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const timeout = setTimeout(
      () => {
        if (!isDeleting) {
          if (text.length < userData.bio.length) {
            setText(userData.bio.slice(0, text.length + 1));
          } else {
            setTimeout(() => setIsDeleting(true), 2000);
          }
        } else {
          if (text.length > 0) {
            setText(text.slice(0, -1));
          } else {
            setTimeout(() => setIsDeleting(false), 1000);
          }
        }
      },
      isDeleting ? 150 : 200,
    );

    return () => clearTimeout(timeout);
  }, [text, isDeleting, userData.bio]);

  return <span className="text-zinc-300 text-sm">{text}|</span>;
};

export default function LayoutTwo({
  userData,
  discordData,
  slug,
  theme = {},
}: LayoutTwoProps) {
  const [visible, setVisible] = useState(true);
  const [guildInfo, setGuildInfo] = useState<DiscordData | null>(null);

  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const rotateX = useTransform(y, [-300, 300], [10, -10]);
  const rotateY = useTransform(x, [-300, 300], [-10, 10]);

  useEffect(() => {
    setGuildInfo(discordData);
  }, [discordData]);

  const getAnimationStyle = () => {
    const textConfig =
      typeof theme.blurScreen?.text === "string"
        ? {}
        : theme.blurScreen?.text || {};
    const type = textConfig.animation?.type || "none";
    const speed = textConfig.animation?.speed || "normal";

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

  const serverIconUrl = guildInfo?.guild?.icon
    ? `https://cdn.discordapp.com/icons/${guildInfo.guild.id}/${guildInfo.guild.icon}.png`
    : "/0.png";

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

      <div
        className={`min-h-screen flex items-center justify-center ${jetbrainsMono.className}`}
      >
        <div className="fixed inset-0 z-0">
          <img
            src="https://r2.guns.lol/cc0484e9-3843-4660-862e-f6a20b79236e.jpg"
            alt=""
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-purple-900/30 to-orange-700/30" />
        </div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="w-[800px] max-w-[95vw] relative z-10"
          style={{
            perspective: 2000,
          }}
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const centerX = rect.x + rect.width / 2;
            const centerY = rect.y + rect.height / 2;
            x.set(e.clientX - centerX);
            y.set(e.clientY - centerY);
          }}
          onMouseLeave={() => {
            x.set(0);
            y.set(0);
          }}
        >
          <motion.div
            variants={itemVariants}
            className="absolute inset-0"
            style={{
              backdropFilter: `blur(${
                theme.container?.backdropBlur || "24px"
              })`,
              WebkitBackdropFilter: `blur(${
                theme.container?.backdropBlur || "24px"
              })`,
              borderRadius: theme.container?.borderRadius || "32px",
              rotateX,
              rotateY,
            }}
          />
          <motion.div
            variants={itemVariants}
            className="relative rounded-[32px] backdrop-blur-2xl"
            style={{
              backgroundColor: safeColor(
                theme.container?.backgroundColor,
                "rgba(0, 0, 0, 0.2)",
              ),
              borderWidth: theme.container?.borderWidth || "1px",
              borderColor: safeColor(
                theme.container?.borderColor,
                "rgba(255, 255, 255, 0.1)",
              ),
              boxShadow: theme.container?.glowColor
                ? `0 0 ${theme.container.glowIntensity || "30px"} ${
                    theme.container.glowColor
                  }`
                : "0 0 30px rgba(0,0,0,0.3)",
              rotateX,
              rotateY,
              transition: "all 0.15s ease",
            }}
          >
            <motion.div variants={itemVariants} className="p-8">
              <motion.div variants={itemVariants} className="flex gap-4 mb-8">
                <motion.div variants={itemVariants} className="relative">
                  <motion.img
                    src="https://cdn.discordapp.com/avatars/442626774841556992/e18f44d77f1a91c939ba827a964c9f05.webp?size=128"
                    alt=""
                    className={`
                      ${theme.avatar?.size || "w-[100px] h-[100px]"}
                      ${theme.avatar?.borderRadius || "rounded-full"}
                      ${theme.avatar?.borderWidth || "border-2"}
                      border
                    `}
                    style={{
                      borderColor: safeColor(
                        theme.avatar?.borderColor,
                        "rgba(255, 255, 255, 0.05)",
                      ),
                      boxShadow: theme.avatar?.glow
                        ? `0 0 ${theme.avatar.glow.intensity || "20px"} ${
                            theme.avatar.glow.color
                          }`
                        : "none",
                    }}
                  />
                </motion.div>
                <div>
                  <motion.div
                    variants={itemVariants}
                    className="flex items-center gap-2"
                  >
                    <div className="group relative">
                      <span
                        className={`
                          cursor-help
                          ${theme.text?.title?.size || "text-[28px]"}
                          ${theme.text?.title?.weight || "font-medium"}
                        `}
                        style={{
                          color: safeColor(theme.text?.title?.color, "#ffffff"),
                        }}
                      >
                        {userData.displayName}
                      </span>
                      <div
                        className="absolute -top-7 left-1/2 -translate-x-1/2 bg-black/80 backdrop-blur-md px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap"
                        style={{
                          fontSize: theme.text?.username?.size || "12px",
                          color: safeColor(
                            theme.text?.username?.color,
                            "#ffffff",
                          ),
                        }}
                      >
                        @{userData.username}
                      </div>
                    </div>
                  </motion.div>
                  <motion.div variants={itemVariants} className="mt-0.5">
                    <TypingText userData={userData} />
                  </motion.div>
                </div>
              </motion.div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-6 mb-8">
                {discordData?.presence && (
                  <div
                    className="flex items-center gap-4 p-3 backdrop-blur-xl rounded-2xl w-full"
                    style={{
                      backgroundColor: safeColor(
                        theme.discord?.presence?.backgroundColor,
                        "rgba(0, 0, 0, 0.2)",
                      ),
                      borderWidth: "1px",
                      borderColor: safeColor(
                        theme.discord?.presence?.borderColor,
                        "rgba(255, 255, 255, 0.05)",
                      ),
                    }}
                  >
                    <img
                      src={`https://cdn.discordapp.com/avatars/${discordData.presence.user.id}/${discordData.presence.user.avatar}.webp?size=128`}
                      alt=""
                      className={`${
                        theme.discord?.presence?.avatar?.size || "w-10 h-10"
                      } ${
                        theme.discord?.presence?.avatar?.borderRadius ||
                        "rounded-lg"
                      }`}
                    />
                    <div className="flex-1">
                      <div
                        style={{
                          color: safeColor(
                            theme.discord?.presence?.text?.primaryColor,
                            "#ffffff",
                          ),
                        }}
                      >
                        {discordData.presence.user.username}
                      </div>
                      <div
                        style={{
                          color: safeColor(
                            theme.discord?.presence?.text?.secondaryColor,
                            "rgb(113, 113, 122)",
                          ),
                        }}
                      >
                        {discordData.presence.activities?.[0]?.name || "Online"}
                      </div>
                    </div>
                  </div>
                )}

                {guildInfo && (
                  <div
                    className="flex items-center gap-4 p-3 backdrop-blur-xl rounded-2xl w-full"
                    style={{
                      backgroundColor: safeColor(
                        theme.discord?.guild?.backgroundColor,
                        "rgba(0, 0, 0, 0.2)",
                      ),
                      borderWidth: "1px",
                      borderColor: safeColor(
                        theme.discord?.guild?.borderColor,
                        "rgba(255, 255, 255, 0.05)",
                      ),
                    }}
                  >
                    <img
                      src={serverIconUrl}
                      alt=""
                      className={`${
                        theme.discord?.guild?.avatar?.size || "w-10 h-10"
                      } ${
                        theme.discord?.guild?.avatar?.borderRadius ||
                        "rounded-lg"
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div
                        style={{
                          color: safeColor(
                            theme.discord?.guild?.text?.primaryColor,
                            "#ffffff",
                          ),
                        }}
                      >
                        {guildInfo.guild?.name || "Loading..."}
                      </div>
                      <div
                        style={{
                          color: safeColor(
                            theme.discord?.guild?.text?.secondaryColor,
                            "rgb(161, 161, 170)",
                          ),
                        }}
                      >
                        <span className="text-emerald-400">●</span>{" "}
                        {guildInfo.approximate_presence_count?.toLocaleString()}{" "}
                        Online •{" "}
                        {guildInfo.approximate_member_count?.toLocaleString()}{" "}
                        Members
                      </div>
                      <button
                        className="px-3 py-1 mt-1 rounded"
                        style={{
                          backgroundColor: safeColor(
                            theme.discord?.guild?.button?.backgroundColor,
                            "#22c55e",
                          ),
                          color: safeColor(
                            theme.discord?.guild?.button?.textColor,
                            "#ffffff",
                          ),
                        }}
                      >
                        Join
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div
                className={`flex justify-center mb-6 ${
                  theme.links?.gap || "gap-2"
                }`}
              >
                {userData.links.map((link, index) => (
                  <a
                    key={index}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`
                      ${
                        theme.links?.icon?.backgroundColor
                          ? "bg-black/20 p-2"
                          : ""
                      }
                      ${theme.links?.icon?.borderRadius || "rounded-lg"}
                    `}
                  >
                    <img
                      src={link.iconUrl}
                      alt={link.title}
                      className={`
    ${theme.links?.icon?.size || "w-8 h-8"}
    transition-transform duration-300 ease-out hover:scale-125 cursor-pointer
  `}
                      style={{
                        filter: `${
                          theme.links?.icon?.color === "#ffffff"
                            ? "brightness(0) invert(1)"
                            : ""
                        } ${
                          theme.links?.icon?.glow
                            ? `drop-shadow(0 0 ${
                                theme.links.icon.glow.intensity || "15px"
                              } ${theme.links.icon.glow.color})`
                            : ""
                        }`,
                      }}
                    />
                  </a>
                ))}
              </div>

              <div
                className="absolute bottom-8 left-8 flex items-center gap-1.5"
                style={{
                  color: safeColor(theme.stats?.color, "rgb(113, 113, 122)"),
                  fontSize: theme.stats?.size || "0.875rem",
                }}
              >
                <svg
                  viewBox="0 0 24 24"
                  className="w-4 h-4 fill-current"
                  style={{
                    color: safeColor(theme.stats?.iconColor, "currentColor"),
                  }}
                >
                  <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z" />
                </svg>
                <span>
                  {userData.links
                    .reduce((acc, link) => acc + link.clicks, 0)
                    .toLocaleString()}
                </span>
              </div>
            </motion.div>
          </motion.div>
        </motion.div>
      </div>
    </>
  );
}
