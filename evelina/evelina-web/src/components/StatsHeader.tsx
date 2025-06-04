import React, { useState, useEffect, useRef } from 'react';

interface Stats {
  users: number;
  servers: number;
  commands: number;
}

const FALLBACK_STATS = {
  users: 2630000,
  servers: 9200,
  commands: 200
};

// Staff categories that should be excluded from the command count
const STAFF_CATEGORIES = ['jishaku', 'helper', 'owner'];

function StatsHeader() {
  const [stats, setStats] = useState<Stats>({ ...FALLBACK_STATS, commands: 0 });
  const [displayStats, setDisplayStats] = useState<Stats>({ users: 0, servers: 0, commands: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const animationRef = useRef<{ users?: NodeJS.Timeout, servers?: NodeJS.Timeout, commands?: NodeJS.Timeout }>({});

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [shardsResponse, commandsResponse] = await Promise.all([
          fetch('/api/shards'),
          fetch('/api/commands')
        ]);
        
        if (!shardsResponse.ok || !commandsResponse.ok) throw new Error('Failed to fetch data');
        
        const shardsData = await shardsResponse.json();
        const commandsData = await commandsResponse.json();
        
        // Calculate totals from shards without rounding
        const totalUsers = shardsData.reduce((acc: number, shard: any) => acc + (shard.member_count || 0), 0);
        // Round users to nearest 10k
        const roundedUsers = Math.round(totalUsers / 10000) * 10000;
        const totalServers = shardsData.reduce((acc: number, shard: any) => acc + (shard.server_count || 0), 0);
        
        // Filter out staff commands and count public commands only
        const publicCommands = commandsData.filter((cmd: any) => 
          !STAFF_CATEGORIES.includes(cmd.category.toLowerCase())
        );
        
        setStats({
          users: roundedUsers,
          servers: totalServers,
          commands: publicCommands.length || FALLBACK_STATS.commands
        });
      } catch (err) {
        console.warn('Using fallback stats:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!isLoading) {
      Object.values(animationRef.current).forEach(timeout => {
        if (timeout) clearTimeout(timeout);
      });

      const duration = 2000;
      const steps = 50;
      const interval = duration / steps;

      const animate = (key: keyof Stats, target: number) => {
        const increment = Math.ceil(target / steps);
        let current = 0;

        const updateValue = () => {
          if (current < target) {
            current = Math.min(current + increment, target);
            setDisplayStats(prev => ({ ...prev, [key]: current }));
            
            if (current < target) {
              animationRef.current[key] = setTimeout(updateValue, interval);
            }
          }
        };

        updateValue();
      };

      animate('users', stats.users);
      animate('servers', stats.servers);
      animate('commands', stats.commands);

      return () => {
        Object.values(animationRef.current).forEach(timeout => {
          if (timeout) clearTimeout(timeout);
        });
      };
    }
  }, [isLoading, stats]);

  if (isLoading) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-4xl mx-auto">
      <div className="feature-card p-6 rounded-xl text-center transform hover:scale-105 transition-all duration-300 fade-in-left">
        <div className="text-2xl sm:text-3xl font-bold text-white tabular-nums mb-2">
          {displayStats.users.toLocaleString().replace(/,/g, '.')}
        </div>
        <div className="text-sm text-gray-400 uppercase tracking-wider font-medium">Users</div>
      </div>
      <div className="feature-card p-6 rounded-xl text-center transform hover:scale-105 transition-all duration-300 fade-in-scale" style={{ animationDelay: '0.2s' }}>
        <div className="text-2xl sm:text-3xl font-bold text-white tabular-nums mb-2">
          {displayStats.servers.toLocaleString().replace(/,/g, '.')}
        </div>
        <div className="text-sm text-gray-400 uppercase tracking-wider font-medium">Guilds</div>
      </div>
      <div className="feature-card p-6 rounded-xl text-center transform hover:scale-105 transition-all duration-300 fade-in-right" style={{ animationDelay: '0.4s' }}>
        <div className="text-2xl sm:text-3xl font-bold text-white tabular-nums mb-2">
          {displayStats.commands.toLocaleString().replace(/,/g, '.')}
        </div>
        <div className="text-sm text-gray-400 uppercase tracking-wider font-medium">Commands</div>
      </div>
    </div>
  );
}

export default StatsHeader;