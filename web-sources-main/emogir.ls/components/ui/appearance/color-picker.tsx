"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import { IconColorPicker } from "@tabler/icons-react";
import { cn } from "@/lib/utils";

type Color = {
  h: number;
  s: number;
  l: number;
  hex: string;
};

interface ColorPickerProps {
  label: string;
  value: string | null;
  name?: string;
  onChange: (color: string) => void;
  className?: string;
}

function hexToHsl(hex: string): { h: number; s: number; l: number } {
  hex = hex.replace(/^#/, "");

  const r = parseInt(hex.slice(0, 2), 16) / 255;
  const g = parseInt(hex.slice(2, 4), 16) / 255;
  const b = parseInt(hex.slice(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      case b:
        h = (r - g) / d + 4;
        break;
    }

    h *= 60;
  }

  return {
    h: Math.round(h),
    s: Math.round(s * 100),
    l: Math.round(l * 100),
  };
}

function hslToHex(h: number, s: number, l: number): string {
  s /= 100;
  l /= 100;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color)
      .toString(16)
      .padStart(2, "0");
  };
  return `${f(0)}${f(8)}${f(4)}`;
}

function hexToRgba(hex: string, alpha: number = 1): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function rgbaToHex(rgba: string): { hex: string; alpha: number } {
  const match = rgba.match(
    /rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([0-9.]+))?\)/,
  );
  if (!match) return { hex: "#000000", alpha: 1 };

  const r = parseInt(match[1]).toString(16).padStart(2, "0");
  const g = parseInt(match[2]).toString(16).padStart(2, "0");
  const b = parseInt(match[3]).toString(16).padStart(2, "0");
  const a = match[4] ? parseFloat(match[4]) : 1;

  return { hex: `#${r}${g}${b}`, alpha: a };
}

const DraggableColorCanvas = ({
  h,
  s,
  l,
  handleChange,
}: {
  h: number;
  s: number;
  l: number;
  handleChange: (e: Partial<Color>) => void;
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const colorAreaRef = useRef<HTMLDivElement>(null);

  const calculatePosition = useCallback(
    (clientX: number, clientY: number) => {
      if (!colorAreaRef.current) return;
      const rect = colorAreaRef.current.getBoundingClientRect();
      const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
      const y = Math.max(0, Math.min(clientY - rect.top, rect.height));
      const newS = Math.round((x / rect.width) * 100);
      const newL = Math.round((1 - y / rect.height) * 100);
      handleChange({ s: newS, l: newL });
    },
    [handleChange],
  );

  const startDragging = useCallback(
    (clientX: number, clientY: number) => {
      setIsDragging(true);
      calculatePosition(clientX, clientY);
    },
    [calculatePosition],
  );

  useEffect(() => {
    const handleMove = (e: MouseEvent | TouchEvent) => {
      if (!isDragging) return;
      const clientX = "touches" in e ? e.touches[0].clientX : e.clientX;
      const clientY = "touches" in e ? e.touches[0].clientY : e.clientY;
      calculatePosition(clientX, clientY);
    };

    const stopDragging = () => setIsDragging(false);

    if (isDragging) {
      window.addEventListener("mousemove", handleMove);
      window.addEventListener("touchmove", handleMove);
      window.addEventListener("mouseup", stopDragging);
      window.addEventListener("touchend", stopDragging);
    }

    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("touchmove", handleMove);
      window.removeEventListener("mouseup", stopDragging);
      window.removeEventListener("touchend", stopDragging);
    };
  }, [isDragging, calculatePosition]);

  return (
    <div
      ref={colorAreaRef}
      className="h-48 w-full touch-none rounded-lg border border-primary/10"
      style={{
        background: `linear-gradient(to bottom, #fff, transparent, #000), 
                    linear-gradient(to right, hsl(${h}, 0%, 50%), hsl(${h}, 100%, 50%))`,
        position: "relative",
        cursor: isDragging ? "grabbing" : "grab",
      }}
      onMouseDown={(e) => startDragging(e.clientX, e.clientY)}
      onTouchStart={(e) =>
        startDragging(e.touches[0].clientX, e.touches[0].clientY)
      }
    >
      <div
        className="absolute w-4 h-4 -translate-x-1/2 -translate-y-1/2 rounded-full shadow-xl border-2 border-white ring-1 ring-black/20"
        style={{
          left: `${s}%`,
          top: `${100 - l}%`,
          backgroundColor: `hsl(${h}, ${s}%, ${l}%)`,
          cursor: isDragging ? "grabbing" : "grab",
        }}
      />
    </div>
  );
};

