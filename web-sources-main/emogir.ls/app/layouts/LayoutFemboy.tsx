"use client";

import { motion, useAnimation } from "framer-motion";
import React, { useState, useEffect } from "react";
import { DiscordData } from "@/app/types/discord";
import Image from "next/image";
import { SOCIAL_ICONS } from "@/config/icons";

interface LayoutFemboyProps {
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
    presence?: {
      status: string;
      activities: any[];
    };
    badges?: string[];
  };
  presence?: {
    status: string;
    activities: any[];
  };
  discordData: DiscordData | null;
  theme?: {
    primaryColor?: string;
    secondaryColor?: string;
    accentColor?: string;
    backgroundColor?: string;
  };
}

const ThighHighSock = () => (
  <div className="absolute -left-24 top-1/2 -translate-y-1/2 w-24 h-[400px] hidden lg:block">
    <motion.div
      className="w-full h-full relative"
      animate={{
        y: [0, -10, 0],
      }}
      transition={{
        duration: 4,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    >
      <div className="absolute inset-0 bg-pink-200 rounded-full" />

      <div className="absolute top-8 inset-x-0 flex flex-col gap-4">
        <div className="h-4 bg-white/50 rounded-full" />
        <div className="h-4 bg-white/50 rounded-full" />
      </div>

      <div className="absolute top-4 left-1/2 -translate-x-1/2">
        <motion.div
          className="w-12 h-8 bg-pink-400 rounded-full relative"
          animate={{
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-4 h-4 bg-white/30 rounded-full" />
          </div>
        </motion.div>
      </div>

      <div className="absolute top-0 inset-x-0 flex justify-center gap-1">
        {[...Array(5)].map((_, i) => (
          <motion.div
            key={i}
            className="w-4 h-4 bg-pink-300 rounded-full"
            animate={{
              y: [0, -2, 0],
            }}
            transition={{
              duration: 2,
              delay: i * 0.2,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>
    </motion.div>
  </div>
);

export default function LayoutFemboy({
  userData,
  discordData,
  theme,
}: LayoutFemboyProps) {
  const [sparklePosition, setSparklePosition] = useState({ x: 0, y: 0 });
  const controls = useAnimation();

  const handleMouseMove = (e: React.MouseEvent) => {
    const { clientX, clientY } = e;
    const { left, top } = e.currentTarget.getBoundingClientRect();
    setSparklePosition({
      x: clientX - left,
      y: clientY - top,
    });
  };

  const getIconUrl = (url: string) => {
    const socialIcon = SOCIAL_ICONS.find((icon) => url.includes(icon.url));
    return (
      socialIcon?.iconUrl || "https://r.emogir.ls/assets/icons/svg/default.svg"
    );
  };

  return (
    <div className="min-h-screen w-full bg-gradient-to-b from-pink-100 via-purple-100 to-blue-100 flex items-center justify-center p-4">
      <div className="relative w-full max-w-[900px]">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full rounded-[30px] overflow-hidden bg-white/80 backdrop-blur-lg shadow-xl relative"
          onMouseMove={handleMouseMove}
        >
          <div className="absolute left-0 top-0 bottom-0 w-24 hidden lg:block">
            <ThighHighSock />
          </div>

          <div className="lg:pl-24">
            <motion.div
              className="pointer-events-none absolute w-8 h-8 text-yellow-300"
              animate={{
                x: sparklePosition.x - 16,
                y: sparklePosition.y - 16,
                scale: [1, 1.2, 1],
                rotate: [0, 90, 180, 270, 360],
              }}
              transition={{ duration: 0.5 }}
            >
              ✧
            </motion.div>

            <div className="h-[200px] relative bg-gradient-to-r from-pink-300 via-purple-300 to-blue-300 overflow-hidden">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-white text-opacity-20 text-8xl font-bold animate-pulse">
                  ✧･ﾟ: *✧･ﾟ:*
                </div>
              </div>
              <div className="absolute top-0 left-1/2 -translate-x-1/2 flex gap-8">
                <motion.div
                  className="w-12 h-12 bg-pink-400 rounded-full transform origin-bottom -rotate-45"
                  animate={{ rotate: [-45, -30, -45] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
                <motion.div
                  className="w-12 h-12 bg-pink-400 rounded-full transform origin-bottom rotate-45"
                  animate={{ rotate: [45, 30, 45] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              </div>
            </div>

            <div className="relative px-8 pb-8">
              <div className="absolute -top-16 left-8">
                <div className="w-32 h-32 rounded-full border-4 border-white overflow-hidden relative">
                  <div className="absolute inset-0 bg-gradient-to-r from-pink-200 to-purple-200 opacity-30 z-10" />
                  <Image
                    src={userData.avatar}
                    alt="Profile"
                    fill
                    className="object-cover"
                  />
                  <motion.div
                    className="absolute inset-0 border-4 border-pink-300 rounded-full"
                    animate={{
                      scale: [1, 1.1, 1],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                    }}
                  />
                </div>
              </div>

              <div className="pt-20 pb-4">
                <motion.h1
                  className="text-2xl font-bold text-pink-500 flex items-center gap-2"
                  whileHover={{ scale: 1.05 }}
                >
                  <span className="text-sm">♡</span>
                  {userData.displayName}
                  <span className="text-sm">♡</span>
                </motion.h1>
                <p className="text-gray-400">@{userData.username}</p>

                {userData.badges && userData.badges.length > 0 && (
                  <div className="mt-2 inline-flex items-center rounded-full px-1 py-1 bg-pink-100/50 border border-pink-200">
                    <div className="flex gap-1">
                      {userData.badges.map((badge) => (
                        <div
                          key={badge}
                          className="group relative flex items-center p-1 transition-all duration-200 hover:scale-110"
                        >
                          <Image
                            src={`/badges/${badge.toLowerCase()}.svg`}
                            alt={badge}
                            width={16}
                            height={16}
                            className="opacity-75 hover:opacity-100"
                          />
                          <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1 px-2 py-1 text-xs font-medium bg-pink-100/80 text-pink-700 rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                            {badge.replace("_", " ")}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <p className="mt-2 text-gray-600 italic">
                  ˗ˏˋ {userData.bio} ˎˊ˗
                </p>
              </div>

              {userData.presence && (
                <motion.div
                  className="mb-6 p-4 rounded-xl bg-gradient-to-r from-pink-100/50 to-purple-100/50 border border-pink-200"
                  whileHover={{ scale: 1.02 }}
                >
                  <div className="flex items-center gap-4">
                    <motion.div
                      className={`w-3 h-3 rounded-full ${
                        userData.presence?.status === "online"
                          ? "bg-green-400"
                          : userData.presence?.status === "idle"
                            ? "bg-yellow-400"
                            : userData.presence?.status === "dnd"
                              ? "bg-red-400"
                              : "bg-gray-400"
                      }`}
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    />

                    {userData.presence.activities?.[0]?.name === "Spotify" ? (
                      <div className="flex items-center gap-3 flex-1">
                        {userData.presence.activities[0].album_cover_url && (
                          <Image
                            src={
                              userData.presence.activities[0].album_cover_url
                            }
                            alt="Album cover"
                            width={40}
                            height={40}
                            className="rounded-lg"
                            unoptimized
                          />
                        )}
                        <div className="min-w-0">
                          <div className="text-gray-700 font-medium truncate">
                            {userData.presence.activities[0].details ||
                              "Unknown Track"}
                          </div>
                          <div className="text-gray-500 text-sm truncate">
                            by{" "}
                            {userData.presence.activities[0].state ||
                              "Unknown Artist"}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <span className="text-gray-600">
                        ⋆｡°✩{" "}
                        {userData.presence.activities?.[0]?.state ||
                          "Just vibing~"}{" "}
                        ⋆｡°✩
                      </span>
                    )}
                  </div>
                </motion.div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {userData.links.map((link) => (
                  <motion.a
                    key={link.id}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-4 rounded-xl bg-gradient-to-r from-pink-100/50 to-purple-100/50 
                                             border border-pink-200 backdrop-blur-sm
                                             flex items-center gap-3 group relative overflow-hidden"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <motion.div
                      className="absolute inset-0 opacity-0 group-hover:opacity-100"
                      initial={false}
                      animate={{
                        background: [
                          "radial-gradient(circle at 50% 50%, rgba(255,182,193,0.2) 0%, transparent 50%)",
                          "radial-gradient(circle at 50% 50%, rgba(255,182,193,0.2) 0%, transparent 100%)",
                        ],
                      }}
                      transition={{ duration: 1, repeat: Infinity }}
                    />

                    <div className="w-10 h-10 rounded-full bg-white p-2 shadow-inner">
                      <Image
                        src={getIconUrl(link.url)}
                        alt={link.title}
                        width={24}
                        height={24}
                        className="w-full h-full object-contain"
                        unoptimized
                      />
                    </div>
                    <div>
                      <div className="font-medium text-gray-700">
                        ˗ˏˋ {link.title} ˎˊ˗
                      </div>
                      <div className="text-sm text-gray-500">
                        {link.clicks} clicks ♡
                      </div>
                    </div>
                  </motion.a>
                ))}
              </div>

              <div className="mt-8 text-center">
                <motion.div
                  className="text-gray-400 text-sm"
                  animate={{
                    scale: [1, 1.1, 1],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                  }}
                >
                  ✧･ﾟ: *✧･ﾟ:* 💖 *:･ﾟ✧*:･ﾟ✧
                </motion.div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
