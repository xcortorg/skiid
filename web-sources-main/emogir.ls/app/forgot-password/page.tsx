"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { AuthButton } from "@/components/ui/auth-button";
import { FaEnvelope, FaCheckCircle } from "react-icons/fa";
import { useToast } from "@/components/ui/toast-provider";
import { Turnstile } from "@/components/ui/turnstile";

export default function ForgotPasswordPage() {
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string>("");
  const [isEmailSent, setIsEmailSent] = useState(false);
  const turnstileRef = useRef<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!turnstileToken) {
      toast({
        title: "Verification required",
        description: "Please complete the challenge",
        variant: "error",
      });
      return;
    }

    setIsLoading(true);

    try {
      const res = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          turnstileToken,
        }),
      });

      if (!res.ok) throw new Error();

      const data = await res.json();
      setIsEmailSent(true);
      toast({
        title: "Success",
        description: data.message,
        variant: "success",
      });
    } catch (error) {
      turnstileRef.current?.reset();
      setTurnstileToken("");
      toast({
        title: "Error",
        description: "Failed to send reset email",
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isEmailSent) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="relative w-full max-w-[400px] overflow-hidden rounded-lg border border-primary bg-darker p-8">
          <div className="absolute inset-0 bg-grid-white/5 [mask-image:radial-gradient(white,transparent_85%)]" />

          <div className="relative text-center">
            <FaCheckCircle className="mx-auto text-6xl text-green-500 mb-4" />
            <h2 className="text-xl font-semibold mb-4">Check Your Email</h2>
            <p className="text-white/60 mb-6">
              If an account exists with {email}, you&apos;ll receive a password
              reset link shortly.
            </p>
            <Link
              href="/login"
              className="inline-block text-pink hover:opacity-80 transition-opacity"
            >
              Return to Login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="relative w-full max-w-[400px] overflow-hidden rounded-lg border border-primary bg-darker p-8">
        <div className="absolute inset-0 bg-grid-white/5 [mask-image:radial-gradient(white,transparent_85%)]" />

        <div className="relative">
          <Link href="/" className="block mb-6">
            <h2 className="text-2xl font-bold">
              emogir<span className="text-[#ff3379] text-sm">.ls</span>
            </h2>
          </Link>

          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-2">
              <label className="text-sm opacity-80">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink"
                placeholder="your@email.com"
                required
              />
            </div>

            <div className="flex justify-center">
              <Turnstile
                ref={turnstileRef}
                siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!}
                onSuccess={setTurnstileToken}
              />
            </div>

            <AuthButton
              text="Send Reset Link"
              icon={FaEnvelope}
              isLoading={isLoading}
              className="mt-2"
            />

            <p className="text-sm text-center opacity-80 mt-4">
              Remember your password?{" "}
              <Link
                href="/login"
                className="text-pink hover:opacity-80 transition-opacity"
              >
                Login
              </Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
