"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { useMeasure } from "@/lib/useMeasure";

const WIDTH = 380;

export interface ToastProps {
  id: string;
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  duration?: number;
  variant?: "success" | "error";
  onRemove: (id: string) => void;
}

export function DynamicIslandToast({
  id,
  title,
  description,
  icon,
  duration = 5000,
  variant = "success",
  onRemove,
}: ToastProps) {
  const [ref, { height: viewHeight }] = useMeasure();
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(() => onRemove(id), 300);
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, id, onRemove]);

  const getIconColor = () => {
    switch (variant) {
      case "success":
        return "#ff3379";
      case "error":
        return "rgb(239, 68, 68)";
      default:
        return "#ff3379";
    }
  };

  const renderIcon = () =>
    icon || (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke={getIconColor()}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {variant === "success" ? (
          <path d="M20 6L9 17l-5-5" />
        ) : (
          <>
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </>
        )}
      </svg>
    );

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          exit={{ y: -100, filter: "blur(8px)", opacity: 0 }}
          initial={{ y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className={cn(
            "w-[380px] z-50 overflow-hidden rounded-xl bg-[#050505] border border-primary/10 text-white shadow-lg"
          )}
          transition={{
            type: "spring",
            bounce: 0.2,
            duration: 0.6,
          }}
        >
          <motion.div
            key="content"
            ref={ref}
            initial={{ opacity: 0, filter: "blur(4px)" }}
            animate={{ opacity: 1, filter: "blur(0px)" }}
            exit={{ opacity: 0, filter: "blur(4px)" }}
            transition={{ duration: 0.3 }}
            className="flex flex-col p-3 pr-10"
          >
            <div className="flex items-center gap-2 mb-1">
              <div className="size-4 rounded-full bg-primary/10 flex items-center justify-center">
                {renderIcon()}
              </div>
              {title && <div className="text-sm font-medium">{title}</div>}
            </div>
            {description && (
              <div className="text-xs text-white/60">{description}</div>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsVisible(false);
                setTimeout(() => onRemove(id), 300);
              }}
              className="absolute right-2 top-2 p-1 text-white/40 hover:text-white"
            >
              <X size={14} />
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
