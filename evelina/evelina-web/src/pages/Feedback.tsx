import React, { useState, useEffect } from 'react';
import { MessageSquare, AlertCircle, ThumbsUp, RefreshCw, ChevronDown } from 'lucide-react';
import PageHeader from '../components/PageHeader';

interface FeedbackItem {
  approved: boolean;
  feedback: string;
  user_id: string;
  message_id?: number;
  user_data?: {
    avatar: string;
    user: string;
  };
}

const MAX_RETRIES = 3;

// Cache für Benutzerdaten, um wiederholte API-Aufrufe zu vermeiden
const userDataCache: Record<string, {data: any, timestamp: number}> = {};
const CACHE_EXPIRY = 30 * 60 * 1000; // 30 Minuten Cache-Gültigkeit

function Feedback() {
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const fetchWithRetry = async (url: string, retries = MAX_RETRIES): Promise<any> => {
    try {
      const response = await fetch(url, {
        headers: {
          'X-API-Key': 'loveskei'
        }
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      if (retries > 0) {
        await delay(1000);
        return fetchWithRetry(url, retries - 1);
      }
      throw error;
    }
  };

  const fetchUserData = async (userId: string) => {
    try {
      // Prüfe ob gültige gecachte Daten vorhanden sind
      const cachedData = userDataCache[userId];
      if (cachedData && Date.now() - cachedData.timestamp < CACHE_EXPIRY) {
        console.log(`Using cached user data for ${userId}`);
        return cachedData.data;
      }
      
      // Wenn nicht im Cache oder abgelaufen, vom Server holen
      console.log(`Fetching user data for ${userId}`);
      const userData = await fetchWithRetry(`/api/user/${userId}`);
      
      // Im Cache speichern
      userDataCache[userId] = {
        data: userData,
        timestamp: Date.now()
      };
      
      return userData;
    } catch (error) {
      console.warn(`Failed to fetch user data for ${userId}:`, error);
      return null;
    }
  };

  const fetchAllFeedback = async () => {
    try {
      setError(null);
  
      // Feedback-Daten abrufen
      const feedbackResponse = await fetchWithRetry('/api/feedback');
      if (!feedbackResponse) throw new Error('Failed to fetch feedback');
  
      // Nur genehmigtes Feedback filtern und nach message_id absteigend sortieren
      const approvedFeedback = feedbackResponse
        .filter((item: FeedbackItem) => item.approved)
        .sort((a: any, b: any) => Number(b.message_id) - Number(a.message_id));
  
      // Verarbeite alle Feedback-Elemente parallel
      const processedItems = await Promise.all(
        approvedFeedback.map(async (item: FeedbackItem) => {
          const userData = await fetchUserData(item.user_id);
          return {
            ...item,
            user_data: userData
          };
        })
      );
  
      setFeedback(processedItems);
      return processedItems;
    } catch (err) {
      console.error('Error fetching feedback:', err);
      setError('Unable to fetch feedback, please try again later or join our support server for assistance.');
      return [];
    }
  };  

  useEffect(() => {
    const loadFeedback = async () => {
      setLoading(true);
      await fetchAllFeedback();
      setLoading(false);
    };

    loadFeedback();
  }, [retryCount]);

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    setRetryCount(prev => prev + 1);
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <PageHeader
          icon={<MessageSquare />}
          title="Community Feedback"
          description="See what our users are saying about Evelina"
        />

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={`skeleton-${i}`} className="feature-card rounded-lg p-6 flex flex-col min-h-[300px]">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 bg-dark-2 rounded-full"></div>
                <div className="flex-1">
                  <div className="h-5 bg-dark-2 rounded w-32 mb-2"></div>
                </div>
                <div className="bg-green-500/20 h-7 px-3 rounded text-sm w-24"></div>
              </div>

              <div className="space-y-2 flex-1">
                <div className="h-4 bg-dark-2 rounded w-full"></div>
                <div className="h-4 bg-dark-2 rounded w-3/4"></div>
                <div className="h-4 bg-dark-2 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <PageHeader
          icon={<MessageSquare />}
          title="Community Feedback"
          description="See what our users are saying about Evelina"
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

  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<MessageSquare />}
        title="Community Feedback"
        description="See what our users are saying about Evelina"
      />

      {feedback.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <MessageSquare className="w-12 h-12 text-gray-400 mb-4" />
          <h3 className="text-xl font-semibold mb-2">No Feedback Yet</h3>
          <p className="text-gray-400">Be the first to share your experience with Evelina!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {feedback.map((item) => (
            <div key={`feedback-${item.user_id}-${item.message_id || Math.random()}`} className="feature-card rounded-lg p-6 flex flex-col min-h-[300px]">
              <div className="flex items-center gap-4 mb-6">
                {item.user_data?.avatar ? (
                  <img
                    src={item.user_data.avatar}
                    alt={item.user_data.user}
                    className="w-12 h-12 rounded-full"
                  />
                ) : (
                  <div className="w-12 h-12 bg-dark-2 rounded-full flex items-center justify-center">
                    <MessageSquare className="w-6 h-6 text-gray-600" />
                  </div>
                )}
                <div className="flex-1">
                  <h3 className="font-semibold">
                    {item.user_data?.user || 'Unknown User'}
                  </h3>
                </div>
                <div className="bg-green-500/20 text-green-400 px-2 py-1 rounded text-sm flex items-center gap-1">
                  <ThumbsUp className="w-4 h-4" />
                  Approved
                </div>
              </div>

              <div className="flex-1">
                <p className="text-gray-300">{item.feedback}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Feedback;