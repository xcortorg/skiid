import { create } from 'zustand';

export interface TeamMember {
  rank: string;
  socials: string;
  user_id: string;
  username: string | null;
}

interface TeamState {
  members: TeamMember[];
  isLoading: boolean;
  error: string | null;
  isFetched: boolean;
  
  // Actions
  fetchTeamMembers: () => Promise<void>;
  isUserInTeam: (userId: string) => boolean;
  getUserRank: (userId: string) => string | null;
}

export const useTeamStore = create<TeamState>((set, get) => ({
  members: [],
  isLoading: false,
  error: null,
  isFetched: false,

  fetchTeamMembers: async () => {
    // Only fetch if not already loading and not already fetched
    const { isLoading, isFetched } = get();
    if (isLoading || isFetched) return;
    
    try {
      set({ isLoading: true, error: null });
      const response = await fetch('/api/team');

      if (response.ok) {
        const members = await response.json();
        set({ members, isLoading: false, isFetched: true });
      } else {
        const errorData = await response.json();
        set({ error: errorData.error || 'Failed to fetch team members', isLoading: false });
      }
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch team members', 
        isLoading: false 
      });
    }
  },

  isUserInTeam: (userId: string) => {
    const { members } = get();
    return members.some(member => member.user_id === userId);
  },

  getUserRank: (userId: string) => {
    const { members } = get();
    const member = members.find(member => member.user_id === userId);
    return member ? member.rank : null;
  }
})); 