import React, { useState, useEffect } from 'react';
import { Bot, Shield, Ticket, Gift, UserPlus, Mic2, Tag, Lightbulb, SatelliteDish, Award, Clock, Music, Mail, LayoutTemplate as Template, ExternalLink, Terminal, Book, Hammer, Lock, RotateCcw, Contact2, Code, Menu, Users, Crown, MessageSquare, Settings, Coins, Star, Bell } from 'lucide-react';
import { FaDiscord } from 'react-icons/fa';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useScrollToTop } from './hooks/useScrollToTop';
import { usePageTitle } from './hooks/usePageTitle';
import Commands from './pages/Commands';
import Status from './pages/Status';
import Home from './pages/Home';
import Terms from './pages/Terms';
import Economy from './pages/Economy';
import Privacy from './pages/Privacy';
import Refund from './pages/Refund';
import Contact from './pages/Contact';
import EmbedBuilder from './pages/EmbedBuilder';
import EmbedTemplates from './pages/EmbedTemplates';
import Team from './pages/Team';
import Premium from './pages/Premium';
import Feedback from './pages/Feedback';
import NotFound from './pages/NotFound';
import MobileMenu from './components/MobileMenu';
import ScrollToTop from './components/ScrollToTop';
import NavDropdown from './components/NavDropdown';
import Avatars from './pages/Avatars';
import UserAvatars from './pages/UserAvatars';
import AutoModeration from './pages/features/AutoModeration';
import TicketSystem from './pages/features/TicketSystem';
import WelcomeSystem from './pages/features/WelcomeSystem';
import MusicPlayer from './pages/features/MusicPlayer';
import EconomySystem from './pages/features/EconomySystem';
import Giveaways from './pages/features/Giveaways';
import VoiceMaster from './pages/features/VoiceMaster';
import VanityRoles from './pages/features/VanityRoles';
import ButtonRoles from './pages/features/ButtonRoles';
import Leveling from './pages/features/Leveling';
import BumpReminder from './pages/features/BumpReminder';
import DiscordRedirect from './pages/redirects/DiscordRedirect';
import InviteRedirect from './pages/redirects/InviteRedirect';
import TeamRequired from './components/TeamRequired';
import LoginButton from './components/LoginButton';
import { useAuthStore } from './lib/authStore';
import StaffLayout from './pages/staff/Layout';
import StaffOverview from './pages/staff/Overview';
import StaffRedirect from './pages/staff/Redirect';
import StaffCommands from './pages/staff/Commands';
import EconomyLogs from './pages/staff/logging/Economy';
import UserBlacklist from './pages/staff/blacklist/user/User';
import UserCommandBlacklist from './pages/staff/blacklist/user/Commands';
import UserCogBlacklist from './pages/staff/blacklist/user/Cog';
import ServerBlacklist from './pages/staff/blacklist/server/Server';
import ServerCommandBlacklist from './pages/staff/blacklist/server/Command';
import ServerCogBlacklist from './pages/staff/blacklist/server/Cog';
import { useTeamStore } from './lib/teamStore';

// Epic Games Redirect Component
function EpicGamesRedirect() {
  React.useEffect(() => {
    const gameId = window.location.pathname.split('/epicgames/')[1];
    if (gameId) {
      window.location.href = `com.epicgames.launcher://apps/${gameId}?action=launch&silent=true`;
      // Close the window after a short delay to ensure the redirect has started
      setTimeout(() => window.close(), 500);
    }
  }, []);

  return null;
}

