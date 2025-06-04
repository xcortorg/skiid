"use client";

import { Header } from "@/components/ui/header";
import { Footer } from "@/components/ui/footer";
import { motion } from "framer-motion";
import { apiDocs } from "./index";
import { IconKey, IconLock } from "@tabler/icons-react";

export default function DocsPage() {
  return (
    <>
      <div className="fixed inset-0 animated-bg" />
      <main className="mx-auto h-full w-full max-w-[1200px] px-[45px] py-0 relative overflow-hidden">
        <Header />
        <section className="relative mt-[40px] mb-[150px] py-10">
          <div className="text-center mb-16">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <span className="inline-block px-4 py-1.5 text-xs font-medium text-primary border border-primary/30 rounded-full mb-4">
                API Documentation
              </span>
            </motion.div>

            <motion.h1
              className="text-4xl md:text-5xl font-bold mb-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              Build with our{" "}
              <span className="relative inline-block">
                <span className="absolute inset-0 bg-primary/20 blur-[20px] rounded-md"></span>
                <span className="relative bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                  API
                </span>
              </span>
            </motion.h1>

            <motion.p
              className="text-base md:text-lg opacity-70 max-w-2xl mx-auto"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              Access your profile, links, and appearance settings
              programmatically
            </motion.p>
          </div>

          <motion.div
            className="mb-12"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <div className="bg-darker p-8 rounded-2xl border border-white/5">
              <div className="flex items-center gap-3 mb-6">
                <IconKey className="text-primary" size={24} />
                <h2 className="text-xl font-semibold">Authentication</h2>
              </div>
              <div className="space-y-4 text-white/80">
                <p>
                  All API endpoints require authentication using a Bearer token.
                  You can generate API tokens in your dashboard settings.
                </p>
                <div className="bg-black/40 p-4 rounded-lg font-mono text-sm">
                  Authorization: Bearer your_api_token_here
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <div className="space-y-8">
              {Object.entries(apiDocs.paths).map(([path, methods]) => (
                <div
                  key={path}
                  className="bg-darker p-8 rounded-2xl border border-white/5"
                >
                  <div className="flex items-center gap-3 mb-6">
                    <IconLock className="text-primary" size={24} />
                    <h2 className="text-xl font-semibold">{path}</h2>
                  </div>
                  {Object.entries(methods).map(
                    ([method, details]: [string, any]) => (
                      <div key={method} className="mb-8 last:mb-0">
                        <div className="flex items-center gap-4 mb-4">
                          <span className="uppercase text-xs font-bold px-3 py-1 rounded-full bg-primary/20 text-primary">
                            {method}
                          </span>
                          <span className="text-white/60">
                            {details.summary}
                          </span>
                        </div>

                        {details.parameters && (
                          <div className="mb-6">
                            <h3 className="text-sm font-semibold mb-2 text-white/80">
                              Parameters
                            </h3>
                            <div className="bg-black/40 rounded-lg overflow-hidden">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="border-b border-white/10">
                                    <th className="text-left p-4">Name</th>
                                    <th className="text-left p-4">Type</th>
                                    <th className="text-left p-4">
                                      Description
                                    </th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {details.parameters.map((param: any) => (
                                    <tr
                                      key={param.name}
                                      className="border-b border-white/5 last:border-0"
                                    >
                                      <td className="p-4">{param.name}</td>
                                      <td className="p-4 text-primary">
                                        {param.schema.type}
                                      </td>
                                      <td className="p-4 text-white/60">
                                        {param.description}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}

                        {details.examples && (
                          <div className="mt-6">
                            <h3 className="text-sm font-semibold mb-2 text-white/80">
                              Examples
                            </h3>
                            <div className="space-y-4">
                              <div>
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-xs font-medium text-white/60">
                                    cURL
                                  </span>
                                </div>
                                <div className="bg-black/40 p-4 rounded-lg">
                                  <pre className="text-sm overflow-x-auto text-white/80">
                                    {details.examples.curl}
                                  </pre>
                                </div>
                              </div>

                              <div>
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-xs font-medium text-white/60">
                                    JavaScript
                                  </span>
                                </div>
                                <div className="bg-black/40 p-4 rounded-lg">
                                  <pre className="text-sm overflow-x-auto text-white/80">
                                    {details.examples.javascript}
                                  </pre>
                                </div>
                              </div>

                              <div>
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-xs font-medium text-white/60">
                                    Python
                                  </span>
                                </div>
                                <div className="bg-black/40 p-4 rounded-lg">
                                  <pre className="text-sm overflow-x-auto text-white/80">
                                    {details.examples.python}
                                  </pre>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                        <div>
                          <h3 className="text-sm font-semibold mb-2 text-white/80">
                            Response
                          </h3>
                          <div className="bg-black/40 p-4 rounded-lg">
                            <pre className="text-sm overflow-x-auto">
                              {JSON.stringify(
                                details.responses["200"].content?.[
                                  "application/json"
                                ]?.example || {},
                                null,
                                2,
                              )}
                            </pre>
                          </div>
                        </div>
                      </div>
                    ),
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        </section>
      </main>
      <Footer />
    </>
  );
}
