"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  FaGithub,
  FaDiscord,
  FaTwitter,
  FaTwitch,
  FaYoutube,
  FaLink,
  FaSpotify,
} from "react-icons/fa";
import Iphone15Pro from "@/components/magicui/iphone-15-pro";
import LayoutThree from "@/app/layouts/LayoutThree";

const showcaseProfiles = [
  {
    id: "modern",
    name: "Modern Layout",
    username: "showcase",
    bio: "Full customization with animated effects, gradient themes, and dynamic content.",
    theme: "modern",
    avatar: "/placeholder.svg?height=100&width=100",
    background: "bg-gradient-to-br from-primary to-secondary",
    links: [
      { icon: FaDiscord, label: "Join Discord", url: "#", highlight: true },
      { icon: FaSpotify, label: "Listen on Spotify", url: "#" },
      { icon: FaGithub, label: "View Projects", url: "#" },
      { icon: FaLink, label: "Portfolio Website", url: "#" },
    ],
    screenshot: "https://r.emogir.ls/HjvKjgg.png",
    stats: {
      followers: "2.5k+",
      views: "100k+",
    },
  },
  {
    id: "discord",
    name: "Discord Layout",
    username: "gamer",
    bio: "Live Discord presence, server widget, and real-time activity tracking.",
    theme: "discord",
    avatar: "/placeholder.svg?height=100&width=100",
    background: "bg-[#5865F2]/10",
    links: [
      { icon: FaTwitch, label: "Watch Live", url: "#", highlight: true },
      { icon: FaYoutube, label: "Latest Videos", url: "#" },
      { icon: FaDiscord, label: "Gaming Server", url: "#" },
      { icon: FaTwitter, label: "Updates", url: "#" },
    ],
    screenshot: "https://r.emogir.ls/HjvKjgg.png",
    stats: {
      followers: "48K",
      views: "1.2M",
    },
  },
  {
    id: "console",
    name: "Console Layout",
    username: "dev",
    bio: "Terminal-style interface with custom commands and interactive elements.",
    theme: "console",
    avatar: "/placeholder.svg?height=100&width=100",
    background: "bg-black",
    links: [
      { icon: FaGithub, label: "Open Source", url: "#", highlight: true },
      { icon: FaLink, label: "Dev Blog", url: "#" },
      { icon: FaTwitter, label: "Tech Updates", url: "#" },
      { icon: FaDiscord, label: "Dev Community", url: "#" },
    ],
    screenshot: "https://r.emogir.ls/HjvKjgg.png",
    stats: {
      followers: "32K",
      views: "780K",
    },
  },
];

const sampleUserData = {
  user: {
    id: "123",
    name: showcaseProfiles[0].name,
    avatar: showcaseProfiles[0].avatar,
    banner: null,
    created_at: new Date().toISOString(),
  },
  colors: {
    profile: {
      type: "gradient" as "gradient" | "linear",
      linear_color: "",
      gradient_colors: [
        { color: "#ff3379", position: 0 },
        { color: "#7c1f4e", position: 100 },
      ],
    },
    elements: {
      bio: { type: "linear" as const, color: "#ffffff" },
      status: { type: "linear" as const, color: "#22c55e" },
    },
  },
  presence: {
    status: "online",
    activities: [
      {
        name: "Spotify",
        type: "ActivityType.listening",
        details: "Never Gonna Give You Up",
        state: "Rick Astley",
        start: Date.now(),
        end: Date.now() + 1000 * 60 * 3,
        album_cover_url: "/placeholder.svg",
      },
    ],
  },
  bio: "Professional gamer & content creator. Join my Discord for exclusive content!",
  background_url: null,
  glass_effect: true,
  links: [
    { type: "twitch", url: "#" },
    { type: "youtube", url: "#" },
    { type: "discord", url: "#" },
    { type: "twitter", url: "#" },
  ],
  click: {
    enabled: false,
    text: "",
  },
};

