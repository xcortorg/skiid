import { IconExternalLink } from "@tabler/icons-react";
import { IconProps } from "@tabler/icons-react";

interface RecentLinkItemProps {
  title: string;
  url: string;
  clicks: number;
  iconUrl?: string;
}

export function RecentLinkItem({
  title,
  url,
  clicks,
  iconUrl,
}: RecentLinkItemProps) {
  return (
    <div className="group relative rounded-lg border border-primary/[0.125] hover:border-primary/20 transition-all bg-black/20">
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center space-x-4">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-primary/10 bg-primary/5 backdrop-blur-sm">
            {iconUrl ? (
              <img src={iconUrl} alt={title} className="w-5 h-5 preset-icon" />
            ) : (
              <IconExternalLink size={18} className="text-primary" />
            )}
          </div>
          <div>
            <h3 className="font-medium text-white/90">{title}</h3>
            <p className="text-sm text-white/60">{url}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-white/60">
            {clicks.toLocaleString()} clicks
          </span>
          <IconExternalLink
            size={16}
            className="opacity-0 group-hover:opacity-60 transition-opacity text-white/60"
          />
        </div>
      </div>
    </div>
  );
}
