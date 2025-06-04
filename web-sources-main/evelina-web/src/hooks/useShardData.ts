import { useState, useEffect } from 'react';

interface Shard {
  is_ready: boolean;
  last_updated: string;
  latency: number;
  member_count: number;
  server_count: number;
  shard_id: number;
  uptime: number;
}

const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second
const CACHE_DURATION = 60 * 1000; // 1 minute

// Client-side cache
let clientCache: {
  data: Shard[] | null;
  timestamp: number;
} = {
  data: null,
  timestamp: 0
};

export function useShardData() {
  const [shards, setShards] = useState<Shard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const fetchWithRetry = async (url: string, retries = MAX_RETRIES): Promise<any> => {
    let lastError: Error | null = null;

    for (let i = 0; i < retries; i++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        const response = await fetch(url, {
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
        
        // Log detailed error information
        console.warn(`Fetch attempt ${i + 1}/${retries} failed:`, {
          error,
          url,
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

  useEffect(() => {
    let isMounted = true;
    const abortController = new AbortController();

    const fetchShards = async () => {
      try {
        if (!isMounted) return;
        setLoading(true);
        setError(null);

        // Check client-side cache
        if (clientCache.data && Date.now() - clientCache.timestamp < CACHE_DURATION) {
          setShards(clientCache.data);
          setLoading(false);
          return;
        }

        // Fetch current shards data
        const data = await fetchWithRetry('/api/shards');
        
        if (!isMounted) return;

        if (!Array.isArray(data)) {
          throw new Error('Invalid response format: expected array of shards');
        }

        if (data.length === 0) {
          throw new Error('No shard data available. Please try again later.');
        }

        // Sort shards by ID
        const sortedShards = [...data].sort((a, b) => a.shard_id - b.shard_id);

        if (!isMounted) return;

        // Update cache
        clientCache = {
          data: sortedShards,
          timestamp: Date.now()
        };

        setShards(sortedShards);
        setError(null);
      } catch (err) {
        if (!isMounted) return;
        
        const errorMessage = err instanceof Error 
          ? err.message
          : 'An unexpected error occurred. Please try again later.';
        
        console.error('Error fetching shards:', errorMessage);
        setError(errorMessage);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchShards();

    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, []);

  // Füge eine Funktion zum manuellen Aktualisieren hinzu
  const refreshShards = () => {
    // Lösche den Cache, um eine tatsächliche Aktualisierung zu erzwingen
    clientCache = {
      data: null,
      timestamp: 0
    };
    // Trigger für useEffect
    setLoading(true);
  };

  return { shards, loading, error, refreshShards };
}