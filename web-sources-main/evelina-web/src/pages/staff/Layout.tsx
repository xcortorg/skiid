import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../lib/authStore';
import { useTeamStore } from '../../lib/teamStore';
import { LayoutDashboard, LineChart, ChevronDown, ChevronRight, Book, Terminal, Shield, Users, Command, Package, Server, Menu, X } from 'lucide-react';

// Define interfaces for navigation items
interface NavItem {
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  path: string;
}

interface NavItemWithSubItems extends NavItem {
  subItems: NavItem[];
}

interface SectionItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  items: (NavItem | NavItemWithSubItems)[];
}

const StaffLayout: React.FC = () => {
  const { user } = useAuthStore();
  const { getUserRank } = useTeamStore();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Get user rank from team store
  const userRank = user ? getUserRank(user.id) : null;

  // State for tracking expanded sections
  const [expandedSections, setExpandedSections] = useState<{[key: string]: boolean}>({
    logging: location.pathname.includes('/staff/logging'),
    blacklist: location.pathname.includes('/staff/blacklist')
  });

  // State for mobile sidebar visibility
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Toggle section expansion
  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };
  
  // Navigation items
  const navItems: NavItem[] = [
    { 
      icon: <LayoutDashboard className="w-5 h-5" />, 
      label: 'Overview', 
      isActive: location.pathname === '/staff/overview',
      path: '/staff/overview'
    },
    { 
      icon: <Terminal className="w-5 h-5" />, 
      label: 'Commands', 
      isActive: location.pathname === '/staff/commands',
      path: '/staff/commands'
    },
  ];

  // Collapsible sections
  const collapsibleSections: SectionItem[] = [
    {
      id: 'logging',
      icon: <LineChart className="w-5 h-5" />,
      label: 'Logging',
      items: [
        { 
          icon: <Book className="w-4 h-4" />, 
          label: 'Economy', 
          isActive: location.pathname === '/staff/logging/economy',
          path: '/staff/logging/economy'
        }
      ]
    },
    {
      id: 'blacklist',
      icon: <Shield className="w-5 h-5" />,
      label: 'Blacklist',
      items: [
        {
          icon: <Users className="w-4 h-4" />,
          label: 'User',
          isActive: location.pathname.includes('/staff/blacklist/user'),
          path: '/staff/blacklist/user/user',
          subItems: [
            {
              icon: <Users className="w-4 h-4" />,
              label: 'User',
              isActive: location.pathname === '/staff/blacklist/user/user',
              path: '/staff/blacklist/user/user'
            },
            {
              icon: <Command className="w-4 h-4" />,
              label: 'Commands',
              isActive: location.pathname === '/staff/blacklist/user/command',
              path: '/staff/blacklist/user/command'
            },
            {
              icon: <Package className="w-4 h-4" />,
              label: 'Cog',
              isActive: location.pathname === '/staff/blacklist/user/cog',
              path: '/staff/blacklist/user/cog'
            }
          ]
        },
        {
          icon: <Server className="w-4 h-4" />,
          label: 'Server',
          isActive: location.pathname.includes('/staff/blacklist/server'),
          path: '/staff/blacklist/server/server',
          subItems: [
            {
              icon: <Server className="w-4 h-4" />,
              label: 'Server',
              isActive: location.pathname === '/staff/blacklist/server/server',
              path: '/staff/blacklist/server/server'
            },
            {
              icon: <Command className="w-4 h-4" />,
              label: 'Command',
              isActive: location.pathname === '/staff/blacklist/server/command',
              path: '/staff/blacklist/server/command'
            },
            {
              icon: <Package className="w-4 h-4" />,
              label: 'Cog',
              isActive: location.pathname === '/staff/blacklist/server/cog',
              path: '/staff/blacklist/server/cog'
            }
          ]
        }
      ]
    }
  ];

  // Handle navigation
  const handleNavigation = (path: string) => {
    navigate(path);
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Mobile sidebar toggle button */}
      <div className="lg:hidden fixed top-24 left-4 z-50">
        <button 
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="bg-[#1a1a1a] p-2 rounded-md text-white hover:bg-[#2a2a2a] transition-colors"
        >
          {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Main container with sidebar and content */}
      <div className="flex flex-1">
        {/* Left Sidebar */}
        <div className={`bg-[#121212] border-r border-[#2a2a2a] h-[calc(100vh-55px)] overflow-y-auto fixed transition-all duration-300 z-40
          ${sidebarOpen ? 'left-0 w-64' : '-left-64 w-64 lg:left-0'} lg:w-64`}>
          {/* User Profile */}
          <div className="p-4 border-b border-[#2a2a2a]">
            <div className="flex items-center">
              {user?.avatar && (
                <img 
                  src={`https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`} 
                  alt={user.username} 
                  className="w-12 h-12 rounded-full mr-3"
                />
              )}
              <div>
                <h3 className="text-white font-medium">{user?.username || 'User'}</h3>
                <span className="text-xs text-gray-400">{userRank || 'Team Member'}</span>
              </div>
            </div>
          </div>
          
          {/* Navigation */}
          <nav className="p-2">
            <ul>
              {/* Regular nav items */}
              {navItems.map((item, index) => (
                <li key={index} className="mb-1">
                  <button
                    onClick={() => {
                      handleNavigation(item.path);
                      if (window.innerWidth < 1024) setSidebarOpen(false);
                    }}
                    className={`w-full flex items-center px-3 py-2 rounded-md text-left ${
                      item.isActive 
                        ? 'bg-[#1a1a1a] text-white' 
                        : 'text-gray-400 hover:bg-[#1a1a1a] hover:text-gray-300'
                    } transition-colors`}
                  >
                    <span className="mr-3">{item.icon}</span>
                    {item.label}
                  </button>
                </li>
              ))}
              
              {/* Collapsible sections */}
              {collapsibleSections.map((section, index) => (
                <li key={`section-${index}`} className="mb-1">
                  {/* Section header */}
                  <button
                    onClick={() => toggleSection(section.id)}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-md text-left text-gray-400 hover:bg-[#1a1a1a] hover:text-gray-300 transition-colors"
                  >
                    <div className="flex items-center">
                      <span className="mr-3">{section.icon}</span>
                      {section.label}
                    </div>
                    <span>
                      {expandedSections[section.id] ? 
                        <ChevronDown className="w-4 h-4" /> : 
                        <ChevronRight className="w-4 h-4" />
                      }
                    </span>
                  </button>
                  
                  {/* Section items */}
                  {expandedSections[section.id] && (
                    <ul className="ml-6 mt-1">
                      {section.items.map((item, itemIndex) => (
                        <li key={`${section.id}-item-${itemIndex}`} className="mb-1">
                          <button
                            onClick={() => handleNavigation(item.path)}
                            className={`w-full flex items-center px-3 py-2 rounded-md text-left ${
                              item.isActive 
                                ? 'bg-[#1a1a1a] text-white' 
                                : 'text-gray-400 hover:bg-[#1a1a1a] hover:text-gray-300'
                            } transition-colors`}
                          >
                            <span className="mr-3">{item.icon}</span>
                            {item.label}
                          </button>
                          
                          {/* SubItems for nested menus */}
                          {('subItems' in item) && item.isActive && (
                            <ul className="ml-6 mt-1">
                              {(item as NavItemWithSubItems).subItems.map((subItem, subItemIndex) => (
                                <li key={`${section.id}-item-${itemIndex}-sub-${subItemIndex}`} className="mb-1">
                                  <button
                                    onClick={() => handleNavigation(subItem.path)}
                                    className={`w-full flex items-center px-3 py-2 rounded-md text-left ${
                                      subItem.isActive 
                                        ? 'bg-[#1a1a1a] text-white' 
                                        : 'text-gray-400 hover:bg-[#1a1a1a] hover:text-gray-300'
                                    } transition-colors`}
                                  >
                                    <span className="mr-3">{subItem.icon}</span>
                                    {subItem.label}
                                  </button>
                                </li>
                              ))}
                            </ul>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </nav>
        </div>

        {/* Overlay for mobile when sidebar is open */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          ></div>
        )}

        {/* Main Content Area */}
        <div className="lg:ml-64 flex-1 bg-[#0a0a0a] transition-all duration-300">
          {/* Content */}
          <div className="px-4 py-4">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
};

export default StaffLayout; 