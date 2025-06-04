"use client";

import { Button } from "@/components/ui/button";
import { DataCard } from "@/components/ui/data-card";
import {
  IconLock,
  IconPalette,
  IconTrash,
  IconSeo,
  IconUser,
  IconDownload,
  IconCopy,
  IconDevices,
  IconLink,
  IconServer,
} from "@tabler/icons-react";
import { InputGroup } from "@/components/ui/input-group";
import { Switch } from "@/components/ui/switch";
import { useState, useEffect } from "react";
import { QRCodeSVG } from "qrcode.react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FaDiscord, FaLastfm } from "react-icons/fa";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast-provider";

const AVAILABLE_DOMAINS = [
  { url: "emogir.ls", featured: true },
  { url: "bigblackmen.lol" },
  { url: "boob.lol" },
  { url: "esex.top" },
  { url: "evil.bio" },
  { url: "exitscam.online" },
  { url: "femboys.wtf" },
  { url: "free-thigh.pics" },
  { url: "gays.lol" },
  { url: "regret.wtf" },
  { url: "remt-a-negro.lol" },
  { url: "screwnnegros.lol" },
  { url: "oooooooooooo.online" },
  { url: "heists.lol" },
  { url: "girlfriend.lol" },
  { url: "boyfriend.lol" },
  { url: "husband.lol" },
  { url: "wife.lol" },
  { url: "hell.lol" },
  { url: "loves-virg.in" },
  { url: "lame.rip" },
  { url: "betray.rip" },
  { url: "creep.ovh" },
  { url: "harassi.ng" },
  { url: "inject.bio" },
  { url: "punish.lol" },
  { url: "occur.lol" },
  { url: "femboy-feet.pics" },
  { url: "eslut.online" },
  { url: "is-a-femboy.lol" },
  { url: "chasity.lol" },
  { url: "is-femboy.lol" },
  { url: "femboy-gooner.lol" },
  { url: "femboy-porn.pics" },
  { url: "suck-dick.online" },
  { url: "zombie.gold" },
  { url: "yvl.rocks" },
  { url: "boykisser.space" },
  { url: "degrad.es" },
  { url: "convul.se" },
  { url: "sexts.me" },
  { url: "humilaties.me" },
  { url: "degrades.me" },
  { url: "reallyri.ch" },
  { url: "tortures.men" },
  { url: "threateni.ng" },
  { url: "scari.ng" },
  { url: "doxing-ur.info" },
  { url: "depressi.ng" },
  { url: "youngvamp.life" },
  { url: "astolfo-pics.lol" },
  { url: "kayne-feet.pics" },
  { url: "opm.baby" },
  { url: "finesh.it" },
  { url: "ageplayi.ng" },
  { url: "astolfo-feet.pics" },
  { url: "kanye-feet.pics" },
  { url: "xmrpri.de" },
  { url: "gasje.ws" },
  { url: "playboicarti.net" },
  { url: "playboicarti.org" },
  { url: "goth.pics" },
  { url: "ageba.it" },
].sort((a, b) => {
  if (a.featured) return -1;
  if (b.featured) return 1;
  return a.url.localeCompare(b.url);
});

interface SettingsState {
  displayName: string;
  username: string;
  pageTitle: string;
  seoDescription: string;
  isPrivate: boolean;
  twoFactorEnabled: boolean;
  discordAccount: {
    username: string;
    discriminator: string;
    id: string;
  } | null;
  lastfmAccount: {
    username: string;
    url: string;
  } | null;
  selectedDomains: string[];
  newLoginVerification: boolean;
  pinEnabled: boolean;
  pin: string;
  confirmPin: string;
  customHostname: string;
  isPremium: boolean;
}

interface UserSession {
  id: string;
  deviceInfo:
    | string
    | {
        name: string;
        details: {
          browser: string;
          os: string;
          device: string;
        };
      };
  location: string;
  lastActive: string;
  isActive: boolean;
}

function formatDeviceInfo(deviceInfoStr: string | object): string {
  try {
    const info =
      typeof deviceInfoStr === "string"
        ? JSON.parse(deviceInfoStr)
        : deviceInfoStr;
    if (info.name) {
      return info.name;
    }
    return `${info.browser} on ${info.os}`;
  } catch (e) {
    return "Unknown Device";
  }
}

