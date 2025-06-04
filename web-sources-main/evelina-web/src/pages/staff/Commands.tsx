import React, { useState, useEffect } from 'react';
import { Search, AlertCircle, Terminal, Shield, Bot, ChevronDown, Settings, PenTool as Tool, Users, Coins, Heart, Music, Ticket, Star, Code, Crown, Bell, Mic2, RefreshCw, Lock, XCircle, SearchX } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import { Button } from '../../components/ui/button';

interface Command {
  name: string;
  description: string;
  category: string;
  permissions: string;
  arguments: string;
  aliases: string[];
}

const staffCategories = ['supporter', 'moderator', 'manager', 'developer', 'jishaku'];

const categoryMapping = {
  'supporter': 'Supporter',
  'moderator': 'Moderator',
  'manager': 'Manager',
  'developer': 'Developer',
  'jishaku': 'Developer',
};

const categoryIcons = {
  'Supporter': Shield,
  'Moderator': Lock,
  'Manager': Crown,
  'Developer': Code,
};

function StaffCommands() {
  const [commands, setCommands] = useState<Command[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All Commands");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

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
        // Filter only staff commands and sort alphabetically by name
        const filteredCommands = data
          .filter((cmd: Command) => 
            staffCategories.includes(cmd.category.toLowerCase())
          )
          .sort((a: Command, b: Command) => a.name.localeCompare(b.name));
        
        setCommands(filteredCommands);
        setLoading(false);
      } catch (err) {
        setError('Unable to fetch commands, please try again later.');
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
    const mappedCategory = categoryMapping[lowerCategory as keyof typeof categoryMapping] || lowerCategory;
    
    const matchesCategory = selectedCategory === "All Commands" || mappedCategory === selectedCategory;
    const matchesSearch = command.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         command.description.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const categories = [
    'All Commands',
    'Supporter',
    'Moderator',
    'Manager',
    'Developer'
  ];

  if (loading) {
    return (
      <div className="p-6">
        <PageHeader
          icon={<Terminal />}
          title="Staff Commands"
          description="Access staff-only commands and their usage"
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
      <div className="p-6">
        <PageHeader
          icon={<Terminal />}
          title="Staff Commands"
          description="Access staff-only commands and their usage"
        />
        <div className="flex flex-col items-center justify-center py-12">
          <XCircle className="h-16 w-16 text-red-500 mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">Error Loading Commands</h3>
          <p className="text-gray-400 text-center max-w-md mb-6">
            There was an error loading the staff commands. Please try again later or contact support.
          </p>
          <Button onClick={() => window.location.reload()} variant="default">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <PageHeader
        icon={<Terminal />}
        title="Staff Commands"
        description="Access staff-only commands and their usage"
      />

      {/* Search and Category Selection */}
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
              onClick={() => setIsOpen(!isOpen)}
              className="flex items-center gap-2 px-4 py-2 bg-[#111] rounded-lg text-white border border-[rgba(114,155,176,0.1)] w-full md:w-auto"
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
            {isOpen && (
              <div className="absolute mt-2 w-full min-w-[200px] bg-[#111] border border-[rgba(114,155,176,0.1)] rounded-lg z-10 py-1">
                {categories.map(category => (
                  <button
                    key={category}
                    className={`flex items-center gap-2 px-4 py-2 w-full text-left hover:bg-[#222] transition-colors ${
                      selectedCategory === category ? "text-theme" : "text-gray-300"
                    }`}
                    onClick={() => {
                      setSelectedCategory(category);
                      setIsOpen(false);
                    }}
                  >
                    {selectedCategory !== 'All Commands' && categoryIcons[selectedCategory as keyof typeof categoryIcons] && (
                      React.createElement(categoryIcons[selectedCategory as keyof typeof categoryIcons], { size: 16, className: selectedCategory === category ? 'text-theme' : 'text-gray-400' })
                    )}
                    <span>{category}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Commands Grid */}
      {filteredCommands.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCommands.map((command) => (
            <div key={command.name} className="feature-card rounded-lg p-4 border border-[rgba(114,155,176,0.1)]">
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
                    <code className="bg-[#111] px-3 py-2 rounded text-gray-300 text-sm font-mono">
                      {command.arguments}
                    </code>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12">
          <SearchX className="h-16 w-16 text-theme mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">No Commands Found</h3>
          <p className="text-gray-400 text-center max-w-md mb-6">
            No commands match your current search criteria. Try changing your search terms or filter.
          </p>
          <Button onClick={() => { setSearchTerm(''); setSelectedCategory('All Commands'); }} variant="default">
            Clear Filters
          </Button>
        </div>
      )}
    </div>
  );
}

export default StaffCommands; 