import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface User {
  id: string;
  username: string;
  email: string;
  avatar: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: () => void;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
  setUser: (user: User | null) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: () => {
        // Redirect to Discord OAuth login endpoint using frontend route
        window.location.href = '/api/auth/discord';
      },

      logout: async () => {
        try {
          set({ isLoading: true });
          const response = await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include'
          });

          if (response.ok) {
            set({ user: null, isAuthenticated: false });
          } else {
            const data = await response.json();
            set({ error: data.error || 'Logout failed' });
          }
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Logout failed' });
        } finally {
          set({ isLoading: false });
        }
      },

      fetchUser: async () => {
        try {
          set({ isLoading: true, error: null });
          const response = await fetch('/api/auth/me', {
            credentials: 'include'
          });

          if (response.ok) {
            const user = await response.json();
            set({ user, isAuthenticated: true });
          } else if (response.status === 401) {
            // Not authenticated
            set({ user: null, isAuthenticated: false });
          } else {
            const data = await response.json();
            set({ error: data.error || 'Failed to fetch user' });
          }
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to fetch user' });
        } finally {
          set({ isLoading: false });
        }
      },

      setUser: (user) => {
        set({ user, isAuthenticated: !!user });
      },

      setError: (error) => {
        set({ error });
      },

      clearError: () => {
        set({ error: null });
      }
    }),
    {
      name: 'auth-storage',
      // Don't persist sensitive data as users' token is stored in an HTTP-only cookie
      partialize: (state) => ({ isAuthenticated: state.isAuthenticated })
    }
  )
); 