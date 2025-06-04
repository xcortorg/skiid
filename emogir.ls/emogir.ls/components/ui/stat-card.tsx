import { IconProps } from "@tabler/icons-react";
import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<IconProps>;
  subValue?: string | number | ReactNode;
  subLabel?: string;
  className?: string;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  subValue,
  subLabel,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "group relative isolate overflow-hidden rounded-xl",
        className,
      )}
    >
      <div className="absolute inset-0 -z-10 rounded-xl bg-gradient-to-b from-black/60 to-black/40" />
      <div className="absolute inset-0 -z-10 rounded-xl bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      <div className="relative p-5">
        <div className="flex flex-col gap-4">
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <div className="text-sm text-white/60">{title}</div>
              <div className="text-2xl font-semibold text-white">{value}</div>
            </div>
            <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 backdrop-blur-sm">
              <Icon size={18} className="text-primary" />
            </div>
          </div>

          {(subValue || subLabel) && (
            <div className="flex items-center justify-between gap-4 pt-2 border-t border-primary/[0.125]">
              {subLabel && (
                <div className="text-sm text-white/40">{subLabel}</div>
              )}
              {subValue && (
                <div className="text-sm text-white/60">{subValue}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
