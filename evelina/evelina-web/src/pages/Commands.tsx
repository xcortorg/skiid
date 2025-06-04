import React, { useState, useEffect } from 'react';
import { Search, AlertCircle, Terminal, Shield, Bot, ChevronDown, ChevronUp, Settings, PenTool as Tool, Users, Coins, Heart, Music, Ticket, Star, Code, Crown, Bell, Mic2, RefreshCw } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { useParams, useNavigate, useLocation } from 'react-router-dom';

interface Command {
  name: string;
  description: string;
  category: string;
  permissions: string;
  arguments: string;
  aliases: string[];
}

const categoryMapping = {
  'antinuke': 'Administration',
  'auth': 'Administration',
  'automod': 'Automod',
  'autopost': 'Utility',
  'autorole': 'Utility',
  'boosterrole': 'Utility',
  'colorrole': 'Utility',
  'confessions': 'Fun',
  'config': 'Settings',
  'counters': 'Utility',
  'donor': 'Donator',
  'economy': 'Economy',
  'emoji': 'Fun',
  'events': 'Utility',
  'fun': 'Fun',
  'giveaway': 'Fun',
  'info': 'Utility',
  'instagram': 'Social',
  'instance': 'Settings',
  'invitetracker': 'Settings',
  'invoke': 'Utility',
  'lastfm': 'Fun',
  'leveling': 'Leveling',
  'logging': 'Moderation',
  'moderation': 'Moderation',
  'paginate': 'Utility',
  'reseller': 'Settings',
  'responders': 'Utility',
  'role': 'Utility',
  'roleplay': 'Fun',
  'selfbot': 'Fun',
  'social': 'Social',
  'spotify': 'Music',
  'starboard': 'Utility',
  'store': 'Donator',
  'suggestion': 'Utility',
  'ticket': 'Tickets',
  'tiktok': 'Social',
  'twitch': 'Social',
  'twitter': 'Social',
  'utility': 'Utility',
  'vanity': 'Settings',
  'voicemaster': 'Voice',
  'voicetrack': 'Voice',
  'vote': 'Utility',
  'webhooks': 'Utility',
  'whitelist': 'Administration',
  'youtube': 'Social',
};

const categoryIcons = {
  'Administration': Crown,
  'Automod': Shield,
  'Donator': Bell,
  'Economy': Coins,
  'Fun': Heart,
  'Leveling': Star,
  'Moderation': Shield,
  'Music': Music,
  'Settings': Settings,
  'Social': Users,
  'Tickets': Ticket,
  'Utility': Tool,
  'Voice': Mic2,
};

