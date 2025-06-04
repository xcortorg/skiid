"use client";

import { signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/toast-provider";
import { useEffect } from "react";
import { ToastProvider } from "@/components/ui/toast-provider";

export default function SignOutPage() {
  const router = useRouter();
  const { toast } = useToast();

  useEffect(() => {
    const handleSignOut = async () => {
      try {
        await signOut({ redirect: false });
        router.push("/login");
        toast({
          title: "Success",
          description: "Signed out successfully",
          variant: "success",
        });
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to sign out",
          variant: "error",
        });
        router.push("/login");
      }
    };

    handleSignOut();
  }, [router, toast]);

  return (
    <ToastProvider>
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse">Signing out...</div>
      </div>
    </ToastProvider>
  );
}