export function ColorPicker({
  label,
  value,
  name,
  onChange,
  className,
}: ColorPickerProps) {
  const [color, setColor] = useState<Color>(() => {
    const hex = value?.replace("#", "") || "";
    const hsl = hexToHsl(hex || "000000");
    return { ...hsl, hex };
  });

  const [isUpdating, setIsUpdating] = useState(false);

  const handleColorChange = useCallback((partial: Partial<Color>) => {
    setColor((prev) => {
      const next = { ...prev, ...partial };
      const hex = hslToHex(next.h, next.s, next.l);
      return { ...next, hex };
    });
    setIsUpdating(true);
  }, []);

  useEffect(() => {
    if (isUpdating) {
      onChange(`#${color.hex}`);
      setIsUpdating(false);
    }
  }, [color.hex, onChange, isUpdating]);

  useEffect(() => {
    const newHex = value?.replace("#", "") || "";
    if (newHex !== color.hex && !isUpdating) {
      const hsl = hexToHsl(newHex || "000000");
      setColor({ ...hsl, hex: newHex });
    }
  }, [value, isUpdating]);

  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium text-white/80">{label}</label>

      <Popover.Root>
        <Popover.Trigger asChild>
          <button
            type="button"
            className={cn(
              "w-full flex items-center gap-2 px-3 py-2 rounded-lg",
              "bg-black/20 border border-primary/10 hover:border-primary/30 transition-colors",
              className,
            )}
          >
            <div
              className="w-5 h-5 rounded-full border border-white/10"
              style={{
                backgroundColor: value ? `#${color.hex}` : "transparent",
              }}
            />
            <span className="text-sm text-white/60 font-mono flex-1 text-left">
              {value ? `#${color.hex}` : "None"}
            </span>
            <IconColorPicker size={14} className="text-white/40" />
          </button>
        </Popover.Trigger>

        <Popover.Portal>
          <Popover.Content
            className="w-[300px] p-4 rounded-lg bg-darker border border-primary/10 shadow-2xl z-50"
            sideOffset={8}
          >
            <div className="space-y-4">
              <DraggableColorCanvas
                h={color.h}
                s={color.s}
                l={color.l}
                handleChange={handleColorChange}
              />

              <input
                type="range"
                min="0"
                max="360"
                value={color.h}
                className="w-full h-3 appearance-none rounded-full"
                style={{
                  background: `linear-gradient(to right, 
                    hsl(0, 100%, 50%), 
                    hsl(60, 100%, 50%), 
                    hsl(120, 100%, 50%), 
                    hsl(180, 100%, 50%), 
                    hsl(240, 100%, 50%), 
                    hsl(300, 100%, 50%), 
                    hsl(360, 100%, 50%))`,
                }}
                onChange={(e) => {
                  handleColorChange({ h: e.target.valueAsNumber });
                }}
              />

              <div className="relative">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3">
                  <span className="text-white/40">#</span>
                </div>
                <input
                  type="text"
                  value={color.hex}
                  onChange={(e) => {
                    const hex = e.target.value;
                    if (hex.match(/^[0-9A-Fa-f]{0,6}$/)) {
                      if (hex.length === 6) {
                        const hsl = hexToHsl(hex);
                        handleColorChange({ ...hsl });
                      } else {
                        setColor((prev) => ({ ...prev, hex }));
                      }
                    }
                  }}
                  className="w-full bg-black/20 border border-primary/10 rounded-lg pl-7 pr-3 py-2 text-sm font-mono"
                  placeholder="000000"
                  maxLength={6}
                  spellCheck={false}
                />
              </div>
            </div>

            <Popover.Arrow className="fill-primary/10" />
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </div>
  );
}