export function Showcase() {
  const [activeProfile, setActiveProfile] = useState(showcaseProfiles[0].id);

  const userData = {
    ...sampleUserData,
    user: {
      ...sampleUserData.user,
      name: showcaseProfiles.find((p) => p.id === activeProfile)?.name || "",
      avatar:
        showcaseProfiles.find((p) => p.id === activeProfile)?.avatar || "",
    },
    bio: showcaseProfiles.find((p) => p.id === activeProfile)?.bio || "",
    links:
      showcaseProfiles
        .find((p) => p.id === activeProfile)
        ?.links.map((link) => ({
          type: link.icon.name.toLowerCase().replace("fa", ""),
          url: link.url,
        })) || [],
  };

  return (
    <section className="relative py-24 overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <div className="absolute left-1/4 top-1/4 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[100px]" />
        <div className="absolute right-1/4 bottom-1/4 w-[500px] h-[500px] bg-secondary/5 rounded-full blur-[100px]" />
        <div className="absolute right-1/4 top-1/2 w-[500px] h-[500px] bg-primary/3 rounded-full blur-[100px]" />
      </div>

      <div className="max-w-[1200px] mx-auto px-6">
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <span className="inline-block px-4 py-1.5 text-xs font-medium text-primary border border-primary/30 rounded-full mb-8">
              Showcase
            </span>
          </motion.div>

          <motion.h2
            className="text-4xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-white to-white/70"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            Choose your style{" "}
            <span className="relative inline-block">
              <span className="relative bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                effortlessly
              </span>
            </span>
          </motion.h2>

          <motion.p
            className="text-base text-white/60 max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            Create your perfect online presence with our selection of
            professionally designed layouts. Each theme is fully customizable to
            match your brand and style.
          </motion.p>
        </div>

        <div className="flex justify-center mb-16">
          <div className="inline-flex bg-darker/80 backdrop-blur-sm rounded-full p-1.5 border border-white/[0.08]">
            {showcaseProfiles.map((profile) => (
              <button
                key={profile.id}
                onClick={() => setActiveProfile(profile.id)}
                className={`px-6 py-2 rounded-full text-sm font-medium transition-all duration-300 ${
                  activeProfile === profile.id
                    ? "bg-primary text-white shadow-lg shadow-primary/25"
                    : "text-white/60 hover:text-white shadow-none"
                }`}
              >
                {profile.id === "modern"
                  ? "Modern"
                  : profile.id === "discord"
                    ? "Discord"
                    : "Console"}
              </button>
            ))}
          </div>
        </div>

        <div className="grid lg:grid-cols-2 items-center">
          <motion.div
            className="relative order-2 lg:order-1"
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <div className="relative max-w-[280px] aspect-[433/882] mx-auto">
              <div className="absolute -z-10 inset-0 bg-gradient-to-b from-primary/5 to-secondary/5 blur-xl rounded-[32px]" />
              <Iphone15Pro
                className="w-full h-full"
                src={
                  showcaseProfiles.find((p) => p.id === activeProfile)
                    ?.screenshot
                }
              />
            </div>
          </motion.div>

          <motion.div
            className="order-1 lg:order-2 select-none"
            initial={{ opacity: 0, x: 50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            {showcaseProfiles.map((profile) => (
              <div
                key={profile.id}
                className={`transition-all duration-500 ${
                  activeProfile === profile.id
                    ? "opacity-100"
                    : "opacity-0 hidden"
                }`}
              >
                <div className="mb-8">
                  <h3 className="text-2xl font-bold mb-4 text-white">
                    {profile.id === "modern"
                      ? "Modern Layout"
                      : profile.id === "discord"
                        ? "Discord Layout"
                        : "Console Layout"}
                  </h3>

                  <p className="text-white/60 mb-6">{profile.bio}</p>

                  <div className="space-y-4">
                    {[
                      {
                        title:
                          profile.id === "modern"
                            ? "Grow Your Community"
                            : profile.id === "discord"
                              ? "Showcase Your Work"
                              : "Increase Conversions",
                        description:
                          profile.id === "modern"
                            ? "Direct followers to your most important platforms and boost your subscriber count across channels."
                            : profile.id === "discord"
                              ? "Create a beautiful gallery of your work that's easy to share and helps you get discovered."
                              : "Drive traffic to your website, products, and services with a professional online presence.",
                      },
                      {
                        title:
                          profile.id === "modern"
                            ? "Track Performance"
                            : profile.id === "discord"
                              ? "Build Your Brand"
                              : "Professional Appearance",
                        description:
                          profile.id === "modern"
                            ? "Monitor which links get the most clicks and optimize your profile to maximize engagement."
                            : profile.id === "discord"
                              ? "Establish a consistent visual identity that helps you stand out in a crowded market."
                              : "Create a polished, branded experience that builds trust with potential customers.",
                      },
                    ].map((item, i) => (
                      <div
                        key={i}
                        className="bg-darker/80 backdrop-blur-sm border border-white/[0.08] p-4 rounded-xl hover:border-primary/20 transition-colors"
                      >
                        <h4 className="font-medium text-white mb-1">
                          {item.title}
                        </h4>
                        <p className="text-sm text-white/60">
                          {item.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex gap-4">
                  <button className="px-6 py-2.5 bg-primary hover:bg-primary/90 text-white rounded-lg font-medium transition-colors">
                    Try this template
                  </button>
                  <button className="px-6 py-2.5 border border-white/[0.08] hover:border-primary/30 text-white/80 hover:text-white rounded-lg transition-colors">
                    Learn more
                  </button>
                </div>
              </div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