function Commands() {
  const [commands, setCommands] = useState<Command[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All Commands");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  
  // Extrahiere Kategorie aus URL für Direktnavigation
  useEffect(() => {
    const path = location.pathname.toLowerCase();
    if (path.startsWith('/commands/')) {
      const categoryParam = path.split('/commands/')[1];
      const categoryKey = Object.keys(categoryMapping).find(key => 
        key.toLowerCase() === categoryParam.toLowerCase()
      );
      
      if (categoryKey && categoryKey in categoryMapping) {
        setSelectedCategory(categoryMapping[categoryKey as keyof typeof categoryMapping]);
      } else {
        // Für kategorisierte URLs
        const matchedCategory = categories.find(cat => 
          cat.toLowerCase() === categoryParam.toLowerCase()
        );
        
        if (matchedCategory) {
          setSelectedCategory(matchedCategory);
        } else {
          // Wenn Kategorie nicht existiert, zu allen Commands umleiten
          navigate('/commands', { replace: true });
        }
      }
    }
  }, [location.pathname, navigate]);

  // Aktualisiere URL wenn Kategorie geändert wird
  useEffect(() => {
    if (selectedCategory !== "All Commands" && !loading) {
      const categoryForUrl = selectedCategory.toLowerCase();
      navigate(`/commands/${categoryForUrl}`, { replace: true });
    } else if (selectedCategory === "All Commands" && !loading && location.pathname !== '/commands') {
      navigate('/commands', { replace: true });
    }
  }, [selectedCategory, loading, navigate, location.pathname]);

  useEffect(() => {
    const fetchCommands = async () => {
      try {
        const response = await fetch('/api/commands', {
          headers: {
            'X-API-Key': 'loveskei'
          }
        });
        if (!response.ok) {
          throw new Error('Failed to fetch commands');
        }
        const data = await response.json();
        // Filter out staff commands and sort alphabetically by name
        const filteredCommands = data
          .filter((cmd: Command) => 
            !['supporter', 'moderator', 'manager', 'developer', 'jishaku'].includes(cmd.category.toLowerCase())
          )
          .sort((a: Command, b: Command) => a.name.localeCompare(b.name));
        
        setCommands(filteredCommands);
        setLoading(false);
      } catch (err) {
        setError('Unable to fetch commands, please try again later or join our support server for assistance.');
        setLoading(false);
        setCommands([]);
      }
    };

    fetchCommands();
  }, []);

  const capitalizePermissions = (permissions: string) => {
    return permissions.split(' ').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const getCommandCountForCategory = (category: string) => {
    if (category === "All Commands") {
      return commands.length;
    }
    return commands.filter(cmd => {
      const lowerCategory = cmd.category.toLowerCase();
      return lowerCategory in categoryMapping && categoryMapping[lowerCategory as keyof typeof categoryMapping] === category;
    }).length;
  };

  const filteredCommands = commands.filter(command => {
    const lowerCategory = command.category.toLowerCase();
    const matchesCategory = selectedCategory === "All Commands" || 
      (lowerCategory in categoryMapping && categoryMapping[lowerCategory as keyof typeof categoryMapping] === selectedCategory);
    const matchesSearch = command.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         command.description.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const categories = [
    'All Commands',
    'Administration',
    'Automod',
    'Donator',
    'Economy',
    'Fun',
    'Leveling',
    'Moderation',
    'Music',
    'Settings',
    'Social',
    'Tickets',
    'Utility',
    'Voice'
  ];

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <PageHeader
          icon={<Terminal />}
          title="Commands"
          description="Explore all available commands and their usage"
        />

        {/* Search and Category Selection - mit realer Suchleiste */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search commands..."
                className="w-full pl-10 pr-4 py-2 bg-[#111] rounded-lg text-white placeholder-gray-400 focus:outline-none border border-[rgba(114,155,176,0.1)]"
                disabled
              />
            </div>
            <div className="relative">
              <button
                className="flex items-center gap-2 px-4 py-2 bg-[#111] rounded-lg text-white border border-[rgba(114,155,176,0.1)] w-full md:w-auto"
                disabled
              >
                <div className="flex items-center gap-2">
                  <span className="text-gray-400 flex items-center gap-1">
                    <Terminal size={16} className="text-gray-400" />
                    <span>All Commands</span>
                  </span>
                  <ChevronDown size={16} className="text-gray-400" />
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Animierte Command-Karten mit einheitlicher Border */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(9)].map((_, i) => (
            <div key={i} className="feature-card rounded-lg p-4 border border-[rgba(114,155,176,0.1)] relative">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <div className="h-6 bg-theme/10 rounded w-32 mb-2"></div>
                  <div className="h-4 bg-dark-2 rounded w-48"></div>
                </div>
                <div className="h-6 bg-dark-2 rounded-full px-3 flex items-center justify-center">
                  <div className="w-16 h-3 bg-theme/20 rounded-full"></div>
                </div>
              </div>
              <div className="space-y-3 mt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <div className="h-4 bg-dark-2 rounded w-20"></div>
                    <div className="h-8 bg-[#111] rounded"></div>
                  </div>
                  <div className="space-y-1">
                    <div className="h-4 bg-dark-2 rounded w-20"></div>
                    <div className="h-8 bg-[#111] rounded"></div>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="h-4 bg-dark-2 rounded w-20"></div>
                  <div className="h-8 bg-[#111] rounded"></div>
                </div>
              </div>
              
              {/* Loading overlay mit leichtem blur-effekt und aktivierter Animation */}
              <div className="absolute inset-0 bg-dark-2/20 backdrop-blur-sm flex items-center justify-center rounded-lg opacity-30">
                <div className="w-8 h-8 border-2 border-theme border-t-transparent rounded-full animate-spin"></div>
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
          icon={<Terminal />}
          title="Commands"
          description="Explore all available commands and their usage"
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
        icon={<Terminal />}
        title="Commands"
        description="Explore all available commands and their usage"
      />

      {/* Search and Category Selection - Mobile Optimized */}
      <div className="mb-8">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search commands..."
              className="w-full pl-10 pr-4 py-2 bg-[#111] rounded-lg text-white placeholder-gray-400 focus:outline-none border border-[rgba(114,155,176,0.1)]"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="relative">
            <button
              className="flex items-center gap-2 px-4 py-2 bg-[#111] rounded-lg text-white border border-[rgba(114,155,176,0.1)] w-full md:w-auto"
              onClick={() => {
                const dropdown = document.getElementById('categoryDropdown');
                if (dropdown) {
                  dropdown.classList.toggle('hidden');
                }
              }}
            >
              <div className="flex items-center gap-2">
                <span className="text-gray-400 flex items-center gap-1">
                  {selectedCategory === "All Commands" ? (
                    <Terminal size={16} className="text-gray-400" />
                  ) : (
                    React.createElement(categoryIcons[selectedCategory as keyof typeof categoryIcons], { 
                      size: 16, 
                      className: "text-theme" 
                    })
                  )}
                  <span>{selectedCategory}</span>
                </span>
                <ChevronDown size={16} className="text-gray-400" />
              </div>
            </button>
            <div 
              id="categoryDropdown" 
              className="absolute z-10 mt-2 w-56 max-h-96 overflow-y-auto bg-dark-3 border border-[rgba(114,155,176,0.1)] rounded-lg shadow-lg hidden right-0"
            >
              {categories.map(category => (
                <button
                  key={category}
                  onClick={() => {
                    setSelectedCategory(category);
                    const dropdown = document.getElementById('categoryDropdown');
                    if (dropdown) {
                      dropdown.classList.add('hidden');
                    }
                  }}
                  className={`w-full text-left px-4 py-2 transition-colors flex items-center justify-between ${
                    selectedCategory === category
                      ? 'bg-theme/20 text-white'
                      : 'text-gray-400 hover:bg-dark-2 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {category !== 'All Commands' && categoryIcons[category as keyof typeof categoryIcons] && (
                      React.createElement(categoryIcons[category as keyof typeof categoryIcons], { size: 16, className: selectedCategory === category ? 'text-theme' : 'text-gray-400' })
                    )}
                    <span>{category}</span>
                  </div>
                  <span className="text-sm text-gray-500">
                    {getCommandCountForCategory(category)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Commands Grid */}
        <div className="flex-1">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCommands.map((command) => (
              <div key={command.name} className="feature-card rounded-lg p-4">
                <div className="flex flex-col h-full">
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-theme">
                        {command.name}
                      </h3>
                      <p className="text-gray-400 mt-1">{command.description}</p>
                    </div>
                    <span className="px-3 py-1 rounded-full bg-[#111] text-xs text-theme whitespace-nowrap">
                      {command.category.toLowerCase() in categoryMapping 
                        ? categoryMapping[command.category.toLowerCase() as keyof typeof categoryMapping] 
                        : command.category}
                    </span>
                  </div>
                  <div className="space-y-3 mt-auto">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex flex-col gap-1">
                        <span className="text-gray-500 text-sm">Permissions</span>
                        <div className="bg-[#111] px-3 py-2 rounded text-theme text-sm">
                          {capitalizePermissions(command.permissions)}
                        </div>
                      </div>
                      {command.aliases && command.aliases.length > 0 && (
                        <div className="flex flex-col gap-1">
                          <span className="text-gray-500 text-sm">Aliases</span>
                          <div className="bg-[#111] px-3 py-2 rounded text-gray-300 text-sm">
                            {command.aliases.join(', ')}
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-gray-500 text-sm">Arguments</span>
                      <code className="bg-[#111] px-3 py-2 rounded text-gray-300 text-sm">
                        {command.arguments}
                      </code>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {filteredCommands.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              No commands found matching your criteria.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Commands;