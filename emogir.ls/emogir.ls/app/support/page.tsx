"use client";

import { Header } from "@/components/ui/header";
import { Footer } from "@/components/ui/footer";
import { FaDiscord, FaArrowRight } from "react-icons/fa";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { ShineBorder } from "@/components/magicui/shine-border";

export default function SupportPage() {
  return (
    <>
      <div className="fixed inset-0 -z-10 animated-bg" />
      <div className="relative w-full bg-gradient-to-r from-primary/5 to-primary/10">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-[45px] py-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <span className="text-sm font-medium text-primary">
                New features released
              </span>
              <span className="hidden sm:block text-sm text-primary/60">
                Check out our latest updates
              </span>
            </div>

            <a
              href="https://discord.gg/emogirls"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 hover:bg-primary/20 text-primary transition-all duration-300 group"
            >
              <FaDiscord className="w-3.5 h-3.5" />
              <span className="text-sm font-medium">Join Discord</span>
              <FaArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
            </a>
          </div>
        </div>
      </div>
      <main className="mx-auto h-full w-full max-w-[1200px] px-[45px] py-0 relative">
        <Header />
        <section className="relative mt-[80px] mb-[150px] py-10">
          <div className="max-w-3xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-center"
            >
              <h1 className="text-4xl font-bold mb-6">Support Center</h1>
              <p className="text-lg opacity-60 mb-8">
                Need help? Our Discord community is the fastest way to get
                assistance.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="mb-12"
            >
              <ShineBorder
                className="transition-colors !min-w-0 w-full !border-0 bg-primary/5 rounded-lg overflow-hidden"
                color="#ff3379"
                borderRadius={12}
              >
                <div className="p-8 text-center">
                  <div className="flex justify-center mb-6">
                    <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
                      <FaDiscord className="w-8 h-8 text-primary" />
                    </div>
                  </div>
                  <h2 className="text-2xl font-bold mb-4">
                    Join Our Discord Community
                  </h2>
                  <p className="opacity-60 mb-6">
                    Get instant support, connect with other users, and stay
                    updated with the latest announcements.
                  </p>
                  <Button
                    href="https://discord.gg/emogirls"
                    text="Join Discord Server"
                    icon={FaArrowRight}
                    className="mx-auto"
                  />
                </div>
              </ShineBorder>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="grid grid-cols-1 md:grid-cols-2 gap-6"
            >
              <div className="bg-darker rounded-lg p-6 border border-primary/10">
                <h3 className="text-lg font-semibold mb-2">Support Hours</h3>
                <p className="opacity-60">
                  Our Discord moderators are typically active 24/7 across
                  different time zones.
                </p>
              </div>
              <div className="bg-darker rounded-lg p-6 border border-primary/10">
                <h3 className="text-lg font-semibold mb-2">Response Time</h3>
                <p className="opacity-60">
                  Most queries are answered within minutes in our Discord
                  server.
                </p>
              </div>
            </motion.div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
