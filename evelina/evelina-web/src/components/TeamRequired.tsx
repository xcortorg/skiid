import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../lib/authStore';
import { useTeamStore } from '../lib/teamStore';

interface TeamRequiredProps {
  children: React.ReactNode;
  redirectTo?: string;
}

const TeamRequired: React.FC<TeamRequiredProps> = ({ 
  children, 
  redirectTo = '/' 
}) => {
  const location = useLocation();
  const { user, isAuthenticated, isLoading: authLoading, fetchUser } = useAuthStore();
  const { 
    fetchTeamMembers, 
    isUserInTeam, 
    members, 
    isLoading: teamLoading,
    isFetched
  } = useTeamStore();
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);

  // On initial mount, always fetch user to ensure we have the latest data
  useEffect(() => {
    const initialize = async () => {
      await fetchUser();
      setInitialLoadComplete(true);
    };
    
    initialize();
  }, [fetchUser]);

  // Fetch team members if user is authenticated
  useEffect(() => {
    if (isAuthenticated && !isFetched && !teamLoading) {
      fetchTeamMembers();
    }
  }, [isAuthenticated, isFetched, teamLoading, fetchTeamMembers]);

  // Display loading spinner before initial loading is complete
  if (!initialLoadComplete || authLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-theme"></div>
      </div>
    );
  }

  // After initial loading, check if user is authenticated
  if (!isAuthenticated || !user) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  // If team data is still loading and user is authenticated, show loading spinner
  if (teamLoading || members.length === 0) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-theme"></div>
      </div>
    );
  }

  // Check if the logged-in user is in the team
  const isTeamMember = isUserInTeam(user.id);
  
  // If not a team member, redirect to homepage
  if (!isTeamMember) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  // If the user is in the team, show the children
  return <>{children}</>;
};

export default TeamRequired; 