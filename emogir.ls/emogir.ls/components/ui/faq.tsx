"use client";

import { motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { useState } from "react";

const faqs = [
  {
    question: "What is emogir.ls?",
    answer:
      "emogir.ls is a profile customization platform with advanced features like real-time Discord presence, Last.fm integration, custom themes, and analytics. Create a personalized hub for all your online content with our modern, secure platform.",
  },
  {
    question: "What layouts are available?",
    answer:
      "We offer 4 unique layouts: Modern (clean and customizable), Discord (with live presence and server widget), Console (terminal-style interface), and Femboy. Each layout can be fully customized with colors, effects, and animations.",
  },
  {
    question: "What security features do you offer?",
    answer:
      "We provide robust security with two-factor authentication (2FA), backup codes, new login location verification, profile PIN protection, and session management. Your data is protected with enterprise-grade encryption.",
  },
  {
    question: "Can I connect my Discord presence?",
    answer:
      "Yes! Our Discord integration shows your real-time presence, current activity, and server widget. Pro users can customize the appearance of their Discord components and add server invites.",
  },
  {
    question: "What's included in the Pro plan?",
    answer:
      "Pro users get custom domains, 100GB storage, unlimited links, premium themes, audio player, advanced analytics, custom email addresses with forwarding, watermark removal, and priority support.",
  },
  {
    question: "How does the audio player work?",
    answer:
      "Pro users can add up to 3 audio tracks to their profile page. Visitors can play these tracks while browsing your profile, creating an immersive experience. You can customize the player's appearance to match your theme.",
  },
];

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="py-24 relative" id="faq">
      <div className="absolute inset-0 -z-10">
        <div className="absolute bottom-0 left-0 w-72 h-72 bg-primary/5 rounded-full blur-3xl"></div>
        <div className="absolute top-0 right-0 w-72 h-72 bg-secondary/5 rounded-full blur-3xl"></div>
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
              FAQ
            </span>
          </motion.div>

          <motion.h2
            className="text-4xl font-bold mb-6"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            Frequently Asked Questions
          </motion.h2>

          <motion.p
            className="text-base opacity-70 max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            Got questions? We&apos;ve got answers! Here are some of the most
            common questions we receive.
          </motion.p>
        </div>

        <div className="max-w-3xl mx-auto">
          {faqs.map((faq, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="mb-4"
            >
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="w-full flex items-center justify-between p-4 rounded-lg bg-darker hover:bg-darker/80 transition-colors text-left"
              >
                <span className="font-medium">{faq.question}</span>
                <ChevronDown
                  className={`w-5 h-5 transition-transform ${
                    openIndex === index ? "rotate-180" : ""
                  }`}
                />
              </button>

              <motion.div
                initial={false}
                animate={{
                  height: openIndex === index ? "auto" : 0,
                  opacity: openIndex === index ? 1 : 0,
                }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div className="p-4 opacity-70">{faq.answer}</div>
              </motion.div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
