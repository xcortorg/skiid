"use client";

import { toast } from "sonner";
import Image from "next/image";

export function UserActions({ user }: { user: any }) {
  const toggleAccountStatus = async () => {
    try {
      const response = await fetch(
        `/api/admin/users/${user.id}/toggle-status`,
        {
          method: "POST",
        },
      );
      if (!response.ok) throw new Error();
      toast.success(
        `Account ${user.isDisabled ? "enabled" : "disabled"} successfully`,
      );
      window.location.reload();
    } catch {
      toast.error("Failed to update account status");
    }
  };

  const removeBadge = async (badge: string) => {
    try {
      const response = await fetch(`/api/admin/badges`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: user.id, badge }),
      });
      if (!response.ok) throw new Error();
      toast.success("Badge removed successfully");
      window.location.reload();
    } catch {
      toast.error("Failed to remove badge");
    }
  };

  const addBadge = async (badge: string) => {
    try {
      const response = await fetch(`/api/admin/badges`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId: user.id,
          badge: badge,
        }),
      });
      if (!response.ok) throw new Error();
      toast.success("Badge added successfully");
      window.location.reload();
    } catch {
      toast.error("Failed to add badge");
    }
  };

  const togglePremiumFeature = async () => {
    try {
      const response = await fetch(`/api/admin/users/${user.id}/premium`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          until: new Date("2030-12-31").toISOString(),
        }),
      });
      if (!response.ok) throw new Error();
      toast.success("Premium status updated successfully");
      window.location.reload();
    } catch {
      toast.error("Failed to update premium status");
    }
  };

  return (
    <div className="hidden">
      <button onClick={toggleAccountStatus}>Toggle Status</button>
      <button onClick={() => addBadge("OWNER")}>Add Badge</button>
    </div>
  );
}

export const useUserActions = (user: any) => {
  const toggleAccountStatus = async () => {
    try {
      const response = await fetch(`/api/admin/users/${user.id}/disable`, {
        method: "POST",
      });
      if (!response.ok) throw new Error();
      toast.success(
        `Account ${user.isDisabled ? "enabled" : "disabled"} successfully`,
      );
      window.location.reload();
    } catch {
      toast.error("Failed to update account status");
    }
  };

  const removeBadge = async (badge: string) => {
    try {
      const response = await fetch(`/api/admin/badges`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: user.id, badge }),
      });
      if (!response.ok) throw new Error();
      toast.success("Badge removed successfully");
      window.location.reload();
    } catch {
      toast.error("Failed to remove badge");
    }
  };

  const addBadge = async (badge: string) => {
    try {
      const response = await fetch(`/api/admin/badges`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId: user.id,
          badge: badge,
        }),
      });
      if (!response.ok) throw new Error();
      toast.success("Badge added successfully");
      window.location.reload();
    } catch {
      toast.error("Failed to add badge");
    }
  };

  const togglePremiumFeature = async () => {
    try {
      const response = await fetch(`/api/admin/users/${user.id}/premium`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          until: new Date("2030-12-31").toISOString(),
        }),
      });
      if (!response.ok) throw new Error();
      toast.success("Premium status updated successfully");
      window.location.reload();
    } catch {
      toast.error("Failed to update premium status");
    }
  };

  const toggleApiAccess = async () => {
    try {
      const response = await fetch(`/api/admin/users/${user.id}/api-keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          maxKeys: user.apiKeysEnabled ? 0 : 5,
        }),
      });
      if (!response.ok) throw new Error();
      toast.success("API access updated successfully");
      window.location.reload();
    } catch {
      toast.error("Failed to update API access");
    }
  };

  const updateMaxApiKeys = async (amount: number) => {
    try {
      const response = await fetch(`/api/admin/users/${user.id}/api-keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ maxKeys: amount }),
      });
      if (!response.ok) throw new Error();
      toast.success("API key limit updated successfully");
      window.location.reload();
    } catch {
      toast.error("Failed to update API key limit");
    }
  };

  const updateAccountStatus = async (
    status: string,
    options?: {
      reason?: string;
      expiresAt?: Date;
      sendEmail?: boolean;
    },
  ) => {
    try {
      const response = await fetch(`/api/admin/users/${user.id}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status,
          reason: options?.reason,
          expiresAt: options?.expiresAt?.toISOString(),
          sendEmail: options?.sendEmail ?? true,
        }),
      });
      if (!response.ok) throw new Error();
      toast.success("Account status updated successfully");
      window.location.reload();
    } catch {
      toast.error("Failed to update account status");
    }
  };

  return {
    toggleAccountStatus,
    removeBadge,
    addBadge,
    togglePremiumFeature,
    toggleApiAccess,
    updateMaxApiKeys,
    updateAccountStatus,
  };
};
