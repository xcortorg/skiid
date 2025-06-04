"use client";

import { motion } from "framer-motion";
import { Header } from "@/components/ui/header";
import { Footer } from "@/components/ui/footer";

const licenses = [
  {
    name: "React",
    version: "19.0.0",
    license: "MIT",
    description: "A JavaScript library for building user interfaces",
    url: "https://reactjs.org",
  },
  {
    name: "Next.js",
    version: "15.1.7",
    license: "MIT",
    description: "The React Framework for Production",
    url: "https://nextjs.org",
  },
  {
    name: "Tailwind CSS",
    version: "3.3.0",
    license: "MIT",
    description: "A utility-first CSS framework",
    url: "https://tailwindcss.com",
  },
  {
    name: "Framer Motion",
    version: "12.4.7",
    license: "MIT",
    description: "Production-ready animation library for React",
    url: "https://www.framer.com/motion",
  },
  {
    name: "Lucide Icons",
    version: "0.475.0",
    license: "MIT",
    description: "Beautiful & consistent icons",
    url: "https://lucide.dev",
  },
  {
    name: "React Icons",
    version: "5.5.0",
    license: "MIT",
    description: "Popular icons in your React projects",
    url: "https://react-icons.github.io/react-icons",
  },
  {
    name: "Zod",
    version: "3.24.2",
    license: "MIT",
    description:
      "TypeScript-first schema validation with static type inference",
    url: "https://github.com/colinhacks/zod",
  },
  {
    name: "UUID",
    version: "11.1.0",
    license: "MIT",
    description: "Unique identifier generator for JavaScript",
    url: "https://github.com/uuidjs/uuid",
  },
  {
    name: "Sonner",
    version: "2.0.1",
    license: "MIT",
    description: "An opinionated toast component for React",
    url: "https://github.com/emilkowalski/sonner",
  },
  {
    name: "Recharts",
    version: "2.15.1",
    license: "MIT",
    description: "A composable charting library built on React components",
    url: "https://recharts.org",
  },
  {
    name: "Qrcode.react",
    version: "4.2.0",
    license: "MIT",
    description: "A React component to generate QR codes",
    url: "https://github.com/zpao/qrcode.react",
  },
  {
    name: "Otplib",
    version: "12.0.1",
    license: "MIT",
    description:
      "One Time Password library (HOTP/TOTP) for Node.js and browser",
    url: "https://github.com/yeojz/otplib",
  },
];

export default function LicensesPage() {
  return (
    <>
      <div className="fixed inset-0 -z-10 animated-bg" />
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
                Legal
              </span>
            </motion.div>

            <motion.h1
              className="text-4xl md:text-5xl font-bold mb-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              Open Source Licenses
            </motion.h1>

            <motion.p
              className="text-base opacity-70 max-w-2xl mx-auto mb-12"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              We&apos;re proud to use and contribute to open source software.
              Here are the licenses for the packages we use.
            </motion.p>
          </div>

          <motion.div
            className="max-w-4xl mx-auto"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <div className="space-y-6">
              {licenses.map((lib, index) => (
                <motion.div
                  key={lib.name}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.1 * index }}
                  className="bg-darker p-6 rounded-xl border border-white/5"
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <h3 className="text-xl font-semibold mb-2">
                        {lib.name}{" "}
                        <span className="text-sm opacity-50">
                          v{lib.version}
                        </span>
                      </h3>
                      <p className="text-sm opacity-70 mb-2">
                        {lib.description}
                      </p>
                      <a
                        href={lib.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-primary hover:underline"
                      >
                        {lib.url}
                      </a>
                    </div>
                    <div className="shrink-0">
                      <span className="inline-block px-3 py-1 text-xs font-medium bg-primary/10 text-primary rounded-full">
                        {lib.license} License
                      </span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            <motion.div
              className="mt-12 text-center"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.6 }}
            >
              <p className="text-sm opacity-70">
                For more information about our open source contributions, visit
                our{" "}
                <a
                  href="https://github.com/kyronorg"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  GitHub profile
                </a>
              </p>
            </motion.div>
          </motion.div>
        </section>
      </main>
      <Footer />
    </>
  );
}
