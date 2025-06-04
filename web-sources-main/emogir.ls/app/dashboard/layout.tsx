"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  IconHome,
  IconLink,
  IconSettings,
  IconUser,
  IconChartBar,
  IconPalette,
  IconChevronUp,
  IconLogout,
  IconMail,
  IconPhoto,
  IconCrown,
  IconEdit,
} from "@tabler/icons-react";
import { IconProps } from "@tabler/icons-react";
import { ShineBorder } from "@/components/magicui/shine-border";
import { useSession, signOut } from "next-auth/react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { QRCodeSVG } from "qrcode.react";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/appearance/input";
import { Label } from "@/components/ui/label";
import { ColorPicker } from "@/components/ui/appearance/color-picker";
import { MediaUpload } from "@/components/ui/appearance/media-upload";
import { AudioTracksManager } from "@/components/ui/appearance/audio-tracks-manager";
import { AlertCircle } from "lucide-react";
import { MessageSquare, LogOut } from "lucide-react";
import { ToastProvider } from "@/components/ui/toast-provider";
import { useToast } from "@/components/ui/toast-provider";
import { AppearanceSelect } from "@/components/ui/appearance/select";
import { Switch } from "@/components/ui/switch";
import { DecorationDialog } from "@/components/ui/appearance/decoration-dialog";
import { FileInput } from "@/components/ui/appearance/file-input";

type IconComponent = React.ComponentType<IconProps>;

type NavLink = {
  label: string;
  href?: string;
  icon?: IconComponent;
  type?: "section";
  children?: { href: string; label: string; isPremium?: boolean }[];
  isPremium?: boolean;
  badge?: string;
};

const links: NavLink[] = [
  {
    label: "Dashboard",
    type: "section",
  },
  {
    label: "Overview",
    href: "/dashboard",
    icon: IconHome,
  },
  {
    label: "Links",
    href: "/dashboard/links",
    icon: IconLink,
  },
  {
    label: "Analytics",
    href: "/dashboard/analytics",
    icon: IconChartBar,
  },
  {
    label: "Customize",
    type: "section",
  },
  {
    label: "Appearance",
    href: "/dashboard/appearance",
    icon: IconPalette,
    children: [
      { href: "/dashboard/appearance?tab=general", label: "General" },
      { href: "/dashboard/appearance?tab=typography", label: "Typography" },
      { href: "/dashboard/appearance?tab=links", label: "Links" },
      { href: "/dashboard/appearance?tab=effects", label: "Effects" },
      { href: "/dashboard/appearance?tab=discord", label: "Discord" },
    ],
  },
  {
    label: "Premium",
    type: "section",
  },
  {
    label: "Images",
    href: "/dashboard/image",
    icon: IconPhoto,
  },
  {
    label: "Email",
    href: "/dashboard/email",
    icon: IconMail,
    badge: "Coming Soon",
  },
  {
    label: "Account",
    type: "section",
  },
  {
    label: "Settings",
    href: "/dashboard/settings",
    icon: IconSettings,
  },
];

