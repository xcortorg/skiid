"use client";

import { motion } from "framer-motion";
import { Header } from "@/components/ui/header";
import { Footer } from "@/components/ui/footer";

export default function PrivacyPage() {
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
              Privacy Policy
            </motion.h1>

            <motion.p
              className="text-base opacity-70 max-w-2xl mx-auto mb-12"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              Last updated: March 5, 2025
            </motion.p>
          </div>

          <motion.div
            className="prose prose-invert max-w-4xl mx-auto opacity-80"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <div className="space-y-8">
              <section>
                <h2 className="text-2xl font-bold mb-4">Introduction</h2>
                <p>
                  At emogir.ls, we take your privacy seriously. This Privacy
                  Policy explains how we collect, use, disclose, and safeguard
                  your information when you use our service.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  Information We Collect
                </h2>
                <h3 className="text-xl font-semibold mb-2">
                  Information you provide:
                </h3>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Email address (optional)</li>
                  <li>Profile information (username, bio, links)</li>
                  <li>Images you upload</li>
                  <li>Custom domain settings</li>
                </ul>

                <h3 className="text-xl font-semibold mb-2 mt-4">
                  Information automatically collected:
                </h3>
                <ul className="list-disc pl-6 space-y-2">
                  <li>IP address</li>
                  <li>Browser type</li>
                  <li>Device information</li>
                  <li>Usage data</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  How We Use Your Information
                </h2>
                <ul className="list-disc pl-6 space-y-2">
                  <li>To provide and maintain our service</li>
                  <li>To notify you about changes to our service</li>
                  <li>To provide customer support</li>
                  <li>
                    To gather analysis or valuable information to improve our
                    service
                  </li>
                  <li>To detect, prevent and address technical issues</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  Data Storage and Security
                </h2>
                <p>
                  We implement appropriate technical and organizational security
                  measures to protect your personal information. However, no
                  method of transmission over the Internet is 100% secure, and
                  we cannot guarantee absolute security.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">Your Data Rights</h2>
                <p>You have the right to:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Access your personal data</li>
                  <li>Correct inaccurate data</li>
                  <li>Request deletion of your data</li>
                  <li>Export your data</li>
                  <li>Opt-out of marketing communications</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">Cookies</h2>
                <p>
                  We use cookies and similar tracking technologies to track
                  activity on our service and hold certain information. You can
                  instruct your browser to refuse all cookies or to indicate
                  when a cookie is being sent.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  Cloudflare CSAM Scanning & Data Retention
                </h2>
                <p>
                  We use Cloudflare&apos;s CSAM (Child Sexual Abuse Material)
                  scanning tool to ensure compliance with legal and security
                  standards. This tool automatically scans uploaded content for
                  potential CSAM to help prevent illegal activity on our
                  platform.
                </p>
                <p>
                  In accordance with local laws, we may be required to retain
                  certain account information, including but not limited to user
                  activity logs and uploaded content metadata, for up to 90
                  days. This retention policy ensures compliance with
                  regulations and helps in legal investigations if necessary.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  Third-Party Services
                </h2>
                <p>
                  We may employ third-party companies and individuals to
                  facilitate our service, provide service-related services, or
                  assist us in analyzing how our service is used.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  Changes to This Policy
                </h2>
                <p>
                  We may update our Privacy Policy from time to time. We will
                  notify you of any changes by posting the new Privacy Policy on
                  this page and updating the &quot;Last updated&quot; date.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">Contact Us</h2>
                <p>
                  If you have any questions about this Privacy Policy, please
                  contact us at{" "}
                  <a
                    href="mailto:legal@emogir.ls"
                    className="text-primary hover:underline"
                  >
                    legal@emogir.ls
                  </a>
                </p>
              </section>
            </div>
          </motion.div>
        </section>
      </main>
      <Footer />
    </>
  );
}
