"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { User, Upload } from "lucide-react";

export interface FileInputProps
  extends Omit<
    React.InputHTMLAttributes<HTMLInputElement>,
    "type" | "value" | "onChange"
  > {
  onValueChange?: (file: File | null) => void;
  value?: string | null;
  error?: string;
}

const FileInput = React.forwardRef<HTMLInputElement, FileInputProps>(
  ({ className, onValueChange, value, error, ...props }, ref) => {
    const inputRef = React.useRef<HTMLInputElement>(null);

    return (
      <div className="relative w-24 h-24">
        <input
          ref={inputRef}
          type="file"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (onValueChange) {
              onValueChange(file || null);
            }
          }}
          {...props}
        />
        <div
          className={cn(
            "absolute inset-0 rounded-full bg-primary/5 border-2 border-dashed border-primary/20 flex items-center justify-center overflow-hidden transition-all hover:border-primary/40",
            error && "border-red-500 hover:border-red-600",
            className,
          )}
        >
          {value ? (
            <img
              src={value}
              alt="Avatar"
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="flex flex-col items-center justify-center gap-2">
              <User className="w-8 h-8 text-primary/40" />
              <Upload className="w-4 h-4 text-primary/40" />
            </div>
          )}
        </div>
        {error && (
          <p className="absolute -bottom-6 left-0 right-0 text-xs text-red-500 text-center">
            {error}
          </p>
        )}
      </div>
    );
  },
);

FileInput.displayName = "FileInput";

export { FileInput };
