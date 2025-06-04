"use client";

import { cn } from "@/lib/utils";
import {
  FaPalette,
  FaBolt,
  FaCrown,
  FaChartLine,
  FaShieldAlt,
  FaMusic,
} from "react-icons/fa";
import { motion } from "framer-motion";

export function Features() {
  const features = [
    {
      title: "Custom Themes",
      description:
        "Express yourself with modern themes and layouts including Discord integration, custom colors, animated effects, and full profile customization.",
      icon: FaPalette,
      stat: "4",
      statLabel: "layouts",
    },
    {
      title: "Live Integration",
      description:
        "Show off your Discord presence, Last.fm activity, and more in real-time. Connect your favorite platforms and keep your profile dynamic.",
      icon: FaBolt,
      stat: "Real-time",
      statLabel: "updates",
    },
    {
      title: "Premium Features",
      description:
        "Unlock advanced features like custom domains, image hosting with 100GB storage, and priority support with our Pro plan.",
      icon: FaCrown,
      stat: "100GB",
      statLabel: "storage",
    },
    {
      title: "Analytics Dashboard",
      description:
        "Track your profile performance with comprehensive analytics including visitor counts, link clicks, and engagement metrics.",
      icon: FaChartLine,
      stat: "30 days",
      statLabel: "history",
    },
    {
      title: "Secure & Private",
      description:
        "Control your privacy with features like profile PIN protection, 2FA security, and new login location verification.",
      icon: FaShieldAlt,
      stat: "2FA",
      statLabel: "ready",
    },
    {
      title: "Audio Player",
      description:
        "Add your favorite tracks to your profile with our built-in audio player. Share music and set the perfect mood for visitors.",
      icon: FaMusic,
      stat: "3",
      statLabel: "tracks",
    },
  ];

  return (
    <section id="features" className="py-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <span className="inline-block px-4 py-1.5 text-xs font-medium text-primary border border-primary/30 rounded-full mb-8">
              Features
            </span>
          </motion.div>

          <motion.h2
            className="text-4xl font-bold mb-6 text-white"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            Everything you need for your
            <span className="bg-primary text-white px-2 py-1 ml-2">
              digital presence
            </span>
          </motion.h2>

          <motion.p
            className="text-base text-neutral-300 max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            Our platform combines powerful features with elegant design to help
            you create the perfect online hub for all your content and social
            profiles.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 relative z-10">
          {features.map((feature, index) => (
            <Feature key={feature.title} {...feature} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}

const Feature = ({
  title,
  description,
  icon: Icon,
  stat,
  statLabel,
  index,
}: {
  title: string;
  description: string;
  icon: React.ElementType;
  stat: string;
  statLabel: string;
  index: number;
}) => {
  return (
    <motion.div
      className="relative group/feature overflow-hidden bg-black/20 border border-neutral-800 rounded-xl p-6 flex flex-col h-full"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
    >
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-primary/0 opacity-0 group-hover/feature:opacity-100 transition-opacity duration-500" />

      <div className="relative z-10 flex flex-col flex-1">
        <div className="mb-2 inline-block p-2 text-primary">
          <Icon className="w-6 h-6" />
        </div>

        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-lg font-semibold text-white group-hover/feature:text-primary transition-colors">
            {title}
          </h3>
        </div>

        <p className="text-sm text-neutral-300">{description}</p>

        <div className="flex items-center gap-2 text-xs text-neutral-400 mt-auto pt-4">
          <span className="font-bold text-primary">{stat}</span>
          <span>{statLabel}</span>
        </div>
      </div>
    </motion.div>
  );
};
