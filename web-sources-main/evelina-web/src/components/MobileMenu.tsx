import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X, Bot, Home, Terminal, Circle, Code, ExternalLink, Activity, Users, Shield, MessageSquare, UserPlus, Music, Coins, Crown, Gift, ChevronDown, Mic2, Tag, Star, Book, Settings, Bell } from 'lucide-react';
import { useAuthStore } from '../lib/authStore';
import { useNavigate } from 'react-router-dom';
import { useTeamStore } from '../lib/teamStore';

interface MobileMenuProps {
  isOpen: boolean;
  onClose: () => void;
}

function MobileMenu({ isOpen, onClose }: MobileMenuProps) {
  const [featuresOpen, setFeaturesOpen] = useState(false);
  const [informationOpen, setInformationOpen] = useState(false);
  const { login, logout, isAuthenticated, isLoading, user } = useAuthStore();
  const { isUserInTeam } = useTeamStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    onClose();
    navigate('/');
  };

  // Check if user is a team member
  const isTeamMember = user ? isUserInTeam(user.id) : false;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 w-[90%] max-w-md max-h-[90vh] overflow-y-auto bg-[#1a1a1a] p-6 shadow-xl rounded-lg">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2">
            <img 
              src="https://r.emogir.ls/evelina-pfp.png" 
              alt="Evelina" 
              className="w-10 h-10 rounded-full"
            />
            <span className="font-bold text-xl">Evelina</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="space-y-6">
          {/* Features Dropdown */}
          <div>
            <button
              onClick={() => setFeaturesOpen(!featuresOpen)}
              className="flex items-center justify-between w-full text-sm font-medium text-gray-400 mb-2"
            >
              <span>Features</span>
              <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${featuresOpen ? 'rotate-180' : ''}`} />
            </button>
            <div className={`grid grid-cols-3 gap-2 transition-all duration-200 ${
              featuresOpen ? 'opacity-100 max-h-[500px]' : 'opacity-0 max-h-0 overflow-hidden'
            }`}>
              <Link
                to="/features/automod"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Shield className="w-6 h-6" />
                <span className="text-sm text-center">Auto Mod</span>
              </Link>
              <Link
                to="/features/tickets"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <MessageSquare className="w-6 h-6" />
                <span className="text-sm text-center">Tickets</span>
              </Link>
              <Link
                to="/features/welcome"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <UserPlus className="w-6 h-6" />
                <span className="text-sm text-center">Welcome</span>
              </Link>
              <Link
                to="/features/music"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Music className="w-6 h-6" />
                <span className="text-sm text-center">Music</span>
              </Link>
              <Link
                to="/features/economy"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Coins className="w-6 h-6" />
                <span className="text-sm text-center">Economy</span>
              </Link>
              <Link
                to="/features/giveaways"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Gift className="w-6 h-6" />
                <span className="text-sm text-center">Giveaways</span>
              </Link>
              <Link
                to="/features/voicemaster"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Mic2 className="w-6 h-6" />
                <span className="text-sm text-center">Voice Master</span>
              </Link>
              <Link
                to="/features/vanityroles"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Crown className="w-6 h-6" />
                <span className="text-sm text-center">Vanity Roles</span>
              </Link>
              <Link
                to="/features/buttonroles"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Tag className="w-6 h-6" />
                <span className="text-sm text-center">Button Roles</span>
              </Link>
              <Link
                to="/features/leveling"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Star className="w-6 h-6" />
                <span className="text-sm text-center">Leveling</span>
              </Link>
              <Link
                to="/features/bump"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Bell className="w-6 h-6" />
                <span className="text-sm text-center">Bump</span>
              </Link>
              <Link
                to="/avatars"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Users className="w-6 h-6" />
                <span className="text-sm text-center">Avatars</span>
              </Link>
            </div>
          </div>

          {/* Information Dropdown */}
          <div>
            <button
              onClick={() => setInformationOpen(!informationOpen)}
              className="flex items-center justify-between w-full text-sm font-medium text-gray-400 mb-2"
            >
              <span>Information</span>
              <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${informationOpen ? 'rotate-180' : ''}`} />
            </button>
            <div className={`grid grid-cols-2 gap-2 transition-all duration-200 ${
              informationOpen ? 'opacity-100 max-h-96' : 'opacity-0 max-h-0 overflow-hidden'
            }`}>
              <Link
                to="/embed"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Code className="w-6 h-6" />
                <span className="text-sm text-center">Embed Builder</span>
              </Link>
              <Link
                to="/templates"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Code className="w-6 h-6" />
                <span className="text-sm text-center">Templates</span>
              </Link>
              <a
                href="https://docs.evelina.bot"
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Book className="w-6 h-6" />
                <span className="text-sm text-center">Documentation</span>
              </a>
              <Link
                to="/team"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Users className="w-6 h-6" />
                <span className="text-sm text-center">Team</span>
              </Link>
              <Link
                to="/feedback"
                className="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <MessageSquare className="w-6 h-6" />
                <span className="text-sm text-center">Feedback</span>
              </Link>
            </div>
          </div>

          {/* Navigation Links */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 mb-2">Navigation</h3>
            <nav className="space-y-2">
              <Link
                to="/commands"
                className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Terminal className="w-5 h-5" />
                Commands
              </Link>
              <Link
                to="/status"
                className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-black/20 text-gray-300 hover:text-white transition-colors"
                onClick={onClose}
              >
                <Activity className="w-5 h-5" />
                Status
              </Link>
            </nav>
          </div>

          {/* Auth Section */}
          <div className="pt-4 border-t border-gray-800">
            {isLoading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-theme border-t-transparent"></div>
                <span className="ml-2 text-sm text-gray-400">Loading...</span>
              </div>
            ) : isAuthenticated && user ? (
              <div className="space-y-3">
                <div className="flex items-center space-x-3 mb-2">
                  <img 
                    src={`https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`} 
                    alt={user.username}
                    className="w-8 h-8 rounded-full"
                  />
                  <span className="text-sm font-medium">{user.username}</span>
                </div>

                {isTeamMember && (
                  <Link 
                    to="/staff"
                    className="flex items-center w-full px-4 py-2 rounded-lg text-sm text-gray-200 hover:bg-theme/10 hover:text-theme transition-colors"
                    onClick={onClose}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    Staff Dashboard
                  </Link>
                )}

                <button 
                  onClick={handleLogout}
                  className="flex items-center w-full px-4 py-2 rounded-lg text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  Logout
                </button>
              </div>
            ) : (
              <button 
                onClick={() => {
                  login();
                  onClose();
                }}
                className="w-full bg-[#5865F2] hover:bg-[#4752c4] text-white px-4 py-3 rounded-lg font-medium transition-all duration-300 flex items-center justify-center gap-2.5 shadow-lg hover:shadow-[#5865F2]/30"
              >
                <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 127.14 96.36">
                  <path fill="currentColor" d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1A105.25,105.25,0,0,0,126.6,80.22h0C129.24,52.84,122.09,29.11,107.7,8.07ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,46,53.89,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,46,96.12,53,91.08,65.69,84.69,65.69Z" />
                </svg>
                Login with Discord
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default MobileMenu;