export default function SettingsPage() {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [settings, setSettings] = useState<SettingsState>({
    displayName: "",
    username: "",
    pageTitle: "",
    seoDescription: "",
    isPrivate: false,
    twoFactorEnabled: false,
    discordAccount: null,
    lastfmAccount: null,
    selectedDomains: [],
    newLoginVerification: true,
    pinEnabled: false,
    pin: "",
    confirmPin: "",
    customHostname: "",
    isPremium: false,
  });
  const [showTwoFactorDialog, setShowTwoFactorDialog] = useState(false);
  const [verificationCode, setVerificationCode] = useState("");
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [mockSecret, setMockSecret] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [qrCodeUrl, setQrCodeUrl] = useState("");
  const [showVerifyDialog, setShowVerifyDialog] = useState(false);
  const [verifyAction, setVerifyAction] = useState<
    "disable" | "viewCodes" | "changePassword" | null
  >(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [passwordData, setPasswordData] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [passwordError, setPasswordError] = useState("");
  const [userSessions, setUserSessions] = useState<UserSession[]>([]);
  const [domainSearch, setDomainSearch] = useState("");
  const [pinError, setPinError] = useState("");
  const [pinSettings, setPinSettings] = useState({
    enabled: false,
    pin: "",
    confirmPin: "",
  });
  const [showChangePin, setShowChangePin] = useState(false);
  const [currentPin, setCurrentPin] = useState("");
  const [connectionStatus, setConnectionStatus] = useState<{
    type: "error" | "success";
    message: string;
  } | null>(null);
  const [hostnameError, setHostnameError] = useState("");
  const [isCheckingHostname, setIsCheckingHostname] = useState(false);
  const [isPremium, setIsPremium] = useState(false);
  const [premiumFeatures, setPremiumFeatures] = useState<{
    customDomain?: boolean;
    imageHosting?: boolean;
    maxLinks?: number;
    maxStorage?: number;
    customThemes?: boolean;
    removeWatermark?: boolean;
    prioritySupport?: boolean;
  }>({});
  const [isVerifyingDomain, setIsVerifyingDomain] = useState(false);
  const [domainStatus, setDomainStatus] = useState<{
    verified: boolean;
    message: string;
    step?: number;
    records?: { type: string; name: string; value: string }[];
  } | null>(null);

  const nodeInfo = "EU-NL-LOAD1";

  useEffect(() => {
    const fetchData = async () => {
      try {
        const settingsRes = await fetch("/api/settings");
        const settingsData = await settingsRes.json();

        setSettings((prevSettings) => ({
          ...prevSettings,
          ...settingsData,
          customHostname: settingsData.customHostname || "",
        }));

        setPinSettings((prev) => ({
          ...prev,
          enabled: settingsData.pinEnabled,
          pin: "",
          confirmPin: "",
        }));

        const premiumRes = await fetch("/api/user/premium");
        const premiumData = await premiumRes.json();

        setIsPremium(premiumData.isPremium);
        setPremiumFeatures(premiumData.features || {});

        if (
          settingsData.customHostname &&
          premiumData.isPremium &&
          premiumData.features?.customDomain
        ) {
          checkDomainStatus(settingsData.customHostname);
        }

        const [discordRes, lastfmRes] = await Promise.all([
          fetch("/api/account/discord"),
          fetch("/api/account/lastfm"),
        ]);

        if (!discordRes.ok || !lastfmRes.ok)
          throw new Error("Failed to load accounts");
        const discordData = await discordRes.json();
        const lastfmData = await lastfmRes.json();

        setSettings((prev) => ({
          ...prev,
          discordAccount: discordData,
          lastfmAccount: lastfmData,
          newLoginVerification: settingsData.newLoginVerification ?? true,
          pinEnabled: settingsData.pinEnabled || false,
          customHostname: settingsData.customHostname || "",
        }));

        if (
          settingsData.customHostname &&
          premiumData.isPremium &&
          premiumData.features?.customDomain
        ) {
          checkDomainStatus(settingsData.customHostname);
        }
      } catch (error) {
        console.error("Failed to load data:", error);
        toast({
          title: "Error",
          description: "Failed to load settings",
          variant: "error",
        });
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    const fetchSessions = async () => {
      const res = await fetch("/api/account/sessions");
      const data = await res.json();
      setUserSessions(data);
    };
    fetchSessions();
  }, []);

  useEffect(() => {
    const handleConnectionStatus = () => {
      const params = new URLSearchParams(window.location.search);

      if (params.get("success") === "discord_updated") {
        setConnectionStatus({
          type: "success",
          message: "Discord connection updated successfully",
        });
      } else if (params.get("error") === "account_in_use") {
        setConnectionStatus({
          type: "error",
          message: "Discord account already connected to another profile",
        });
      } else if (params.get("error") === "no_code") {
        setConnectionStatus({
          type: "error",
          message: "No authorization code received from Discord",
        });
      } else if (params.get("error") === "connection_failed") {
        setConnectionStatus({
          type: "error",
          message: "Failed to connect account",
        });
      } else if (params.get("error") === "unauthorized") {
        setConnectionStatus({
          type: "error",
          message: "Unauthorized access",
        });
      } else if (params.get("error") === "no_token") {
        setConnectionStatus({
          type: "error",
          message: "No access token received",
        });
      }

      if (params.get("success") === "discord_connected") {
        setConnectionStatus({
          type: "success",
          message: "Discord account connected successfully",
        });
      } else if (params.get("success") === "lastfm_connected") {
        setConnectionStatus({
          type: "success",
          message: "Last.fm account connected successfully",
        });
      }

      if (window.history.replaceState) {
        window.history.replaceState({}, "", window.location.pathname);
      }
    };

    handleConnectionStatus();
  }, []);

  const handleChange = (
    key: keyof SettingsState,
    value: string | boolean | string[],
  ) => {
    setSettings((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSave = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });

      const data = await response.json();

      if (!response.ok) {
        if (data.errors) {
          data.errors.forEach((error: any) => {
            toast({
              title: "Error",
              description: `${error.message} [${error.code}]`,
              variant: "error",
            });
          });
          return;
        }
        throw new Error();
      }

      toast({
        title: "Success",
        description: "Settings saved successfully",
        variant: "success",
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to save settings",
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSetup2FA = async () => {
    try {
      const response = await fetch("/api/auth/2fa/setup", {
        method: "POST",
      });

      if (!response.ok) throw new Error();

      const data = await response.json();
      setMockSecret(data.secret);
      setBackupCodes(data.backupCodes);

      const totpUri = encodeURI(
        `otpauth://totp/Emogirls:${settings.username}?secret=${data.secret}&issuer=Emogirls&algorithm=SHA1&digits=6&period=30`,
      );
      setQrCodeUrl(totpUri);

      setShowTwoFactorDialog(true);
    } catch {
      toast({
        title: "Error",
        description: "Failed to setup 2FA",
        variant: "error",
      });
    }
  };

  const handleVerify2FA = async () => {
    setIsVerifying(true);

    try {
      const response = await fetch("/api/auth/2fa/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: verificationCode }),
      });

      if (!response.ok) {
        toast({
          title: "Error",
          description: "Invalid 2FA code",
          variant: "error",
        });
        setIsVerifying(false);
        return;
      }

      if (verifyAction === "disable") {
        const disableResponse = await fetch("/api/auth/2fa/disable", {
          method: "POST",
        });

        if (!disableResponse.ok) throw new Error();

        setSettings((prev) => ({
          ...prev,
          twoFactorEnabled: false,
        }));
        toast({
          title: "Success",
          description: "2FA disabled successfully",
          variant: "success",
        });
        setShowVerifyDialog(false);
      } else if (verifyAction === "viewCodes") {
        const codesResponse = await fetch("/api/auth/2fa/backup-codes");
        if (!codesResponse.ok) throw new Error();

        const data = await codesResponse.json();
        setBackupCodes(data.backupCodes);
        setShowBackupCodes(true);
        await new Promise((resolve) => setTimeout(resolve, 100));
        setShowVerifyDialog(false);
      } else if (verifyAction === "changePassword") {
        const changePasswordResponse = await fetch(
          "/api/auth/change-password",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              currentPassword: passwordData.currentPassword,
              newPassword: passwordData.newPassword,
              code: verificationCode,
            }),
          },
        );

        if (!changePasswordResponse.ok) {
          const data = await changePasswordResponse.json();
          setPasswordError(data.error || "Failed to change password");
          return;
        }

        toast({
          title: "Success",
          description: "Password changed successfully",
          variant: "success",
        });
        setShowPasswordDialog(false);
        setShowVerifyDialog(false);
        setPasswordData({
          currentPassword: "",
          newPassword: "",
          confirmPassword: "",
        });
      } else {
        setShowBackupCodes(true);
        setSettings((prev) => ({
          ...prev,
          twoFactorEnabled: true,
        }));
        toast({
          title: "Success",
          description: "2FA verified successfully",
          variant: "success",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to verify 2FA code",
        variant: "error",
      });
    } finally {
      setIsVerifying(false);
      setVerificationCode("");
    }
  };

  const handleChangePassword = async () => {
    setPasswordError("");

    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setPasswordError("New passwords don't match");
      return;
    }

    if (passwordData.newPassword.length < 8) {
      setPasswordError("Password must be at least 8 characters");
      return;
    }

    try {
      const response = await fetch("/api/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          currentPassword: passwordData.currentPassword,
          newPassword: passwordData.newPassword,
          code: verificationCode,
        }),
      });

      const data = await response.json();

      if (data.error === "2FA_REQUIRED") {
        setVerifyAction("changePassword");
        setShowVerifyDialog(true);
        return;
      }

      if (!response.ok) {
        setPasswordError(data.error || "Failed to change password");
        return;
      }

      toast({
        title: "Success",
        description: "Password changed successfully",
        variant: "success",
      });
      setShowPasswordDialog(false);
      setPasswordData({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to change password",
        variant: "error",
      });
    }
  };

  const handleConnectDiscord = () => {
    const params = new URLSearchParams({
      client_id: "1344236586564587580",
      redirect_uri: `https://emogir.ls/settings/discord/callback`,
      response_type: "code",
      scope: "identify",
    });

    window.location.href = `https://discord.com/oauth2/authorize?${params}`;
  };

  const handleConnectLastfm = () => {
    const params = new URLSearchParams({
      api_key: "93b2a32276e364e6c922b08becdf42b3",
      redirect_uri: `https://emogir.ls/settings/lastfm/callback`,
      response_type: "code",
    });
    window.location.href = `http://www.last.fm/api/auth?${params}`;
  };

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await fetch(`/api/account/sessions?id=${sessionId}`, {
        method: "DELETE",
      });
      setUserSessions(userSessions.filter((s) => s.id !== sessionId));
      toast({
        title: "Success",
        description: "Session revoked successfully",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to revoke session",
        variant: "error",
      });
    }
  };

  const handlePinToggle = async (checked: boolean) => {
    setPinSettings((prev) => ({
      ...prev,
      enabled: checked,
      ...(checked ? {} : { pin: "", confirmPin: "" }),
    }));

    if (!checked) {
      try {
        const response = await fetch("/api/settings/pin", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            enabled: false,
            pin: null,
          }),
        });

        if (!response.ok) throw new Error();
        toast({
          title: "Success",
          description: "PIN protection disabled",
          variant: "success",
        });
      } catch {
        toast({
          title: "Error",
          description: "Failed to disable PIN",
          variant: "error",
        });
        setPinSettings((prev) => ({ ...prev, enabled: true }));
      }
    }
  };

  const handlePinSave = async () => {
    setPinError("");

    if (pinSettings.enabled) {
      if (pinSettings.pin.length !== 6) {
        setPinError("PIN must be exactly 6 digits");
        return;
      }

      if (pinSettings.pin !== pinSettings.confirmPin) {
        setPinError("PINs do not match");
        return;
      }
    }

    try {
      const response = await fetch("/api/settings/pin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled: pinSettings.enabled,
          pin: pinSettings.pin,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        if (data.errors) {
          setPinError(data.errors[0].message);
          return;
        }
        throw new Error();
      }

      toast({
        title: "Success",
        description: "PIN settings updated successfully",
        variant: "success",
      });
      setPinSettings((prev) => ({ ...prev, pin: "", confirmPin: "" }));
    } catch {
      toast({
        title: "Error",
        description: "Failed to update PIN settings",
        variant: "error",
      });
    }
  };

  const handlePinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 6);
    setPinSettings((prev) => ({
      ...prev,
      pin: value,
    }));
  };

  const handleConfirmPinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 6);
    setPinSettings((prev) => ({
      ...prev,
      confirmPin: value,
    }));
  };

  const handleChangePin = async () => {
    setPinError("");

    try {
      const verifyResponse = await fetch("/api/settings/pin", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: currentPin }),
      });

      const { isValid } = await verifyResponse.json();

      if (!isValid) {
        setPinError("Current PIN is incorrect");
        return;
      }

      if (pinSettings.pin.length !== 6) {
        setPinError("New PIN must be exactly 6 digits");
        return;
      }

      if (pinSettings.pin !== pinSettings.confirmPin) {
        setPinError("New PINs do not match");
        return;
      }

      const response = await fetch("/api/settings/pin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled: true,
          pin: pinSettings.pin,
        }),
      });

      if (!response.ok) throw new Error();

      toast({
        title: "Success",
        description: "PIN updated successfully",
        variant: "success",
      });
      setShowChangePin(false);
      setCurrentPin("");
      setPinSettings((prev) => ({ ...prev, pin: "", confirmPin: "" }));
    } catch {
      toast({
        title: "Error",
        description: "Failed to update PIN",
        variant: "error",
      });
    }
  };

  const validateHostname = (hostname: string): boolean => {
    const hostnameRegex =
      /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$/;
    return hostnameRegex.test(hostname);
  };

  const checkHostnameAvailability = async (hostname: string) => {
    if (!hostname) return;

    setIsCheckingHostname(true);
    setHostnameError("");

    try {
      const response = await fetch(
        `/api/settings/check-hostname?hostname=${encodeURIComponent(hostname)}`,
      );
      const data = await response.json();

      if (!response.ok) {
        setHostnameError(data.error || "Failed to check hostname availability");
        return false;
      }

      if (!data.available) {
        setHostnameError("This hostname is already in use");
        return false;
      }

      return true;
    } catch (error) {
      setHostnameError("Failed to check hostname availability");
      return false;
    } finally {
      setIsCheckingHostname(false);
    }
  };

  const handleHostnameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.trim();
    setHostnameError("");
    handleChange("customHostname", value);
  };

  const handleHostnameBlur = async () => {
    if (!settings.customHostname) return;

    if (!validateHostname(settings.customHostname)) {
      setHostnameError("Please enter a valid hostname (e.g., example.com)");
      return;
    }

    await checkHostnameAvailability(settings.customHostname);
  };

  const checkDomainStatus = async (hostname: string) => {
    if (!hostname) return;

    try {
      const response = await fetch(
        `/api/settings/check-domain?hostname=${encodeURIComponent(hostname)}`,
      );
      const data = await response.json();

      if (!response.ok) {
        console.error("Error checking domain status:", data.error);
        return;
      }

      setDomainStatus({
        verified: data.verified,
        message: data.message,
        step: data.step,
        records: data.records,
      });
    } catch (error) {
      console.error("Error checking domain status:", error);
    }
  };

  const handleVerifyDomain = async () => {
    if (!settings.customHostname) {
      toast({
        title: "Error",
        description: "Please enter a hostname first",
        variant: "error",
      });
      return;
    }

    setIsVerifyingDomain(true);

    try {
      if (!validateHostname(settings.customHostname)) {
        setHostnameError("Please enter a valid hostname (e.g., example.com)");
        setIsVerifyingDomain(false);
        return;
      }

      const isAvailable = await checkHostnameAvailability(
        settings.customHostname,
      );
      if (!isAvailable) {
        setIsVerifyingDomain(false);
        return;
      }

      const response = await fetch("/api/settings/verify-domain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hostname: settings.customHostname }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to verify domain");
      }

      setDomainStatus({
        verified: data.verified,
        message: data.message,
        step: data.step,
        records: data.records,
      });

      if (data.verified) {
        toast({
          title: "Success",
          description: "Domain verified successfully!",
          variant: "success",
        });
      } else {
        toast({
          title: "Info",
          description: data.message || "Please complete the verification steps",
        });
      }
    } catch (error) {
      console.error("Domain verification error:", error);
      toast({
        title: "Error",
        description: "Failed to verify domain",
        variant: "error",
      });
    } finally {
      setIsVerifyingDomain(false);
    }
  };

  const handleRemoveDomain = async () => {
    if (!settings.customHostname) return;

    try {
      const response = await fetch("/api/settings/remove-domain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hostname: settings.customHostname }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || "Failed to remove domain");
      }

      handleChange("customHostname", "");
      setDomainStatus(null);
      toast({
        title: "Success",
        description: "Custom domain removed successfully",
        variant: "success",
      });
    } catch (error) {
      console.error("Error removing domain:", error);
      toast({
        title: "Error",
        description: "Failed to remove domain",
        variant: "error",
      });
    }
  };

  const copyEmail = async (email: string) => {
    try {
      await navigator.clipboard.writeText(email);
      toast({
        title: "Success",
        description: "Email copied to clipboard",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to copy email",
        variant: "error",
      });
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2 text-sm text-white/60 bg-white/5 px-3 py-1.5 rounded-md">
          <IconServer size={16} />
          <span>Connected to: {nodeInfo}</span>
        </div>
      </div>

      {connectionStatus && (
        <div
          className={`p-4 rounded-lg ${
            connectionStatus.type === "error"
              ? "bg-red-500/10 border border-red-500/20 text-red-500"
              : "bg-green-500/10 border border-green-500/20 text-green-500"
          }`}
        >
          {connectionStatus.message}
        </div>
      )}

      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Settings</h1>
        <Button text="Save Changes" onClick={handleSave} loading={isLoading} />
      </div>

      <div className="grid gap-6">
        <DataCard title="Profile Settings" icon={IconUser}>
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-white/80">
                  Display Name
                </label>
                <div className="mt-1.5">
                  <InputGroup
                    name="displayName"
                    placeholder="Your Name"
                    value={settings.displayName}
                    onChange={(value) => handleChange("displayName", value)}
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-white/80">
                  Username
                </label>
                <div className="mt-1.5">
                  <InputGroup
                    prefix="emogir.ls/"
                    placeholder="username"
                    value={settings.username}
                    onChange={(value) => {
                      if (value.length < 4) {
                        toast({
                          title: "Error",
                          description:
                            "Username too short. Please contact support for usernames shorter than 4 characters",
                          variant: "error",
                        });
                        return;
                      }
                      handleChange("username", value);
                    }}
                  />
                </div>
                <p className="mt-1.5 text-xs text-white/60">
                  Usernames must be at least 4 characters long. Contact support
                  for shorter usernames.
                </p>
              </div>
            </div>
          </div>
        </DataCard>

        <DataCard title="Custom Domains" icon={IconLink}>
          <div className="space-y-4">
            <p className="text-sm text-white/60">
              Select up to 3 domains for your profile. Your profile will be
              accessible from all selected domains.
            </p>

            <div className="p-3 bg-primary/5 border border-primary/10 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium">emogir.ls</span>
                  <span className="ml-2 text-xs bg-primary/20 text-primary px-2 py-0.5 rounded">
                    Default
                  </span>
                </div>
                <Button
                  text="Default"
                  disabled
                  className="opacity-50 cursor-not-allowed"
                />
              </div>
            </div>

            <Input
              placeholder="Search domains..."
              value={domainSearch}
              onChange={(e) => setDomainSearch(e.target.value)}
              className="bg-black/20"
            />

            <div className="grid gap-2 max-h-[400px] overflow-y-auto">
              <div className="sticky top-0 bg-black/90 p-2 backdrop-blur-sm border-b border-white/10">
                <h3 className="text-sm font-medium">
                  Selected Custom Domains ({settings.selectedDomains.length}/3)
                </h3>
              </div>
              {settings.selectedDomains
                .filter((domain) => domain !== "emogir.ls")
                .map((domain) => (
                  <div
                    key={domain}
                    className="flex items-center justify-between p-3 bg-primary/5 border border-primary/10 rounded-lg"
                  >
                    <span className="text-sm font-medium">{domain}</span>
                    <Button
                      text="Remove"
                      onClick={() => {
                        handleChange(
                          "selectedDomains",
                          settings.selectedDomains.filter((d) => d !== domain),
                        );
                      }}
                      className="bg-red-500/10 border-red-500/20 text-red-500"
                    />
                  </div>
                ))}

              <div className="sticky top-12 bg-black/90 p-2 backdrop-blur-sm border-b border-white/10">
                <h3 className="text-sm font-medium">Available Domains</h3>
              </div>
              {AVAILABLE_DOMAINS.filter(
                (domain) =>
                  domain.url !== "emogir.ls" &&
                  domain.url
                    .toLowerCase()
                    .includes(domainSearch.toLowerCase()) &&
                  !settings.selectedDomains.includes(domain.url),
              ).map((domain) => (
                <div
                  key={domain.url}
                  className="flex items-center justify-between p-3 bg-black/20 rounded-lg"
                >
                  <span className="text-sm font-medium">
                    {domain.url}
                    {domain.featured && (
                      <span className="ml-2 text-xs bg-primary/20 text-primary px-2 py-0.5 rounded">
                        Featured
                      </span>
                    )}
                  </span>
                  <Button
                    text="Add"
                    onClick={() => {
                      if (settings.selectedDomains.length >= 3) {
                        toast({
                          title: "Error",
                          description:
                            "You can only select up to 3 custom domains",
                          variant: "error",
                        });
                        return;
                      }
                      handleChange("selectedDomains", [
                        ...settings.selectedDomains,
                        domain.url,
                      ]);
                    }}
                    className="bg-primary/10 text-primary"
                    disabled={settings.selectedDomains.length >= 3}
                  />
                </div>
              ))}
            </div>
          </div>
        </DataCard>

        <DataCard title="Custom Domain" icon={IconLink}>
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-medium text-white/80">
                Custom Domain
              </h3>
              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-primary/20 text-primary">
                Premium
              </span>
            </div>

            <p className="text-sm text-white/60">
              Connect your own domain to your profile. We'll handle the SSL
              certificate and domain setup for you.
            </p>

            {!isPremium || !premiumFeatures.customDomain ? (
              <div className="p-4 rounded-lg bg-primary/5 border border-primary/10">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-medium">Upgrade to Premium</h3>
                    <p className="text-sm text-white/60">
                      Custom domains are available for premium users only
                    </p>
                  </div>
                  <Button
                    text="Upgrade"
                    onClick={() =>
                      (window.location.href = "/dashboard/billing")
                    }
                    className="w-full sm:w-auto bg-primary text-white"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-white/80">
                    Your Domain
                  </label>
                  <div className="mt-1.5">
                    <InputGroup
                      name="customHostname"
                      placeholder="example.com"
                      value={settings.customHostname}
                      onChange={(value) =>
                        handleChange("customHostname", value)
                      }
                    />
                  </div>
                  {hostnameError && (
                    <p className="mt-1.5 text-xs text-red-500">
                      {hostnameError}
                    </p>
                  )}
                  <p className="mt-1.5 text-xs text-white/60">
                    Enter your domain without http:// or www (e.g., example.com)
                  </p>
                </div>

                {domainStatus && (
                  <div
                    className={`p-4 rounded-lg ${
                      domainStatus.verified
                        ? "bg-green-500/10 border border-green-500/20"
                        : "bg-amber-500/10 border border-amber-500/20"
                    }`}
                  >
                    <h4 className="text-sm font-medium mb-2">
                      {domainStatus.verified
                        ? "Domain Verified"
                        : "Verification Required"}
                    </h4>
                    <p className="text-sm text-white/80 mb-2">
                      {domainStatus.message}
                    </p>

                    {!domainStatus.verified && domainStatus.step === 1 && (
                      <div className="mt-4">
                        <p className="text-sm font-medium mb-2">
                          DNS Configuration:
                        </p>
                        <div className="p-2 bg-black/30 rounded-lg mb-2">
                          <div className="grid grid-cols-3 gap-2">
                            <div className="text-xs font-medium text-white/60">
                              Type
                            </div>
                            <div className="text-xs font-medium text-white/60">
                              Name
                            </div>
                            <div className="text-xs font-medium text-white/60">
                              Value
                            </div>
                          </div>
                        </div>

                        {domainStatus.records &&
                          domainStatus.records.map((record, index) => (
                            <div
                              key={index}
                              className="p-2 bg-black/20 rounded-lg mb-2"
                            >
                              <div className="grid grid-cols-3 gap-2">
                                <div className="text-sm">{record.type}</div>
                                <div className="text-sm">{record.name}</div>
                                <div className="text-sm font-mono">
                                  {record.value}
                                </div>
                              </div>
                            </div>
                          ))}

                        <p className="mt-4 text-xs text-white/60">
                          DNS changes can take up to 24 hours to propagate. Once
                          configured, your profile will be accessible at your
                          domain.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <Button
                    text={isVerifyingDomain ? "Verifying..." : "Verify Domain"}
                    onClick={handleVerifyDomain}
                    loading={isVerifyingDomain}
                    disabled={
                      isVerifyingDomain ||
                      !settings.customHostname ||
                      !!hostnameError
                    }
                    className="bg-primary/10 text-primary"
                  />

                  {settings.customHostname && (
                    <Button
                      text="Remove Domain"
                      onClick={handleRemoveDomain}
                      className="bg-red-500/10 border-red-500/20 text-red-500"
                    />
                  )}
                </div>
              </div>
            )}
          </div>
        </DataCard>

        <DataCard title="SEO Settings" icon={IconSeo}>
          <div className="space-y-6">
            <div>
              <label className="text-sm font-medium text-white/80">
                Page Title
              </label>
              <div className="mt-1.5">
                <InputGroup
                  name="title"
                  placeholder="My Links"
                  value={settings.pageTitle}
                  onChange={(value) => handleChange("pageTitle", value)}
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-white/80">
                SEO Description
              </label>
              <div className="mt-1.5">
                <textarea
                  className="w-full bg-black/20 border border-primary/10 rounded-lg px-4 py-2.5 text-white placeholder:text-white/40 focus:outline-none focus:border-primary/30 transition-colors min-h-[80px]"
                  placeholder="A short description of your page for search engines"
                  value={settings.seoDescription}
                  onChange={(e) =>
                    handleChange("seoDescription", e.target.value)
                  }
                  rows={2}
                />
              </div>
            </div>
          </div>
        </DataCard>

        <DataCard title="Privacy" icon={IconLock}>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-white/80">
                  Private Profile
                </h3>
                <p className="text-sm text-white/60">
                  Make your profile visible only to you
                </p>
              </div>
              <Switch
                checked={settings.isPrivate}
                onCheckedChange={(value) => handleChange("isPrivate", value)}
              />
            </div>
            <Button
              text="Change Password"
              onClick={() => setShowPasswordDialog(true)}
              className="w-full sm:w-auto"
            />
          </div>
        </DataCard>

        <DataCard title="Security" icon={IconLock}>
          <div className="space-y-4 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-white/80">
                  Location Verification
                </h3>
                <p className="text-sm text-white/60">
                  Verify new login locations via email
                </p>
              </div>
              <Switch
                checked={settings.newLoginVerification}
                onCheckedChange={(checked) =>
                  handleChange("newLoginVerification", checked)
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-white/80">
                  Two-Factor Authentication
                </h3>
                <p className="text-sm text-white/60">
                  Add an extra layer of security to your account
                </p>
              </div>
              <div className="space-x-2">
                {settings.twoFactorEnabled ? (
                  <>
                    <Button
                      text="View Backup Codes"
                      className="bg-primary/10 text-primary"
                      onClick={() => {
                        setVerifyAction("viewCodes");
                        setShowVerifyDialog(true);
                      }}
                    />
                    <Button
                      text="Disable 2FA"
                      className="bg-red-500/10 border-red-500/20 text-red-500"
                      onClick={() => {
                        setVerifyAction("disable");
                        setShowVerifyDialog(true);
                      }}
                    />
                  </>
                ) : (
                  <Button text="Setup 2FA" onClick={handleSetup2FA} />
                )}
              </div>
            </div>
            <Button
              text="Change Password"
              onClick={() => setShowPasswordDialog(true)}
              className="w-full sm:w-auto"
            />
          </div>
        </DataCard>

        <DataCard title="Privacy & Security" icon={IconLock}>
          <div className="space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-white/80">
                    Profile PIN
                  </h3>
                  <p className="text-sm text-white/60">
                    Require a 6-digit PIN to access your profile
                  </p>
                </div>
                <Switch
                  checked={pinSettings.enabled}
                  onCheckedChange={handlePinToggle}
                />
              </div>

              {pinSettings.enabled && (
                <div className="space-y-4 pt-4">
                  {!showChangePin ? (
                    <Button
                      onClick={() => setShowChangePin(true)}
                      className="w-full"
                    >
                      Change PIN
                    </Button>
                  ) : (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Input
                          type="password"
                          maxLength={6}
                          placeholder="Enter current PIN"
                          value={currentPin}
                          onChange={(e) => {
                            const value = e.target.value
                              .replace(/\D/g, "")
                              .slice(0, 6);
                            setCurrentPin(value);
                          }}
                          className="bg-white/5 border-white/10"
                        />
                      </div>
                      <div className="space-y-2">
                        <Input
                          type="password"
                          maxLength={6}
                          placeholder="Enter new PIN"
                          value={pinSettings.pin}
                          onChange={handlePinChange}
                          className="bg-white/5 border-white/10"
                        />
                      </div>
                      <div className="space-y-2">
                        <Input
                          type="password"
                          maxLength={6}
                          placeholder="Confirm new PIN"
                          value={pinSettings.confirmPin}
                          onChange={handleConfirmPinChange}
                          className="bg-white/5 border-white/10"
                        />
                      </div>
                      {pinError && (
                        <p className="text-sm text-red-500">{pinError}</p>
                      )}
                      <div className="flex gap-2">
                        <Button
                          onClick={() => {
                            setShowChangePin(false);
                            setCurrentPin("");
                            setPinSettings((prev) => ({
                              ...prev,
                              pin: "",
                              confirmPin: "",
                            }));
                            setPinError("");
                          }}
                          className="flex-1"
                        >
                          Cancel
                        </Button>
                        <Button onClick={handleChangePin} className="flex-1">
                          Update PIN
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </DataCard>

        <Dialog
          open={showTwoFactorDialog}
          onOpenChange={(open) => {
            if (!open) {
              setShowTwoFactorDialog(false);
              setShowBackupCodes(false);
              setVerificationCode("");
              setQrCodeUrl("");
            }
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {showBackupCodes
                  ? "Save Backup Codes"
                  : "Setup Two-Factor Authentication"}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {!showBackupCodes ? (
                <>
                  <div className="flex justify-center">
                    {qrCodeUrl && (
                      <QRCodeSVG
                        value={qrCodeUrl}
                        size={200}
                        level="M"
                        className="bg-white p-2 rounded-lg"
                      />
                    )}
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm text-white/60">
                      1. Scan the QR code with your authenticator app
                    </p>
                    <p className="text-sm text-white/60">
                      2. Enter the 6-digit code to verify
                    </p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-white/80">
                      Verification Code
                    </label>
                    <InputGroup
                      name="verificationCode"
                      placeholder="000000"
                      value={verificationCode}
                      onChange={setVerificationCode}
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <Button
                      text="Cancel"
                      onClick={() => setShowTwoFactorDialog(false)}
                      className="bg-white/5"
                    />
                    <Button text="Verify" onClick={handleVerify2FA} />
                  </div>
                </>
              ) : (
                <>
                  <p className="text-sm text-white/60">
                    Save these backup codes in a secure location. You can use
                    these codes to access your account if you lose your
                    authenticator device.
                  </p>

                  <div className="bg-black/20 rounded-lg p-4 space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      {backupCodes.map((code, index) => (
                        <div
                          key={index}
                          className="font-mono text-sm bg-black/20 p-2 rounded text-center"
                        >
                          {code}
                        </div>
                      ))}
                    </div>

                    <div className="flex justify-center space-x-2 pt-4">
                      <Button
                        text="Copy"
                        onClick={() => {
                          navigator.clipboard.writeText(backupCodes.join("\n"));
                          toast({
                            title: "Success",
                            description: "Backup codes copied to clipboard",
                            variant: "success",
                          });
                        }}
                        className="bg-white/5 space-x-2 flex items-center"
                      >
                        <IconCopy size={16} />
                        <span>Copy</span>
                      </Button>
                      <Button
                        text="Download"
                        onClick={() => {
                          const text = `EMOGIRLS BACKUP CODES\n\nKeep these backup codes somewhere safe but accessible.\n\n${backupCodes.join(
                            "\n",
                          )}\n\nGenerated: ${new Date().toLocaleString()}`;
                          const blob = new Blob([text], { type: "text/plain" });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = "emogirls-backup-codes.txt";
                          document.body.appendChild(a);
                          a.click();
                          document.body.removeChild(a);
                          URL.revokeObjectURL(url);
                        }}
                        className="bg-primary/10 text-primary space-x-2 flex items-center"
                      >
                        <IconDownload size={16} />
                        <span>Download</span>
                      </Button>
                    </div>
                  </div>

                  <div className="flex justify-end space-x-2">
                    <Button
                      text="Back"
                      onClick={() => setShowBackupCodes(false)}
                      className="bg-white/5"
                    />
                    <Button
                      text="Complete Setup"
                      onClick={() => {
                        setSettings((prev) => ({
                          ...prev,
                          twoFactorEnabled: true,
                        }));
                        setShowTwoFactorDialog(false);
                        setShowBackupCodes(false);
                        toast({
                          title: "Success",
                          description: "2FA enabled successfully",
                          variant: "success",
                        });
                      }}
                    />
                  </div>
                </>
              )}
            </div>
          </DialogContent>
        </Dialog>

        <Dialog
          open={showVerifyDialog}
          onOpenChange={(open) => {
            if (!open && !isVerifying) {
              setShowVerifyDialog(false);
              setVerificationCode("");
              setVerifyAction(null);
            }
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Verify 2FA</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-white/80">
                  Enter your 2FA code to continue
                </label>
                <InputGroup
                  name="verificationCode"
                  placeholder="000000"
                  value={verificationCode}
                  onChange={setVerificationCode}
                />
              </div>
              <div className="flex justify-end space-x-2">
                <Button
                  text="Cancel"
                  onClick={() => {
                    if (!isVerifying) {
                      setShowVerifyDialog(false);
                      setVerificationCode("");
                      setVerifyAction(null);
                    }
                  }}
                  className="bg-white/5"
                />
                <Button
                  text="Verify"
                  onClick={handleVerify2FA}
                  loading={isVerifying}
                  disabled={isVerifying}
                />
              </div>
            </div>
            <div className="mt-6 pt-4 border-t border-white/10">
              <p className="text-sm text-white/60 text-center">
                Lost access to your authenticator? Contact{" "}
                <a
                  href="mailto:support@emogir.ls"
                  className="text-primary hover:underline"
                >
                  support@emogir.ls
                </a>
              </p>
            </div>
          </DialogContent>
        </Dialog>

        <Dialog open={showBackupCodes} onOpenChange={() => {}}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Backup Codes</DialogTitle>
              <Button
                text="Close"
                onClick={() => setShowBackupCodes(false)}
                className="absolute right-4 top-4 bg-white/5 hover:bg-white/10"
              />
            </DialogHeader>
            <div className="space-y-4 py-4">
              <p className="text-sm text-white/60">
                Save these backup codes in a secure location. You can use these
                codes to access your account if you lose your authenticator
                device.
              </p>

              <div className="bg-black/20 rounded-lg p-4 space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  {backupCodes.map((code, index) => (
                    <div
                      key={index}
                      className="font-mono text-sm bg-black/20 p-2 rounded text-center"
                    >
                      {code}
                    </div>
                  ))}
                </div>

                <div className="flex justify-center space-x-2 pt-4">
                  <Button
                    text="Copy"
                    onClick={() => {
                      navigator.clipboard.writeText(backupCodes.join("\n"));
                      toast({
                        title: "Success",
                        description: "Backup codes copied to clipboard",
                        variant: "success",
                      });
                    }}
                    className="bg-white/5 space-x-2 flex items-center"
                  >
                    <IconCopy size={16} />
                    <span>Copy</span>
                  </Button>
                  <Button
                    text="Download"
                    onClick={() => {
                      const text = `EMOGIRLS BACKUP CODES\n\nKeep these backup codes somewhere safe but accessible.\n\n${backupCodes.join(
                        "\n",
                      )}\n\nGenerated: ${new Date().toLocaleString()}`;
                      const blob = new Blob([text], { type: "text/plain" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = "emogirls-backup-codes.txt";
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                      URL.revokeObjectURL(url);
                    }}
                    className="bg-primary/10 text-primary space-x-2 flex items-center"
                  >
                    <IconDownload size={16} />
                    <span>Download</span>
                  </Button>
                </div>
              </div>
              <div className="flex justify-between items-center pt-4 mt-4 border-t border-white/10">
                <Button
                  text="Reset Backup Codes"
                  onClick={async () => {
                    try {
                      const response = await fetch(
                        "/api/auth/2fa/reset-backup-codes",
                        { method: "POST" },
                      );
                      if (!response.ok) throw new Error();
                      const data = await response.json();
                      setBackupCodes(data.backupCodes);
                      toast({
                        title: "Success",
                        description: "Backup codes reset successfully",
                        variant: "success",
                      });
                    } catch {
                      toast({
                        title: "Error",
                        description: "Failed to reset backup codes",
                        variant: "error",
                      });
                    }
                  }}
                  className="bg-red-500/10 border-red-500/20 text-red-500"
                />
              </div>
            </div>
          </DialogContent>
        </Dialog>

        <Dialog open={showPasswordDialog} onOpenChange={setShowPasswordDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Change Password</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-white/80">
                  Current Password
                </label>
                <InputGroup
                  type="password"
                  value={passwordData.currentPassword}
                  onChange={(value) =>
                    setPasswordData((prev) => ({
                      ...prev,
                      currentPassword: value,
                    }))
                  }
                  placeholder="Enter current password"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-white/80">
                  New Password
                </label>
                <InputGroup
                  type="password"
                  value={passwordData.newPassword}
                  onChange={(value) =>
                    setPasswordData((prev) => ({ ...prev, newPassword: value }))
                  }
                  placeholder="Enter new password"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-white/80">
                  Confirm New Password
                </label>
                <InputGroup
                  type="password"
                  value={passwordData.confirmPassword}
                  onChange={(value) =>
                    setPasswordData((prev) => ({
                      ...prev,
                      confirmPassword: value,
                    }))
                  }
                  placeholder="Confirm new password"
                />
              </div>
              {passwordError && (
                <p className="text-sm text-red-500">{passwordError}</p>
              )}
              <div className="flex justify-end space-x-2">
                <Button
                  text="Cancel"
                  onClick={() => {
                    setShowPasswordDialog(false);
                    setPasswordData({
                      currentPassword: "",
                      newPassword: "",
                      confirmPassword: "",
                    });
                    setPasswordError("");
                  }}
                  className="bg-white/5"
                />
                <Button text="Change Password" onClick={handleChangePassword} />
              </div>
            </div>
          </DialogContent>
        </Dialog>

        <DataCard title="Connected Accounts" icon={IconLink}>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FaDiscord className="w-5 h-5 text-[#5865F2]" />
                <div>
                  <h3 className="text-sm font-medium text-white/80">Discord</h3>
                  {settings.discordAccount ? (
                    <p className="text-sm text-white/60">
                      Connected as {settings.discordAccount.username}
                      {settings.discordAccount.discriminator !== "0"
                        ? `#${settings.discordAccount.discriminator}`
                        : ""}
                    </p>
                  ) : (
                    <p className="text-sm text-white/60">Not connected</p>
                  )}
                </div>
              </div>
              {settings.discordAccount ? (
                <Button
                  text="Disconnect"
                  onClick={async () => {
                    try {
                      const response = await fetch("/api/account/discord", {
                        method: "DELETE",
                      });
                      if (!response.ok) throw new Error();
                      setSettings((prev) => ({
                        ...prev,
                        discordAccount: null,
                      }));
                      toast({
                        title: "Success",
                        description: "Discord account disconnected",
                        variant: "success",
                      });
                    } catch {
                      toast({
                        title: "Error",
                        description: "Failed to disconnect Discord account",
                        variant: "error",
                      });
                    }
                  }}
                  className="bg-red-500/10 border-red-500/20 text-red-500"
                />
              ) : (
                <Button
                  text="Connect"
                  onClick={handleConnectDiscord}
                  className="flex items-center gap-2"
                >
                  <FaDiscord className="w-4 h-4" />
                  <span>Connect</span>
                </Button>
              )}
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FaLastfm className="w-5 h-5 text-[#d51007]" />
                <div>
                  <h3 className="text-sm font-medium text-white/80">Last.fm</h3>
                  {settings.lastfmAccount ? (
                    <p className="text-sm text-white/60">
                      Connected as {settings.lastfmAccount.username}
                    </p>
                  ) : (
                    <p className="text-sm text-white/60">Not connected</p>
                  )}
                </div>
              </div>
              {settings.lastfmAccount ? (
                <Button
                  text="Disconnect"
                  onClick={async () => {
                    try {
                      const response = await fetch("/api/account/lastfm", {
                        method: "DELETE",
                      });
                      if (!response.ok) throw new Error();
                      setSettings((prev) => ({
                        ...prev,
                        lastfmAccount: null,
                      }));
                      toast({
                        title: "Success",
                        description: "Last.fm account disconnected",
                        variant: "success",
                      });
                    } catch {
                      toast({
                        title: "Error",
                        description: "Failed to disconnect Last.fm account",
                        variant: "error",
                      });
                    }
                  }}
                  className="bg-red-500/10 border-red-500/20 text-red-500"
                />
              ) : (
                <Button
                  text="Connect"
                  onClick={handleConnectLastfm}
                  className="flex items-center gap-2"
                >
                  <FaLastfm className="w-4 h-4" />
                  <span>Connect</span>
                </Button>
              )}
            </div>
          </div>
        </DataCard>

        <DataCard title="Active Sessions" icon={IconDevices}>
          <div className="space-y-4">
            {userSessions.map((session) => (
              <div
                key={session.id}
                className="flex items-center justify-between p-4 bg-black/20 rounded-lg"
              >
                <div className="space-y-1">
                  <p className="font-medium">
                    {formatDeviceInfo(session.deviceInfo)}
                  </p>
                  <p className="text-sm text-white/60">
                    {session.location} • Last active{" "}
                    {new Date(session.lastActive).toLocaleString()}
                  </p>
                </div>
                <Button
                  onClick={() => handleRevokeSession(session.id)}
                  className="bg-red-500/10 border-red-500/20 text-red-500"
                >
                  Revoke
                </Button>
              </div>
            ))}
          </div>
        </DataCard>

        <DataCard
          title="Danger Zone"
          icon={IconTrash}
          className="!border-red-500/10"
        >
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium text-red-500">
                Delete Account
              </h3>
              <p className="text-sm text-white/60">
                Permanently delete your account and all data
              </p>
            </div>
            <Button
              text="Delete Account"
              className="!bg-red-500/10 !border-red-500/20 !text-red-500 hover:!bg-red-500 hover:!text-white"
            />
          </div>
        </DataCard>
      </div>
    </div>
  );
}
