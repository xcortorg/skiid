import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

interface DropdownItem {
  title: string;
  description: string;
  icon: React.ReactNode;
  path: string;
  external?: boolean;
}

interface NavDropdownProps {
  title: string;
  items: DropdownItem[];
}

function NavDropdown({ title, items }: NavDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        className="flex items-center gap-2 h-20 px-4 text-gray-400 hover:text-theme transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        {title}
        <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <div
        className={`absolute left-1/2 -translate-x-1/2 w-[700px] max-w-[95vw] bg-[#0a0a0a]/95 backdrop-blur-lg rounded-xl shadow-2xl border border-zinc-800/50 p-3 grid grid-cols-2 gap-2 z-50 transition-all duration-200 ${
          isOpen
            ? 'opacity-100 translate-y-2'
            : 'opacity-0 -translate-y-4 pointer-events-none'
        }`}
      >
        {items.map((item, index) => (
          item.external ? (
            <a
              key={index}
              href={item.path}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 p-3 rounded-lg hover:bg-zinc-800/50 transition-colors group"
              onClick={() => setIsOpen(false)}
            >
              <div className="w-10 h-10 rounded-lg bg-theme/10 flex items-center justify-center text-theme group-hover:scale-110 transition-transform">
                {item.icon}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium text-white">{item.title}</h3>
                  <ExternalLink className="w-3.5 h-3.5 text-gray-400" />
                </div>
                <p className="text-xs text-gray-400 mt-0.5">{item.description}</p>
              </div>
            </a>
          ) : (
            <Link
              key={index}
              to={item.path}
              className="flex items-start gap-3 p-3 rounded-lg hover:bg-zinc-800/50 transition-colors group"
              onClick={() => setIsOpen(false)}
            >
              <div className="w-10 h-10 rounded-lg bg-theme/10 flex items-center justify-center text-theme group-hover:scale-110 transition-transform">
                {item.icon}
              </div>
              <div>
                <h3 className="text-sm font-medium text-white">{item.title}</h3>
                <p className="text-xs text-gray-400 mt-0.5">{item.description}</p>
              </div>
            </Link>
          )
        ))}
      </div>
    </div>
  );
}

export default NavDropdown;