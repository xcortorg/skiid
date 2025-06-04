"use client";

interface ImageActionsProps {
  imageUrl: string;
}

export default function ImageActions({ imageUrl }: ImageActionsProps) {
  return (
    <div className="flex gap-3 pt-2">
      <a
        href={imageUrl}
        download
        className="px-4 py-2 bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors"
      >
        Download
      </a>
      <button
        onClick={() => navigator.clipboard.writeText(imageUrl)}
        className="px-4 py-2 bg-white/5 text-white/80 rounded-lg hover:bg-white/10 transition-colors"
      >
        Copy Link
      </button>
    </div>
  );
}
