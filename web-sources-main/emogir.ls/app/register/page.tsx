"use client";

import Link from "next/link";
import {
  FaUserPlus,
  FaDiscord,
  FaCheck,
  FaTimes,
  FaSpinner,
} from "react-icons/fa";
import { AuthButton } from "@/components/ui/auth-button";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/toast-provider";
import { Turnstile } from "@/components/ui/turnstile";
import { validatePassword } from "@/lib/validations";
import { useSession } from "next-auth/react";

export default function RegisterPage() {
  const { toast } = useToast();
  const { data: session, status } = useSession();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [isBlocked, setIsBlocked] = useState(false);
  const [blockTimer, setBlockTimer] = useState(0);
  const [showVerification, setShowVerification] = useState(false);
  const [verificationCode, setVerificationCode] = useState("");
  const [turnstileToken, setTurnstileToken] = useState<string>("");
  const turnstileRef = useRef<any>(null);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    slug: "",
    displayName: "",
    inviteCode: "",
  });
  const [slugError, setSlugError] = useState("");

  useEffect(() => {
    if (status === "authenticated") {
      router.push("/dashboard");
    }
  }, [status, router]);

  if (status === "loading" || status === "authenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <FaSpinner className="animate-spin text-4xl text-pink" />
      </div>
    );
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    if (name === "slug") {
      const sanitizedValue = value.toLowerCase().replace(/[^a-z0-9-]/g, "");
      setFormData((prev) => ({
        ...prev,
        [name]: sanitizedValue,
      }));

      if (slugError) {
        setSlugError("");
      }
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  };

  const handleSendVerification = async (e: React.FormEvent) => {
    e.preventDefault();

    if (formData.slug.length < 4) {
      toast({
        title: "Username too short",
        description:
          "Please contact support for usernames shorter than 4 characters",
        variant: "error",
      });
      return;
    }

    if (!turnstileToken) {
      toast({
        title: "Please complete the challenge",
        variant: "error",
      });
      return;
    }

    const { isValid, errors } = validatePassword(formData.password);
    if (!isValid) {
      toast({
        title: "Invalid password",
        description: errors[0],
        variant: "error",
      });
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch("/api/auth/verify-email", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: formData.email,
          inviteCode: formData.inviteCode,
          turnstileToken: turnstileToken,
          debugKey: process.env.NEXT_PUBLIC_DEBUG_KEY,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        if (res.status === 429) {
          setIsBlocked(true);
          setBlockTimer(data.remainingTime);
          toast({
            title: "Too many attempts",
            description: data.error,
            variant: "error",
          });
          return;
        }
        throw new Error(data.error);
      }

      setShowVerification(true);
      toast({
        title: "Verification code sent",
        description: "Please check your email",
        variant: "success",
      });
    } catch (error: any) {
      toast({
        title: "Failed to send verification code",
        description: error.message,
        variant: "error",
      });
    } finally {
      setIsLoading(false);
      turnstileRef.current?.reset();
      setTurnstileToken("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!verificationCode) {
      toast({
        title: "Please enter verification code",
        variant: "error",
      });
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...formData,
          verificationCode,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        if (res.status === 429) {
          setIsBlocked(true);
          setBlockTimer(data.remainingTime);
          toast({
            title: "Registration blocked",
            description: data.error,
            variant: "error",
          });
          return;
        }
        throw new Error(data.error || "Registration failed");
      }

      toast({
        title: "Registration successful",
        variant: "success",
      });
      router.push("/login");
    } catch (error: any) {
      toast({
        title: "Registration failed",
        description: error.message,
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (showVerification) {
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

            <h2 className="text-2xl font-bold mb-6">Verify your email</h2>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-sm opacity-80">Verification Code</label>
                <div className="flex gap-2">
                  {[...Array(6)].map((_, i) => (
                    <input
                      key={i}
                      type="text"
                      maxLength={1}
                      className="w-12 h-12 text-center bg-primary border border-[#1a1a1a] rounded focus:outline-none focus:border-pink text-lg"
                      value={verificationCode[i] || ""}
                      onChange={(e) => {
                        const newCode = verificationCode.split("");
                        newCode[i] = e.target.value;
                        setVerificationCode(newCode.join(""));
                        if (e.target.value && e.target.nextElementSibling) {
                          (
                            e.target.nextElementSibling as HTMLInputElement
                          ).focus();
                        }
                      }}
                      onKeyDown={(e) => {
                        if (
                          e.key === "Backspace" &&
                          !verificationCode[i] &&
                          (e.target as HTMLInputElement).previousElementSibling
                        ) {
                          (
                            (e.target as HTMLInputElement)
                              .previousElementSibling as HTMLInputElement
                          ).focus();
                        }
                      }}
                      onPaste={(e) => {
                        e.preventDefault();
                        const paste = e.clipboardData.getData("text");
                        const numbers = paste
                          .replace(/[^0-9]/g, "")
                          .slice(0, 6);
                        setVerificationCode(numbers);
                      }}
                    />
                  ))}
                </div>
              </div>

              <AuthButton
                text="verify & register"
                icon={FaUserPlus}
                isLoading={isLoading}
              />
            </form>
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

          <div className="mb-6 p-4 rounded bg-primary/10 border border-primary/20">
            <h3 className="text-sm font-medium mb-2">Private Beta Access</h3>
            <p className="text-sm text-muted-foreground">
              Registration is currently invite-only. Join our{" "}
              <a
                href="https://discord.gg/emogirls"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline inline-flex items-center gap-1"
              >
                Discord <FaDiscord className="w-3 h-3" />
              </a>{" "}
              to request an invite code.
            </p>
          </div>

          <form
            className="flex flex-col gap-4"
            onSubmit={handleSendVerification}
          >
            <div className="flex flex-col gap-2">
              <label className="text-sm opacity-80">URL Slug</label>
              <div className="relative w-full">
                <input
                  type="text"
                  name="slug"
                  value={formData.slug}
                  onChange={handleInputChange}
                  className="w-full bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink pl-[90px]"
                  placeholder="your-unique-url"
                  pattern="[a-z0-9-]+"
                  title="Only lowercase letters, numbers, and hyphens"
                  required
                />
                <div className="absolute left-0 top-0 h-full flex items-center px-3 text-sm text-muted-foreground border-r border-[#1a1a1a] bg-primary/50">
                  emogir.ls/
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm opacity-80">Email</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                className="bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink"
                placeholder="your@email.com"
                required
              />
            </div>

            {/* <div className="flex flex-col gap-2">
              <label className="text-sm opacity-80">
                Display Name (optional)
              </label>
              <input
                type="text"
                name="displayName"
                value={formData.displayName}
                onChange={handleInputChange}
                className="bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink"
                placeholder="Your Name"
              />
            </div> */}

            <div className="flex flex-col gap-2">
              <label className="text-sm opacity-80">Password</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className="bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink"
                placeholder="••••••••"
                required
              />
              <ul className="text-xs space-y-1 text-muted-foreground">
                <li
                  className={`flex items-center gap-2 ${
                    formData.password.length >= 8
                      ? "text-green-500"
                      : "text-red-500"
                  }`}
                >
                  {formData.password.length >= 8 ? (
                    <FaCheck size={12} />
                  ) : (
                    <FaTimes size={12} />
                  )}
                  At least 8 characters long
                </li>
                <li
                  className={`flex items-center gap-2 ${
                    /[A-Z]/.test(formData.password)
                      ? "text-green-500"
                      : "text-red-500"
                  }`}
                >
                  {/[A-Z]/.test(formData.password) ? (
                    <FaCheck size={12} />
                  ) : (
                    <FaTimes size={12} />
                  )}
                  One uppercase letter
                </li>
                <li
                  className={`flex items-center gap-2 ${
                    /[a-z]/.test(formData.password)
                      ? "text-green-500"
                      : "text-red-500"
                  }`}
                >
                  {/[a-z]/.test(formData.password) ? (
                    <FaCheck size={12} />
                  ) : (
                    <FaTimes size={12} />
                  )}
                  One lowercase letter
                </li>
                <li
                  className={`flex items-center gap-2 ${
                    /[0-9]/.test(formData.password)
                      ? "text-green-500"
                      : "text-red-500"
                  }`}
                >
                  {/[0-9]/.test(formData.password) ? (
                    <FaCheck size={12} />
                  ) : (
                    <FaTimes size={12} />
                  )}
                  One number
                </li>
              </ul>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm opacity-80">Invite Code</label>
              <input
                type="text"
                name="inviteCode"
                value={formData.inviteCode}
                onChange={handleInputChange}
                className="bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink"
                placeholder="Enter your invite code"
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
              text="send verification"
              icon={FaUserPlus}
              isLoading={isLoading}
            />

            <p className="text-sm text-center opacity-80 mt-4">
              Already have an account?{" "}
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