const features = [
  {
    title: 'Auto Moderation',
    description: 'Keep your server safe with advanced auto-mod features',
    icon: <Shield className="w-5 h-5" />,
    path: '/features/automod'
  },
  {
    title: 'Ticket System',
    description: 'Manage support tickets efficiently',
    icon: <Ticket className="w-5 h-5" />,
    path: '/features/tickets'
  },
  {
    title: 'Welcome System',
    description: 'Customize welcome messages and autoroles',
    icon: <UserPlus className="w-5 h-5" />,
    path: '/features/welcome'
  },
  {
    title: 'Music Player',
    description: 'High quality music playback with playlist support',
    icon: <Music className="w-5 h-5" />,
    path: '/features/music'
  },
  {
    title: 'Economy System',
    description: 'Engage your community with a virtual economy',
    icon: <Coins className="w-5 h-5" />,
    path: '/features/economy'
  },
  {
    title: 'Giveaways',
    description: 'Create and manage server giveaways',
    icon: <Gift className="w-5 h-5" />,
    path: '/features/giveaways'
  },
  {
    title: 'Voice Master',
    description: 'Create and manage custom voice channels',
    icon: <Mic2 className="w-5 h-5" />,
    path: '/features/voicemaster'
  },
  {
    title: 'Vanity Roles',
    description: 'Custom roles for boosters and special members',
    icon: <Crown className="w-5 h-5" />,
    path: '/features/vanityroles'
  },
  {
    title: 'Button Roles',
    description: 'Create interactive role selection menus',
    icon: <Tag className="w-5 h-5" />,
    path: '/features/buttonroles'
  },
  {
    title: 'Leveling System',
    description: 'Text and voice leveling with rewards',
    icon: <Star className="w-5 h-5" />,
    path: '/features/leveling'
  },
  {
    title: 'Bump Reminder',
    description: 'Never miss a bump with automated reminders',
    icon: <Bell className="w-5 h-5" />,
    path: '/features/bump'
  },
  {
    title: 'Avatar History',
    description: 'Browse user avatar history',
    icon: <Users className="w-5 h-5" />,
    path: '/avatars'
  }
];

const information = [
  {
    title: 'Embed Builder',
    description: 'Create beautiful Discord embeds',
    icon: <Code className="w-5 h-5" />,
    path: '/embed'
  },
  {
    title: 'Embed Templates',
    description: 'Browse pre-made embed templates',
    icon: <Template className="w-5 h-5" />,
    path: '/templates'
  },
  {
    title: 'Team',
    description: 'Meet the people behind Evelina',
    icon: <Users className="w-5 h-5" />,
    path: '/team'
  },
  {
    title: 'Feedback',
    description: 'See what our users are saying',
    icon: <MessageSquare className="w-5 h-5" />,
    path: '/feedback'
  },
  {
    title: 'Documentation',
    description: 'Learn how to use Evelina',
    icon: <Book className="w-5 h-5" />,
    path: 'https://docs.evelina.bot',
    external: true
  }
];

