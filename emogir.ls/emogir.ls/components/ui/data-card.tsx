import { IconProps } from "@tabler/icons-react";
import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface DataCardProps {
  title: string;
  icon: React.ComponentType<IconProps>;
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export function DataCard({
  title,
  icon: Icon,
  children,
  className,
}: DataCardProps) {
  return (
    <div
      className={cn(
        "group relative isolate overflow-hidden rounded-xl",
        className,
      )}
    >
      <div className="absolute inset-0 -z-10 rounded-xl bg-gradient-to-b from-black/60 to-black/40" />
      <div className="absolute inset-0 -z-10 rounded-xl bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

      <div className="relative">
        <div className="flex items-center gap-3 p-5 border-b border-primary/[0.125]">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 backdrop-blur-sm">
            <Icon size={18} className="text-primary" />
          </div>
          <h2 className="text-lg font-medium text-white">{title}</h2>
        </div>

        <div className="relative p-5 space-y-4">{children}</div>
      </div>
    </div>
  );
}
