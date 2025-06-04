"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { useEffect, useState } from "react";
import { fetchTopProfiles } from "@/lib/actions/leaderboard";

export function TopUsersMarquee() {
  const [profiles, setProfiles] = useState<any[]>([]);

  useEffect(() => {
    fetchTopProfiles().then(setProfiles);
  }, []);

  return (
    <div className="w-full overflow-hidden py-2">
      <div className="flex animate-marquee">
        {[...profiles, ...profiles].map((profile, index) => (
          <div
            key={index}
            className="flex items-center gap-2 mx-4 bg-darker/50 px-3 py-1.5 rounded-full border border-primary/10"
          >
            <div className="relative w-6 h-6 flex-shrink-0 overflow-hidden rounded-full">
              {profile.avatar ? (
                <Image
                  src={profile.avatar}
                  alt={profile.displayName}
                  width={24}
                  height={24}
                  className="w-full h-full object-cover rounded-full"
                />
              ) : (
                <div className="w-full h-full rounded-full bg-primary/20 flex items-center justify-center text-primary text-xs">
                  {profile.username[0].toUpperCase()}
                </div>
              )}
            </div>
            <span className="text-sm text-white/70">@{profile.username}</span>
            <span className="text-xs text-primary/80">
              {profile.views.toLocaleString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
