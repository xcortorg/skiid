import React, { useState, useEffect } from 'react';
import { Server as ServerIcon, Shield, Download, User as UserIcon, Search } from 'lucide-react';
import { format } from 'date-fns';
import { fetchWithHeaders } from '../../../../lib/api';
import PageHeader from '../../../../components/PageHeader';

// Types for blacklist data
interface BlacklistServer {
  guild_id: string;
  moderator_id: string;
  duration: number; // Duration in seconds
  reason: string;
  timestamp: number; // Unix timestamp
}

const Server: React.FC = () => {
  // State for logs data
  const [blacklists, setBlacklists] = useState<BlacklistServer[]>([]);
  // State for loading status
  const [isLoading, setIsLoading] = useState<boolean>(true);
  // State for errors
  const [error, setError] = useState<string | null>(null);

  // Fetch all blacklists when component mounts
  useEffect(() => {
    const fetchAllBlacklists = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        const blacklistsData = await fetchAllServerBlacklists();
        setBlacklists(blacklistsData);
      } catch (err) {
        console.error('Error fetching server blacklists:', err);
        setError('Failed to fetch server blacklists. Please try again.');
        setBlacklists([]);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchAllBlacklists();
  }, []);

  // Function to fetch all server blacklists
  const fetchAllServerBlacklists = async () => {
    return fetchWithHeaders('/blacklist/server/servers');
  };

  // Format timestamp to readable date
  const formatTimestamp = (timestamp: number) => {
    return format(new Date(timestamp * 1000), 'dd.MM.yyyy HH:mm:ss');
  };

  // Format duration in a human-readable format
  const formatDuration = (durationInSeconds: number) => {
    if (durationInSeconds === 0) {
      return 'Permanent';
    }
    
    const days = Math.floor(durationInSeconds / 86400);
    const hours = Math.floor((durationInSeconds % 86400) / 3600);
    const minutes = Math.floor((durationInSeconds % 3600) / 60);
    const seconds = durationInSeconds % 60;
    
    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  };

  // Export logs to CSV
  const exportToCSV = () => {
    if (blacklists.length === 0) return;
    
    const headers = ['Server ID', 'Moderator ID', 'Duration', 'Reason', 'Date'];
    const csvRows = [
      headers.join(','),
      ...blacklists.map(blacklist => [
        blacklist.guild_id,
        blacklist.moderator_id,
        formatDuration(blacklist.duration),
        `"${blacklist.reason.replace(/"/g, '""')}"`, // Escape quotes in CSV
        formatTimestamp(blacklist.timestamp)
      ].join(','))
    ];
    
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `server_blacklists_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-6">
      {/* Page Header */}
      <PageHeader
        icon={<Shield />}
        title="Server Blacklist"
        description="View all server blacklists"
      />
      
      {/* Error message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-500 p-4 rounded-xl mb-6">
          {error}
        </div>
      )}
      
      {/* Loading indicator */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-12 w-12 rounded-full border-4 border-t-theme border-r-transparent border-l-transparent border-b-theme animate-spin"></div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Blacklist Table */}
          <div className="bg-[#161616] rounded-xl shadow-md overflow-hidden">
            {blacklists.length > 0 ? (
              <>
                <div className="p-4 border-b border-[#2a2a2a] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                  <h3 className="text-lg font-medium">
                    Server Blacklist
                  </h3>
                  <div className="flex items-center gap-2">
                    <div className="text-sm text-gray-400">{blacklists.length} entries found</div>
                    <button
                      onClick={exportToCSV}
                      className="ml-2 bg-[#232323] hover:bg-[#333] text-white p-1.5 rounded transition-colors"
                      title="Export to CSV"
                      disabled={blacklists.length === 0}
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-[#1a1a1a] text-gray-400 text-xs uppercase">
                        <th className="py-3.5 px-4 text-left font-medium">Server ID</th>
                        <th className="py-3.5 px-4 text-left font-medium">Moderator</th>
                        <th className="py-3.5 px-4 text-left font-medium">Duration</th>
                        <th className="py-3.5 px-4 text-left font-medium">Reason</th>
                        <th className="py-3.5 px-4 text-left font-medium">Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#2a2a2a]">
                      {blacklists.map((blacklist, index) => (
                        <tr key={index} className="hover:bg-[#1a1a1a] transition-colors">
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              <ServerIcon className="w-4 h-4 text-gray-400" />
                              {blacklist.guild_id}
                            </div>
                          </td>
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              <UserIcon className="w-4 h-4 text-gray-400" />
                              {blacklist.moderator_id}
                            </div>
                          </td>
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            <span className="px-2.5 py-1 text-xs rounded-full bg-opacity-10 font-medium inline-block"
                                  style={{
                                    backgroundColor: blacklist.duration === 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                                    color: blacklist.duration === 0 ? 'rgb(239, 68, 68)' : 'rgb(59, 130, 246)'
                                  }}>
                              {formatDuration(blacklist.duration)}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 max-w-[250px]">
                            <div className="truncate">{blacklist.reason}</div>
                          </td>
                          <td className="py-3.5 px-4 whitespace-nowrap text-gray-400">
                            {formatTimestamp(blacklist.timestamp)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div className="text-center py-12">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[#1a1a1a] mb-4">
                  <Search className="w-8 h-8 text-gray-500" />
                </div>
                <h3 className="text-lg font-medium mb-2">No Server Blacklist Entries Found</h3>
                <p className="text-gray-400 max-w-md mx-auto">
                  There are currently no server blacklist entries in the database.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Server; 