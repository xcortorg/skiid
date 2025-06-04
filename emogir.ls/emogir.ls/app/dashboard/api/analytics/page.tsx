"use client";

import { useState, useEffect } from "react";
import { StatCard } from "@/components/ui/stat-card";
import { DataCard } from "@/components/ui/data-card";
import {
  IconServer,
  IconCpu,
  IconClock,
  IconAlertTriangle,
  IconChartBar,
  IconTerminal2,
  IconCode,
  IconStatusChange,
} from "@tabler/icons-react";
import { AnalyticsGraph } from "@/components/ui/analytics-graph";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast-provider";

type TimePeriod = "24h" | "7d" | "30d" | "6mo" | "12mo";

export default function ApiAnalyticsPage() {
  const [timePeriod, setTimePeriod] = useState<TimePeriod>("30d");
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const [analyticsData, setAnalyticsData] = useState<{
    totalRequests: number;
    averageResponseTime: number;
    errorRate: number;
    cpuUsage: number;
    endpointStats: { endpoint: string; count: number; avgDuration: number }[];
    statusCodes: { code: number; count: number }[];
    requestsOverTime: { timestamp: string; count: number }[];
    topErrors: { message: string; count: number }[];
  }>({
    totalRequests: 0,
    averageResponseTime: 0,
    errorRate: 0,
    cpuUsage: 0,
    endpointStats: [],
    statusCodes: [],
    requestsOverTime: [],
    topErrors: [],
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`/api/analytics/api?period=${timePeriod}`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to fetch API analytics");
        }

        setAnalyticsData(data);
      } catch (error) {
        console.error("Error fetching API analytics:", error);
        toast({
          title: "Error",
          description: "Failed to load API analytics data",
          variant: "error",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [timePeriod]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-10 w-[180px]" />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="p-6 rounded-lg border border-primary/[0.125] bg-gradient-to-tr from-darker/80 to-darker/60"
            >
              <div className="flex justify-between items-start">
                <div className="space-y-3">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-8 w-16" />
                  <Skeleton className="h-3 w-20" />
                </div>
                <Skeleton className="h-8 w-8 rounded-full" />
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-6">
          <Skeleton className="h-[400px] w-full" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-[300px] w-full" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">API Analytics</h1>

        <Select
          value={timePeriod}
          onValueChange={(value: TimePeriod) => setTimePeriod(value)}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select time period" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="24h">Last 24 hours</SelectItem>
            <SelectItem value="7d">Last 7 days</SelectItem>
            <SelectItem value="30d">Last 30 days</SelectItem>
            <SelectItem value="6mo">Last 6 months</SelectItem>
            <SelectItem value="12mo">Last 12 months</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          title="Total Requests"
          value={analyticsData.totalRequests.toLocaleString()}
          icon={IconServer}
          subLabel="All endpoints"
        />
        <StatCard
          title="Avg Response Time"
          value={`${analyticsData.averageResponseTime.toFixed(2)}ms`}
          icon={IconClock}
          subLabel="Response time"
        />
        <StatCard
          title="Error Rate"
          value={`${(analyticsData.errorRate * 100).toFixed(1)}%`}
          icon={IconAlertTriangle}
          subLabel="Failed requests"
        />
      </div>

      <div className="grid gap-6">
        <DataCard title="Request Volume" icon={IconChartBar}>
          <div className="px-4">
            <AnalyticsGraph
              data={analyticsData.requestsOverTime.map((point) => ({
                label: new Date(point.timestamp).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                }),
                value: point.count,
              }))}
            />
          </div>
        </DataCard>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <DataCard title="Top Endpoints" icon={IconTerminal2}>
            <div className="-mx-3 divide-y divide-primary/5">
              {analyticsData.endpointStats.map((endpoint) => (
                <div
                  key={endpoint.endpoint}
                  className="flex items-center justify-between py-2 px-3 hover:bg-primary/5"
                >
                  <div className="flex items-center gap-2">
                    <IconCode size={14} className="text-white/60" />
                    <span className="text-sm font-mono">
                      {endpoint.endpoint}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-white/60">
                      {endpoint.count.toLocaleString()} requests
                    </span>
                    <span className="text-xs text-white/60">
                      {endpoint.avgDuration.toFixed(1)}ms
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </DataCard>

          <DataCard title="Status Codes" icon={IconStatusChange}>
            <div className="-mx-3 divide-y divide-primary/5">
              {analyticsData.statusCodes.map((status) => (
                <div
                  key={status.code}
                  className="flex items-center justify-between py-2 px-3 hover:bg-primary/5"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        status.code >= 500
                          ? "bg-red-500"
                          : status.code >= 400
                            ? "bg-yellow-500"
                            : "bg-green-500"
                      }`}
                    />
                    <span className="text-sm font-mono">{status.code}</span>
                  </div>
                  <span className="text-xs text-white/60">
                    {status.count.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </DataCard>

          <DataCard title="Top Errors" icon={IconAlertTriangle}>
            <div className="-mx-3 divide-y divide-primary/5">
              {analyticsData.topErrors.map((error, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between py-2 px-3 hover:bg-primary/5"
                >
                  <span className="text-sm text-white/80 truncate pr-4">
                    {error.message}
                  </span>
                  <span className="text-xs text-white/60">
                    {error.count.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </DataCard>
        </div>
      </div>
    </div>
  );
}
