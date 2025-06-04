"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Header } from "@/components/ui/header";
import { Footer } from "@/components/ui/footer";
import Link from "next/link";

const domains = [
  { url: "emogir.ls", featured: true },
  { url: "bigblackmen.lol" },
  { url: "boob.lol" },
  { url: "esex.top" },
  { url: "evil.bio" },
  { url: "exitscam.online" },
  { url: "femboys.wtf" },
  { url: "free-thigh.pics" },
  { url: "gays.lol" },
  { url: "regret.wtf" },
  { url: "remt-a-negro.lol" },
  { url: "screwnnegros.lol" },
  { url: "oooooooooooo.online" },
  { url: "heists.lol" },
  { url: "girlfriend.lol" },
  { url: "boyfriend.lol" },
  { url: "husband.lol" },
  { url: "wife.lol" },
  { url: "hell.lol" },
  { url: "loves-virg.in" },
  { url: "lame.rip" },
  { url: "betray.rip" },
  { url: "creep.ovh" },
  { url: "harassi.ng" },
  { url: "inject.bio" },
  { url: "punish.lol" },
  { url: "occur.lol" },
  { url: "femboy-feet.pics" },
  { url: "eslut.online" },
  { url: "is-a-femboy.lol" },
  { url: "chasity.lol" },
  { url: "is-femboy.lol" },
  { url: "femboy-gooner.lol" },
  { url: "femboy-porn.pics" },
  { url: "suck-dick.online" },
  { url: "zombie.gold" },
  { url: "yvl.rocks" },
  { url: "boykisser.space" },
  { url: "degrad.es" },
  { url: "convul.se" },
  { url: "sexts.me" },
  { url: "humilaties.me" },
  { url: "degrades.me" },
  { url: "reallyri.ch" },
  { url: "tortures.men" },
  { url: "threateni.ng" },
  { url: "scari.ng" },
  { url: "doxing-ur.info" },
  { url: "depressi.ng" },
  { url: "youngvamp.life" },
  { url: "astolfo-pics.lol" },
  { url: "kayne-feet.pics" },
  { url: "opm.baby" },
  { url: "finesh.it" },
  { url: "ageplayi.ng" },
  { url: "astolfo-feet.pics" },
];

export default function DomainsPage() {
  return (
    <>
      <main className="mx-auto h-full w-full max-w-[1200px] px-[45px] py-0 relative overflow-hidden">
        <Header />
        <div className="container mx-auto py-12">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold mb-4">Our Domains</h1>
            <p className="text-lg text-white/60">
              Choose from over {domains.length} unique domains for your profile
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {domains.map((domain) => (
              <Card
                key={domain.url}
                className="p-4 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-lg font-medium">
                      {domain.url}
                      {domain.featured && (
                        <Badge className="ml-2 bg-primary/20 text-primary">
                          Featured
                        </Badge>
                      )}
                    </p>
                    <Link
                      href={`https://${domain.url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-white/60 hover:text-white transition-colors"
                    >
                      Visit domain →
                    </Link>
                  </div>
                  <button
                    onClick={() => navigator.clipboard.writeText(domain.url)}
                    className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                    title="Copy domain"
                  >
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    </svg>
                  </button>
                </div>
              </Card>
            ))}
          </div>

          <div className="mt-12 text-center">
            <p className="text-white/60">
              Want a custom domain?{" "}
              <Link href="/premium" className="text-primary hover:underline">
                Upgrade to Premium
              </Link>
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
