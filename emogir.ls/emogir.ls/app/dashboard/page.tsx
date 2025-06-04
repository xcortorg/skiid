"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/ui/stat-card";
import {
  IconPlus,
  IconExternalLink,
  IconEye,
  IconLink as LinkIcon,
  IconClick,
  IconArrowUpRight,
  IconChartBar,
  IconClock,
  IconCopy,
  IconUsers,
  IconWorld,
  IconDeviceLaptop,
} from "@tabler/icons-react";
import { DataCard } from "@/components/ui/data-card";
import { RecentLinkItem } from "@/components/ui/recent-link-item";
import { useSession } from "next-auth/react";
import { useToast } from "@/components/ui/toast-provider";
import Link from "next/link";
import Image from "next/image";

interface Analytics {
  totalViews: number;
  totalLinks: number;
  totalClicks: number;
  viewsChange: number;
  clicksChange: number;
  recentLinks: {
    id: string;
    title: string;
    url: string;
    clicks: number;
    iconUrl?: string;
  }[];
}

export default function DashboardPage() {
  const { toast } = useToast();
  const { data: session } = useSession();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const [analyticsResponse, linksResponse] = await Promise.all([
          fetch("/api/analytics"),
          fetch("/api/links"),
        ]);

        const analyticsData = await analyticsResponse.json();
        const linksData = await linksResponse.json();

        setAnalytics({
          totalViews: analyticsData.aggregate.results.pageviews.value,
          totalLinks: linksData.length,
          totalClicks: analyticsData.aggregate.results.visitors.value,
          viewsChange: 0,
          clicksChange: 0,
          recentLinks: linksData.slice(0, 5).map((link: any) => ({
            id: link.id,
            title: link.title,
            url: link.url,
            clicks: link.clicks,
            iconUrl: link.iconUrl,
          })),
        });
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to load analytics",
          variant: "error",
        });
      }
    };

    fetchAnalytics();
  }, [toast]);

  const copyProfileUrl = async () => {
    if (session?.user?.username) {
      try {
        await navigator.clipboard.writeText(
          `https://emogir.ls/${session.user.username}`
        );
        toast({
          title: "Copied",
          description: `emogir.ls/${session.user.username}`,
          variant: "success",
        });
      } catch (err) {}
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">
          Welcome, {session?.user?.name || "User"}
        </h1>
        <Button text="Add Link" icon={IconPlus} href="/dashboard/links" />
      </div>

      <div className="relative overflow-hidden rounded-xl border border-primary/[0.125] p-6 isolate">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl -z-20" />
        <div className="absolute inset-0 bg-gradient-to-tr from-primary/[0.08] to-transparent -z-10" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent -z-10" />

        <div className="absolute -z-10 animate-pulse">
          <div className="absolute -right-[40%] top-0 h-[200px] w-[200px] rounded-full bg-primary/5 blur-[64px]" />
          <div className="absolute -left-[40%] bottom-0 h-[200px] w-[200px] rounded-full bg-primary/5 blur-[64px]" />
        </div>

        <div className="relative flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-6">
          <div className="flex-shrink-0 size-20 sm:size-24 overflow-hidden rounded-full border-2 border-primary/20 bg-black/20 backdrop-blur-sm">
            {session?.user?.image ? (
              <Image
                src={session.user.image}
                alt={session.user.name || "Avatar"}
                width={80}
                height={80}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full bg-primary/10 flex items-center justify-center">
                <span className="text-2xl font-bold text-primary">
                  {session?.user?.name?.charAt(0) || "?"}
                </span>
              </div>
            )}
          </div>

          <div className="flex-1">
            <h2 className="text-xl font-semibold">{session?.user?.name}</h2>
            <p className="text-white/60 mt-1">
              @{session?.user?.username || "username"}
            </p>

            <div className="flex flex-wrap gap-3 mt-3">
              <Button
                text="Your Profile"
                href={`/${session?.user?.username || "username"}`}
                icon={IconExternalLink}
                className="bg-white/5 hover:bg-white/10 transition-colors"
              />
              <Button
                text="Copy Link"
                onClick={copyProfileUrl}
                className="bg-primary/10 hover:bg-primary/20 transition-colors backdrop-blur-sm"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          title="Total Views"
          value={(analytics?.totalViews ?? "??").toLocaleString()}
          icon={IconEye}
          subLabel="Since last month"
          subValue={
            <span
              className={
                analytics?.viewsChange ?? 0 >= 0
                  ? "text-emerald-500"
                  : "text-red-500"
              }
            >
              {analytics?.viewsChange
                ? (analytics.viewsChange >= 0 ? "+" : "") +
                  analytics.viewsChange +
                  "%"
                : "??"}
            </span>
          }
        />
        <StatCard
          title="Total Links"
          value={(analytics?.totalLinks ?? "??").toLocaleString()}
          icon={LinkIcon}
          subLabel="Active links"
          subValue={(analytics?.totalLinks ?? "??").toLocaleString()}
        />
        <StatCard
          title="Total Clicks"
          value={(analytics?.totalClicks ?? "??").toLocaleString()}
          icon={IconClick}
          subLabel="Last 7 days"
          subValue={
            <span
              className={
                analytics?.viewsChange ?? 0 >= 0
                  ? "text-emerald-500"
                  : "text-red-500"
              }
            >
              {analytics?.clicksChange
                ? (analytics.clicksChange >= 0 ? "+" : "") +
                  analytics.clicksChange +
                  "%"
                : "??"}
            </span>
          }
        />
      </div>
      <div className="grid grid-cols-1 gap-6">
        <DataCard title="Recent Links" icon={LinkIcon}>
          <div className="space-y-3">
            {analytics?.recentLinks?.length ? (
              analytics.recentLinks.map((link) => (
                <RecentLinkItem
                  key={link.id}
                  title={link.title}
                  url={link.url}
                  clicks={link.clicks}
                  iconUrl={link.iconUrl}
                />
              ))
            ) : (
              <div className="text-center py-8 text-white/60">
                No links created yet
              </div>
            )}
          </div>
        </DataCard>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        <DataCard title="Performance Insights" icon={IconChartBar}>
          <div className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium">Profile Performance</h3>
                <p className="text-xs text-white/60 mt-1">
                  Based on recent activity
                </p>
              </div>
              {analytics?.totalViews && analytics?.totalClicks ? (
                <div className="text-right">
                  <div className="text-lg font-semibold">
                    {(
                      (analytics.totalClicks / analytics.totalViews) *
                      100
                    ).toFixed(1)}
                    %
                  </div>
                  <div className="text-xs text-white/60">Engagement Rate</div>
                </div>
              ) : (
                <div className="h-10 w-16 bg-white/5 rounded animate-pulse"></div>
              )}
            </div>

            <div className="h-24 w-full bg-black/20 rounded-lg overflow-hidden relative">
              {(analytics?.recentLinks || []).length > 0 ? (
                <div className="absolute inset-0 flex items-end">
                  {(analytics?.recentLinks || []).map((link, i) => (
                    <div
                      key={link.id}
                      className="h-full flex-1 flex flex-col justify-end"
                    >
                      <div
                        className="bg-primary/60 rounded-t-sm transition-all hover:bg-primary/80"
                        style={{
                          height: `${Math.max(
                            15,
                            (link.clicks /
                              Math.max(
                                ...(analytics?.recentLinks || []).map(
                                  (l) => l.clicks
                                )
                              )) *
                              100
                          )}%`,
                        }}
                      ></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full">
                  <p className="text-xs text-white/40">No data available</p>
                </div>
              )}
            </div>
          </div>
        </DataCard>

        <DataCard title="Quick Actions" icon={IconClock}>
          <div className="p-4">
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => (window.location.href = "/dashboard/links")}
                className="flex flex-col items-center justify-center p-4 rounded-lg bg-black/20 hover:bg-black/30 transition-colors border border-primary/10 hover:border-primary/20"
              >
                <IconPlus size={20} className="text-primary mb-2" />
                <span className="text-sm">New Link</span>
              </button>

              <button
                onClick={() => (window.location.href = "/dashboard/appearance")}
                className="flex flex-col items-center justify-center p-4 rounded-lg bg-black/20 hover:bg-black/30 transition-colors border border-primary/10 hover:border-primary/20"
              >
                <IconDeviceLaptop size={20} className="text-primary mb-2" />
                <span className="text-sm">Edit Theme</span>
              </button>

              <button
                onClick={() => (window.location.href = "/dashboard/analytics")}
                className="flex flex-col items-center justify-center p-4 rounded-lg bg-black/20 hover:bg-black/30 transition-colors border border-primary/10 hover:border-primary/20"
              >
                <IconChartBar size={20} className="text-primary mb-2" />
                <span className="text-sm">Analytics</span>
              </button>

              <button
                onClick={copyProfileUrl}
                className="flex flex-col items-center justify-center p-4 rounded-lg bg-black/20 hover:bg-black/30 transition-colors border border-primary/10 hover:border-primary/20"
              >
                <IconCopy size={20} className="text-primary mb-2" />
                <span className="text-sm">Share Profile</span>
              </button>
            </div>
          </div>
        </DataCard>
      </div>
    </div>
  );
}
