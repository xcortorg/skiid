"use client";

import { motion } from "framer-motion";
import { Header } from "@/components/ui/header";
import { Footer } from "@/components/ui/footer";

export default function CookiesPage() {
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
              Cookie Policy
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
                <h2 className="text-2xl font-bold mb-4">What Are Cookies</h2>
                <p>
                  Cookies are small pieces of text used to store information on
                  web browsers. They are used to store and receive identifiers
                  and other information on computers, phones, and other devices.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">How We Use Cookies</h2>
                <p>We use cookies to:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Remember your login status and preferences</li>
                  <li>Understand how you use our service</li>
                  <li>Protect your account security</li>
                  <li>Improve our service based on usage data</li>
                  <li>Provide personalized content and features</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  Types of Cookies We Use
                </h2>
                <div className="space-y-4">
                  <div>
                    <h3 className="text-xl font-semibold mb-2">
                      Essential Cookies
                    </h3>
                    <p>
                      Required for the operation of our service. They include
                      cookies that enable you to log into secure areas.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold mb-2">
                      Analytics Cookies
                    </h3>
                    <p>
                      Allow us to analyze how the service is accessed, used, or
                      is performing to provide you with a better experience.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold mb-2">
                      Functionality Cookies
                    </h3>
                    <p>
                      Used to recognize you when you return to our service,
                      enabling us to personalize content and remember your
                      preferences.
                    </p>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">Your Cookie Choices</h2>
                <p>
                  Most web browsers are set to accept cookies by default. If you
                  prefer, you can usually choose to set your browser to remove
                  or reject browser cookies. Please note that if you choose to
                  remove or reject cookies, this could affect the availability
                  and functionality of our service.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">Third-Party Cookies</h2>
                <p>
                  In addition to our own cookies, we may also use various
                  third-party cookies to report usage statistics, deliver
                  advertisements, and so on. These cookies may track your
                  browsing habits across different websites and establish a
                  profile of your online behavior.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">
                  Updates to This Policy
                </h2>
                <p>
                  We may update this Cookie Policy from time to time in order to
                  reflect changes to the cookies we use or for other
                  operational, legal, or regulatory reasons.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold mb-4">Contact Us</h2>
                <p>
                  If you have questions about our use of cookies, please contact
                  us at{" "}
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