const AccountSuspensionBanner = ({ accountStatus }: { accountStatus: any }) => {
  return (
    <div className="min-h-screen bg-darker">
      <div className="max-w-2xl mx-auto pt-20 px-4">
        <div className="bg-black/40 border border-white/10 rounded-xl p-8 space-y-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-full bg-red-500/10">
              <AlertCircle className="w-6 h-6 text-red-500" />
            </div>
            <div className="space-y-1">
              <h1 className="text-xl font-semibold text-white">
                {accountStatus.accountStatus === "BANNED"
                  ? "Account Banned"
                  : accountStatus.accountStatus === "DISABLED"
                  ? "Account Temporarily Suspended"
                  : "Account Restricted"}
              </h1>
              <p className="text-white/60">
                {accountStatus.accountStatus === "BANNED"
                  ? "Your account has been permanently banned."
                  : accountStatus.accountStatus === "DISABLED"
                  ? "Your account has been temporarily suspended."
                  : "Your account has limited functionality."}
              </p>
            </div>
          </div>

          {(accountStatus.banReason || accountStatus.disabledReason) && (
            <div className="bg-white/5 border border-white/10 rounded-lg p-4">
              <div className="text-sm text-white/60">
                <span className="font-medium text-white">Reason: </span>
                {accountStatus.banReason || accountStatus.disabledReason}
              </div>
            </div>
          )}

          {accountStatus.banExpires && (
            <div className="bg-white/5 border border-white/10 rounded-lg p-4">
              <div className="text-sm text-white/60">
                <span className="font-medium text-white">
                  Suspension ends:{" "}
                </span>
                {new Date(accountStatus.banExpires).toLocaleDateString()}
              </div>
            </div>
          )}

          <div className="pt-4 flex flex-col sm:flex-row gap-3">
            <Link
              href="/support"
              className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary/90 transition-colors"
            >
              <MessageSquare className="w-4 h-4" />
              Contact Support
            </Link>
            <button
              onClick={() => signOut()}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-white/5 text-white hover:bg-white/10 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const LoadingState = () => (
  <div className="min-h-screen bg-darker flex items-center justify-center">
    <div className="flex flex-col items-center gap-4">
      <div className="w-12 h-12 rounded-full border-4 border-primary/10 border-t-primary animate-spin" />
      <div className="text-white/60 text-sm animate-pulse">
        Loading dashboard...
      </div>
    </div>
  </div>
);

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { toast } = useToast();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { data: session, status } = useSession();
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    avatar: null as string | null | undefined,
    banner: null as string | null | undefined,
    audioTracks: [] as any[],
    primaryColor: "#ff3379",
    secondaryColor: "#1a1a1a",
    glassEffect: false,
    bio: "",
    playerEnabled: false,
    displayName: "",
    font: "satoshi",
    fontSize: "md",
    fontWeight: "normal",
    gradientEnabled: false,
    borderRadius: "0px",
    titleColor: "#ffffff",
    bioColor: "#ffffff",
    clickEffectEnabled: false,
    backdropBlur: "0px",
    decoration: null as string | null,
  });
  const [accountStatus, setAccountStatus] = useState<{
    accountStatus: string;
    isDisabled: boolean;
    banReason?: string;
    banExpires?: Date;
    disabledReason?: string;
    warningCount: number;
    appealStatus?: string;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [openSections, setOpenSections] = useState<{ [key: string]: boolean }>(
    {}
  );
  const [decorationDialogOpen, setDecorationDialogOpen] = useState(false);
  const [uploading, setUploading] = useState(false);

  const showOnboarding =
    !isLoading && session?.user && !session.user.onboarding;

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
    }
  };

  const handleFinish = async () => {
    try {
      await fetch("/api/appearance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile: {
            avatar: formData.avatar,
            banner: formData.banner,
            bio: formData.bio,
            displayName: formData.displayName,
          },
          container: {
            glassEffect: formData.glassEffect,
          },
          colors: {
            primary: formData.primaryColor,
            secondary: formData.secondaryColor,
          },
          audio: {
            tracks: formData.audioTracks,
          },
          font: {
            name: formData.font,
            size: formData.fontSize,
            weight: formData.fontWeight,
          },
        }),
      });

      await fetch("/api/user/onboarding", { method: "POST" });

      router.refresh();
      toast({
        title: "Success",
        description: "Profile setup completed!",
        variant: "success",
      });

      if (session?.user) {
        session.user.onboarding = true;
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to complete onboarding",
        variant: "error",
      });
      console.error(error);
    }
  };

  const toggleSection = (label: string) => {
    setOpenSections((prev) => ({
      ...prev,
      [label]: !prev[label],
    }));
  };

  const handleDecorationSelect = ({
    type,
    url,
  }: {
    type: "avatar" | "decoration";
    url: string;
  }) => {
    setFormData((prev) => ({
      ...prev,
      [type]: url,
    }));
    setDecorationDialogOpen(false);
  };

  useEffect(() => {
    const checkAccountStatus = async () => {
      try {
        const response = await fetch("/api/user/status");
        if (!response.ok) {
          throw new Error("Failed to fetch account status");
        }
        const data = await response.json();
        setAccountStatus(data);
      } catch (error) {
        console.error("Error checking account status:", error);
        router.push("/login");
      } finally {
        setIsLoading(false);
      }
    };

    if (session?.user) {
      checkAccountStatus();
    }
  }, [session, router]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push(`/login?redirect=${encodeURIComponent("/dashboard")}`);
    }
  }, [status, router]);

  if (status === "loading") {
    return <LoadingState />;
  }

  if (status === "unauthenticated") {
    return null;
  }

  if (
    accountStatus &&
    (accountStatus.accountStatus !== "ACTIVE" || accountStatus.isDisabled)
  ) {
    return <AccountSuspensionBanner accountStatus={accountStatus} />;
  }

  return (
    <ToastProvider>
      <div className="min-h-screen">
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="lg:hidden fixed top-6 right-6 z-50 p-2 rounded-lg bg-primary/5 border border-primary/10"
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            className="text-white"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d={
                isMobileMenuOpen
                  ? "M6 18L18 6M6 6l12 12"
                  : "M4 6h16M4 12h16M4 18h16"
              }
            />
          </svg>
        </button>

        <nav
          className={`w-64 fixed inset-y-0 left-0 bg-darker border-r border-primary/10 p-4 z-40 styled-scrollbar flex flex-col transform lg:translate-x-0 transition-transform duration-200 ${
            isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="px-3 py-2 mb-4">
            <Link href="/">
              <h2 className="text-2xl font-bold">
                emogir<span className="text-primary text-sm">.ls</span>
              </h2>
            </Link>
          </div>
          <div className="px-2">
            <ShineBorder
              className="hover:bg-primary/10 transition-colors !min-w-0 w-full !border-0 bg-primary/5 rounded-lg"
              color="#ff3379"
              borderRadius={12}
            >
              <a
                href="https://discord.gg/emogirls"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 px-3 py-1"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="text-primary shrink-0"
                >
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z" />
                </svg>
                <div className="min-w-0">
                  <div className="text-xs font-medium text-white">
                    Join our Discord
                  </div>
                  <div className="text-[10px] text-white/50">
                    Be part of our community
                  </div>
                </div>
              </a>
            </ShineBorder>
          </div>

          <div className="px-2 mt-2 space-y-1 flex-1">
            <ul className="space-y-1">
              {links.map((link) => (
                <li key={link.label}>
                  {link.type === "section" ? (
                    <div className="px-3 py-2 text-xs font-semibold text-white/40 uppercase tracking-wider">
                      {link.label}
                    </div>
                  ) : (
                    <>
                      {link.children ? (
                        <div className="space-y-1">
                          <button
                            onClick={() => toggleSection(link.label)}
                            className="flex items-center justify-between w-full gap-3 px-4 py-3 text-white/60 hover:text-white hover:bg-primary/5 rounded-lg"
                          >
                            <div className="flex items-center gap-3">
                              {link.icon && (
                                <span className="text-primary">
                                  <link.icon size={16} />
                                </span>
                              )}
                              <span className="font-medium text-sm">
                                {link.label}
                              </span>
                            </div>
                            <IconChevronUp
                              size={16}
                              className={`text-white/60 transition-transform ${
                                openSections[link.label]
                                  ? "transform rotate-180"
                                  : ""
                              }`}
                            />
                          </button>

                          {openSections[link.label] !== false && (
                            <ul className="ml-4 border-l border-primary/10 pl-4 space-y-1">
                              {link.children.map((child) => (
                                <li key={child.href}>
                                  <Link
                                    href={child.href}
                                    className={`block py-2 px-4 rounded-lg text-sm transition-all outline-none ${
                                      pathname === child.href
                                        ? "bg-primary/10 text-primary border border-primary/20"
                                        : "text-white/60 hover:text-white hover:bg-primary/5"
                                    }`}
                                  >
                                    {child.label}
                                  </Link>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ) : (
                        <Link
                          href={link.href!}
                          className={`peer/menu-button rounded-md flex w-full items-center gap-2 overflow-hidden p-2 text-left outline-none ring-ring transition-all focus-visible:ring-2 active:bg-primary/5 active:text-foreground disabled:pointer-events-none disabled:opacity-50 h-10 text-sm relative flex items-center rounded-lg px-3 border ${
                            pathname === link.href
                              ? "border-primary/[0.125] bg-primary/5 bg-gradient-to-br from-primary/[0.01] to-primary/[0.03] !text-foreground"
                              : "border-transparent text-white/60 hover:text-white hover:bg-primary/5"
                          }`}
                        >
                          {pathname === link.href && (
                            <div className="absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-r-xl bg-primary" />
                          )}
                          <span className="mr-1 text-primary">
                            {link.icon && <link.icon size={16} />}
                          </span>
                          <span className="font-medium">{link.label}</span>
                          {link.isPremium && (
                            <div className="ml-auto flex items-center gap-1">
                              <IconCrown size={12} className="text-primary" />
                              <span className="text-xs text-primary/80">
                                Premium
                              </span>
                            </div>
                          )}
                          {link.badge && (
                            <span className="ml-auto text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                              {link.badge}
                            </span>
                          )}
                        </Link>
                      )}
                    </>
                  )}
                </li>
              ))}
            </ul>
          </div>
          <div className="mt-auto px-2 space-y-2">
            <div className="group relative">
              <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-primary/5 cursor-pointer">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center overflow-hidden">
                  {session?.user?.image ? (
                    <img
                      src={session.user.image}
                      alt={session.user.name || "Profile"}
                      className="w-8 h-8 object-cover"
                    />
                  ) : (
                    <IconUser size={16} className="text-primary" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate">
                    {session?.user?.name || "User"}
                  </div>
                  <div className="text-xs text-white/60 truncate">
                    @{session?.user?.username || "username"}
                  </div>
                </div>
                <IconChevronUp size={16} className="text-white/60" />
              </div>

              <div className="absolute bottom-full mb-2 left-0 w-full">
                <div className="bg-darker border border-primary/10 rounded-lg shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto transition-all">
                  <Link
                    href="/dashboard/settings"
                    className="flex items-center gap-2 p-2 hover:bg-primary/5 text-white/80 hover:text-white transition-colors"
                  >
                    <IconUser size={16} className="text-primary" />
                    <span className="text-sm">Profile</span>
                  </Link>
                  <button
                    onClick={handleSignOut}
                    className="w-full flex items-center gap-2 p-2 hover:bg-primary/5 text-white/80 hover:text-white transition-colors text-left border-t border-primary/10"
                  >
                    <IconLogout size={16} className="text-primary" />
                    <span className="text-sm">Sign out</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </nav>

        <AnimatePresence>
          {showShareDialog && (
            <Dialog open={showShareDialog} onOpenChange={setShowShareDialog}>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Share Your Profile</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <p className="text-sm text-white/60">
                      Get more views by sharing your emogir.ls link across all
                      platforms.
                    </p>

                    <div className="flex justify-center animate-in fade-in-50 slide-in-from-bottom-4 duration-300 delay-100">
                      <div className="relative">
                        <QRCodeSVG
                          value={`https://emogir.ls/${session?.user?.username}`}
                          size={200}
                          className="bg-darker p-4 rounded-lg border border-primary/10"
                          bgColor="#030303"
                          fgColor="#ff3379"
                          level="H"
                          imageSettings={{
                            src: "/emogirls-eyes.webp",
                            height: 40,
                            width: 40,
                            excavate: true,
                          }}
                        />
                      </div>
                    </div>

                    <div className="bg-black/20 rounded-lg p-3 flex items-center justify-between animate-in fade-in-50 slide-in-from-bottom-3 duration-300 delay-150">
                      <span className="text-sm text-white/60">
                        emogir.ls/{session?.user?.username}
                      </span>
                      <Button
                        onClick={() => {
                          navigator.clipboard.writeText(
                            `https://emogir.ls/${session?.user?.username}`
                          );
                          toast({
                            title: "Copied",
                            description: `emogir.ls/${session?.user?.username}`,
                            variant: "success",
                          });
                        }}
                        className="bg-primary/10 text-primary text-sm px-3 py-1"
                      >
                        Copy
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </motion.div>
            </Dialog>
          )}
        </AnimatePresence>

        {showOnboarding && (
          <div className="fixed inset-0 bg-black/90 backdrop-blur-xl z-50 flex items-center justify-center overflow-y-auto">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="w-full min-h-screen flex flex-col md:flex-row"
            >
              <div className="md:hidden fixed top-0 inset-x-0 z-50 bg-black/80 backdrop-blur-md border-b border-primary/10 p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full flex items-center justify-center bg-primary text-white">
                      <span className="text-xs">{currentStep}</span>
                    </div>
                    <span className="text-sm font-medium text-white">
                      {
                        ["Welcome", "Appearance", "Media", "Social"][
                          currentStep - 1
                        ]
                      }
                    </span>
                  </div>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4].map((step) => (
                      <div
                        key={`mobile-step-indicator-${step}`}
                        className={`h-1 rounded-full transition-all duration-300 ${
                          step === currentStep
                            ? "w-6 bg-rose-500"
                            : step < currentStep
                            ? "w-4 bg-rose-500/40"
                            : "w-4 bg-white/10"
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <div className="hidden md:block w-80 bg-darker border-r border-primary/10 relative overflow-hidden">
                <div className="absolute -top-60 -right-60 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
                <div className="absolute -bottom-60 -left-60 w-80 h-80 bg-primary/5 rounded-full blur-3xl pointer-events-none" />

                <div className="relative z-10 p-8 h-full flex flex-col">
                  <div className="mb-12">
                    <h2 className="text-2xl font-bold bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent">
                      Setup your profile
                    </h2>
                    <p className="text-sm text-white/60 mt-2">
                      Complete in just a few steps
                    </p>
                  </div>

                  <div className="space-y-4 flex-1">
                    {[
                      { step: 1, title: "Welcome", desc: "Basic information" },
                      {
                        step: 2,
                        title: "Appearance",
                        desc: "Customize your profile",
                      },
                      { step: 3, title: "Media", desc: "Add photos and music" },
                      {
                        step: 4,
                        title: "Social",
                        desc: "Connect your accounts",
                      },
                    ].map(({ step, title, desc }) => (
                      <motion.div
                        key={step}
                        initial={{ opacity: 0, filter: "blur(8px)" }}
                        animate={{
                          opacity: currentStep >= step ? 1 : 0.5,
                          filter: "blur(0px)",
                        }}
                        transition={{
                          duration: 0.4,
                          ease: [0.4, 0, 0.2, 1],
                          scale: {
                            type: "spring",
                            damping: 15,
                            stiffness: 200,
                          },
                        }}
                        className={`relative p-4 rounded-lg backdrop-blur-sm
                        ${
                          currentStep === step
                            ? "bg-gradient-to-r from-primary/10 to-transparent border-primary/20"
                            : currentStep > step
                            ? "bg-white/[0.02] border-white/10"
                            : "bg-black/20 border-white/5"
                        } border transition-all duration-500`}
                      >
                        <div className="flex items-center gap-4">
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center ${
                              currentStep === step
                                ? "bg-primary text-white"
                                : currentStep > step
                                ? "bg-primary/20 text-primary"
                                : "bg-white/5 text-white/40"
                            } transition-all duration-300`}
                          >
                            {currentStep > step ? (
                              <svg
                                className="w-4 h-4"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M5 13l4 4L19 7"
                                />
                              </svg>
                            ) : (
                              <span className="text-sm">{step}</span>
                            )}
                          </div>
                          <div>
                            <h3
                              className={`text-base font-medium ${
                                currentStep === step
                                  ? "text-white"
                                  : currentStep > step
                                  ? "text-primary/80"
                                  : "text-white/40"
                              }`}
                            >
                              {title}
                            </h3>
                            <p className="text-xs text-white/40">{desc}</p>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>

                  <div className="mt-auto pt-6">
                    <motion.div
                      key={currentStep}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.5 }}
                      className="text-xs text-white/40 flex items-center gap-2"
                    >
                      <span className="w-2 h-2 rounded-full bg-primary/50 animate-pulse"></span>
                      Step {currentStep} of 4
                    </motion.div>
                  </div>
                </div>
              </div>

              <div className="flex-1 flex flex-col bg-gradient-to-br from-black to-black/90 min-h-screen">
                <div className="flex-1 overflow-auto styled-scrollbar pt-16 md:pt-0">
                  <div className="max-w-3xl mx-auto w-full px-4 py-6 md:p-8">
                    <motion.div
                      key={currentStep}
                      initial={{ opacity: 0, filter: "blur(8px)" }}
                      animate={{
                        opacity: 1,
                        filter: "blur(0px)",
                        transition: {
                          opacity: { duration: 0.4, ease: "easeOut" },
                          filter: { duration: 0.3, ease: "easeOut" },
                        },
                      }}
                      exit={{
                        opacity: 0,
                        filter: "blur(4px)",
                        transition: {
                          opacity: { duration: 0.2, ease: "easeIn" },
                          filter: { duration: 0.2, ease: "easeIn" },
                        },
                      }}
                      className="space-y-6"
                    >
                      {currentStep === 1 && (
                        <div className="space-y-6">
                          <div className="relative">
                            {/* <div className="absolute -top-20 -right-20 w-40 h-40 bg-primary/10 rounded-full blur-3xl" /> */}
                            <div className="relative">
                              <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ duration: 0.3 }}
                              >
                                <span className="inline-block px-3 py-1 text-xs font-medium text-primary border border-primary/30 rounded-full mb-3">
                                  Welcome to emogir.ls
                                </span>
                              </motion.div>
                              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white">
                                Let's set up your profile
                              </h1>
                              <p className="text-sm text-white/60 mt-2">
                                Share your identity with the world in style
                              </p>
                            </div>
                          </div>

                          <div className="space-y-6 rounded-xl border border-white/5 bg-white/[0.01] backdrop-blur-sm p-4 sm:p-6">
                            <div className="space-y-4">
                              <div className="space-y-2">
                                <Label
                                  htmlFor="displayName"
                                  className="text-white"
                                >
                                  Display Name
                                </Label>
                                <Input
                                  id="displayName"
                                  placeholder="Your display name"
                                  value={formData.displayName}
                                  onChange={(e) =>
                                    setFormData({
                                      ...formData,
                                      displayName: e.target.value,
                                    })
                                  }
                                  className="bg-black/20 border-primary/10 text-white placeholder:text-white/40"
                                />
                              </div>

                              <div className="space-y-2">
                                <Label htmlFor="bio" className="text-white">
                                  Bio
                                </Label>
                                <textarea
                                  id="bio"
                                  placeholder="Tell the world about yourself..."
                                  value={formData.bio}
                                  onChange={(e) =>
                                    setFormData({
                                      ...formData,
                                      bio: e.target.value,
                                    })
                                  }
                                  className="w-full h-20 sm:h-24 bg-black/20 border border-primary/10 rounded-lg p-3 text-white placeholder:text-white/40 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
                                />
                              </div>

                              <div className="space-y-2">
                                <Label className="text-white">Typography</Label>
                                <AppearanceSelect
                                  label="Font"
                                  value={formData.font}
                                  onChange={(value) =>
                                    setFormData({ ...formData, font: value })
                                  }
                                  options={[
                                    { label: "Satoshi", value: "satoshi" },
                                    { label: "Inter", value: "inter" },
                                    { label: "Outfit", value: "outfit" },
                                    {
                                      label: "Space Grotesk",
                                      value: "space-grotesk",
                                    },
                                    {
                                      label: "Plus Jakarta Sans",
                                      value: "plus-jakarta-sans",
                                    },
                                    { label: "Sora", value: "sora" },
                                  ]}
                                />
                              </div>

                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                                <div className="space-y-2">
                                  <AppearanceSelect
                                    label="Font Size"
                                    value={formData.fontSize}
                                    onChange={(value) =>
                                      setFormData({
                                        ...formData,
                                        fontSize: value,
                                      })
                                    }
                                    options={[
                                      { label: "Small", value: "sm" },
                                      { label: "Medium", value: "md" },
                                      { label: "Large", value: "lg" },
                                    ]}
                                  />
                                </div>
                                <div className="space-y-2">
                                  <AppearanceSelect
                                    label="Font Weight"
                                    value={formData.fontWeight}
                                    onChange={(value) =>
                                      setFormData({
                                        ...formData,
                                        fontWeight: value,
                                      })
                                    }
                                    options={[
                                      { label: "Normal", value: "normal" },
                                      { label: "Medium", value: "medium" },
                                      { label: "Bold", value: "bold" },
                                    ]}
                                  />
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {currentStep === 2 && (
                        <div className="space-y-6">
                          <div className="relative">
                            {/* <div className="absolute -top-20 -right-20 w-40 h-40 bg-primary/10 rounded-full blur-3xl" /> */}
                            <div className="relative">
                              <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ duration: 0.3 }}
                              >
                                <span className="inline-block px-3 py-1 text-xs font-medium text-primary border border-primary/30 rounded-full mb-3">
                                  Appearance
                                </span>
                              </motion.div>
                              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white">
                                Make it yours
                              </h1>
                              <p className="text-sm text-white/60 mt-2">
                                Customize colors and effects to reflect your
                                style
                              </p>
                            </div>
                          </div>

                          <div className="space-y-6 rounded-xl border border-white/5 bg-white/[0.01] backdrop-blur-sm p-4 sm:p-6">
                            <div className="space-y-6">
                              <div className="space-y-4">
                                <h3 className="text-sm font-medium text-white/80 border-b border-white/10 pb-2">
                                  Colors
                                </h3>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                                  <div className="space-y-3">
                                    <ColorPicker
                                      label="Primary Color"
                                      value={formData.primaryColor}
                                      onChange={(color) =>
                                        setFormData({
                                          ...formData,
                                          primaryColor: color,
                                        })
                                      }
                                    />
                                  </div>
                                  <div className="space-y-3">
                                    <ColorPicker
                                      label="Secondary Color"
                                      value={formData.secondaryColor}
                                      onChange={(color) =>
                                        setFormData({
                                          ...formData,
                                          secondaryColor: color,
                                        })
                                      }
                                    />
                                  </div>
                                </div>
                              </div>

                              <div className="space-y-4">
                                <h3 className="text-sm font-medium text-white/80 border-b border-white/10 pb-2">
                                  Text Colors
                                </h3>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                                  <ColorPicker
                                    label="Title Color"
                                    value={formData.titleColor}
                                    onChange={(color) =>
                                      setFormData({
                                        ...formData,
                                        titleColor: color,
                                      })
                                    }
                                  />
                                  <ColorPicker
                                    label="Bio Color"
                                    value={formData.bioColor}
                                    onChange={(color) =>
                                      setFormData({
                                        ...formData,
                                        bioColor: color,
                                      })
                                    }
                                  />
                                </div>
                              </div>

                              <div className="space-y-4">
                                <h3 className="text-sm font-medium text-white/80 border-b border-white/10 pb-2">
                                  Effects
                                </h3>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                  <div className="flex items-center space-x-2 bg-black/20 p-3 rounded-lg">
                                    <Switch
                                      checked={formData.glassEffect}
                                      onCheckedChange={(checked) =>
                                        setFormData({
                                          ...formData,
                                          glassEffect: checked,
                                        })
                                      }
                                    />
                                    <Label>Glass effect</Label>
                                  </div>

                                  <div className="flex items-center space-x-2 bg-black/20 p-3 rounded-lg">
                                    <Switch
                                      checked={formData.gradientEnabled}
                                      onCheckedChange={(checked) =>
                                        setFormData({
                                          ...formData,
                                          gradientEnabled: checked,
                                        })
                                      }
                                    />
                                    <Label>Gradient effect</Label>
                                  </div>

                                  <div className="flex items-center space-x-2 bg-black/20 p-3 rounded-lg">
                                    <Switch
                                      checked={formData.clickEffectEnabled}
                                      onCheckedChange={(checked) =>
                                        setFormData({
                                          ...formData,
                                          clickEffectEnabled: checked,
                                        })
                                      }
                                    />
                                    <Label>Click effects</Label>
                                  </div>
                                </div>
                              </div>

                              <div className="space-y-4">
                                <h3 className="text-sm font-medium text-white/80 border-b border-white/10 pb-2">
                                  Container Style
                                </h3>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                                  <AppearanceSelect
                                    label="Border Radius"
                                    value={formData.borderRadius}
                                    onChange={(value) =>
                                      setFormData({
                                        ...formData,
                                        borderRadius: value,
                                      })
                                    }
                                    options={[
                                      { label: "None", value: "0px" },
                                      { label: "Small", value: "8px" },
                                      { label: "Medium", value: "12px" },
                                      { label: "Large", value: "16px" },
                                    ]}
                                  />
                                  <AppearanceSelect
                                    label="Blur Effect"
                                    value={formData.backdropBlur}
                                    onChange={(value) =>
                                      setFormData({
                                        ...formData,
                                        backdropBlur: value,
                                      })
                                    }
                                    options={[
                                      { label: "None", value: "0px" },
                                      { label: "Subtle", value: "4px" },
                                      { label: "Medium", value: "8px" },
                                      { label: "Strong", value: "12px" },
                                    ]}
                                  />
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {currentStep === 3 && (
                        <div className="space-y-6">
                          <div className="relative">
                            {/* <div className="absolute -top-20 -right-20 w-40 h-40 bg-primary/10 rounded-full blur-3xl" /> */}
                            <div className="relative">
                              <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ duration: 0.3 }}
                              >
                                <span className="inline-block px-3 py-1 text-xs font-medium text-primary border border-primary/30 rounded-full mb-3">
                                  Media
                                </span>
                              </motion.div>
                              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white">
                                Show yourself
                              </h1>
                              <p className="text-sm text-white/60 mt-2">
                                Add images and music to express who you are
                              </p>
                            </div>
                          </div>

                          <div className="space-y-6 rounded-xl border border-white/5 bg-white/[0.01] backdrop-blur-sm p-4 sm:p-6">
                            <div className="space-y-6">
                              <div className="space-y-4">
                                <h3 className="text-sm font-medium text-white/80 border-b border-white/10 pb-2">
                                  Profile Media
                                </h3>

                                <div className="mb-6">
                                  <Label className="text-white block mb-2">
                                    Profile Picture
                                  </Label>
                                  <div className="relative bg-black/20 rounded-lg p-4 border border-white/5 hover:border-primary/20 transition-colors">
                                    {formData.avatar ? (
                                      <div className="relative w-28 h-28 sm:w-32 sm:h-32 mx-auto rounded-full overflow-hidden">
                                        <img
                                          src={formData.avatar}
                                          alt="Avatar"
                                          className="w-full h-full object-cover"
                                        />
                                        <button
                                          onClick={() =>
                                            setFormData((prev) => ({
                                              ...prev,
                                              avatar: null,
                                            }))
                                          }
                                          className="absolute top-0 right-0 bg-black/60 p-1 rounded-full hover:bg-black/80"
                                        >
                                          <svg
                                            className="w-4 h-4 text-white"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor"
                                          >
                                            <path
                                              strokeLinecap="round"
                                              strokeLinejoin="round"
                                              strokeWidth={2}
                                              d="M6 18L18 6M6 6l12 12"
                                            />
                                          </svg>
                                        </button>
                                      </div>
                                    ) : (
                                      <FileInput
                                        accept="image/jpeg,image/png,image/webp"
                                        value={formData.avatar}
                                        disabled={uploading}
                                        onValueChange={async (file) => {
                                          if (!file) {
                                            setFormData((prev) => ({
                                              ...prev,
                                              avatar: null,
                                            }));
                                            return;
                                          }
                                          try {
                                            setUploading(true);
                                            const formData = new FormData();
                                            formData.append("file", file);
                                            const response = await fetch(
                                              "/api/upload/avatar",
                                              {
                                                method: "POST",
                                                body: formData,
                                              }
                                            );
                                            if (!response.ok)
                                              throw new Error("Upload failed");
                                            const data = await response.json();
                                            setFormData((prev) => ({
                                              ...prev,
                                              avatar: data.url,
                                            }));
                                            toast({
                                              title: "Success",
                                              description:
                                                "Avatar uploaded successfully",
                                              variant: "success",
                                            });
                                          } catch (error) {
                                            toast({
                                              title: "Error",
                                              description:
                                                "Failed to upload avatar",
                                              variant: "error",
                                            });
                                            console.error(error);
                                          } finally {
                                            setUploading(false);
                                          }
                                        }}
                                      />
                                    )}
                                  </div>
                                  <p className="text-xs text-white/60 mt-1">
                                    Recommended size: 500×500px
                                  </p>
                                </div>

                                <div>
                                  <Label className="text-white block mb-2">
                                    Banner Image
                                  </Label>
                                  <MediaUpload
                                    type="banner"
                                    value={formData.banner}
                                    onChange={(url: string | boolean | null) =>
                                      setFormData({
                                        ...formData,
                                        banner: url as string | null,
                                      })
                                    }
                                    className="aspect-video bg-black/20 rounded-lg border border-white/5 hover:border-primary/20 transition-colors"
                                  />
                                  <p className="text-xs text-white/60 mt-1">
                                    Recommended size: 1500×500px
                                  </p>
                                </div>
                              </div>

                              <div className="space-y-4">
                                <h3 className="text-sm font-medium text-white/80 border-b border-white/10 pb-2">
                                  Audio Player
                                </h3>
                                <div className="space-y-4 bg-black/20 rounded-lg p-4 border border-white/5">
                                  <div className="flex items-center gap-2">
                                    <Switch
                                      checked={formData.playerEnabled}
                                      onCheckedChange={(enabled) =>
                                        setFormData({
                                          ...formData,
                                          playerEnabled: enabled,
                                        })
                                      }
                                    />
                                    <Label className="text-white">
                                      Enable audio player
                                    </Label>
                                  </div>

                                  <AudioTracksManager
                                    tracks={formData.audioTracks}
                                    onTracksChange={(tracks) =>
                                      setFormData({
                                        ...formData,
                                        audioTracks: tracks,
                                      })
                                    }
                                    playerEnabled={formData.playerEnabled}
                                    onPlayerEnabledChange={(enabled) =>
                                      setFormData({
                                        ...formData,
                                        playerEnabled: enabled,
                                      })
                                    }
                                  />
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {currentStep === 4 && (
                        <div className="space-y-6">
                          <div className="relative">
                            {/* <div className="absolute -top-20 -right-20 w-40 h-40 bg-primary/10 rounded-full blur-3xl" /> */}
                            <div className="relative">
                              <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ duration: 0.3 }}
                              >
                                <span className="inline-block px-3 py-1 text-xs font-medium text-primary border border-primary/30 rounded-full mb-3">
                                  Social
                                </span>
                              </motion.div>
                              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white">
                                Connect accounts
                              </h1>
                              <p className="text-sm text-white/60 mt-2">
                                Link your social media accounts to enhance your
                                profile
                              </p>
                            </div>
                          </div>

                          <div className="space-y-6 rounded-xl border border-white/5 bg-white/[0.01] backdrop-blur-sm p-4 sm:p-6">
                            <motion.div
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              transition={{
                                duration: 0.4,
                                ease: [0.4, 0, 0.2, 1],
                              }}
                              className="flex flex-col gap-4 backdrop-blur-[2px]"
                            >
                              <div className="text-center text-white/60">
                                <p className="mb-2">
                                  You can connect your social accounts later in
                                  the settings page.
                                </p>
                                <p className="text-sm">
                                  This includes Discord, Last.fm, and more!
                                </p>
                              </div>
                            </motion.div>
                          </div>
                        </div>
                      )}
                    </motion.div>
                  </div>
                </div>

                <div className="sticky bottom-0 left-0 right-0 backdrop-blur-md bg-black/60 border-t border-primary/10 p-4 md:p-6 mt-auto">
                  <div className="max-w-3xl mx-auto w-full flex items-center justify-between gap-4">
                    <div className="flex gap-3 w-full">
                      {currentStep > 1 ? (
                        <Button
                          onClick={() => setCurrentStep(currentStep - 1)}
                          className="px-4 py-2 bg-black/40 hover:bg-black/60 text-white text-sm shadow-lg w-1/2"
                        >
                          Back
                        </Button>
                      ) : (
                        <div className="w-1/2"></div>
                      )}
                      <Button
                        onClick={() => {
                          if (currentStep < 4) {
                            setCurrentStep(currentStep + 1);
                          } else {
                            handleFinish();
                          }
                        }}
                        className="px-4 py-2 bg-primary hover:bg-primary/90 text-white text-sm font-medium shadow-lg shadow-primary/20 w-1/2"
                      >
                        {currentStep === 4 ? "Complete Setup" : "Continue"}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        )}
        <div className="lg:pl-64 min-h-screen">
          <main className="mx-auto pt-8 pb-16 px-4">{children}</main>
        </div>
      </div>
    </ToastProvider>
  );
}
