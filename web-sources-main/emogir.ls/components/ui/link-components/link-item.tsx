"use client";

import {
  IconExternalLink,
  IconTrash,
  IconGripVertical,
} from "@tabler/icons-react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Link } from "@/types/link";
import { useToast } from "@/components/ui/toast-provider";

interface LinkItemProps extends Link {
  onDelete: (id: string) => void;
  onToggle: (id: string, enabled: boolean) => void;
}

export function LinkItem({
  id,
  title,
  url,
  iconUrl,
  clicks,
  enabled,
  onDelete,
  onToggle,
}: LinkItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id,
    transition: {
      duration: 150,
      easing: "cubic-bezier(0.25, 1, 0.5, 1)",
    },
  });

  const { toast } = useToast();

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const handleToggle = (id: string, newState: boolean) => {
    onToggle(id, newState);
    toast({
      title: newState ? "Link enabled" : "Link disabled",
      description: `${title} is now ${newState ? "enabled" : "disabled"}`,
      variant: "success",
    });
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`relative flex items-center justify-between p-4 rounded-lg border border-primary/[0.125] bg-primary/5 bg-gradient-to-br from-primary/[0.01] to-primary/[0.03] transition-colors ${
        isDragging ? "z-50 shadow-xl opacity-75" : ""
      }`}
    >
      <div className="flex items-center space-x-4">
        <button
          {...attributes}
          {...listeners}
          className="touch-none p-1.5 text-white/40 hover:text-white cursor-grab active:cursor-grabbing hover:bg-primary/5 rounded-md transition-colors"
        >
          <IconGripVertical size={18} />
        </button>
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-primary/10 bg-primary/5">
          {iconUrl ? (
            <img src={iconUrl} alt={title} className="w-5 h-5 preset-icon" />
          ) : (
            <IconExternalLink size={18} className="text-primary" />
          )}
        </div>
        <div>
          <h3 className="font-medium text-foreground">{title}</h3>
          <div className="flex items-center gap-2">
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-white/60 hover:text-primary flex items-center gap-1"
            >
              {url}
              <IconExternalLink size={12} />
            </a>
            <span className="text-xs text-white/40">
              • {clicks.toLocaleString()} clicks
            </span>
          </div>
        </div>
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={() => onToggle(id, !enabled)}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            enabled
              ? "bg-primary text-white hover:bg-primary/90"
              : "bg-primary/10 text-primary hover:bg-primary/20"
          }`}
        >
          {enabled ? "Enabled" : "Disabled"}
        </button>
        <button
          onClick={() => onDelete(id)}
          className="p-2 text-red-500/60 hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
        >
          <IconTrash size={18} />
        </button>
      </div>
    </div>
  );
}
