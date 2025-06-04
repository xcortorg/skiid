"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { AuthButton } from "@/components/ui/auth-button";
import { FaKey } from "react-icons/fa";
import { useToast } from "@/components/ui/toast-provider";
import { useRouter, useSearchParams } from "next/navigation";

function ResetPasswordContent() {
  const { toast } = useToast();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isValidToken, setIsValidToken] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        toast({
          title: "Invalid link",
          description: "Invalid reset link",
          variant: "error",
        });
        router.push("/login");
        return;
      }

      try {
        const res = await fetch(
          `/api/auth/validate-reset-token?token=${token}`,
        );
        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.error || "Invalid or expired reset link");
        }

        setIsValidToken(true);
      } catch (error: any) {
        toast({
          title: "Invalid link",
          description: error.message,
          variant: "error",
        });
        router.push("/login");
      } finally {
        setIsLoading(false);
      }
    };

    validateToken();
  }, [token, router, toast]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password.length < 8) {
      toast({
        title: "Invalid password",
        description: "Password must be at least 8 characters",
        variant: "error",
      });
      return;
    }

    if (password !== confirmPassword) {
      toast({
        title: "Password mismatch",
        description: "Passwords do not match",
        variant: "error",
      });
      return;
    }

    setIsLoading(true);

    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Failed to reset password");
      }

      toast({
        title: "Success",
        description: "Password reset successful",
        variant: "success",
      });
      router.push("/login");
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to reset password",
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-pink" />
      </div>
    );
  }

  if (!isValidToken) {
    return null;
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
              <label className="text-sm opacity-80">New Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink"
                placeholder="••••••••"
                required
              />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm opacity-80">Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink"
                placeholder="••••••••"
                required
              />
            </div>

            <AuthButton
              text="Reset Password"
              icon={FaKey}
              isLoading={isLoading}
              className="mt-2"
            />
          </form>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-pink" />
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
