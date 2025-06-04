import React, { useState, useEffect } from 'react';
import { Search, User, Clock, AlertCircle, RefreshCw, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { usePageTitle } from '../hooks/usePageTitle';

interface Avatar {
  avatar: string;
  timestamp: number;
  user_id: string;
}

function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString();
}

function AvatarGrid({ avatars }: { avatars: Avatar[] }) {
  if (!avatars.length) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">No avatars found.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-6 gap-4">
      {avatars.map((avatar, index) => (
        <div key={`${avatar.user_id}-${index}`} className="feature-card rounded-lg overflow-hidden">
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
            <div className="flex items-center justify-between mb-2">
              <div className="flex flex-col">
                <span className="text-xs text-gray-400">{avatar.user_id}</span>
              </div>
            </div>
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <Clock className="w-4 h-4" />
              <span>{formatTimestamp(avatar.timestamp)}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
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

function AvatarsPage() {
  usePageTitle(); // Add page title hook
  const [searchTerm, setSearchTerm] = useState('');
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const itemsPerPage = 100;
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/avatars/${searchTerm.trim()}`);
    }
  };

  useEffect(() => {
    const fetchAvatars = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch('/api/avatars');
        if (!response.ok) {
          throw new Error(`Failed to fetch avatars: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Validate data
        if (!Array.isArray(data)) {
          console.warn('Invalid data format received:', data);
          throw new Error('Invalid data format received from server');
        }
        
        // Sort avatars by timestamp in descending order (newest first)
        const sortedData = [...data].sort((a, b) => b.timestamp - a.timestamp);
        
        // Calculate total pages
        const calculatedTotalPages = Math.ceil(sortedData.length / itemsPerPage);
        setTotalPages(calculatedTotalPages > 0 ? calculatedTotalPages : 1);
        
        setAvatars(sortedData);
      } catch (err) {
        console.error('Error fetching avatars:', err);
        setError('Failed to load avatars. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchAvatars();
  }, []);

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
          description="Browse avatar history for Discord users"
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
          description="Browse avatar history for Discord users"
        />
        <div className="feature-card rounded-lg p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">Error Loading Avatars</h3>
          <p className="text-gray-400 mb-6">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-theme hover:bg-theme/80 text-white rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<User />}
        title="Avatar History"
        description="Browse avatar history for Discord users"
      />

      <div className="mb-8">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search users..."
              className="w-full pl-10 pr-4 py-2 bg-[#111] rounded-lg text-white placeholder-gray-400 focus:outline-none border border-[rgba(114,155,176,0.1)]"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-[#111] hover:bg-[#191919] text-white rounded-lg transition-colors border border-[rgba(114,155,176,0.1)]"
          >
            Search
          </button>
        </form>
      </div>

      <AvatarGrid avatars={getCurrentPageItems()} />
      
      {avatars.length > 0 && (
        <Pagination 
          currentPage={currentPage} 
          totalPages={totalPages} 
          onPageChange={handlePageChange} 
        />
      )}
    </div>
  );
}

export default AvatarsPage;