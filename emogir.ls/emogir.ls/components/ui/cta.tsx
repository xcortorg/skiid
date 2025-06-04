"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import Link from "next/link";

export function CTA() {
  return (
    <section className="py-12 sm:py-24 relative">
      <div className="absolute inset-0 -z-10">
        <div className="absolute bottom-0 left-0 w-48 sm:w-96 h-48 sm:h-96 bg-primary/5 rounded-full blur-3xl"></div>
        <div className="absolute top-0 right-0 w-48 sm:w-96 h-48 sm:h-96 bg-secondary/5 rounded-full blur-3xl"></div>
      </div>

      <div className="max-w-[1200px] mx-auto px-4">
        <div className="relative p-4 sm:p-8 rounded-2xl border border-white/5 bg-darker/50 backdrop-blur-sm overflow-hidden">
          <div className="absolute -top-12 sm:-top-24 -left-12 sm:-left-24 w-32 sm:w-64 h-32 sm:h-64 bg-primary/30 rounded-full blur-3xl"></div>
          <div className="absolute -bottom-12 sm:-bottom-24 -right-12 sm:-right-24 w-32 sm:w-64 h-32 sm:h-64 bg-secondary/30 rounded-full blur-3xl"></div>

          <div className="relative flex flex-col lg:flex-row items-center justify-between gap-4 sm:gap-8">
            <div className="flex-1 text-center lg:text-left">
              <motion.div
                className="text-3xl sm:text-4xl md:text-5xl font-bold space-y-2"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5 }}
              >
                <div>
                  Ready to create your{" "}
                  <span className="relative inline-block">
                    <span className="absolute inset-0 bg-primary/20 blur-[20px] rounded-md"></span>
                    <span className="relative bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                      perfect profile?
                    </span>
                  </span>
                </div>
              </motion.div>

              <motion.p
                className="text-base sm:text-lg opacity-70 mt-4 sm:mt-6 mb-6 sm:mb-8 lg:mb-0 max-w-xl mx-auto lg:mx-0"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.1 }}
              >
                Join thousands of creators who have already made their mark. Get
                started for free!
              </motion.p>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="flex flex-col sm:flex-row gap-3 sm:gap-4 w-full sm:w-auto"
            >
              <Link
                href="/register"
                className="px-6 sm:px-8 py-3 rounded-lg bg-primary hover:bg-primary/90 text-white font-medium transition-colors flex items-center justify-center gap-2 group"
              >
                Get Started
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                href="/showcase"
                className="px-6 sm:px-8 py-3 rounded-lg bg-black/20 hover:bg-black/40 backdrop-blur-sm transition-colors flex items-center justify-center"
              >
                View Examples
              </Link>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}
