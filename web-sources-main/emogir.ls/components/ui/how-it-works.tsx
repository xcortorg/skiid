"use client";

import { motion } from "framer-motion";
import { UserPlus, Palette, Share2, ChartBar } from "lucide-react";
import Link from "next/link";

const steps = [
  {
    icon: UserPlus,
    title: "Create Account",
    description: "Sign up with email or connect Discord for instant setup",
    color: "#ff3379",
  },
  {
    icon: Palette,
    title: "Customize Profile",
    description: "Choose your layout and personalize every detail",
    color: "#f897db",
  },
  {
    icon: Share2,
    title: "Add Your Links",
    description: "Connect your socials and customize link appearance",
    color: "#ff3379",
  },
  {
    icon: ChartBar,
    title: "Track Growth",
    description: "Monitor engagement with real-time analytics",
    color: "#f897db",
  },
];

export function HowItWorks() {
  return (
    <section className="py-24 relative overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <div className="absolute left-1/4 bottom-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[100px]" />
        <div className="absolute right-1/4 top-0 w-[500px] h-[500px] bg-secondary/5 rounded-full blur-[100px]" />
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
              Quick Setup
            </span>
          </motion.div>

          <motion.h2
            className="text-4xl font-bold mb-6 text-white"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            Get started in{" "}
            <span className="relative inline-block">
              <span className="relative bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                Minutes
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
            Creating your perfect profile is easy. Follow these simple steps to
            get started and make your mark online.
          </motion.p>
        </div>

        <div className="relative">
          <div className="absolute top-1/2 left-0 w-full h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent -translate-y-1/2 hidden lg:block" />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {steps.map((step, index) => (
              <motion.div
                key={step.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="relative group"
              >
                <div className="relative z-10 bg-darker/80 backdrop-blur-sm p-6 rounded-xl border border-white/[0.08] h-full transition-colors duration-300 hover:border-primary/20">
                  <div className="flex flex-col items-center text-center">
                    <div className="mb-4 p-3 bg-black/40 rounded-xl text-primary">
                      <step.icon
                        className="w-8 h-8"
                        style={{ color: step.color }}
                      />
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-2">
                      {step.title}
                    </h3>
                    <p className="text-sm text-white/60">{step.description}</p>
                  </div>
                </div>
                <div className="absolute inset-0 bg-gradient-to-r from-primary/10 to-secondary/10 rounded-xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity" />
              </motion.div>
            ))}
          </div>
        </div>

        <motion.div
          className="mt-16 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <Link
            href="/register"
            className="inline-flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-6 py-2.5 rounded-lg font-medium transition-colors"
          >
            Get started now
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
