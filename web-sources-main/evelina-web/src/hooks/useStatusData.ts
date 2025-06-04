import { useState, useEffect } from 'react';

interface StatusData {
  timestamp: string;
  total_servers: number;
  total_users: number;
  average_latency: number;
}

interface HistoryData {
  guilds: number;
  ping: number;
  timestamp: string;
  users: number;
}

type TimeRange = '24h' | '7d' | '30d' | 'all';

const MAX_RETRIES = 3;
const API_BASE_URL = '/api';
const RETRY_DELAY = 1000;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes cache

// Cache for all time ranges
const dataCache: {
  [key in TimeRange]?: {
    data: StatusData[];
    timestamp: number;
  }
} = {};

// Last fetched raw data
let lastFetchedData: {
  history?: HistoryData[];
  shards?: any[];
  timestamp?: number;
} = {};

function roundToMidnight(date: Date): Date {
  const roundedDate = new Date(date);
  roundedDate.setHours(0, 0, 0, 0);
  return roundedDate;
}

function roundToHour(date: Date): Date {
  const roundedDate = new Date(date);
  roundedDate.setMinutes(0, 0, 0);
  return roundedDate;
}

export function useStatusData(timeRange: TimeRange) {
  const [data, setData] = useState<StatusData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fetchId, setFetchId] = useState(0);

  const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const fetchWithRetry = async (endpoint: string, retries = MAX_RETRIES): Promise<any> => {
    let lastError: Error | null = null;

    for (let i = 0; i < retries; i++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
          signal: controller.signal,
          headers: {
            'Accept': 'application/json'
          }
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const errorText = await response.text().catch(() => 'Unknown error');
          throw new Error(`HTTP error ${response.status}: ${errorText}`);
        }

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Invalid response format: expected JSON');
        }

        const data = await response.json();
        return data;
      } catch (error) {
        lastError = error as Error;
        
        console.warn(`Fetch attempt ${i + 1}/${retries} failed:`, {
          error,
          endpoint,
          timestamp: new Date().toISOString()
        });

        if (error instanceof DOMException && error.name === 'AbortError') {
          throw new Error('Request timed out. Please check your connection and try again.');
        }

        if (i < retries - 1) {
          const backoffDelay = RETRY_DELAY * Math.pow(2, i);
          await delay(backoffDelay);
          continue;
        }
      }
    }

    throw new Error(lastError?.message || 'Failed to fetch data. Please try again later.');
  };

  // Process data for all time ranges and update cache
  const processDataForAllRanges = (historyData: HistoryData[], shardsData: any[]) => {
    const timeRanges: TimeRange[] = ['24h', '7d', '30d', 'all'];
    const now = new Date();
    
    // Calculate current stats from shards
    const currentLatency = Math.round(
      shardsData.reduce((acc: number, shard: any) => acc + (shard.latency || 0), 0) / shardsData.length
    );
    const currentServers = shardsData.reduce((acc: number, shard: any) => acc + (shard.server_count || 0), 0);
    const currentUsers = shardsData.reduce((acc: number, shard: any) => acc + (shard.member_count || 0), 0);
    
    // Sort history data by timestamp
    const sortedHistory = [...historyData].sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    
    // Process each time range
    timeRanges.forEach(range => {
      const pastDate = new Date(now);
      
      // Calculate the start date based on timeRange
      if (range !== 'all') {
        switch (range) {
          case '24h':
            pastDate.setHours(now.getHours() - 24);
            break;
          case '7d':
            pastDate.setDate(now.getDate() - 7);
            pastDate.setHours(0, 0, 0, 0); // Set to midnight
            break;
          case '30d':
            pastDate.setDate(now.getDate() - 30);
            pastDate.setHours(0, 0, 0, 0); // Set to midnight
            break;
        }
      }
      
      // Find the earliest available data point within the requested range
      const availableDataStart = sortedHistory.length > 0 
        ? new Date(sortedHistory[0].timestamp) 
        : now;
        
      const effectivePastDate = range === 'all' 
        ? availableDataStart 
        : (availableDataStart > pastDate ? availableDataStart : pastDate);
      
      // Group data by appropriate interval (hour or day)
      const groupedData = new Map<string, StatusData>();
      
      sortedHistory.forEach((item: HistoryData) => {
        const date = new Date(item.timestamp);
        if (date >= effectivePastDate && date <= now) {
          let key: string;
          
          if (range === '24h') {
            // For 24h, group by hour
            key = roundToHour(date).toISOString();
          } else {
            // For 7d, 30d, and all, group by day (midnight)
            key = roundToMidnight(date).toISOString();
          }
          
          // Only keep the first entry for each interval
          if (!groupedData.has(key)) {
            groupedData.set(key, {
              timestamp: key,
              total_servers: item.guilds,
              total_users: item.users,
              average_latency: item.ping
            });
          }
        }
      });
      
      // Convert Map to array and sort by timestamp
      const sortedData = Array.from(groupedData.values()).sort((a, b) => 
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      );
      
      // Add current hour/day data point if needed
      const currentKey = range === '24h' 
        ? roundToHour(now).toISOString()
        : roundToMidnight(now).toISOString();
      
      if (!groupedData.has(currentKey)) {
        sortedData.push({
          timestamp: currentKey,
          total_servers: currentServers,
          total_users: currentUsers,
          average_latency: currentLatency
        });
      }
      
      // Update cache for this time range
      dataCache[range] = {
        data: sortedData,
        timestamp: Date.now()
      };
    });
  };

  useEffect(() => {
    let isMounted = true;
    const abortController = new AbortController();

    const fetchData = async () => {
      try {
        // First check if we have valid cached data for the requested time range
        const cachedItem = dataCache[timeRange];
        const isCacheValid = cachedItem && (Date.now() - cachedItem.timestamp < CACHE_DURATION);
        
        if (isCacheValid) {
          // Use cached data first to show something immediately
          setData(cachedItem.data);
          
          // Keine automatische Aktualisierung mehr - nur bei manueller Anforderung
          setLoading(false);
          return;
        } else {
          // No valid cache, we need to show loading state
          setLoading(true);
        }
        
        // Fetch new data
        const [historyData, shardsData] = await Promise.all([
          fetchWithRetry('/history'),
          fetchWithRetry('/shards')
        ]);

        if (!isMounted) return;

        if (!Array.isArray(historyData)) {
          throw new Error('Invalid history data format: expected array');
        }

        if (!Array.isArray(shardsData)) {
          throw new Error('Invalid shards data format: expected array');
        }

        if (historyData.length === 0) {
          throw new Error('No history data available. Please try again later.');
        }

        if (shardsData.length === 0) {
          throw new Error('No shard data available. Please try again later.');
        }
        
        // Store raw data for potential reprocessing
        lastFetchedData = {
          history: historyData,
          shards: shardsData,
          timestamp: Date.now()
        };
        
        // Process data for all time ranges
        processDataForAllRanges(historyData, shardsData);
        
        // Update state with data for current time range
        if (dataCache[timeRange]) {
          setData(dataCache[timeRange]!.data);
        }
        
        setError(null);
      } catch (err) {
        if (!isMounted) return;
        
        const errorMessage = err instanceof Error 
          ? err.message
          : 'An unexpected error occurred. Please try again later.';
        
        console.error('Error fetching status data:', errorMessage);
        setError(errorMessage);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, [timeRange, fetchId]);

  // Expose a function to force refresh data - with complete cache clear
  const refreshData = () => {
    // Clearing the cache to ensure a full refresh
    Object.keys(dataCache).forEach(key => {
      delete dataCache[key as TimeRange];
    });
    lastFetchedData = {}; // Reset last fetched data
    setFetchId(prev => prev + 1);
  };

  return { data, loading, error, refreshData };
}