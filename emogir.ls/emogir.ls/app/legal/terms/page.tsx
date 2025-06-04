"use client";

import { motion } from "framer-motion";
import { Header } from "@/components/ui/header";
import { Footer } from "@/components/ui/footer";

export default function TermsPage() {
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
              Terms of Service
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
                <h2 className="text-2xl font-bold mb-4">
                  1. Agreement to Terms
                </h2>
                <p>
                  By accessing or using <strong>emogir.ls</strong>, you agree to
                  be bound by these Terms of Service. If you do not agree with
                  any part of these terms, you may not access or use the
                  service.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">2. User Accounts</h2>
                <ul className="list-disc pl-6 space-y-2">
                  <li>
                    You must be at least <strong>13 years old</strong> to use
                    this service.
                  </li>
                  <li>
                    You are responsible for maintaining the security of your
                    account.
                  </li>
                  <li>
                    Any activity under your account is{" "}
                    <strong>your responsibility</strong>.
                  </li>
                  <li>
                    You must provide accurate, complete, and up-to-date
                    information.
                  </li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">3. Acceptable Use</h2>
                <p>
                  By using <strong>emogir.ls</strong>, you agree{" "}
                  <strong>NOT</strong> to:
                </p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>
                    Use the service for any <strong>illegal</strong> or{" "}
                    <strong>unauthorized</strong> purpose.
                  </li>
                  <li>
                    Share, upload, or distribute any{" "}
                    <strong>inappropriate, harmful, or offensive</strong>{" "}
                    content.
                  </li>
                  <li>
                    Attempt to{" "}
                    <strong>hack, exploit, or gain unauthorized access</strong>{" "}
                    to the platform.
                  </li>
                  <li>
                    Interfere with <strong>security features</strong> or attempt
                    to disrupt normal service.
                  </li>
                  <li>
                    Impersonate others or provide{" "}
                    <strong>false or misleading information</strong>.
                  </li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  4. Content Ownership & Rights
                </h2>
                <p>
                  - You retain <strong>ownership</strong> of any content you
                  submit. <br />- By submitting content, you grant{" "}
                  <strong>emogir.ls</strong> a{" "}
                  <strong>non-exclusive, royalty-free license</strong> to use,
                  modify, and display it. <br />- You must have the{" "}
                  <strong>legal rights</strong> to share any content.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  5. Service Modifications & Availability
                </h2>
                <p>
                  - We <strong>reserve the right</strong> to modify, suspend, or
                  discontinue the service at any time,{" "}
                  <strong>with or without notice</strong>. <br />- We are{" "}
                  <strong>not liable</strong> for any disruption, loss of
                  access, or modifications made to the service.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  6. Account Suspension & Termination
                </h2>
                <p>
                  We may suspend or terminate your account{" "}
                  <strong>without prior notice</strong> if:
                </p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>
                    You <strong>violate</strong> these Terms of Service.
                  </li>
                  <li>
                    Your actions{" "}
                    <strong>
                      harm other users, our platform, or third parties
                    </strong>
                    .
                  </li>
                  <li>
                    We determine, at our discretion, that your conduct is{" "}
                    <strong>unacceptable</strong>.
                  </li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  7. Limitation of Liability
                </h2>
                <p>
                  - <strong>emogir.ls</strong> is{" "}
                  <strong>not responsible</strong> for any{" "}
                  <strong>
                    indirect, incidental, special, or consequential damages
                  </strong>{" "}
                  resulting from your use of the service. <br />- We{" "}
                  <strong>do not guarantee</strong> that the service will be{" "}
                  <strong>error-free, uninterrupted, or secure</strong>.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">8. Changes to Terms</h2>
                <p>
                  - We may <strong>update or modify</strong> these Terms at any
                  time. <br />- If we make significant changes, we will notify
                  users by posting the revised Terms on this site.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  9. Contact Information
                </h2>
                <p>
                  For any questions regarding these Terms, contact us at: <br />
                  📧{" "}
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
