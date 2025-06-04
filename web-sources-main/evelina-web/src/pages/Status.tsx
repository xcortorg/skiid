import React, { useState, useEffect, useRef } from 'react';
import { AlertCircle, Activity, Server, Users, Clock, Gauge, Signal, RefreshCw } from 'lucide-react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  Filler,
  ChartOptions
} from 'chart.js';
import 'chartjs-adapter-date-fns';
import PageHeader from '../components/PageHeader';
import { useStatusData } from '../hooks/useStatusData';
import { useShardData } from '../hooks/useShardData';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  Filler
);

type TimeRange = '24h' | '7d' | '30d' | 'all';

interface PeriodChange {
  servers: number;
  users: number;
}

function Status() {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [retryCount, setRetryCount] = useState(0);
  const [periodChanges, setPeriodChanges] = useState<PeriodChange>({ servers: 0, users: 0 });
  const { data, loading: statusLoading, error: statusError, refreshData } = useStatusData(timeRange);
  const { shards, loading: shardsLoading, error: shardsError, refreshShards } = useShardData();
  const serverChartRef = useRef<any>(null);
  const userChartRef = useRef<any>(null);
  const [chartKey, setChartKey] = useState(0);
  const [isChangingTimeRange, setIsChangingTimeRange] = useState(false);

  // Cleanup charts on unmount
  useEffect(() => {
    return () => {
      if (serverChartRef.current) {
        serverChartRef.current.destroy();
      }
      if (userChartRef.current) {
        userChartRef.current.destroy();
      }
    };
  }, []);

  // Calculate changes over the selected period
  useEffect(() => {
    if (data.length >= 2) {
      const firstDataPoint = data[0];
      const lastDataPoint = data[data.length - 1];

      setPeriodChanges({
        servers: lastDataPoint.total_servers - firstDataPoint.total_servers,
        users: lastDataPoint.total_users - firstDataPoint.total_users
      });
    }
  }, [data]);

  const chartOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: isChangingTimeRange ? 0 : 1000 // Disable animation during time range changes
    },
    scales: {
      x: {
        type: 'time' as const,
        time: {
          unit: timeRange === '24h' ? 'hour' as const : 'day' as const,
          displayFormats: {
            hour: 'HH:mm',
            day: 'MMM d'
          }
        },
        grid: {
          display: false
        },
        ticks: {
          color: '#9ca3af'
        }
      },
      y: {
        beginAtZero: false,
        grid: {
          color: 'rgba(255, 255, 255, 0.1)'
        },
        ticks: {
          color: '#9ca3af',
          callback: function(value: number) {
            return value.toLocaleString();
          }
        }
      }
    },
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        backgroundColor: 'rgba(17, 17, 17, 0.9)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: 'rgba(114, 155, 176, 0.2)',
        borderWidth: 1,
        padding: 12,
        displayColors: false,
        callbacks: {
          label: function(context: any) {
            const currentValue = context.raw;
            const dataIndex = context.dataIndex;
            const dataset = context.dataset.data;
            
            // Calculate difference from previous point
            if (dataIndex > 0) {
              const previousValue = dataset[dataIndex - 1];
              const difference = currentValue - previousValue;
              const sign = difference > 0 ? '+' : '';
              return [
                `${currentValue.toLocaleString()} [${sign}${difference.toLocaleString()}]`,
              ];
            }
            
            return `${currentValue.toLocaleString()}`;
          }
        }
      }
    },
    interaction: {
      intersect: false,
      mode: 'index' as const
    }
  };

  const formatUptime = (seconds: number) => {
    if (!seconds || seconds < 0) return '0h 0m';
    
    const ms = seconds * 1000;
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours === 0) {
      return `${minutes}m`;
    }
    
    return `${hours}h ${minutes}m`;
  };

  const handleRetry = () => {
    setRetryCount(prev => prev + 1);
    refreshData();
    refreshShards();
  };

  const handleTimeRangeChange = (range: TimeRange) => {
    if (range === timeRange) return;
    
    setIsChangingTimeRange(true);
    setTimeRange(range);
    
    // Allow a small delay for any cached data to be applied
    // and add a minimum loading time for better UX
    setTimeout(() => {
      setChartKey(prev => prev + 1); // Update chart with new range
      
      // Add a short delay before hiding the loading animation
      // to ensure a smoother transition
      setTimeout(() => {
        setIsChangingTimeRange(false);
      }, 300);
    }, 50);
  };

  // Full page loading state
  if ((statusLoading && !isChangingTimeRange) || shardsLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <PageHeader
          icon={<Activity />}
          title="Status"
          description="Real-time status and performance metrics"
        />

        {/* Loading Skeleton */}
        <div className="feature-card rounded-lg p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500/40 rounded-full"></div>
              <div className="h-7 bg-dark-2 rounded w-48"></div>
            </div>
            <div className="bg-dark-2/50 rounded-full p-1 flex">
              {['24h', '7d', '30d', 'All'].map((btn) => (
                <div key={btn} className="px-4 py-1 rounded-full w-12 h-8"></div>
              ))}
            </div>
          </div>
          
          {/* Stats Cards Skeleton */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="bg-dark-2/50 rounded-lg p-4 border border-[rgba(114,155,176,0.1)]">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-5 h-5 bg-theme/20 rounded"></div>
                  <div className="h-5 bg-dark-2 rounded w-24"></div>
                </div>
                <div className="h-8 bg-dark-2 rounded w-24"></div>
              </div>
            ))}
          </div>
          
          {/* Growth Charts Skeleton */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="bg-dark-2/50 rounded-lg p-4 border border-[rgba(114,155,176,0.1)]">
                <div className="h-6 bg-dark-2 rounded w-32 mb-4"></div>
                <div className="h-64 bg-dark-2/30 rounded-lg flex items-center justify-center">
                  <div className="w-8 h-8 border-2 border-theme/30 border-t-transparent rounded-full animate-spin"></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Shards Loading State */}
        <div className="h-8 bg-dark-2 rounded w-36 mb-4"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="feature-card rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                  <div className="h-6 bg-dark-2 rounded w-28"></div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500/40 rounded-full"></div>
                  <div className="h-5 bg-dark-2 rounded w-20"></div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                {[...Array(4)].map((_, j) => (
                  <div key={j}>
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-4 h-4 bg-dark-2 rounded-full"></div>
                      <div className="h-4 bg-dark-2 rounded w-16"></div>
                    </div>
                    <div className="h-6 bg-dark-2 rounded w-20"></div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (statusError || shardsError) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <PageHeader
          icon={<Activity />}
          title="Status"
          description="Real-time status and performance metrics"
        />
        
        <div className="mb-8 p-6 bg-red-500/10 border border-red-500/20 rounded-lg">
          <div className="flex items-center gap-3 text-red-400 mb-2">
            <AlertCircle className="w-5 h-5" />
            <h3 className="font-semibold">Error</h3>
          </div>
          <p className="text-gray-400">Unable to fetch status, please try again later or join our support server for assistance.</p>
          <div className="mt-4 flex gap-4">
            <a
              href="https://discord.gg/evelina"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-theme hover:text-theme/80 transition-colors"
            >
              Join Discord Server
            </a>
            <button
              onClick={handleRetry}
              className="inline-flex items-center gap-2 text-sm text-theme hover:text-theme/80 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Calculate total stats from all shards
  const totalStats = shards.reduce((acc, shard) => ({
    servers: acc.servers + shard.server_count,
    users: acc.users + shard.member_count,
    latency: acc.latency + shard.latency,
    readyShards: acc.readyShards + (shard.is_ready ? 1 : 0)
  }), { servers: 0, users: 0, latency: 0, readyShards: 0 });

  const averageLatency = Math.round(totalStats.latency / shards.length);

  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<Activity />}
        title="Status"
        description="Real-time status and performance metrics"
      />

      {/* Overall Status */}
      <div className="feature-card rounded-lg p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 ${totalStats.readyShards === shards.length ? 'bg-green-500' : 'bg-yellow-500'} rounded-full`}></div>
            <span className="text-xl font-semibold">
              {totalStats.readyShards === shards.length 
                ? 'All Systems Operational'
                : `${totalStats.readyShards}/${shards.length} Shards Operational`
              }
            </span>
          </div>
          {/* Modernere Timeframe-Auswahl als Pill/Tab Design */}
          <div className="bg-dark-2/50 rounded-full p-1 flex">
            <button
              onClick={() => handleTimeRangeChange('24h')}
              className={`px-4 py-1 rounded-full transition-all ${
                timeRange === '24h' 
                  ? 'bg-theme text-white' 
                  : 'text-gray-400 hover:text-white'
              }`}
              disabled={isChangingTimeRange}
            >
              24h
            </button>
            <button
              onClick={() => handleTimeRangeChange('7d')}
              className={`px-4 py-1 rounded-full transition-all ${
                timeRange === '7d' 
                  ? 'bg-theme text-white' 
                  : 'text-gray-400 hover:text-white'
              }`}
              disabled={isChangingTimeRange}
            >
              7d
            </button>
            <button
              onClick={() => handleTimeRangeChange('30d')}
              className={`px-4 py-1 rounded-full transition-all ${
                timeRange === '30d' 
                  ? 'bg-theme text-white' 
                  : 'text-gray-400 hover:text-white'
              }`}
              disabled={isChangingTimeRange}
            >
              30d
            </button>
            <button
              onClick={() => handleTimeRangeChange('all')}
              className={`px-4 py-1 rounded-full transition-all ${
                timeRange === 'all' 
                  ? 'bg-theme text-white' 
                  : 'text-gray-400 hover:text-white'
              }`}
              disabled={isChangingTimeRange}
            >
              All
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-dark-2/50 rounded-lg p-4 border border-[rgba(114,155,176,0.1)] relative">
            <div className="flex items-center gap-3 mb-2">
              <Gauge className="w-5 h-5 text-theme" />
              <span className="text-gray-400">Avg. Latency</span>
            </div>
            <span className="text-2xl font-bold">
              {averageLatency}ms
            </span>
            {isChangingTimeRange && (
              <div className="absolute inset-0 bg-dark-2/40 backdrop-blur-sm flex items-center justify-center rounded-lg">
                <div className="w-6 h-6 border-2 border-theme border-t-transparent rounded-full animate-spin"></div>
              </div>
            )}
          </div>
          <div className="bg-dark-2/50 rounded-lg p-4 border border-[rgba(114,155,176,0.1)] relative">
            <div className="flex items-center gap-3 mb-2">
              <Server className="w-5 h-5 text-theme" />
              <span className="text-gray-400">Total Servers</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold">
                {totalStats.servers.toLocaleString()}
              </span>
              {periodChanges.servers !== 0 && (
                <span className={`text-sm ${periodChanges.servers > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {periodChanges.servers > 0 ? '+' : ''}{periodChanges.servers.toLocaleString()}
                </span>
              )}
            </div>
            {isChangingTimeRange && (
              <div className="absolute inset-0 bg-dark-2/40 backdrop-blur-sm flex items-center justify-center rounded-lg">
                <div className="w-6 h-6 border-2 border-theme border-t-transparent rounded-full animate-spin"></div>
              </div>
            )}
          </div>
          <div className="bg-dark-2/50 rounded-lg p-4 border border-[rgba(114,155,176,0.1)] relative">
            <div className="flex items-center gap-3 mb-2">
              <Users className="w-5 h-5 text-theme" />
              <span className="text-gray-400">Total Users</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold">
                {totalStats.users.toLocaleString()}
              </span>
              {periodChanges.users !== 0 && (
                <span className={`text-sm ${periodChanges.users > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {periodChanges.users > 0 ? '+' : ''}{periodChanges.users.toLocaleString()}
                </span>
              )}
            </div>
            {isChangingTimeRange && (
              <div className="absolute inset-0 bg-dark-2/40 backdrop-blur-sm flex items-center justify-center rounded-lg">
                <div className="w-6 h-6 border-2 border-theme border-t-transparent rounded-full animate-spin"></div>
              </div>
            )}
          </div>
        </div>

        {/* Growth Charts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          <div className="bg-dark-2/50 rounded-lg p-4 border border-[rgba(114,155,176,0.1)] relative">
            <h3 className="text-lg font-semibold mb-4">Server Growth</h3>
            <div className="h-64">
              <Line
                key={`server-${chartKey}`}
                ref={serverChartRef}
                data={{
                  labels: data.map(d => new Date(d.timestamp)),
                  datasets: [{
                    data: data.map(d => d.total_servers),
                    borderColor: '#729bb0',
                    backgroundColor: 'rgba(114, 155, 176, 0.1)',
                    fill: true,
                    tension: 0.4
                  }]
                }}
                options={chartOptions}
              />
            </div>
            {isChangingTimeRange && (
              <div className="absolute inset-0 bg-dark-2/40 backdrop-blur-sm flex items-center justify-center rounded-lg">
                <div className="w-8 h-8 border-2 border-theme border-t-transparent rounded-full animate-spin"></div>
              </div>
            )}
          </div>
          <div className="bg-dark-2/50 rounded-lg p-4 border border-[rgba(114,155,176,0.1)] relative">
            <h3 className="text-lg font-semibold mb-4">User Growth</h3>
            <div className="h-64">
              <Line
                key={`user-${chartKey}`}
                ref={userChartRef}
                data={{
                  labels: data.map(d => new Date(d.timestamp)),
                  datasets: [{
                    data: data.map(d => d.total_users),
                    borderColor: '#729bb0',
                    backgroundColor: 'rgba(114, 155, 176, 0.1)',
                    fill: true,
                    tension: 0.4
                  }]
                }}
                options={chartOptions}
              />
            </div>
            {isChangingTimeRange && (
              <div className="absolute inset-0 bg-dark-2/40 backdrop-blur-sm flex items-center justify-center rounded-lg">
                <div className="w-8 h-8 border-2 border-theme border-t-transparent rounded-full animate-spin"></div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Shards Status */}
      <h2 className="text-2xl font-bold mb-4">Shard Status</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {shards.map(shard => (
          <div key={shard.shard_id} className="feature-card rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-4">
                <span className="text-xl font-semibold">Shard {shard.shard_id}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 ${shard.is_ready ? 'bg-green-500' : 'bg-red-500'} rounded-full`}></div>
                <span className="text-gray-400">{shard.is_ready ? 'Operational' : 'Down'}</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="flex items-center gap-2 text-gray-400 mb-1">
                  <Clock className="w-4 h-4" />
                  <span>Uptime</span>
                </div>
                <span className="text-lg font-semibold">{formatUptime(shard.uptime)}</span>
              </div>
              <div>
                <div className="flex items-center gap-2 text-gray-400 mb-1">
                  <Signal className="w-4 h-4" />
                  <span>Latency</span>
                </div>
                <span className="text-lg font-semibold">{shard.latency}ms</span>
              </div>
              <div>
                <div className="flex items-center gap-2 text-gray-400 mb-1">
                  <Server className="w-4 h-4" />
                  <span>Servers</span>
                </div>
                <span className="text-lg font-semibold">{shard.server_count.toLocaleString()}</span>
              </div>
              <div>
                <div className="flex items-center gap-2 text-gray-400 mb-1">
                  <Users className="w-4 h-4" />
                  <span>Users</span>
                </div>
                <span className="text-lg font-semibold">{shard.member_count.toLocaleString()}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Status;