function AppContent() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { fetchUser } = useAuthStore();
  const { fetchTeamMembers } = useTeamStore();
  const location = useLocation();
  useScrollToTop();
  usePageTitle();

  // Check if current path is a staff page
  const isStaffPage = location.pathname.startsWith('/staff');

  // Beim Start der App den Auth-Status checken und Team-Mitglieder laden
  useEffect(() => {
    fetchUser();
    fetchTeamMembers();
  }, [fetchUser, fetchTeamMembers]);

  return (
    <div className="h-screen bg-[#0a0a0a] text-white flex flex-col">
      <Toaster position="top-right" />
      <ScrollToTop />
      
      {/* Navbar */}
      <div className="fixed w-full z-50 top-0">
        <nav className="bg-[#0a0a0a]/50 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-4 flex items-center justify-between">
            {/* Left side */}
            <Link to="/" className="text-2xl font-bold text-white flex items-center gap-3 hover:opacity-90 transition-opacity h-20">
              <img 
                src="https://r.emogir.ls/evelina-pfp.png" 
                alt="Evelina" 
                className="w-10 h-10 rounded-full"
              />
              Evelina
            </Link>
            
            {/* Center */}
            <div className="hidden lg:flex items-center">
              <NavDropdown title="Features" items={features} />
              <NavDropdown title="Information" items={information} />
              <Link to="/commands" className="h-20 px-4 flex items-center text-gray-400 hover:text-theme transition-colors">
                Commands
              </Link>
              <Link to="/status" className="h-20 px-4 flex items-center text-gray-400 hover:text-theme transition-colors">
                Status
              </Link>
            </div>

            {/* Right side */}
            <div className="flex items-center">
              <div className="hidden md:flex items-center">
                <LoginButton />
              </div>
              
              <button 
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="ml-4 p-1 text-gray-400 hover:text-white transition-colors md:hidden"
              >
                <Menu className="w-7 h-7" />
              </button>
            </div>
          </div>
        </nav>
        {/* Divider line */}
        <div className="h-px bg-gradient-to-r from-transparent via-gray-800 to-transparent"></div>
      </div>
      
      {/* Mobile menu */}
      <MobileMenu isOpen={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)} />
      
      {/* Page content */}
      <div className="flex-grow pt-20">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/commands" element={<Commands />} />
          <Route path="/commands/:category" element={<Commands />} />
          <Route path="/status" element={<Status />} />
          <Route path="/team" element={<Team />} />
          <Route path="/premium" element={<Premium />} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/refund" element={<Refund />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/economy" element={<Economy />} />
          <Route path="/avatars" element={<Avatars />} />
          <Route path="/avatars/:userId" element={<UserAvatars />} />
          <Route path="/embed" element={<EmbedBuilder />} />
          <Route path="/templates" element={<EmbedTemplates />} />
          
          {/* Staff area with nested routes */}
          <Route path="/staff" element={
            <TeamRequired>
              <StaffRedirect />
            </TeamRequired>
          } />
          
          <Route path="/staff" element={
            <TeamRequired>
              <StaffLayout />
            </TeamRequired>
          }>
            <Route path="overview" element={<StaffOverview />} />
            <Route path="logging/economy" element={<EconomyLogs />} />
            <Route path="blacklist/user/user" element={<UserBlacklist />} />
            <Route path="blacklist/user/command" element={<UserCommandBlacklist />} />
            <Route path="blacklist/user/cog" element={<UserCogBlacklist />} />
            <Route path="blacklist/server/server" element={<ServerBlacklist />} />
            <Route path="blacklist/server/command" element={<ServerCommandBlacklist />} />
            <Route path="blacklist/server/cog" element={<ServerCogBlacklist />} />
            <Route path="commands" element={<StaffCommands />} />
          </Route>
          
          {/* Feature Routes */}
          <Route path="/features/automod" element={<AutoModeration />} />
          <Route path="/features/tickets" element={<TicketSystem />} />
          <Route path="/features/welcome" element={<WelcomeSystem />} />
          <Route path="/features/music" element={<MusicPlayer />} />
          <Route path="/features/economy" element={<EconomySystem />} />
          <Route path="/features/giveaways" element={<Giveaways />} />
          <Route path="/features/voicemaster" element={<VoiceMaster />} />
          <Route path="/features/vanityroles" element={<VanityRoles />} />
          <Route path="/features/buttonroles" element={<ButtonRoles />} />
          <Route path="/features/leveling" element={<Leveling />} />
          <Route path="/features/bump" element={<BumpReminder />} />
          
          {/* Redirects */}
          <Route path="/discord" element={<DiscordRedirect />} />
          <Route path="/invite" element={<InviteRedirect />} />
          <Route path="/epicgames/*" element={<EpicGamesRedirect />} />
          
          {/* 404 */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </div>

      {/* Modern Footer - Hidden on staff pages */}
      {!isStaffPage && (
        <footer className="relative z-20 bg-[#0a0a0a]/50 backdrop-blur-md pt-6 pb-6 mt-auto">
          <div className="h-px bg-gradient-to-r from-transparent via-gray-800 to-transparent mb-2" />
          <div className="max-w-7xl mx-auto px-4">
            <div className="pt-4 flex flex-col md:flex-row justify-between items-center">
              <p className="text-gray-400 text-base mb-6 md:mb-0">
                © 2024 Evelina.bot • All rights reserved
              </p>
              <div className="flex flex-wrap justify-center gap-8">
                <Link to="/terms" className="text-sm text-gray-400 hover:text-white transition-colors font-medium">
                  Terms
                </Link>
                <Link to="/privacy" className="text-sm text-gray-400 hover:text-white transition-colors font-medium">
                  Privacy
                </Link>
                <Link to="/refund" className="text-sm text-gray-400 hover:text-white transition-colors font-medium">
                  Refund
                </Link>
              </div>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;