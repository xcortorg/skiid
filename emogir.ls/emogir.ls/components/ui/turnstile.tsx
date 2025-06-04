"use client";

import { forwardRef, useImperativeHandle } from "react";
import { Turnstile as CloudflareTurnstile } from "@marsidev/react-turnstile";

interface TurnstileProps {
  siteKey: string;
  onSuccess: (token: string) => void;
}

export const Turnstile = forwardRef<{ reset: () => void }, TurnstileProps>(
  ({ siteKey, onSuccess }, ref) => {
    let widgetRef: any = null;

    useImperativeHandle(ref, () => ({
      reset: () => {
        if (widgetRef) {
          widgetRef.reset();
        }
      },
    }));

    return (
      <CloudflareTurnstile
        ref={(r) => {
          widgetRef = r;
        }}
        siteKey={siteKey}
        onSuccess={onSuccess}
        options={{
          theme: "dark",
        }}
      />
    );
  },
);

Turnstile.displayName = "Turnstile";
