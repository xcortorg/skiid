import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuthStore } from '../../lib/authStore';
import { useTeamStore } from '../../lib/teamStore';
import PageHeader from '../../components/PageHeader';
import { LayoutDashboard, Users, BarChart, ChevronRight } from 'lucide-react';
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
} from 'chart.js';
import 'chartjs-adapter-date-fns';
import { format, subDays } from 'date-fns';
import { fetchWithHeaders } from '../../lib/api';
import { fetchMultipleUserData, getUsernameFromCache } from '../../lib/userCache';
import LoadingSpinner from '../../components/LoadingSpinner';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

// Types for our data
interface TeamMember {
  rank: string;
  socials: string;
  user_id: string;
  username: string | null;
}

interface ActivityMessage {
  user_id: string;
  message_date: string;
  total_messages: number;
}

type TimeRange = '7d' | '14d' | '30d' | 'all';

// Function to generate random colors for team members
const generateColor = (index: number) => {
  const colors = [
    '#FF6384', // red
    '#36A2EB', // blue
    '#FFCE56', // yellow
    '#4BC0C0', // teal
    '#9966FF', // purple
    '#FF9F40', // orange
    '#7FD8BE', // mint
    '#FB5607', // dark orange
    '#8338EC', // violet
    '#3A86FF', // royal blue
    '#EFBDEB', // light pink
    '#06D6A0', // green
  ];

  return colors[index % colors.length];
};

