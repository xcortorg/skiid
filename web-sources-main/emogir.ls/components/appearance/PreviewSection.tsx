"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { IconSearch, IconCopy, IconClock } from "@tabler/icons-react";
import { useToast } from "@/components/ui/toast-provider";

export function PreviewSection({ state }: { state: any }) {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [previewLink, setPreviewLink] = useState<string | null>(null);
  const [previewTimeRemaining, setPreviewTimeRemaining] = useState(0);

  const generatePreview = async () => {
    try {
      setIsLoading(true);
      const response = await fetch("/api/appearance/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state),
      });

      if (!response.ok) throw new Error();

      const data = await response.json();
      const fullUrl = `${window.location.origin}/preview/${data.previewId}`;
      setPreviewLink(fullUrl);
      setPreviewTimeRemaining(10);

      const timer = setInterval(() => {
        setPreviewTimeRemaining((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            setPreviewLink(null);
            return 0;
          }
          return prev - 1;
        });
      }, 60000);

      window.open(fullUrl, "_blank");
    } catch {
      toast({
        title: "Error",
        description: "Failed to generate preview link",
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 flex flex-col items-center justify-center min-h-[300px]">
      <div className="text-center space-y-4 max-w-xs mx-auto">
        <IconSearch size={48} className="mx-auto text-primary/30" />
        <h3 className="text-lg font-medium">See your changes live</h3>
        <p className="text-sm text-white/60">
          Generate a temporary preview link to see your changes in a full page
          view before saving.
        </p>
        {previewLink ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between bg-black/30 rounded-lg p-3 border border-primary/20">
              <div className="text-xs truncate max-w-[180px] text-white/70">
                {previewLink}
              </div>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(previewLink);
                  toast({
                    title: "Copied!",
                    description: "Preview link copied to clipboard",
                  });
                }}
                className="text-primary hover:text-primary/80"
              >
                <IconCopy size={16} />
              </button>
            </div>
            <div className="text-xs text-white/60 flex items-center gap-1">
              <IconClock size={12} />
              <span>Expires in {previewTimeRemaining} minutes</span>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => window.open(previewLink, "_blank")}
                text="Open Preview"
                className="flex-1"
              />
              <Button
                onClick={() => {
                  setPreviewLink(null);
                  setPreviewTimeRemaining(0);
                }}
                text="Dismiss"
                className="flex-1"
              />
            </div>
          </div>
        ) : (
          <Button
            onClick={generatePreview}
            text="Generate Preview Link"
            className="w-full"
            loading={isLoading}
          />
        )}
      </div>
    </div>
  );
}
