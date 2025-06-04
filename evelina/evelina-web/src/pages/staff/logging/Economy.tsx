import React, { useState, useEffect } from 'react';
import { Search, Book, Filter, User, Mail, Clock, Activity, Shield, ChevronDown, Trash, Download, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';
import { fetchEconomyLogs, fetchUserData, fetchWithHeaders } from '../../../lib/api';
import PageHeader from '../../../components/PageHeader';

// Types for economy logs data
interface EconomyLog {
  user_id: string;
  action: string;
  type: string;
  amount: number;
  cash: number;
  card: number;
  created: number; // Unix timestamp
}

// Types for user data
interface UserActivity {
  details: string;
  emoji: string;
  image: string;
  name: string;
  state: string;
}

interface UserData {
  activity: UserActivity;
  avatar: string;
  banner: string;
  user: string;
  user_id?: string;
}

// Types for filters
interface FilterOptions {
  action: string;
  type: string;
  minAmount: string;
  maxAmount: string;
  startDate: string;
  endDate: string;
}

const Economy: React.FC = () => {
  // State for search input
  const [searchQuery, setSearchQuery] = useState<string>('');
  // State for logs data
  const [logs, setLogs] = useState<EconomyLog[]>([]);
  // State for all logs without filter
  const [allLogs, setAllLogs] = useState<EconomyLog[]>([]);
  // State for user data
  const [userData, setUserData] = useState<UserData | null>(null);
  // State for loading status
  const [isLoading, setIsLoading] = useState<boolean>(false);
  // State for errors
  const [error, setError] = useState<string | null>(null);
  // State for search executed flag
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  // State for showing filter dropdown
  const [showFilters, setShowFilters] = useState<boolean>(false);
  // State for filter options
  const [filters, setFilters] = useState<FilterOptions>({
    action: '',
    type: '',
    minAmount: '',
    maxAmount: '',
    startDate: '',
    endDate: ''
  });

  // Get unique action and type values for filter dropdowns
  const uniqueActions = Array.from(new Set(allLogs.map(log => log.action)));
  const uniqueTypes = Array.from(new Set(allLogs.map(log => log.type)));

  // Handle search input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  // Handle search form submission
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!searchQuery.trim()) {
      setError('Please enter a user ID');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    
    try {
      // Fetch both user data and logs in parallel
      const [logsData, userInfo] = await Promise.all([
        fetchEconomyLogs(searchQuery.trim()),
        fetchUserData(searchQuery.trim()).catch(err => {
          console.error('Error fetching user data:', err);
          return null;
        })
      ]);
      
      setAllLogs(logsData);
      applyFilters(logsData);
      setUserData(userInfo);
    } catch (err) {
      console.error('Error fetching economy logs:', err);
      setError('Failed to fetch economy logs. Please try again.');
      setAllLogs([]);
      setLogs([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle filter changes
  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Apply filters to logs
  const applyFilters = (logsToFilter = allLogs) => {
    let filteredLogs = [...logsToFilter];
    
    // Apply action filter
    if (filters.action) {
      filteredLogs = filteredLogs.filter(log => log.action === filters.action);
    }
    
    // Apply type filter
    if (filters.type) {
      filteredLogs = filteredLogs.filter(log => log.type === filters.type);
    }
    
    // Apply amount filters
    if (filters.minAmount) {
      filteredLogs = filteredLogs.filter(log => log.amount >= parseFloat(filters.minAmount));
    }
    
    if (filters.maxAmount) {
      filteredLogs = filteredLogs.filter(log => log.amount <= parseFloat(filters.maxAmount));
    }
    
    // Apply date filters
    if (filters.startDate) {
      const startTimestamp = new Date(filters.startDate).getTime() / 1000;
      filteredLogs = filteredLogs.filter(log => log.created >= startTimestamp);
    }
    
    if (filters.endDate) {
      const endTimestamp = new Date(filters.endDate).getTime() / 1000 + 86400; // Add one day to include the end date
      filteredLogs = filteredLogs.filter(log => log.created <= endTimestamp);
    }
    
    setLogs(filteredLogs);
  };

  // Apply filters when filter state changes
  useEffect(() => {
    if (allLogs.length > 0) {
      applyFilters();
    }
  }, [filters]);

  // Reset filters
  const resetFilters = () => {
    setFilters({
      action: '',
      type: '',
      minAmount: '',
      maxAmount: '',
      startDate: '',
      endDate: ''
    });
    setLogs(allLogs);
  };

  // Format timestamp to readable date
  const formatTimestamp = (timestamp: number) => {
    return format(new Date(timestamp * 1000), 'dd.MM.yyyy HH:mm:ss');
  };

  // Format currency values with 2 decimal places and thousand separators
  const formatCurrency = (value: number) => {
    return value.toLocaleString('de-DE', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  };

  // Export logs to CSV
  const exportToCSV = () => {
    if (logs.length === 0) return;
    
    const headers = ['User ID', 'Action', 'Type', 'Amount', 'Cash', 'Card', 'Date'];
    const csvRows = [
      headers.join(','),
      ...logs.map(log => [
        log.user_id,
        log.action,
        log.type,
        log.amount.toString().replace('.', ','),
        log.cash.toString().replace('.', ','),
        log.card.toString().replace('.', ','),
        formatTimestamp(log.created)
      ].join(','))
    ];
    
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `economy_logs_${searchQuery.trim()}_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-6">
      {/* Page Header */}
      <PageHeader
        icon={<Book />}
        title="Economy Logs"
        description="View and search for economy transactions by user ID"
      />
      
      {/* Enhanced Search form */}
      <div className="bg-[#161616] p-5 rounded-xl mb-6 shadow-md">
        <form onSubmit={handleSearch}>
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search by Discord User ID"
                value={searchQuery}
                onChange={handleInputChange}
                className="w-full pl-10 pr-4 py-2.5 bg-[#1f1f1f] border border-[#333] rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-theme focus:border-transparent"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setShowFilters(!showFilters)}
                className="bg-[#1f1f1f] hover:bg-[#2a2a2a] text-white font-medium p-2.5 rounded-lg transition-colors flex items-center justify-center"
                title="Toggle filters"
              >
                <Filter className="w-5 h-5" />
              </button>
              <button 
                type="submit"
                disabled={isLoading}
                className="bg-theme hover:bg-theme/90 text-white px-4 py-2.5 rounded-lg flex items-center gap-2 shadow-lg">
                {isLoading ? (
                  <>
                    <div className="animate-spin w-4 h-4 border-2 border-theme border-t-transparent rounded-full"></div>
                    Loading...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    Search
                  </>
                )}
              </button>
            </div>
          </div>
          
          {/* Filters section */}
          {showFilters && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-[#1a1a1a] rounded-lg border border-[#333]">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Action</label>
                <select
                  name="action"
                  value={filters.action}
                  onChange={handleFilterChange}
                  className="w-full bg-[#232323] border border-[#333] rounded-lg py-2 px-3 text-white"
                >
                  <option value="">All Actions</option>
                  {uniqueActions.map(action => (
                    <option key={action} value={action}>{action}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Type</label>
                <select
                  name="type"
                  value={filters.type}
                  onChange={handleFilterChange}
                  className="w-full bg-[#232323] border border-[#333] rounded-lg py-2 px-3 text-white"
                >
                  <option value="">All Types</option>
                  {uniqueTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Min Amount</label>
                <input
                  type="number"
                  name="minAmount"
                  value={filters.minAmount}
                  onChange={handleFilterChange}
                  placeholder="Min amount"
                  className="w-full bg-[#232323] border border-[#333] rounded-lg py-2 px-3 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Max Amount</label>
                <input
                  type="number"
                  name="maxAmount"
                  value={filters.maxAmount}
                  onChange={handleFilterChange}
                  placeholder="Max amount"
                  className="w-full bg-[#232323] border border-[#333] rounded-lg py-2 px-3 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Start Date</label>
                <input
                  type="date"
                  name="startDate"
                  value={filters.startDate}
                  onChange={handleFilterChange}
                  className="w-full bg-[#232323] border border-[#333] rounded-lg py-2 px-3 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">End Date</label>
                <input
                  type="date"
                  name="endDate"
                  value={filters.endDate}
                  onChange={handleFilterChange}
                  className="w-full bg-[#232323] border border-[#333] rounded-lg py-2 px-3 text-white"
                />
              </div>
              <div className="md:col-span-3 flex justify-end mt-2">
                <button
                  type="button"
                  onClick={resetFilters}
                  className="flex items-center gap-2 text-gray-400 hover:text-white"
                >
                  <RefreshCw className="w-4 h-4" />
                  Reset Filters
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
      
      {/* Results section */}
      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-2 border-theme border-t-transparent"></div>
        </div>
      ) : hasSearched && (
        <div className="space-y-6">
          {/* Logs Table */}
          <div className="bg-[#161616] rounded-xl shadow-md overflow-hidden">
            {logs.length > 0 ? (
              <>
                <div className="p-4 border-b border-[#2a2a2a] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                  {userData ? (
                    <div className="flex items-center gap-3">
                      <img 
                        src={userData.avatar} 
                        alt={userData.user} 
                        className="w-8 h-8 rounded-full" 
                      />
                      <h3 className="text-lg font-medium">{userData.user}</h3>
                    </div>
                  ) : (
                    <h3 className="text-lg font-medium">
                      Economy Logs for User ID: {searchQuery}
                    </h3>
                  )}
                  <div className="flex items-center gap-2">
                    <div className="text-sm text-gray-400">{logs.length} transactions found</div>
                    <button
                      onClick={exportToCSV}
                      className="ml-2 bg-[#232323] hover:bg-[#333] text-white p-1.5 rounded transition-colors"
                      title="Export to CSV"
                      disabled={logs.length === 0}
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-[#1a1a1a] text-gray-400 text-xs uppercase">
                        <th className="py-3.5 px-4 text-left font-medium">Date</th>
                        <th className="py-3.5 px-4 text-left font-medium">Action</th>
                        <th className="py-3.5 px-4 text-left font-medium">Type</th>
                        <th className="py-3.5 px-4 text-left font-medium">Amount</th>
                        <th className="py-3.5 px-4 text-left font-medium">Cash</th>
                        <th className="py-3.5 px-4 text-left font-medium">Card</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#2a2a2a]">
                      {logs.map((log, index) => (
                        <tr key={index} className="hover:bg-[#1d1d1d] transition-colors">
                          <td className="py-3.5 px-4 text-gray-200 font-medium">{formatTimestamp(log.created)}</td>
                          <td className="py-3.5 px-4 font-medium">{log.action}</td>
                          <td className="py-3.5 px-4">
                            <span className="px-2.5 py-1 text-xs rounded-full bg-opacity-10 font-medium inline-block" 
                                  style={{ 
                                    backgroundColor: `rgba(${getTypeColor(log.type)}, 0.1)`,
                                    color: `rgb(${getTypeColor(log.type)})` 
                                  }}>
                              {log.type}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 font-mono">{formatCurrency(log.amount)}</td>
                          <td className="py-3.5 px-4 font-mono">{formatCurrency(log.cash)}</td>
                          <td className="py-3.5 px-4 font-mono">{formatCurrency(log.card)}</td>
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
                <h3 className="text-lg font-medium mb-2">No Economy Logs Found</h3>
                <p className="text-gray-400 max-w-md mx-auto">
                  {userData ? 
                    `There are no economy logs for ${userData.user}.` : 
                    'There are no economy logs for this user ID. Try searching for a different user.'
                  }
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Helper function to get color based on log type
function getTypeColor(type: string): string {
  switch (type.toLowerCase()) {
    case 'add':
    case 'gain':
    case 'win':
      return '34, 197, 94'; // Green
    case 'remove':
    case 'spend':
    case 'loss':
      return '239, 68, 68'; // Red
    case 'transfer':
      return '59, 130, 246'; // Blue
    default:
      return '168, 162, 158'; // Gray
  }
}

export default Economy; 