const StaffOverview: React.FC = () => {
  const { user } = useAuthStore();
  const { members, isLoading: teamLoading, fetchTeamMembers } = useTeamStore();
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');
  const [activityData, setActivityData] = useState<ActivityMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLoadingUsernames, setIsLoadingUsernames] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch team members only once when component mounts
  useEffect(() => {
    if (members.length === 0 && !teamLoading) {
      fetchTeamMembers();
    }
  }, [members.length, teamLoading, fetchTeamMembers]);

  // Get all unique ranks
  const uniqueRanks = useMemo(() => {
    if (!members.length) return [];
    const ranks = [...new Set(members.map(member => member.rank))];
    return ranks.sort(); // Sort ranks alphabetically
  }, [members]);

  // Load user data from API with caching
  const loadUserData = useCallback(async (userIds: string[]) => {
    if (!userIds.length) return;
    
    setIsLoadingUsernames(true);
    try {
      await fetchMultipleUserData(userIds);
    } catch (err) {
      console.error('Error fetching user data:', err);
    } finally {
      setIsLoadingUsernames(false);
    }
  }, []);

  // Pre-load team member user data when members are loaded
  useEffect(() => {
    if (members.length > 0) {
      // Create a set to track which user IDs we need to fetch
      const userIdsToFetch = new Set<string>();
      
      // Only fetch users that aren't already in the cache
      members.forEach(member => {
        const cachedName = getUsernameFromCache(member.user_id);
        if (cachedName === member.user_id) {
          userIdsToFetch.add(member.user_id);
        }
      });
      
      if (userIdsToFetch.size > 0) {
        loadUserData(Array.from(userIdsToFetch));
      }
    }
  }, [members, loadUserData]);

  // Memoize the fetchActivityData function to prevent recreation on every render
  const fetchActivityData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const endpoint = `/activity/messages?server_id=1228371886690537624&time_range=${timeRange}`;
      const data = await fetchWithHeaders(endpoint);
      
      // Filter activity data to only include team members
      const teamUserIds = new Set(members.map(member => member.user_id));
      const filteredData = data.filter((item: ActivityMessage) => teamUserIds.has(item.user_id));
      
      setActivityData(filteredData);
      
      // Extract all user IDs from the filtered activity data that aren't already in the cache
      const userIdsToFetch = new Set<string>();
      filteredData.forEach((item: ActivityMessage) => {
        const cachedName = getUsernameFromCache(item.user_id);
        if (cachedName === item.user_id) {
          userIdsToFetch.add(item.user_id);
        }
      });
      
      if (userIdsToFetch.size > 0) {
        loadUserData(Array.from(userIdsToFetch));
      }
    } catch (err) {
      console.error('Error fetching activity data:', err);
      setError('Failed to fetch activity data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [timeRange, loadUserData, members]);

  // Fetch activity data only when timeRange changes or fetchActivityData function changes
  useEffect(() => {
    fetchActivityData();
  }, [fetchActivityData]);

  // Get display name for a user ID using the cache
  const getDisplayName = useCallback((userId: string) => {
    // First check if we have the username in the userCache
    const cachedName = getUsernameFromCache(userId);
    if (cachedName !== userId) {
      return cachedName;
    }
    
    // Otherwise check if we have the username in the members list
    const memberWithId = members.find(member => member.user_id === userId);
    if (memberWithId?.username) {
      return memberWithId.username;
    }
    
    // If all else fails, return the user ID
    return userId;
  }, [members]);

  // Prepare data for chart grouped by rank
  const prepareChartDataByRank = (rank: string) => {
    if (!members.length || !activityData.length) {
      return {
        labels: [],
        datasets: [],
      };
    }

    // Get all unique dates from the activity data
    const allDates = [...new Set(activityData.map(item => item.message_date))].sort();
    
    // Filter members by rank
    const rankMembers = members.filter(member => member.rank === rank);
    
    // Create datasets for each team member of this rank
    const datasets = rankMembers.map((member, index) => {
      // Filter activity data for this member
      const memberData = activityData.filter(item => item.user_id === member.user_id);
      
      // Map all dates, use 0 for dates without activity
      const dataPoints = allDates.map(date => {
        const entry = memberData.find(item => item.message_date === date);
        return entry ? entry.total_messages : 0;
      });

      const color = generateColor(index);
      
      // Use the display name instead of user ID
      const displayName = getDisplayName(member.user_id);
      
      return {
        label: displayName,
        data: dataPoints,
        borderColor: color,
        backgroundColor: `${color}33`, // Add transparency
        fill: false,
        tension: 0.1,
        borderWidth: 3,
        pointRadius: 4,
        pointHoverRadius: 6,
      };
    });

    return {
      labels: allDates.map(date => format(new Date(date), 'MMM dd, yyyy')),
      datasets,
    };
  };

  // Chart options with modern styling
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    layout: {
      padding: {
        top: 5,
        right: 20,
        bottom: 5,
        left: 5
      }
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Date',
          font: {
            size: 14,
            weight: 'bold' as const
          }
        },
        grid: {
          display: true,
          color: 'rgba(255, 255, 255, 0.05)'
        },
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)'
        }
      },
      y: {
        title: {
          display: true,
          text: 'Message Count',
          font: {
            size: 14,
            weight: 'bold' as const
          }
        },
        beginAtZero: true,
        grid: {
          display: true,
          color: 'rgba(255, 255, 255, 0.05)'
        },
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)'
        }
      },
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          boxWidth: 15,
          usePointStyle: true,
          pointStyle: 'circle',
          padding: 15,
          color: 'rgba(255, 255, 255, 0.8)'
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'rgba(255, 255, 255, 1)',
        bodyColor: 'rgba(255, 255, 255, 0.8)',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        displayColors: true,
        usePointStyle: true,
        callbacks: {
          label: function(context: any) {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            return `${label}: ${value} messages`;
          }
        }
      }
    },
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    hover: {
      mode: 'nearest' as const,
      intersect: true
    }
  };

  return (
    <div className="flex flex-col">
      <div className="p-6">
        <PageHeader
          icon={<LayoutDashboard />}
          title="Overview"
          description={`Welcome back, ${user?.username || 'User'}, here you can see the overview of the staff team.`}
        />

        {/* Time range selector */}
        <div className="mb-6 mt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart className="w-6 h-6 text-theme" />
              <h2 className="text-xl font-semibold">Team Activity</h2>
            </div>
            <div className="flex bg-[#1d1d1d] p-1 rounded-lg">
              <button
                onClick={() => setTimeRange('7d')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  timeRange === '7d'
                    ? 'bg-theme text-white shadow-md'
                    : 'text-gray-300 hover:text-white hover:bg-[#2a2a2a]'
                }`}
              >
                7 days
              </button>
              <button
                onClick={() => setTimeRange('14d')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  timeRange === '14d'
                    ? 'bg-theme text-white shadow-md'
                    : 'text-gray-300 hover:text-white hover:bg-[#2a2a2a]'
                }`}
              >
                14 days
              </button>
              <button
                onClick={() => setTimeRange('30d')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  timeRange === '30d'
                    ? 'bg-theme text-white shadow-md'
                    : 'text-gray-300 hover:text-white hover:bg-[#2a2a2a]'
                }`}
              >
                30 days
              </button>
              <button
                onClick={() => setTimeRange('all')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  timeRange === 'all'
                    ? 'bg-theme text-white shadow-md'
                    : 'text-gray-300 hover:text-white hover:bg-[#2a2a2a]'
                }`}
              >
                All time
              </button>
            </div>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-500 p-4 rounded-xl mb-6">
            {error}
          </div>
        )}

        {/* Loading state */}
        {(isLoading || teamLoading) && (
          <div className="flex items-center justify-center h-[400px] bg-[#161616] rounded-xl p-6 mb-6">
            <LoadingSpinner 
              size="lg" 
              message="Loading activity data..." 
            />
          </div>
        )}

        {/* No data state */}
        {!isLoading && !teamLoading && activityData.length === 0 && (
          <div className="flex flex-col items-center justify-center h-[400px] text-center bg-[#161616] rounded-xl p-6 mb-6">
            <Users className="w-12 h-12 text-gray-500 mb-4" />
            <h3 className="text-lg font-medium mb-2">No Activity Data Available</h3>
            <p className="text-gray-400 max-w-md">
              There is no message activity data available for the selected time range.
            </p>
          </div>
        )}

        {/* Charts separated by rank */}
        {!isLoading && !teamLoading && activityData.length > 0 && (
          <div className="space-y-6">
            {isLoadingUsernames && (
              <div className="flex justify-center py-2 mb-4">
                <LoadingSpinner 
                  size="sm" 
                  message="Loading user information..." 
                />
              </div>
            )}
            
            {uniqueRanks.map((rank) => {
              const rankMembers = members.filter(member => member.rank === rank);
              // Only show charts for ranks that have members with activity
              const hasActivity = rankMembers.some(member => 
                activityData.some(item => item.user_id === member.user_id)
              );
              
              if (!hasActivity) return null;

              return (
                <div key={rank} className="bg-[#161616] rounded-xl p-6 shadow-lg">
                  <div className="flex items-center gap-2 mb-4">
                    <ChevronRight className="w-5 h-5 text-theme" />
                    <h3 className="text-lg font-semibold text-white">{rank}</h3>
                    <span className="text-xs bg-[#232323] px-2 py-1 rounded text-gray-400">
                      {rankMembers.length} {rankMembers.length === 1 ? 'member' : 'members'}
                    </span>
                  </div>
                  <div className="h-[350px]">
                    <Line data={prepareChartDataByRank(rank)} options={chartOptions} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default StaffOverview; 