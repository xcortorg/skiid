"use client";

import { motion } from "framer-motion";
import {
  FaGithub,
  FaDiscord,
  FaTwitter,
  FaInstagram,
  FaHeart,
  FaEnvelope,
} from "react-icons/fa";
import Link from "next/link";
import { useRouter } from "next/navigation";

const socials = [
  { icon: FaGithub, href: "https://github.com/kyronorg", label: "GitHub" },
  { icon: FaDiscord, href: "https://discord.gg/emogirls", label: "Discord" },
  { icon: FaTwitter, href: "https://twitter.com/emogir_ls", label: "Twitter" },
  {
    icon: FaInstagram,
    href: "https://instagram.com/emogir.ls",
    label: "Instagram",
  },
];

const footerLinks = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "/features" },
      { label: "Pricing", href: "/pricing" },
      { label: "Testimonials", href: "/testimonials" },
      { label: "FAQ", href: "/faq" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "/about" },
      { label: "Blog", href: "/blog" },
      { label: "Careers", href: "/careers" },
      { label: "Support", href: "/support" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy", href: "/legal/privacy" },
      { label: "Terms", href: "/legal/terms" },
      { label: "Cookies", href: "/legal/cookies" },
      { label: "Licenses", href: "/legal/licenses" },
    ],
  },
];

export function Footer() {
  const router = useRouter();
  const currentYear = new Date().getFullYear();

  const handleSmoothScroll = (e: React.MouseEvent, sectionId: string) => {
    e.preventDefault();

    if (window.location.pathname !== "/") {
      router.push(`/?scroll=${sectionId}`);
      return;
    }

    const section = document.getElementById(sectionId);
    if (section) {
      section.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  };

  return (
    <footer className="w-full border-t border-primary/20 mt-20">
      <div className="mx-auto max-w-[1200px] px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 mb-12">
          <div className="space-y-4">
            <h1 className="text-2xl font-bold select-none">
              emogir<span className="text-primary text-sm">.ls</span>
            </h1>
            <p className="text-sm opacity-70 max-w-md">
              A premium solution for e-mails, image uploading & showing off your
              digital portfolio. Connect all your social profiles in one
              beautiful link.
            </p>

            <div className="flex items-center gap-4 pt-2">
              {socials.map((social, index) => (
                <motion.a
                  key={index}
                  href={social.href}
                  target="_blank"
                  rel="noreferrer"
                  className="w-9 h-9 rounded-full bg-darker border border-primary/20 flex items-center justify-center group"
                  whileHover={{
                    scale: 1.1,
                    backgroundColor: "rgba(255, 51, 121, 0.1)",
                  }}
                  whileTap={{ scale: 0.95 }}
                  aria-label={social.label}
                >
                  <social.icon className="h-4 w-4 text-white group-hover:text-primary transition-colors" />
                </motion.a>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-primary">
                Stay updated
              </h3>
              <span className="px-2 py-0.5 text-[10px] font-medium bg-primary/10 text-primary rounded-full">
                Coming Soon
              </span>
            </div>
            <p className="text-sm opacity-70">
              Subscribe to our newsletter for updates, tips, and exclusive
              offers.
            </p>

            <div className="flex gap-2 mt-2 relative">
              <div className="absolute inset-0 bg-darker/80 backdrop-blur-[2px] z-10 rounded-lg flex items-center justify-center">
                <span className="text-sm text-white/60">Newsletter coming soon!</span>
              </div>
              <div className="relative flex-1 opacity-50">
                <input
                  type="email"
                  placeholder="Enter your email"
                  className="w-full px-4 py-2.5 rounded-lg bg-darker border border-primary/20 focus:border-primary/50 focus:outline-none transition-colors"
                  disabled
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <FaEnvelope className="h-4 w-4 opacity-50" />
                </div>
              </div>
              <motion.button
                className="px-4 py-2.5 rounded-lg bg-primary text-white font-medium opacity-50"
                disabled
              >
                Subscribe
              </motion.button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 py-8 border-t border-b border-primary/10">
          <div className="col-span-2 md:col-span-1">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-primary mb-4">
              Resources
            </h3>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/docs"
                  className="text-sm opacity-70 hover:opacity-100 hover:text-primary transition-colors"
                >
                  Documentation
                </Link>
              </li>
              <li>
                <Link
                  href="/dashboard/api"
                  className="text-sm opacity-70 hover:opacity-100 hover:text-primary transition-colors"
                >
                  API Reference
                </Link>
              </li>
              <li>
                <Link
                  href="/guides"
                  className="text-sm opacity-70 hover:opacity-100 hover:text-primary transition-colors"
                >
                  Guides & Tutorials
                </Link>
              </li>
              <li>
                <Link
                  href="/examples"
                  className="text-sm opacity-70 hover:opacity-100 hover:text-primary transition-colors"
                >
                  Examples
                </Link>
              </li>
            </ul>
          </div>

          {footerLinks.map((section, idx) => (
            <div key={idx}>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-primary mb-4">
                {section.title}
              </h3>
              <ul className="space-y-2">
                {section.links.map((link, linkIdx) => (
                  <li key={linkIdx}>
                    <Link
                      href={link.href}
                      onClick={
                        link.label === "Features"
                          ? (e) => handleSmoothScroll(e, "features")
                          : link.label === "FAQ"
                          ? (e) => handleSmoothScroll(e, "faq")
                          : undefined
                      }
                      className="text-sm opacity-70 hover:opacity-100 hover:text-primary transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="flex flex-col md:flex-row items-center justify-between pt-8 gap-4">
          <p className="text-sm opacity-60">
            © {currentYear} EMOGIR.LS LLC. All rights reserved.
          </p>

          <div className="flex items-center gap-1 text-sm opacity-60">
            <span>Made with</span>
            <FaHeart className="h-3 w-3 text-primary" />
            <span>by the emogir.ls team</span>
          </div>

          <div className="flex items-center gap-4">
            <Link
              href="/status"
              className="text-xs opacity-60 hover:opacity-100 transition-colors"
            >
              Status
            </Link>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-green-500"></div>
              <span className="text-xs opacity-60">
                All systems operational
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="h-1 w-full bg-gradient-to-r from-transparent via-primary to-transparent opacity-30"></div>
    </footer>
  );
}
