import { fetchWithHeaders } from './api';

interface UserData {
  id: string;
  username: string;
  avatar?: string;
  user?: string;
}

// In-memory cache for user data
const userCache: Record<string, UserData> = {};

// Cache expiration time in milliseconds (24 hours)
const CACHE_EXPIRATION = 24 * 60 * 60 * 1000;

// Cache last update timestamps
const cacheTimestamps: Record<string, number> = {};

// Track pending requests to avoid duplicate API calls
const pendingRequests: Record<string, Promise<UserData>> = {};

/**
 * Fetches user data by ID, with caching
 * @param userId The ID of the user to fetch
 * @param forceUpdate Whether to force a fresh fetch, ignoring cache
 * @returns User data from cache or from API
 */
export const fetchUserData = async (userId: string, forceUpdate = false): Promise<UserData> => {
  const now = Date.now();
  
  // Check if we have a valid cached response
  if (
    !forceUpdate && 
    userCache[userId] && 
    cacheTimestamps[userId] && 
    (now - cacheTimestamps[userId]) < CACHE_EXPIRATION
  ) {
    return userCache[userId];
  }
  
  // If we already have a request in progress for this userId, return that promise
  if (userId in pendingRequests) {
    return pendingRequests[userId];
  }
  
  // Create a new promise for this request
  const requestPromise = (async () => {
    try {
      const userData = await fetchWithHeaders(`/user/${userId}`);
      
      // Standardize user data structure
      const normalizedUserData: UserData = {
        id: userId,
        username: userData.username || userData.user || 'Unknown User',
        avatar: userData.avatar,
        user: userData.user
      };
      
      // Update cache
      userCache[userId] = normalizedUserData;
      cacheTimestamps[userId] = now;
      
      return normalizedUserData;
    } catch (error) {
      console.error(`Failed to fetch user data for ${userId}:`, error);
      
      // Return cached data if available, even if expired
      if (userCache[userId]) {
        return userCache[userId];
      }
      
      // Return a placeholder if no data available
      return {
        id: userId,
        username: userId,
      };
    } finally {
      // Remove from pending requests
      delete pendingRequests[userId];
    }
  })();
  
  // Store the promise
  pendingRequests[userId] = requestPromise;
  
  return requestPromise;
};

/**
 * Fetches user data for multiple user IDs in parallel, with caching
 * @param userIds Array of user IDs to fetch
 * @param forceUpdate Whether to force fresh fetches, ignoring cache
 * @returns A map of user ID to user data
 */
export const fetchMultipleUserData = async (
  userIds: string[], 
  forceUpdate = false
): Promise<Record<string, UserData>> => {
  // If no user IDs to fetch, return an empty object immediately
  if (userIds.length === 0) {
    return {};
  }
  
  const uniqueUserIds = [...new Set(userIds)];
  const result: Record<string, UserData> = {};
  
  // Use Promise.all to fetch all user data in parallel
  await Promise.all(
    uniqueUserIds.map(async (userId) => {
      const userData = await fetchUserData(userId, forceUpdate);
      result[userId] = userData;
    })
  );
  
  return result;
};

/**
 * Clears the user cache
 */
export const clearUserCache = (): void => {
  Object.keys(userCache).forEach(key => {
    delete userCache[key];
    delete cacheTimestamps[key];
  });
};

/**
 * Gets the current cache state for debugging
 */
export const getUserCacheStats = (): { size: number, entries: string[] } => {
  return {
    size: Object.keys(userCache).length,
    entries: Object.keys(userCache)
  };
};

/**
 * Gets a username from cache or returns the user ID if not found
 */
export const getUsernameFromCache = (userId: string): string => {
  return userCache[userId]?.username || userId;
}; 