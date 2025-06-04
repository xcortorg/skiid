"use client";

import { useUserActions } from "./user-actions";
import { notFound } from "next/navigation";
import Image from "next/image";
import { useEffect, useState } from "react";
import Loading from "./loading";

const formatDate = (date: string | Date) => {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
};

const badges = [
  { id: "OWNER", label: "Owner", icon: "/badges/owner.svg" },
  { id: "CO_OWNER", label: "Co-Owner", icon: "/badges/co-owner.svg" },
  { id: "OG", label: "OG", icon: "/badges/og.svg" },
  { id: "PREMIUM", label: "Premium", icon: "/badges/premium.svg" },
  { id: "STAFF", label: "Staff", icon: "/badges/staff.svg" },
  { id: "VERIFIED", label: "Verified", icon: "/badges/verified.svg" },
];

export function UserManagement({ id }: { id: string }) {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showBadgeModal, setShowBadgeModal] = useState(false);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [statusReason, setStatusReason] = useState("");
  const [banExpiry, setBanExpiry] = useState<Date | null>(null);
  const actions = useUserActions(user);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/admin/fetch/${id}`)
      .then((res) => res.json())
      .then((data) => setUser(data))
      .catch(() => notFound())
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Loading />;
  if (!user) return null;

  const BadgeModal = () => (
    <div
      className={`fixed inset-0 bg-black/50 flex items-center justify-center ${
        showBadgeModal ? "" : "hidden"
      }`}
    >
      <div className="bg-black/80 border border-white/10 rounded-xl p-6 w-96">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Add Badge</h3>
          <button
            onClick={() => setShowBadgeModal(false)}
            className="text-white/60 hover:text-white"
          >
            ×
          </button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {badges.map((badge) => (
            <button
              key={badge.id}
              onClick={async () => {
                await actions.addBadge(badge.id);
                setShowBadgeModal(false);
              }}
              disabled={user.badges.includes(badge.id)}
              className={`flex items-center gap-2 p-3 rounded-lg transition-colors ${
                user.badges.includes(badge.id)
                  ? "bg-white/5 text-white/20 cursor-not-allowed"
                  : "bg-black/40 hover:bg-white/10"
              }`}
            >
              <Image
                src={badge.icon}
                alt={badge.label}
                width={24}
                height={24}
              />
              <span>{badge.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  const StatusModal = () => {
    const [localReason, setLocalReason] = useState(statusReason);
    const [localExpiry, setLocalExpiry] = useState<Date | null>(banExpiry);
    const [sendEmail, setSendEmail] = useState(true);

    const handleSubmit = (status: string) => {
      if (status === "ACTIVE") {
        actions.updateAccountStatus(status, { sendEmail });
      } else if (!localReason.trim()) {
        return;
      } else if (status === "BANNED" && !localExpiry) {
        return;
      } else {
        actions.updateAccountStatus(status, {
          reason: localReason,
          expiresAt: localExpiry || undefined,
          sendEmail,
        });
      }
      setShowStatusModal(false);
    };

    return (
      <div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        style={{ display: showStatusModal ? "flex" : "none" }}
      >
        <div
          className="bg-black/80 border border-white/10 rounded-xl p-6 w-96"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Update Account Status</h3>
            <button
              onClick={() => setShowStatusModal(false)}
              className="text-white/60 hover:text-white"
            >
              ×
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-white/60 mb-2">Status</label>
              <div className="grid grid-cols-1 gap-2">
                <button
                  type="button"
                  onClick={() => handleSubmit("ACTIVE")}
                  className="p-2 rounded-lg bg-green-500/10 text-green-400 hover:bg-green-500/20"
                >
                  Activate Account
                </button>

                <button
                  type="button"
                  onClick={() => handleSubmit("DISABLED")}
                  className="p-2 rounded-lg bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20"
                >
                  Temporarily Disable
                </button>

                <button
                  type="button"
                  onClick={() => handleSubmit("BANNED")}
                  className="p-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20"
                >
                  Ban Account
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm text-white/60 mb-2">Reason</label>
              <textarea
                value={localReason}
                onChange={(e) => setLocalReason(e.target.value)}
                className="w-full px-3 py-2 bg-black/40 border border-white/10 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="Enter reason for status change..."
                rows={3}
              />
            </div>

            <div>
              <label className="block text-sm text-white/60 mb-2">
                Ban Duration (for bans only)
              </label>
              <input
                type="datetime-local"
                onChange={(e) => setLocalExpiry(new Date(e.target.value))}
                className="w-full px-3 py-2 bg-black/40 border border-white/10 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="sendEmail"
                checked={sendEmail}
                onChange={(e) => setSendEmail(e.target.checked)}
                className="rounded border-white/10 bg-black/40"
              />
              <label htmlFor="sendEmail" className="text-sm text-white/60">
                Send email notification
              </label>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <>
      <div className="min-h-screen bg-black/40 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl font-bold">User Management</h1>
              <p className="text-white/60">Managing {user.username}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-black/20 border border-white/5 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">User Information</h2>
                <button
                  onClick={() => setShowStatusModal(true)}
                  className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                >
                  Manage Status
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-white/60">Username</label>
                  <p className="text-lg font-medium">{user.username}</p>
                </div>
                <div>
                  <label className="text-sm text-white/60">Email</label>
                  <p className="text-lg font-medium">{user.email}</p>
                </div>
                <div>
                  <label className="text-sm text-white/60">Created At</label>
                  <p className="text-lg font-medium">
                    {formatDate(user.createdAt)}
                  </p>
                </div>
                <div>
                  <label className="text-sm text-white/60">Status</label>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        user.isDisabled
                          ? "bg-red-500/10 text-red-500"
                          : "bg-green-500/10 text-green-500"
                      }`}
                    >
                      {user.isDisabled ? "Disabled" : "Active"}
                    </span>
                    {user.isPremium && (
                      <span className="px-2 py-1 rounded-full text-xs bg-purple-500/10 text-purple-500">
                        Premium
                      </span>
                    )}
                    {user.twoFactorEnabled && (
                      <span className="px-2 py-1 rounded-full text-xs bg-blue-500/10 text-blue-500">
                        2FA Enabled
                      </span>
                    )}
                  </div>
                </div>
              </div>
              {user.accountStatus !== "ACTIVE" && (
                <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                  <p className="text-sm text-red-400">
                    {user.accountStatus === "BANNED"
                      ? "Account Banned"
                      : "Account Disabled"}
                  </p>
                  {user.banReason && (
                    <p className="text-xs text-white/60 mt-1">
                      Reason: {user.banReason}
                    </p>
                  )}
                  {user.banExpires && (
                    <p className="text-xs text-white/60 mt-1">
                      Expires: {formatDate(user.banExpires)}
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="bg-black/20 border border-white/5 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Badges</h2>
              <div className="flex flex-wrap gap-2 mb-4">
                {user.badges.map((badge: any) => (
                  <div
                    key={badge}
                    className="flex items-center gap-2 bg-black/40 rounded-lg px-3 py-2"
                  >
                    <Image
                      src={`/badges/${badge.toLowerCase()}.svg`}
                      alt={badge}
                      width={20}
                      height={20}
                    />
                    <span>{badge}</span>
                    <button
                      onClick={() => actions.removeBadge(badge)}
                      className="ml-2 text-white/60 hover:text-white transition-colors"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setShowBadgeModal(true)}
                className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
              >
                Add Badge
              </button>
            </div>

            <div className="bg-black/20 border border-white/5 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Statistics</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-black/40 rounded-lg p-4">
                  <p className="text-sm text-white/60">Total Links</p>
                  <p className="text-2xl font-bold">{user.links.length}</p>
                </div>
                <div className="bg-black/40 rounded-lg p-4">
                  <p className="text-sm text-white/60">Active Sessions</p>
                  <p className="text-2xl font-bold">
                    {user.sessions.filter((s: any) => s.isActive).length}
                  </p>
                </div>
                <div className="bg-black/40 rounded-lg p-4">
                  <p className="text-sm text-white/60">Storage Used</p>
                  <p className="text-2xl font-bold">
                    {(
                      user.uploads.reduce(
                        (acc: any, upload: any) => acc + upload.size,
                        0,
                      ) /
                      1024 /
                      1024
                    ).toFixed(2)}{" "}
                    MB
                  </p>
                </div>
                <div className="bg-black/40 rounded-lg p-4">
                  <p className="text-sm text-white/60">Invites Created</p>
                  <p className="text-2xl font-bold">
                    {user.createdInvites.length}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-black/20 border border-white/5 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">API Access</h2>
                <button
                  onClick={() => actions.toggleApiAccess()}
                  className={`px-3 py-1 rounded-lg transition-colors ${
                    user.apiKeysEnabled
                      ? "bg-green-500/20 text-green-400"
                      : "bg-white/5 hover:bg-white/10"
                  }`}
                >
                  {user.apiKeysEnabled ? "Enabled" : "Disabled"}
                </button>
              </div>
              {user.apiKeysEnabled && (
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-white/60">Max API Keys:</span>
                  <input
                    type="number"
                    value={user.maxApiKeys}
                    onChange={(e) =>
                      actions.updateMaxApiKeys(parseInt(e.target.value))
                    }
                    className="w-16 px-2 py-1 rounded bg-black/40 border border-white/10"
                    min="1"
                    max="10"
                  />
                </div>
              )}
            </div>

            <div className="bg-black/20 border border-white/5 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">Premium Status</h2>
                <button
                  onClick={() => actions.togglePremiumFeature()}
                  className={`px-3 py-1 rounded-lg transition-colors ${
                    user.isPremium
                      ? "bg-purple-500/20 text-purple-400"
                      : "bg-white/5 hover:bg-white/10"
                  }`}
                >
                  {user.isPremium ? "Premium" : "Free"}
                </button>
              </div>
              {user.isPremium && (
                <>
                  <p className="text-sm text-white/60 mb-2">
                    Premium until: {formatDate(user.premiumUntil)}
                  </p>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-2 rounded hover:bg-white/5">
                      <span>Custom Domain</span>
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          user.features?.customDomain
                            ? "bg-green-500/10 text-green-500"
                            : "bg-white/10 text-white/60"
                        }`}
                      >
                        {user.features?.customDomain ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded hover:bg-white/5">
                      <span>Image Hosting</span>
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          user.features?.imageHosting
                            ? "bg-green-500/10 text-green-500"
                            : "bg-white/10 text-white/60"
                        }`}
                      >
                        {user.features?.imageHosting ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded hover:bg-white/5">
                      <span>Max Links</span>
                      <span className="px-2 py-1 rounded-full text-xs bg-white/10">
                        {user.features?.maxLinks || 10}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded hover:bg-white/5">
                      <span>Max Storage (MB)</span>
                      <span className="px-2 py-1 rounded-full text-xs bg-white/10">
                        {user.features?.maxStorage || 100}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded hover:bg-white/5">
                      <span>Custom Themes</span>
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          user.features?.customThemes
                            ? "bg-green-500/10 text-green-500"
                            : "bg-white/10 text-white/60"
                        }`}
                      >
                        {user.features?.customThemes ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded hover:bg-white/5">
                      <span>Remove Watermark</span>
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          user.features?.removeWatermark
                            ? "bg-green-500/10 text-green-500"
                            : "bg-white/10 text-white/60"
                        }`}
                      >
                        {user.features?.removeWatermark
                          ? "Enabled"
                          : "Disabled"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded hover:bg-white/5">
                      <span>Priority Support</span>
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          user.features?.prioritySupport
                            ? "bg-green-500/10 text-green-500"
                            : "bg-white/10 text-white/60"
                        }`}
                      >
                        {user.features?.prioritySupport
                          ? "Enabled"
                          : "Disabled"}
                      </span>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
      <StatusModal />
      <BadgeModal />
    </>
  );
}
