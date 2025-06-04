import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { cn } from "@/lib/utils";

interface DataPoint {
  label: string;
  value: number;
}

interface AnalyticsGraphProps {
  data: DataPoint[];
  className?: string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border border-primary/20 bg-darker px-3 py-1.5">
        <p className="text-xs font-medium text-white">
          {payload[0].value.toLocaleString()} clicks
        </p>
      </div>
    );
  }
  return null;
};

export function AnalyticsGraph({ data, className }: AnalyticsGraphProps) {
  const chartData = data.map((point) => ({
    name: point.label,
    value: point.value,
  }));

  return (
    <div className={cn("w-full h-[240px]", className)}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="rgb(255,51,121)" stopOpacity={0.2} />
              <stop
                offset="95%"
                stopColor="rgb(255,51,121)"
                stopOpacity={0.02}
              />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="name"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
            dy={10}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
            dx={-10}
          />
          <Tooltip content={CustomTooltip} cursor={false} />
          <Area
            type="monotone"
            dataKey="value"
            stroke="rgb(255,51,121)"
            strokeWidth={2}
            fill="url(#colorValue)"
            dot={false}
            activeDot={{
              r: 6,
              fill: "#050505",
              stroke: "rgb(255,51,121)",
              strokeWidth: 2,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
