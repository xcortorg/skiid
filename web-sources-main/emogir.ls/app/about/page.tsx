"use client";

import { motion } from "framer-motion";
import { Header } from "@/components/ui/header";
import { Footer } from "@/components/ui/footer";
import { Button } from "@/components/ui/button";
import { SiGithub, SiDiscord } from "react-icons/si";

const stats = [
  { label: "Active Users", value: "2.5k+" },
  { label: "Links Created", value: "100k+" },
  { label: "Files Hosted", value: "50k+" },
  { label: "Custom Domains", value: "50+" },
];

const team = [
  {
    name: "Adam",
    role: "Founder",
    image: "/team/adam.png",
    socials: {
      twitter: "",
      github: "",
    },
  },
  {
    name: "72g",
    role: "Co-Owner",
    image: "/team/72g.png",
    socials: {
      twitter: "",
      github: "",
    },
  },
  {
    name: "b",
    role: "Founder & Developer",
    image: "/team/b.png",
    socials: {
      twitter: "",
      github: "",
    },
  },
  {
    name: "Luckyz",
    role: "Manager",
    image: "/team/luckyz.png",
    socials: {
      twitter: "",
      github: "",
    },
  },
];

export default function AboutPage() {
  return (
    <>
      <div className="fixed inset-0 animated-bg" />
      <main className="mx-auto h-full w-full max-w-[1200px] px-[45px] py-0 relative overflow-hidden">
        <Header />
        <section className="relative mt-[80px] mb-[150px] py-10">
          <div className="text-center mb-24">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <span className="inline-block px-4 py-1.5 text-xs font-medium text-primary border border-primary/30 rounded-full mb-4">
                Our Story
              </span>
            </motion.div>

            <motion.h1
              className="text-4xl md:text-5xl font-bold mb-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              Building the Future of{" "}
              <span className="relative inline-block">
                <span className="absolute inset-0 bg-primary/20 blur-[20px] rounded-md"></span>
                <span className="relative bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                  Digital Identity
                </span>
              </span>
            </motion.h1>

            <motion.p
              className="text-base md:text-lg opacity-70 max-w-2xl mx-auto"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              We&apos;re on a mission to revolutionize how creators showcase
              their online presence. Our platform combines powerful tools with
              elegant design to help you stand out.
            </motion.p>
          </div>

          <motion.div
            className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-24"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            {stats.map((stat, index) => (
              <div
                key={stat.label}
                className="bg-darker p-6 rounded-xl border border-white/5 text-center"
              >
                <div className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent mb-2">
                  {stat.value}
                </div>
                <div className="text-sm opacity-70">{stat.label}</div>
              </div>
            ))}
          </motion.div>

          <motion.div
            className="mb-24"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <div className="bg-darker p-8 rounded-2xl border border-white/5 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-r from-primary/5 to-secondary/5" />
              <div className="relative">
                <h2 className="text-2xl md:text-3xl font-bold mb-6">
                  Our Mission
                </h2>
                <div className="space-y-4 text-base md:text-lg opacity-80">
                  <p>
                    emogir.ls was born from a simple idea: everyone deserves a
                    beautiful, professional online presence. We believe in
                    making powerful tools accessible to creators of all sizes.
                  </p>
                  <p>
                    Our platform combines link management, file hosting, and
                    custom domains into one seamless experience. We&apos;re
                    constantly innovating and adding new features based on our
                    community&apos;s feedback.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* <motion.div
            className="text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
          >
            <h2 className="text-2xl md:text-3xl font-bold mb-12">Meet the Team</h2>
            <div className="flex justify-center gap-8">
              {team.map((member) => (
                <div key={member.name} className="relative group">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-primary to-secondary rounded-2xl blur opacity-30 group-hover:opacity-50 transition-opacity" />
                  <div className="relative bg-darker p-6 rounded-2xl">
                    <div className="w-24 h-24 rounded-full overflow-hidden mb-4 mx-auto border-2 border-white/10">
                      <img 
                        src={member.image} 
                        alt={member.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <h3 className="text-lg font-semibold mb-1">{member.name}</h3>
                    <p className="text-sm opacity-70 mb-4">{member.role}</p>
                    <div className="flex justify-center gap-3">
                      {member.socials.twitter && (
                        <a 
                          href={member.socials.twitter}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:text-primary/80 transition-colors"
                        >
                          <SiX className="w-5 h-5" />
                        </a>
                      )}
                      {member.socials.github && (
                        <a 
                          href={member.socials.github}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:text-primary/80 transition-colors"
                        >
                          <SiGit className="w-5 h-5" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div> */}

          <motion.div
            className="mt-24 text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.6 }}
          >
            <h2 className="text-2xl md:text-3xl font-bold mb-6">
              Join Our Community
            </h2>
            <p className="text-base opacity-70 max-w-2xl mx-auto mb-8">
              Connect with other creators, get early access to new features, and
              help shape the future of emogir.ls.
            </p>
            <div className="flex justify-center gap-4">
              <Button
                href="https://discord.gg/emogirls"
                text="Join Discord"
                icon={SiDiscord}
              />
              <Button
                href="https://github.com/kyronorg"
                text="GitHub"
                icon={SiGithub}
              />
            </div>
          </motion.div>
        </section>
      </main>
      <Footer />
    </>
  );
}
