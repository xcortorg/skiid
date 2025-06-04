"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Upload, X, Image as ImageIcon, Film } from "lucide-react";
import { useToast } from "@/components/ui/toast-provider";
import { useState, useEffect } from "react";

interface MediaUploadProps {
  type: "background" | "banner";
  value?: string | null;
  onChange: (url: string | null | boolean) => void;
  className?: string;
  disabled?: boolean;
}

export function MediaUpload({
  type,
  value,
  onChange,
  className,
  disabled,
}: MediaUploadProps) {
  const { toast } = useToast();
  const [uploading, setUploading] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [previewType, setPreviewType] = useState<"image" | "video" | null>(
    null,
  );

  useEffect(() => {
    if (value) {
      const isVideo = value.match(/\.(mp4|webm|ogg)($|\?)/i);
      setPreviewType(isVideo ? "video" : "image");
    } else {
      setPreviewType(null);
    }
  }, [value]);

  const handleUpload = async (file: File) => {
    const allowedImageTypes = [
      "image/jpeg",
      "image/png",
      "image/webp",
      "image/gif",
    ];
    const allowedVideoTypes = ["video/mp4"];

    if (
      !allowedImageTypes.includes(file.type) &&
      !allowedVideoTypes.includes(file.type)
    ) {
      toast({
        title: "Invalid file type",
        description: "Please upload a JPEG, PNG, WebP, GIF, or MP4 file.",
        variant: "error",
      });
      return;
    }

    const maxSize = file.type.startsWith("video/")
      ? 32 * 1024 * 1024
      : 8 * 1024 * 1024;
    if (file.size > maxSize) {
      toast({
        title: "File too large",
        description: `Maximum size: ${maxSize / (1024 * 1024)}MB`,
        variant: "error",
      });
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", file);
      formData.append("type", type);

      const response = await fetch("/api/upload/background", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");

      const data = await response.json();
      onChange(data.url);
      toast({
        title: "Upload successful",
        description: "Media uploaded successfully",
        variant: "success",
      });

      setPreviewType(file.type.startsWith("video/") ? "video" : "image");
    } catch (error) {
      toast({
        title: "Upload failed",
        description: "Failed to upload media",
        variant: "error",
      });
      console.error(error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-2">
      <div
        className={cn(
          "relative group cursor-pointer overflow-hidden",
          type === "banner" ? "h-32 rounded-lg" : "h-40 rounded-xl",
          className,
        )}
        onClick={() => !disabled && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".jpg,.jpeg,.png,.webp,.gif,.mp4"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleUpload(file);
          }}
          disabled={disabled || uploading}
        />

        {value ? (
          <>
            {previewType === "video" ? (
              <video
                src={value}
                autoPlay
                loop
                muted
                className="w-full h-full object-cover"
              />
            ) : (
              <img
                src={value}
                alt={`${type} preview`}
                className="w-full h-full object-cover"
              />
            )}
            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <Upload className="w-6 h-6 text-white" />
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
                setPreviewType(null);
              }}
              className="absolute top-2 right-2 p-1 rounded-full bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/75"
            >
              <X className="w-4 h-4" />
            </button>
          </>
        ) : (
          <div className="absolute inset-0 border-2 border-dashed border-primary/20 hover:border-primary/40 transition-colors">
            <div className="flex flex-col items-center justify-center h-full gap-2">
              <div className="flex gap-2">
                <ImageIcon className="w-6 h-6 text-primary/40" />
                <Film className="w-6 h-6 text-primary/40" />
              </div>
              {uploading ? (
                <p className="text-sm text-primary/60">Uploading...</p>
              ) : (
                <>
                  <p className="text-sm text-primary/60">
                    Click to upload {type}
                  </p>
                  <p className="text-xs text-primary/40">
                    JPEG, PNG, WebP, GIF, MP4
                  </p>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
