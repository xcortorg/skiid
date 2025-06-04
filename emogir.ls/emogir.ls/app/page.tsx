"use client";

import { Header } from "@/components/ui/header";
import { useState, useEffect } from "react";
import {
  FaGithub,
  FaDiscord,
  FaTwitter,
  FaInstagram,
  FaArrowRight,
} from "react-icons/fa";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Footer } from "@/components/ui/footer";
import { Features } from "@/components/ui/features";
import { Showcase } from "@/components/ui/showcase";
import { FAQ } from "@/components/ui/faq";
import { CTA } from "@/components/ui/cta";
import { Integrations } from "@/components/ui/integrations";
import { HowItWorks } from "@/components/ui/how-it-works";
import { ShineBorder } from "@/components/magicui/shine-border";
import {
  IconCrown,
  IconMail,
  IconChartBar,
  IconPalette,
} from "@tabler/icons-react";
import { BarChart, Bar, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { TopUsersMarquee } from "@/components/ui/top-users-marquee";

const socials = [
  { icon: FaGithub, href: "https://github.com/emogir-ls" },
  { icon: FaDiscord, href: "https://discord.gg/emogirls" },
  { icon: FaTwitter, href: "https://twitter.com/emogir_ls" },
  { icon: FaInstagram, href: "https://instagram.com/emogir_ls" },
];

const data = [
  { name: "Mon", users: 19.2 },
  { name: "Tue", users: 14.5 },
  { name: "Wed", users: 12.4 },
  { name: "Thu", users: 19.3 },
  { name: "Fri", users: 15.2 },
  { name: "Sat", users: 17.8 },
  { name: "Sun", users: 20.1 },
];

export default function Home() {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const footer = document.querySelector("footer");
      if (footer && e.clientY < footer.offsetTop) {
        setMousePosition({ x: e.clientX, y: e.clientY });
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  return (
    <>
      <div className="fixed inset-0 -z-10 animated-bg" />
      <div className="relative w-full bg-gradient-to-r from-primary/5 to-primary/10">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            type: "spring",
            stiffness: 150,
            damping: 20,
          }}
          className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-[45px] py-2"
        >
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
        </motion.div>
      </div>
      <main className="mx-auto h-full w-full max-w-[1200px] px-[45px] py-0 relative">
        <Header />
        <section id="hero" className="relative mt-[80px] mb-[150px] py-10">
          <div
            className="absolute pointer-events-none opacity-70 blur-[100px] bg-primary rounded-full w-[300px] h-[300px] -z-10"
            style={{
              left: `${mousePosition.x * 0.05}px`,
              top: `${mousePosition.y * 0.05 - 150}px`,
              transition: "left 0.3s ease-out, top 0.3s ease-out",
            }}
          />

          <div className="absolute top-10 right-10 opacity-20 hidden md:block">
            <div className="w-40 h-40 border border-primary rounded-full" />
            <div className="w-60 h-60 border border-primary rounded-full absolute -top-10 -left-10" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            <div className="flex flex-col gap-1">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  type: "spring",
                  stiffness: 150,
                  damping: 20,
                }}
              >
                <Badge className="bg-darker border border-primary/10 text-primary px-4 py-1.5 cursor-pointer hover:bg-primary/10 transition-colors">
                  <span className="animate-pulse mr-2">●</span> Now in beta
                </Badge>
              </motion.div>

              <motion.h1
                className="text-3xl md:text-[52px] md:leading-tight font-semibold tracking-tighter"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  type: "spring",
                  stiffness: 200,
                  damping: 25,
                  duration: 0.6,
                }}
              >
                <div className="h-full w-full flex items-center">
                  <div className="flex flex-col gap-[15px] w-4/5">
                    <h1 className="text-3xl md:text-[52px] md:leading-tight font-semibold tracking-tighter">
                      <motion.span
                        className="underlined relative text-primary inline-block"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{
                          type: "spring",
                          stiffness: 200,
                          damping: 25,
                          duration: 0.3,
                        }}
                      >
                        <span>your socials</span>
                        <svg
                          className="animated-underline"
                          xmlns="http://www.w3.org/2000/svg"
                          width="100%"
                          height="8"
                          viewBox="0 0 410.262 14.388"
                        >
                          <path
                            d="M0,0S-4.619-8.391,97.131-8.391,407,0,407,0"
                            transform="translate(3.142 11.391)"
                          />
                        </svg>
                      </motion.span>
                      {" in "}
                      <br className="md:hidden" />
                      one place
                    </h1>
                  </div>
                </div>
              </motion.h1>

              <motion.p
                className="text-sm md:text-lg opacity-60 max-w-md"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
              >
                a premium solution for e-mails, image uploading & showing off
                your digital portfolio.
              </motion.p>

              <motion.div
                className="flex items-center gap-4 mt-2"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.3 }}
              >
                <Button
                  href="/register"
                  text="Get started"
                  icon={FaArrowRight}
                />
                <Button href="https://discord.gg/emogirls" icon={FaDiscord} />

                <div className="hidden md:flex items-center gap-4 ml-4">
                  <div className="flex items-center gap-2 text-sm">
                    <div className="flex items-center">
                      <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse mr-2" />
                      <span className="opacity-60">50k+ files hosted</span>
                    </div>
                  </div>
                </div>
              </motion.div>

              <motion.div
                className="mt-8 w-full max-w-2xl"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 0.4 }}
              >
                <TopUsersMarquee />
              </motion.div>
            </div>

            <motion.div
              className="relative hidden md:block"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.7, delay: 0.4 }}
            >
              <div className="relative select-none">
                <ShineBorder
                  className="transition-colors !min-w-0 w-full !border-0 bg-primary/5 rounded-lg overflow-hidden"
                  color="#ff3379"
                  borderRadius={12}
                >
                  <div className="">
                    <div className="grid grid-cols-2 gap-2 mb-4">
                      <div className="col-span-2">
                        <div className="flex items-center justify-between bg-darker rounded-lg p-4 border border-primary/10">
                          <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
                              <IconCrown className="w-6 h-6 text-primary" />
                            </div>
                            <div>
                              <div className="text-sm text-white/60">
                                Total Links Created
                              </div>
                              <div className="text-2xl font-bold">1,472</div>
                            </div>
                          </div>
                          <div className="text-primary text-sm font-medium px-3 py-1 rounded-full bg-primary/10">
                            +12% ↑
                          </div>
                        </div>
                      </div>

                      {[
                        { value: "99.6%", label: "Uptime", icon: IconChartBar },
                        {
                          value: "150GB+",
                          label: "Storage Used",
                          icon: IconMail,
                        },
                      ].map((stat, i) => (
                        <motion.div
                          key={i}
                          className="bg-darker rounded-lg p-4 border border-primary/10"
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.3 + i * 0.1 }}
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
                              <stat.icon className="w-5 h-5 text-primary" />
                            </div>
                            <div>
                              <div className="text-xl font-bold">
                                {stat.value}
                              </div>
                              <div className="text-sm text-white/60">
                                {stat.label}
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>

                    <div className="space-y-2">
                      <div className="text-sm font-medium text-white/60">
                        Total Views
                      </div>
                      <div className="h-[140px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={data}>
                            <defs>
                              <linearGradient
                                id="barGradient"
                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                              >
                                <stop
                                  offset="0%"
                                  stopColor="rgba(255, 51, 121, 0.3)"
                                />
                                <stop
                                  offset="100%"
                                  stopColor="rgba(255, 51, 121, 0.1)"
                                />
                              </linearGradient>
                            </defs>
                            <XAxis
                              dataKey="name"
                              fontSize={12}
                              axisLine={false}
                              tickLine={false}
                              tick={{ fill: "rgba(255, 255, 255, 0.4)" }}
                            />
                            <Tooltip
                              cursor={{ fill: "rgba(255, 51, 121, 0.05)" }}
                              content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                  return (
                                    <div className="bg-darker/80 backdrop-blur-sm px-2 py-1 rounded-md text-xs border border-primary/20 transition-opacity duration-200 ease-in-out opacity-100">
                                      {payload[0].value}k
                                    </div>
                                  );
                                }
                                return null;
                              }}
                              wrapperStyle={{
                                transition: "opacity 200ms ease-in-out",
                              }}
                            />
                            <Bar
                              dataKey="users"
                              fill="url(#barGradient)"
                              stroke="rgba(255, 51, 121, 0.3)"
                              strokeWidth={1}
                              radius={[4, 4, 0, 0]}
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                </ShineBorder>

                <div className="absolute -right-4 -top-4 w-20 h-20 bg-gradient-to-br from-primary/20 to-primary/5 rounded-full blur-xl" />
                <div className="absolute -left-8 -bottom-8 w-32 h-32 bg-gradient-to-br from-primary/10 to-transparent rounded-full blur-2xl" />
              </div>
            </motion.div>
          </div>
        </section>

        <Features />
        <Showcase />
        <HowItWorks />
        <Integrations />
        <FAQ />
        <CTA />
      </main>
      <Footer />
    </>
  );
}
