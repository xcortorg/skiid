"use client";

import { motion } from "framer-motion";
import {
  SiDiscord,
  SiTwitch,
  SiYoutube,
  SiX,
  SiInstagram,
  SiTiktok,
  SiGithub,
  SiSpotify,
  SiReddit,
  SiSnapchat,
  SiLastdotfm,
} from "react-icons/si";

const integrations = [
  { name: "Discord", icon: SiDiscord, color: "#5865F2", available: true },
  { name: "Last.fm", icon: SiLastdotfm, color: "#D51007", available: true },
  { name: "Spotify", icon: SiSpotify, color: "#1DB954", available: false },
  { name: "GitHub", icon: SiGithub, color: "#181717", available: false },
  { name: "Twitter", icon: SiX, color: "#1DA1F2", available: false },
  { name: "Instagram", icon: SiInstagram, color: "#E4405F", available: false },
  { name: "Reddit", icon: SiReddit, color: "#FF4500", available: false },
  { name: "YouTube", icon: SiYoutube, color: "#FF0000", available: false },
  { name: "Twitch", icon: SiTwitch, color: "#9146FF", available: false },
  { name: "TikTok", icon: SiTiktok, color: "#000000", available: false },
];

export function Integrations() {
  return (
    <section className="py-24 relative">
      <div className="absolute inset-0 -z-10">
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl"></div>
        <div className="absolute top-0 right-0 w-96 h-96 bg-secondary/5 rounded-full blur-3xl"></div>
      </div>

      <div className="max-w-[1200px] mx-auto px-4">
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <span className="inline-block px-4 py-1.5 text-xs font-medium text-primary border border-primary/30 rounded-full mb-4">
              Integrations
            </span>
          </motion.div>

          <motion.h2
            className="text-4xl font-bold mb-6"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            Connect Your{" "}
            <span className="relative inline-block">
              <span className="absolute inset-0 bg-primary/20 blur-[20px] rounded-md"></span>
              <span className="relative bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                Digital Presence
              </span>
            </span>
          </motion.h2>

          <motion.p
            className="text-base opacity-70 max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            Seamlessly integrate all your social platforms and online presence
            in one beautiful profile.
          </motion.p>
        </div>

        <motion.div
          className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          {integrations.map((integration, index) => (
            <motion.div
              key={integration.name}
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              whileHover={{ scale: 1.05 }}
              className="relative group"
            >
              <div
                className={`relative bg-darker p-6 rounded-xl border border-white/5 ${!integration.available ? "opacity-50" : ""}`}
              >
                <integration.icon
                  className="w-8 h-8 mx-auto mb-4"
                  style={{ color: integration.color }}
                />
                <p className="text-center text-sm font-medium">
                  {integration.name}
                </p>
                {!integration.available && (
                  <span className="absolute top-2 right-2 text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                    Soon
                  </span>
                )}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
