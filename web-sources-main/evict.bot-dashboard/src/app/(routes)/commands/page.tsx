"use client";

import { Search, Crown, Copy } from "lucide-react";
import { useState, useMemo, useCallback } from "react";
import { Command } from "@/types/Command";
import { Commands, Categories } from "@/data/Commands";
import toast, { Toaster } from "react-hot-toast";


const ITEMS_PER_LOAD = 20;

const CommandsPage = () => {
  const [visibleItems, setVisibleItems] = useState(ITEMS_PER_LOAD);
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCommand, setSelectedCommand] = useState<Command | null>(null);

  const filteredCommands = useMemo(() => {
    return Commands
      .filter(command => {
        if (activeCategory !== "All" && command.category !== activeCategory) {
          return false;
        }
        
        if (searchQuery.trim() === "") {
          return true;
        }
        
        const query = searchQuery.toLowerCase();
        return command.name.toLowerCase().includes(query) ||
               command.description.toLowerCase().includes(query) ||
               command.aliases?.some(alias => alias.toLowerCase().includes(query));
      });
  }, [activeCategory, searchQuery]);

  const loadMore = useCallback(() => {
    setVisibleItems(prev => prev + ITEMS_PER_LOAD);
  }, []);

  const visibleCommands = useMemo(() => 
    filteredCommands.slice(0, visibleItems),
    [filteredCommands, visibleItems]
  );

  const getCategoryCount = useCallback((categoryName: string) => {
    if (categoryName === "All") {
      return Commands.length;
    }
    return Commands.filter(cmd => cmd.category === categoryName).length;
  }, []);

  const copyCommand = async (command: string) => {
    try {
      await navigator.clipboard.writeText(command);
      toast.success('Command copied to clipboard!', {
        style: {
          background: '#333',
          color: '#fff',
          border: '1px solid rgba(255,255,255,0.1)',
        },
      });
    } catch (err) {
      toast.error('Failed to copy command', {
        style: {
          background: '#333',
          color: '#fff',
          border: '1px solid rgba(255,255,255,0.1)',
        },
      });
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0B]">
      <Toaster position="bottom-center" />
      <div className="relative border-b border-white/5 bg-gradient-to-b from-[#0A0A0B] to-black mt-[-64px]">
        <div className="absolute inset-0 bg-[url('/noise.png')] opacity-5" />
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-12 relative">
          <h1 className="font-bold text-4xl sm:text-5xl text-white">Commands</h1>
          <p className="text-white/60 mt-4 text-base sm:text-lg">
            Explore and learn about all available commands.
          </p>
        </div>
      </div>

      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          <div className="w-full lg:w-64 lg:flex-shrink-0">
            <div className="lg:sticky lg:top-8">
              <div className="relative mb-6">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <input
                  type="text"
                  placeholder="Search commands..."
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-10 py-2 text-sm text-white 
                           placeholder:text-white/40 focus:outline-none focus:border-white/20 transition-colors"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <nav className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-1 gap-2">
                {Categories.map((category) => (
                  <button
                    key={category.name}
                    onClick={() => setActiveCategory(category.name)}
                    className={`flex items-center justify-between px-4 py-2 rounded-lg text-sm font-medium transition-colors
                              ${activeCategory === category.name 
                                ? "bg-white/10 text-white" 
                                : "text-white/60 hover:text-white hover:bg-white/5"}`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-lg">{category.icon}</span>
                      {category.name}
                    </div>
                    <span className="text-xs text-white/40">
                      {getCategoryCount(category.name)}
                    </span>
                  </button>
                ))}
              </nav>
            </div>
          </div>

          <div className="flex-1 space-y-4">
            {visibleCommands.map((command) => (
              <CommandItem
                key={command.name}
                command={command}
                isSelected={selectedCommand?.name === command.name}
                onClick={() => setSelectedCommand(
                  selectedCommand?.name === command.name ? null : command
                )}
                onCopy={() => copyCommand(command.name)}
              />
            ))}
            
            {visibleItems < filteredCommands.length && (
              <button 
                onClick={loadMore}
                className="w-full py-2 bg-white/5 rounded-lg mt-4"
              >
                Load More
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const CommandItem = ({ 
  command, 
  isSelected, 
  onClick,
  onCopy
}: { 
  command: Command; 
  isSelected: boolean; 
  onClick: () => void;
  onCopy: () => void;
}) => {
  if (command.name === "reskin remove") {
  }
  return (
    <div
      onClick={onClick}
      className={`group p-4 rounded-xl border transition-colors cursor-pointer
                ${isSelected 
                  ? "bg-white/5 border-white/20" 
                  : "bg-white/[0.02] border-transparent hover:bg-white/[0.04] hover:border-white/10"}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-white font-medium">{command.name}</h3>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onCopy();
              }}
              className="p-1.5 rounded-md bg-white/5 hover:bg-white/10 transition-colors"
            >
              <Copy size={14} className="text-white/60" />
            </button>
            {command.donator === true && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r from-amber-500/20 to-yellow-500/20 text-amber-300 border border-amber-500/20">
                Donator
              </span>
            )}
          </div>
          <p className="text-sm text-white/60 mt-1">{command.description}</p>
        </div>
        {command.aliases && command.aliases.length > 0 && (
          <div className="flex gap-2">
            {command.aliases.map((alias: any) => (
              <span 
                key={alias}
                className="px-2 py-1 rounded-md text-xs font-medium bg-white/5 text-white/60"
              >
                {alias}
              </span>
            ))}
          </div>
        )}
      </div>

      {isSelected && (
        <div className="mt-4 pt-4 border-t border-white/10 transition-opacity duration-100">
          {command.parameters.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-white/80">Parameters</h4>
              <div className="space-y-2">
                {command.parameters.map((param, idx) => (
                  <div 
                    key={idx}
                    className="p-3 rounded-lg bg-white/[0.02] border border-white/5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">
                          {param.name}
                        </span>
                        {param.optional && (
                          <span className="px-1.5 py-0.5 rounded text-xs bg-white/5 text-white/40">
                            Optional
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-white/40">{param.type}</span>
                    </div>

                    {param.flags && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {param.flags.required?.map((flag) => (
                          <span
                            key={flag.name}
                            className="px-2 py-1 rounded text-xs bg-red-500/10 text-red-400"
                            title={flag.description}
                          >
                            {flag.name}
                          </span>
                        ))}
                        {param.flags.optional?.map((flag) => (
                          <span
                            key={flag.name}
                            className="px-2 py-1 rounded text-xs bg-white/5 text-white/60"
                            title={flag.description}
                          >
                            {flag.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {command.permissions.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-white/80 mb-2">Required Permissions</h4>
              <div className="flex flex-wrap gap-2">
                {command.permissions.map((permission) => (
                  <span
                    key={permission}
                    className="px-2 py-1 rounded text-xs bg-yellow-500/10 text-yellow-400"
                  >
                    {permission}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CommandsPage;
