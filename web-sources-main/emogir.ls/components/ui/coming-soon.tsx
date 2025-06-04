"use client";

import { motion } from "framer-motion";
import { Button } from "./button";
import { FaDiscord, FaArrowLeft } from "react-icons/fa";

export function ComingSoon() {
  return (
    <div className="min-h-screen bg-darker flex items-center justify-center p-4">
      <div className="absolute inset-0 -z-10 animated-bg" />

      <div className="absolute inset-0 -z-10">
        <div className="absolute left-1/4 top-1/4 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[100px]" />
        <div className="absolute right-1/4 bottom-1/4 w-[500px] h-[500px] bg-secondary/5 rounded-full blur-[100px]" />
        <div className="absolute right-1/4 top-1/2 w-[500px] h-[500px] bg-primary/3 rounded-full blur-[100px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-2xl w-full text-center"
      >
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <span className="inline-block px-4 py-1.5 text-xs font-medium text-primary border border-primary/30 rounded-full mb-8">
            Coming Soon
          </span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-4xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-white to-white/70"
        >
          This page is under{" "}
          <span className="relative inline-block">
            <span className="relative bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              construction
            </span>
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-base text-white/60 max-w-2xl mx-auto mb-8"
        >
          We're working hard to bring you something amazing. Join our Discord
          community to stay updated and be the first to know when we launch.
        </motion.p>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="flex justify-center gap-4"
        >
          <Button
            href="/"
            text="Back to Home"
            icon={FaArrowLeft}
            className="bg-darker/80 backdrop-blur-sm border border-white/[0.08] hover:border-primary/20"
          />
          <Button
            href="https://discord.gg/emogirls"
            icon={FaDiscord}
            text="Join Discord"
            className="bg-[#5865F2] hover:bg-[#4752C4]"
          />
        </motion.div>
      </motion.div>
    </div>
  );
}
