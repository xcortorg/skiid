import React, { useState, useEffect } from 'react';
import { User, Clock, AlertCircle, RefreshCw, ArrowLeft, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react';
import { useParams, Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { usePageTitle } from '../hooks/usePageTitle';

interface Avatar {
  avatar: string;
  timestamp: number;
  user_id: string;
}

interface UserData {
  activity?: {
    details: string;
    emoji: string;
    image: string;
    name: string;
    state: string | null;
  };
  avatar: string;
  banner: string | null;
  banner_color?: string;
  user: string;
}

function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString();
}

function Pagination({ 
  currentPage, 
  totalPages, 
  onPageChange 
}: { 
  currentPage: number; 
  totalPages: number; 
  onPageChange: (page: number) => void 
}) {
  return (
    <div className="flex justify-center items-center mt-8 gap-2">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="p-2 rounded-lg bg-dark-2 text-gray-400 hover:bg-dark-1 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <ChevronLeft className="w-5 h-5" />
      </button>
      
      <div className="px-4 py-2 bg-dark-2 rounded-lg">
        <span className="text-gray-400">
          Page {currentPage} of {totalPages}
        </span>
      </div>
      
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="p-2 rounded-lg bg-dark-2 text-gray-400 hover:bg-dark-1 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <ChevronRight className="w-5 h-5" />
      </button>
    </div>
  );
}

function UserAvatars() {
  usePageTitle(); // Add page title hook
  const { userId } = useParams<{ userId: string }>();
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [userData, setUserData] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const itemsPerPage = 100;

  useEffect(() => {
    const fetchUserData = async (userId: string) => {
      try {
        const response = await fetch(`/api/user/${userId}`);
        if (!response.ok) {
          console.warn(`Failed to fetch user data: ${response.status}`);
          return null; // Return null instead of throwing an error
        }
        const data = await response.json();
        setUserData(data);
      } catch (error) {
        console.error('Error fetching user data:', error);
        // Don't set error state for user data - just log it
      }
    };

    const fetchUserAvatars = async () => {
      if (!userId) return;
      
      try {
        setLoading(true);
        setError(null);
        
        // Fetch user data and avatars in parallel
        await Promise.all([
          fetchUserData(userId),
          fetch(`/api/avatars/${userId}`)
            .then(async (avatarsResponse) => {
              // Handle different response statuses for avatars
              if (avatarsResponse.status === 404) {
                setAvatars([]);
                return;
              }
              
              if (!avatarsResponse.ok) {
                throw new Error(`Failed to fetch user avatars: ${avatarsResponse.status} ${avatarsResponse.statusText}`);
              }
              
              let data;
              try {
                data = await avatarsResponse.json();
              } catch (parseError) {
                console.error('Error parsing JSON response:', parseError);
                setAvatars([]);
                return;
              }
              
              // Check if data is valid
              if (!Array.isArray(data)) {
                console.warn('Invalid data format received:', data);
                setAvatars([]);
              } else {
                // Sort avatars by timestamp in descending order (newest first)
                const sortedData = [...data].sort((a, b) => b.timestamp - a.timestamp);
                
                // Calculate total pages
                const calculatedTotalPages = Math.ceil(sortedData.length / itemsPerPage);
                setTotalPages(calculatedTotalPages > 0 ? calculatedTotalPages : 1);
                
                setAvatars(sortedData);
              }
            })
            .catch(err => {
              console.error('Error fetching user avatars:', err);
              // Don't set error state for 404s or empty arrays - just show "No Avatars Found"
              if (err instanceof Error && err.message.includes('404')) {
                setAvatars([]);
              } else {
                setError('Failed to load avatars for this user. Please try again later.');
              }
            })
        ]);
      } catch (err) {
        console.error('Error in fetchUserAvatars:', err);
        setError('Failed to load data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchUserAvatars();
  }, [userId, itemsPerPage]);

  // Get current page items
  const getCurrentPageItems = () => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return avatars.slice(startIndex, endIndex);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    // Scroll to top when changing pages
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <PageHeader
          icon={<User />}
          title="Avatar History"
          description={`Loading avatar history for User ID: ${userId}`}
        />
        <div className="flex justify-center items-center py-12">
          <div className="w-12 h-12 border-4 border-theme border-t-transparent rounded-full animate-spin"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <PageHeader
          icon={<User />}
          title="Avatar History"
          description={`Error loading avatar history for User ID: ${userId}`}
        />
        
        <div className="mb-8 p-6 bg-red-500/10 border border-red-500/20 rounded-lg">
          <div className="flex items-center gap-3 text-red-400 mb-2">
            <AlertCircle className="w-5 h-5" />
            <h3 className="font-semibold">Error</h3>
          </div>
          <p className="text-gray-400">{error}</p>
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
              onClick={() => window.location.reload()}
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

  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<User />}
        title="Avatar History"
        description={`Viewing avatar history for ${userData?.user || `User ID: ${userId}`}`}
      />

      <div className="mb-8">
        <Link
          to="/avatars"
          className="inline-flex items-center gap-2 text-theme hover:text-theme/80 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to All Avatars
        </Link>
      </div>

      {/* User Info Card - only render if userData exists */}
      {userData && (
        <div className="feature-card rounded-lg p-6 mb-8">
          <div className="flex items-center gap-6">
            {userData.avatar ? (
              <img 
                src={userData.avatar}
                alt={userData.user || 'User avatar'}
                className="w-16 h-16 rounded-full"
              />
            ) : (
              <div className="w-16 h-16 bg-dark-2 rounded-full flex items-center justify-center">
                <User className="w-8 h-8 text-gray-600" />
              </div>
            )}
            <div>
              {userData.user ? (
                <>
                  <h2 className="text-xl font-bold">{userData.user}</h2>
                  <p className="text-gray-400">{userId}</p>
                </>
              ) : (
                <>
                  <h2 className="text-xl font-bold">User ID</h2>
                  <p className="text-gray-400">{userId}</p>
                </>
              )}
            </div>
          </div>
          
          {userData.activity && (
            <div className="mt-4 p-3 bg-dark-2 rounded-lg">
              <div className="flex items-center gap-2 text-gray-300">
                {userData.activity.emoji && (
                  <img 
                    src={userData.activity.emoji} 
                    alt="activity"
                    className="w-4 h-4"
                  />
                )}
                {userData.activity.image && (
                  <img 
                    src={userData.activity.image} 
                    alt="app"
                    className="w-5 h-5 rounded"
                  />
                )}
                <span className="font-medium">{userData.activity.name}</span>
              </div>
              
              {(userData.activity.details || userData.activity.state) && (
                <div className="mt-2 text-sm text-gray-400">
                  {userData.activity.details && <div>{userData.activity.details}</div>}
                  {userData.activity.state && <div>{userData.activity.state}</div>}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {avatars.length === 0 ? (
        <div className="feature-card rounded-lg p-6 text-center">
          <User className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">No Avatars Found</h3>
          <p className="text-gray-400">This user has no avatar history available.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-6 gap-4">
            {getCurrentPageItems().map((avatar, index) => (
              <div key={index} className="feature-card rounded-lg overflow-hidden">
                <div className="relative group">
                  <img
                    src={`https://cdn.evelina.bot/avatars/${avatar.avatar}`}
                    alt={`Avatar ${index + 1}`}
                    className="w-full aspect-square object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "https://r.emogir.ls/evelina-pfp.png";
                    }}
                  />
                  <a 
                    href={`https://cdn.evelina.bot/avatars/${avatar.avatar}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="absolute top-2 right-2 p-2 bg-dark-2/80 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                    title="Open in new tab"
                  >
                    <ExternalLink className="w-4 h-4 text-white" />
                  </a>
                </div>
                <div className="p-4">
                  <div className="flex items-center gap-2 text-gray-400 text-sm">
                    <Clock className="w-4 h-4" />
                    <span>{formatTimestamp(avatar.timestamp)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {avatars.length > itemsPerPage && (
            <Pagination 
              currentPage={currentPage} 
              totalPages={totalPages} 
              onPageChange={handlePageChange} 
            />
          )}
        </>
      )}
    </div>
  );
}

export default UserAvatars;