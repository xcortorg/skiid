"use client";

import { motion } from "framer-motion";
import { Check, HelpCircle, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Header } from "@/components/ui/header";
import { Footer } from "@/components/ui/footer";

const features = {
  free: [
    "Modern profile page",
    "4 layout options",
    "Up to 10 links",
    "Basic analytics",
    "Discord presence",
    "Last.fm integration",
    "5GB image storage",
    "2FA security",
    "Default emogir.ls subdomain",
  ],
  pro: [
    "Everything in Free",
    "Custom domain support",
    "100GB image storage",
    "Unlimited links",
    "Premium themes & effects",
    "Advanced analytics",
    "Custom email addresses",
    "Email forwarding",
    "Remove watermark",
    "Priority support",
    "Audio player with 3 tracks",
    "Real-time visitor tracking",
    "Multiple email aliases",
    "Custom CSS themes",
  ],
};

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);

  return (
    <>
      <div className="fixed inset-0 animated-bg" />
      <main className="mx-auto h-full w-full max-w-[1200px] px-[45px] py-0 relative overflow-hidden">
        <Header />
        <section className="relative mt-[80px] mb-[150px] py-10">
          <div className="text-center mb-16">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <span className="inline-block px-4 py-1.5 text-xs font-medium text-primary border border-primary/30 rounded-full mb-4">
                Pricing
              </span>
            </motion.div>

            <motion.h1
              className="text-4xl md:text-5xl font-bold mb-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              Choose Your{" "}
              <span className="relative inline-block">
                <span className="absolute inset-0 bg-primary/20 blur-[20px] rounded-md"></span>
                <span className="relative bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                  Perfect Plan
                </span>
              </span>
            </motion.h1>

            <motion.p
              className="text-base opacity-70 max-w-2xl mx-auto mb-12"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              Start with our free plan and upgrade when you need more features.
              All plans include our core features to help you create an amazing
              profile.
            </motion.p>

            <motion.div
              className="inline-flex items-center gap-6 mb-16 text-sm"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <button
                className={`font-medium transition-colors ${
                  !annual ? "text-white" : "text-white/50 hover:text-white/70"
                }`}
                onClick={() => setAnnual(false)}
              >
                Monthly
              </button>
              <button
                className={`font-medium transition-colors ${
                  annual ? "text-white" : "text-white/50 hover:text-white/70"
                }`}
                onClick={() => setAnnual(true)}
              >
                Annually <span className="text-primary">(-20%)</span>
              </button>
            </motion.div>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              <div className="relative z-10 bg-darker p-8 rounded-2xl border border-white/5">
                <h3 className="text-2xl font-bold mb-4">Free</h3>
                <p className="opacity-70 mb-6">Perfect for getting started</p>

                <div className="mb-6">
                  <div className="text-3xl font-bold">$0</div>
                  <div className="text-sm opacity-70">Forever free</div>
                </div>

                <Link
                  href="/register"
                  className="block w-full py-3 px-4 rounded-lg bg-white/5 hover:bg-white/10 text-center font-medium transition-colors mb-8"
                >
                  Get Started
                </Link>

                <div className="space-y-4">
                  {features.free.map((feature) => (
                    <div key={feature} className="flex items-start gap-3">
                      <Check className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              className="relative group"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-primary to-secondary rounded-2xl blur-[2px]" />
              <div className="relative z-10 bg-darker p-8 rounded-2xl border border-white/10">
                <div className="absolute -top-3 -right-3 px-3 py-1 bg-primary rounded-full text-sm font-medium">
                  Popular
                </div>

                <h3 className="text-2xl font-bold mb-4">Pro</h3>
                <p className="opacity-70 mb-6">
                  For creators who need more storage and custom email
                </p>

                <div className="mb-6">
                  <div className="text-3xl font-bold">
                    ${annual ? "8" : "10"}
                    <span className="text-lg opacity-70">/mo</span>
                  </div>
                  <div className="text-sm opacity-70">
                    {annual ? "Billed annually" : "Billed monthly"}
                  </div>
                </div>

                <Link
                  href="/register?plan=pro"
                  className="block w-full py-3 px-4 rounded-lg bg-gradient-to-r from-primary to-secondary text-center font-medium hover:opacity-90 transition-opacity mb-8"
                >
                  Upgrade to Pro
                </Link>

                <div className="space-y-4">
                  {features.pro.map((feature) => (
                    <div key={feature} className="flex items-start gap-3">
                      <Check className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          </div>

          <div className="mt-24 max-w-3xl mx-auto">
            <h2 className="text-2xl font-bold mb-8 text-center">
              Frequently Asked Questions
            </h2>

            <div className="space-y-6">
              <div className="bg-darker p-6 rounded-xl">
                <div className="flex items-start gap-3">
                  <HelpCircle className="w-5 h-5 text-primary shrink-0 mt-1" />
                  <div>
                    <h3 className="font-medium mb-2">
                      Can I switch plans later?
                    </h3>
                    <p className="opacity-70">
                      Yes! You can upgrade, downgrade, or cancel your plan at
                      any time.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-darker p-6 rounded-xl">
                <div className="flex items-start gap-3">
                  <HelpCircle className="w-5 h-5 text-primary shrink-0 mt-1" />
                  <div>
                    <h3 className="font-medium mb-2">
                      What payment methods do you accept?
                    </h3>
                    <p className="opacity-70">
                      We accept all major credit cards, PayPal, and crypto
                      payments.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-darker p-6 rounded-xl">
                <div className="flex items-start gap-3">
                  <HelpCircle className="w-5 h-5 text-primary shrink-0 mt-1" />
                  <div>
                    <h3 className="font-medium mb-2">Do you offer refunds?</h3>
                    <p className="opacity-70">
                      Yes, we offer a 14-day money-back guarantee if you&apos;re
                      not satisfied.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-darker p-6 rounded-xl">
                <div className="flex items-start gap-3">
                  <HelpCircle className="w-5 h-5 text-primary shrink-0 mt-1" />
                  <div>
                    <h3 className="font-medium mb-2">
                      What&apos;s included with custom email?
                    </h3>
                    <p className="opacity-70">
                      Pro users get custom email addresses with their domain
                      (e.g., you@emogir.ls), email forwarding, catch-all
                      addresses, and multiple aliases. Plus, you get 100GB of
                      image storage for your content.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
