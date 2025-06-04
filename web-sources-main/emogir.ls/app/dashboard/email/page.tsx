"use client";

import { IconMail } from "@tabler/icons-react";

export default function EmailPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
      <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
        <IconMail size={32} className="text-primary" />
      </div>
      <h1 className="text-3xl font-bold text-white">Email Integration</h1>
      <p className="text-white/60 text-center max-w-md">
        Coming soon! You&apos;ll be able to manage your email preferences and
        notifications here.
      </p>
      <div className="bg-black/20 border border-white/5 rounded-lg p-6 mt-8 w-full max-w-md backdrop-blur-sm">
        <p className="text-lg font-medium text-white/90 mb-4">
          Features to look forward to:
        </p>
        <div className="space-y-3">
          <div className="flex items-center gap-3 text-white/70">
            <div className="w-1.5 h-1.5 rounded-full bg-primary/50" />
            <span>Custom email domains</span>
          </div>
          <div className="flex items-center gap-3 text-white/70">
            <div className="w-1.5 h-1.5 rounded-full bg-primary/50" />
            <span>Email forwarding</span>
          </div>
          <div className="flex items-center gap-3 text-white/70">
            <div className="w-1.5 h-1.5 rounded-full bg-primary/50" />
            <span>Newsletter management</span>
          </div>
          <div className="flex items-center gap-3 text-white/70">
            <div className="w-1.5 h-1.5 rounded-full bg-primary/50" />
            <span>Notification preferences</span>
          </div>
        </div>
      </div>
    </div>
  );
}
