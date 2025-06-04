import React, { useState, useEffect } from 'react';
import { Code, Copy, Import, AlertCircle, X, Image, Check, Plus, Trash, ExternalLink } from 'lucide-react';
import { HexColorPicker } from 'react-colorful';
import toast from 'react-hot-toast';
import Modal from '../components/Modal';
import PageHeader from '../components/PageHeader';

interface Field {
  name: string;
  value: string;
  inline: boolean;
}

interface Button {
  label: string;
  style: 'primary' | 'secondary' | 'success' | 'danger';
  url?: string;
  emoji?: string;
}

interface EmbedData {
  content?: string;
  title?: string;
  description?: string;
  url?: string;
  color?: string;
  author?: {
    name?: string;
    icon?: string;
    url?: string;
  };
  footer?: {
    text?: string;
    icon?: string;
  };
  thumbnail?: string;
  image?: string;
  fields: Field[];
  buttons: Button[];
  timestamp?: boolean;
}

// Mock data for variable replacement
const mockData = {
  user: {
    id: '335500798752456705',
    name: 'curet',
    nick: 'curet',
    display: 'curet',
    mention: '@curet',
    discriminator: '0001',
    avatar: 'https://cdn.discordapp.com/avatars/335500798752456705/97175ab711048b2d110484b0ae3187ba.png',
    guild: {
      avatar: 'https://cdn.discordapp.com/avatars/335500798752456705/97175ab711048b2d110484b0ae3187ba.png'
    },
    joined_at: '1716602880',
    created_at: '1500060000'
  },
  guild: {
    id: '1228371886690537624',
    name: 'evelina',
    icon: 'https://cdn.discordapp.com/icons/1228371886690537624/51d5ac0bfb7db1615684020dc2d5b8e5.png',
    created_at: '1712937060',
    count: 3463,
    boost_count: 26,
    booster_count: 13,
    boost_tier: 3,
    vanity: 'evelina'
  }
};

function formatOrdinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function EmbedBuilder() {
  const [embed, setEmbed] = useState<EmbedData>({
    fields: [],
    buttons: [],
    color: '#729bb0'
  });

  const [showImportModal, setShowImportModal] = useState(false);

  const showNotification = (
    icon: React.ReactNode,
    title: string,
    message: string,
    type: 'success' | 'error' = 'success'
  ) => {
    toast.custom(
      (t) => (
        <div
          className={`${
            t.visible ? 'toast-enter' : 'toast-exit'
          } max-w-md w-full bg-dark-2 shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5 transform transition-all duration-300`}
        >
          <div className="flex-1 w-0 p-4">
            <div className="flex items-start">
              <div className={`flex-shrink-0 pt-0.5 ${type === 'success' ? 'text-green-500' : 'text-red-500'}`}>
                {icon}
              </div>
              <div className="ml-3 flex-1">
                <p className="text-sm font-medium text-gray-100">{title}</p>
                <p className="mt-1 text-sm text-gray-400">{message}</p>
              </div>
            </div>
          </div>
          <div className="flex border-l border-dark-4">
            <button
              onClick={() => toast.dismiss(t.id)}
              className="w-full border border-transparent rounded-none rounded-r-lg p-4 flex items-center justify-center text-sm font-medium text-gray-400 hover:text-gray-300 focus:outline-none transition-colors duration-200 ease-in-out hover:bg-dark-3"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      ),
      {
        position: "top-right",
        duration: 3000,
      }
    );
  };

  const [previewCode, setPreviewCode] = useState('');
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [importCode, setImportCode] = useState('');
  const [thumbnailError, setThumbnailError] = useState(false);
  const [imageError, setImageError] = useState(false);

  // Preview URLs for images after variable replacement
  const [previewThumbnailUrl, setPreviewThumbnailUrl] = useState<string>('');
  const [previewImageUrl, setPreviewImageUrl] = useState<string>('');

  const formatDiscordText = (text: string | undefined): string => {
    if (!text) return '';
    
    // Sanitize the input to prevent XSS attacks
    const sanitized = text
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
    
    // First replace variables, then format markdown
    const textWithVars = replaceVariables(sanitized);
    
    // Replace Discord markdown with HTML
    return textWithVars
      // Bold
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/_([^_]+)_/g, '<em>$1</em>')
      // Underline
      .replace(/__(.*?)__/g, '<u>$1</u>')
      // Strikethrough
      .replace(/~~(.*?)~~/g, '<s>$1</s>')
      // Code Blocks
      .replace(/```([\s\S]*?)```/g, '<pre class="bg-dark-1 p-2 rounded text-sm font-mono whitespace-pre-wrap">$1</pre>')
      // Inline Code
      .replace(/`([^`]+)`/g, '<code class="bg-dark-1 px-1 py-0.5 rounded text-sm">$1</code>')
      // Line breaks
      .replace(/\n/g, '<br />');
  };

  const replaceVariables = (text: string): string => {
    if (!text) return '';

    return text
      // User variables
      .replace(/{user\.id}/g, mockData.user.id)
      .replace(/{user\.name}/g, mockData.user.name)
      .replace(/{user\.nick}/g, mockData.user.nick)
      .replace(/{user\.display}/g, mockData.user.display)
      .replace(/{user\.mention}/g, mockData.user.mention)
      .replace(/{user\.discriminator}/g, mockData.user.discriminator)
      .replace(/{user\.avatar}/g, mockData.user.avatar)
      .replace(/{user\.guild\.avatar}/g, mockData.user.guild.avatar)
      .replace(/{user\.joined_at}/g, formatTimestamp(mockData.user.joined_at))
      .replace(/{user\.created_at}/g, formatTimestamp(mockData.user.created_at))
      // Guild variables
      .replace(/{guild\.id}/g, mockData.guild.id)
      .replace(/{guild\.name}/g, mockData.guild.name)
      .replace(/{guild\.icon}/g, mockData.guild.icon)
      .replace(/{guild\.created_at}/g, formatTimestamp(mockData.guild.created_at))
      .replace(/{guild\.count}/g, mockData.guild.count.toString())
      .replace(/{guild\.count\.format}/g, formatOrdinal(mockData.guild.count))
      .replace(/{guild\.boost_count}/g, mockData.guild.boost_count.toString())
      .replace(/{guild\.boost_count\.format}/g, formatOrdinal(mockData.guild.boost_count))
      .replace(/{guild\.booster_count}/g, mockData.guild.booster_count.toString())
      .replace(/{guild\.booster_count\.format}/g, formatOrdinal(mockData.guild.booster_count))
      .replace(/{guild\.boost_tier}/g, mockData.guild.boost_tier.toString())
      .replace(/{guild\.vanity}/g, mockData.guild.vanity);
  };

  const formatTimestamp = (timestamp: string): string => {
    return new Date(parseInt(timestamp)).toLocaleString();
  };

  // Function to validate URLs against common security risks
  const validateUrl = (url: string | undefined): string => {
    if (!url) return '';
    
    // Create a URL object to parse the URL safely
    try {
      const parsedUrl = new URL(url);
      
      // Only allow http and https protocols
      if (parsedUrl.protocol !== 'http:' && parsedUrl.protocol !== 'https:') {
        return '';
      }
      
      return url;
    } catch (e) {
      // If URL is invalid, return empty string
      return '';
    }
  };

  const handleImageError = (type: 'thumbnail' | 'image' | 'authorIcon' | 'footerIcon') => {
    if (type === 'thumbnail') {
      setThumbnailError(true);
    } else if (type === 'image') {
      setImageError(true);
    }
  };

  const handleImageLoad = (type: 'thumbnail' | 'image' | 'authorIcon' | 'footerIcon') => {
    if (type === 'thumbnail') {
      setThumbnailError(false);
    } else if (type === 'image') {
      setImageError(false);
    }
  };

  // Update preview URLs when embed changes
  useEffect(() => {
    setPreviewThumbnailUrl(replaceVariables(embed.thumbnail || ''));
    setPreviewImageUrl(replaceVariables(embed.image || ''));
  }, [embed.thumbnail, embed.image]);

  const handleCopyCode = () => {
    navigator.clipboard.writeText(previewCode);
    showNotification(
      <Check className="h-6 w-6" />,
      "Copied to clipboard",
      "The embed code has been copied to your clipboard."
    );
  };

  const handleImport = () => {
    try {
      const newEmbed = parseEmbedCode(importCode);
      setEmbed(newEmbed);
      generateEmbedCode();
      showNotification(
        <Check className="h-6 w-6" />,
        "Import successful",
        "The embed code has been imported successfully."
      );
      setShowImportModal(false);
      setImportCode('');
    } catch (error) {
      showNotification(
        <AlertCircle className="h-6 w-6" />,
        "Import failed",
        "Invalid embed code format. Please check your input and try again.",
        'error'
      );
    }
  };

  const generateEmbedCode = () => {
    let code = '{embed}';
    if (embed.content) code += `$v{content: ${embed.content}}`;
    if (embed.title) code += `$v{title: ${embed.title}}`;
    if (embed.description) code += `$v{description: ${embed.description}}`;
    if (embed.url) code += `$v{url: ${embed.url}}`;
    if (embed.color) code += `$v{color: ${embed.color}}`;
    if (embed.author?.name) {
      code += `$v{author: name: ${embed.author.name}${embed.author.icon ? ` && icon: ${embed.author.icon}` : ''}${embed.author.url ? ` && url: ${embed.author.url}` : ''}}`;
    }
    if (embed.footer?.text) {
      code += `$v{footer: text: ${embed.footer.text}${embed.footer.icon ? ` && icon: ${embed.footer.icon}` : ''}}`;
    }
    if (embed.thumbnail) code += `$v{thumbnail: ${embed.thumbnail}}`;
    if (embed.image) code += `$v{image: ${embed.image}}`;
    embed.fields.forEach(field => {
      code += `$v{field: name: ${field.name} && value: ${field.value}${field.inline ? ' && inline' : ''}}`;
    });
    embed.buttons.forEach(button => {
      code += `$v{button: label: ${button.label} && style: ${button.style}${button.url ? ` && url: ${button.url}` : ''}${button.emoji ? ` && emoji: ${button.emoji}` : ''}}`;
    });
    setPreviewCode(code);
  };

  const addField = () => {
    setEmbed(prev => ({
      ...prev,
      fields: [...prev.fields, { name: '', value: '', inline: false }]
    }));
  };

  const removeField = (index: number) => {
    setEmbed(prev => ({
      ...prev,
      fields: prev.fields.filter((_, i) => i !== index)
    }));
  };

  const addButton = () => {
    setEmbed(prev => ({
      ...prev,
      buttons: [...prev.buttons, { label: '', style: 'primary' }]
    }));
  };

  const removeButton = (index: number) => {
    setEmbed(prev => ({
      ...prev,
      buttons: prev.buttons.filter((_, i) => i !== index)
    }));
  };

  // Helper function to escape special characters in regex
  const escapeRegExp = (string: string) => {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  };

  // Helper function to safely extract values from embed code
  const extractValue = (text: string, key: string, endDelimiter: string = '}') => {
    // Create a regex pattern that handles variables like {user.mention}
    const pattern = new RegExp(`${escapeRegExp(key)}:\\s*([^${escapeRegExp(endDelimiter)}]+)`, 'i');
    const match = text.match(pattern);
    return match ? match[1].trim() : '';
  };

  const parseEmbedCode = (code: string) => {
    try {
      const newEmbed: EmbedData = {
        fields: [],
        buttons: [],
        color: '#729bb0'
      };

      // Remove {embed} wrapper if present
      code = code.replace(/^\{embed\}/, '');

      // Match all $v{...} blocks, preserving variables like {user.mention}
      const blocks = [];
      let currentIndex = 0;
      let depth = 0;
      let startIndex = -1;

      // Parse the code character by character to handle nested braces correctly
      for (let i = 0; i < code.length; i++) {
        if (code.substring(i, i + 3) === '$v{' && depth === 0) {
          startIndex = i;
          depth = 1;
          i += 2; // Skip the 'v{'
        } else if (code[i] === '{' && depth > 0) {
          depth++;
        } else if (code[i] === '}' && depth > 0) {
          depth--;
          if (depth === 0 && startIndex !== -1) {
            blocks.push(code.substring(startIndex, i + 1));
            startIndex = -1;
          }
        }
      }

      blocks.forEach(block => {
        // Remove $v{ and } wrapper
        const content = block.slice(3, -1);

        if (content.startsWith('content:')) {
          newEmbed.content = content.slice(8).trim();
        } else if (content.startsWith('title:')) {
          newEmbed.title = content.slice(6).trim();
        } else if (content.startsWith('description:')) {
          newEmbed.description = content.slice(12).trim();
        } else if (content.startsWith('url:')) {
          newEmbed.url = content.slice(4).trim();
        } else if (content.startsWith('color:')) {
          newEmbed.color = content.slice(6).trim();
        } else if (content.startsWith('thumbnail:')) {
          newEmbed.thumbnail = content.slice(10).trim();
        } else if (content.startsWith('image:')) {
          newEmbed.image = content.slice(6).trim();
        } else if (content.startsWith('author:')) {
          const authorContent = content.slice(7).trim();
          
          // Handle author fields while preserving variables
          newEmbed.author = {};
          
          // Extract name, preserving variables
          if (authorContent.includes('name:')) {
            const nameMatch = authorContent.match(/name:\s*([^&]+)(?:&&|$)/);
            if (nameMatch) {
              newEmbed.author.name = nameMatch[1].trim();
            }
          }
          
          // Extract icon
          if (authorContent.includes('icon:')) {
            const iconMatch = authorContent.match(/icon:\s*([^&]+)(?:&&|$)/);
            if (iconMatch) {
              newEmbed.author.icon = iconMatch[1].trim();
            }
          }
          
          // Extract url
          if (authorContent.includes('url:')) {
            const urlMatch = authorContent.match(/url:\s*([^&]+)(?:&&|$)/);
            if (urlMatch) {
              newEmbed.author.url = urlMatch[1].trim();
            }
          }
        } else if (content.startsWith('footer:')) {
          const footerContent = content.slice(7).trim();
          
          // Handle footer fields while preserving variables
          newEmbed.footer = {};
          
          // Extract text, preserving variables
          if (footerContent.includes('text:')) {
            const textMatch = footerContent.match(/text:\s*([^&]+)(?:&&|$)/);
            if (textMatch) {
              newEmbed.footer.text = textMatch[1].trim();
            }
          }
          
          // Extract icon
          if (footerContent.includes('icon:')) {
            const iconMatch = footerContent.match(/icon:\s*([^&]+)(?:&&|$)/);
            if (iconMatch) {
              newEmbed.footer.icon = iconMatch[1].trim();
            }
          }
        } else if (content.startsWith('field:')) {
          const fieldContent = content.slice(6).trim();
          
          const field: Field = {
            name: '',
            value: '',
            inline: false
          };
          
          // Extract name, preserving variables
          if (fieldContent.includes('name:')) {
            const nameMatch = fieldContent.match(/name:\s*([^&]+)(?:&&|$)/);
            if (nameMatch) {
              field.name = nameMatch[1].trim();
            }
          }
          
          // Extract value, preserving variables
          if (fieldContent.includes('value:')) {
            const valueMatch = fieldContent.match(/value:\s*([^&]+)(?:&&|$)/);
            if (valueMatch) {
              field.value = valueMatch[1].trim();
            }
          }
          
          // Check for inline
          field.inline = fieldContent.includes(' && inline');
          
          newEmbed.fields.push(field);
        } else if (content.startsWith('button:')) {
          const buttonContent = content.slice(7).trim();
          
          const button: Button = {
            label: '',
            style: 'primary'
          };
          
          // Extract label, preserving variables
          if (buttonContent.includes('label:')) {
            const labelMatch = buttonContent.match(/label:\s*([^&]+)(?:&&|$)/);
            if (labelMatch) {
              button.label = labelMatch[1].trim();
            }
          }
          
          // Extract style
          if (buttonContent.includes('style:')) {
            const styleMatch = buttonContent.match(/style:\s*([^&]+)(?:&&|$)/);
            if (styleMatch) {
              const styleValue = styleMatch[1].trim();
              button.style = styleValue as Button['style'];
            }
          }
          
          // Extract url
          if (buttonContent.includes('url:')) {
            const urlMatch = buttonContent.match(/url:\s*([^&]+)(?:&&|$)/);
            if (urlMatch) {
              button.url = urlMatch[1].trim();
            }
          }

          // Extract emoji
          if (buttonContent.includes('emoji:')) {
            const emojiMatch = buttonContent.match(/emoji:\s*([^&]+)(?:&&|$)/);
            if (emojiMatch) {
              button.emoji = emojiMatch[1].trim();
            }
          }
          
          newEmbed.buttons.push(button);
        } else if (content === 'timestamp') {
          newEmbed.timestamp = true;
        }
      });

      return newEmbed;
    } catch (error) {
      console.error('Failed to parse embed code:', error);
      throw new Error('Invalid embed code format');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<Code />}
        title="Embed Builder"
        description="Create beautiful embeds for your Discord server"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
        {/* Builder Section - Left Side */}
        <div className="space-y-6">
          <div className="feature-card rounded-lg p-6 border border-dark-4">
            <h2 className="text-2xl font-bold mb-4">Embed Builder</h2>
            
            {/* Basic Settings */}
            <div className="space-y-4">
              {/* Color Picker */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Color</label>
                <div className="relative">
                  <div className="flex gap-2">
                    <button
                      className="w-10 h-10 rounded border border-dark-4"
                      style={{ backgroundColor: embed.color }}
                      onClick={() => setShowColorPicker(!showColorPicker)}
                    />
                    <input
                      type="text"
                      className="flex-1 px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                      value={embed.color}
                      onChange={e => setEmbed(prev => ({ ...prev, color: e.target.value }))}
                    />
                  </div>
                  {showColorPicker && (
                    <div className="absolute z-50 mt-2">
                      <div className="fixed inset-0" onClick={() => setShowColorPicker(false)} />
                      <div className="relative">
                        <HexColorPicker
                          color={embed.color}
                          onChange={color => {
                            setEmbed(prev => ({ ...prev, color }));
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Content */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Content</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                  value={embed.content || ''}
                  onChange={e => setEmbed(prev => ({ ...prev, content: e.target.value }))}
                />
              </div>

              {/* Author Settings */}
              <div className="grid grid-cols-3 gap-4">
                {/* Author Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Author Name</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                    value={embed.author?.name || ''}
                    onChange={e =>
                      setEmbed(prev => ({
                        ...prev,
                        author: { ...prev.author, name: e.target.value },
                      }))
                    }
                  />
                </div>
              
                {/* Author Icon URL + Preview */}
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Author Icon URL</label>
                  <div className="space-y-2">
                    <input
                      type="url"
                      className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                      value={embed.author?.icon || ''}
                      onChange={e =>
                        setEmbed(prev => ({
                          ...prev,
                          author: { ...prev.author, icon: e.target.value },
                        }))
                      }
                    />
                  </div>
                </div>
              
                {/* Author URL */}
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Author URL</label>
                  <input
                    type="url"
                    className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                    value={embed.author?.url || ''}
                    onChange={e =>
                      setEmbed(prev => ({
                        ...prev,
                        author: { ...prev.author, url: e.target.value },
                      }))
                    }
                  />
                </div>
              </div>

              {/* Title and URL side by side */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Title</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                    value={embed.title || ''}
                    onChange={e => setEmbed(prev => ({ ...prev, title: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">URL</label>
                  <input
                    type="url"
                    className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                    value={embed.url || ''}
                    onChange={e => setEmbed(prev => ({...prev, url: e.target.value }))}
                  />
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Description</label>
                <textarea
                  className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                  rows={3}
                  value={embed.description || ''}
                  onChange={e => setEmbed(prev => ({ ...prev, description: e.target.value }))}
                />
              </div>

              {/* Thumbnail and Image URLs side by side */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Thumbnail URL</label>
                  <div className="space-y-2">
                    <input
                      type="url"
                      className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                      value={embed.thumbnail || ''}
                      onChange={e => setEmbed(prev => ({ ...prev, thumbnail: e.target.value }))}
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Image URL</label>
                  <div className="space-y-2">
                    <input
                      type="url"
                      className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                      value={embed.image || ''}
                      onChange={e => setEmbed(prev => ({ ...prev, image: e.target.value }))}
                    />
                  </div>
                </div>
              </div>

              {/* Footer Settings */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Footer Text</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                    value={embed.footer?.text || ''}
                    onChange={e => setEmbed(prev => ({ 
                      ...prev, 
                      footer: { ...prev.footer, text: e.target.value }
                    }))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Footer Icon URL</label>
                  <input
                    type="url"
                    className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                    value={embed.footer?.icon || ''}
                    onChange={e => setEmbed(prev => ({ 
                      ...prev, 
                      footer: { ...prev.footer, icon: e.target.value }
                    }))}
                  />
                </div>
              </div>
            </div>

            {/* Fields */}
            <div className="mt-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Fields</h3>
                <button
                  onClick={addField}
                  className="flex items-center gap-2 px-3 py-1 rounded bg-theme/20 hover:bg-theme/30 text-theme transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  Add Field
                </button>
              </div>
              <div className="space-y-4">
                {embed.fields.map((field, index) => (
                  <div key={index} className="bg-[#0a0a0a] rounded-lg p-4">
                    <div className="flex justify-between mb-2">
                      <h4 className="font-medium">Field {index + 1}</h4>
                      <button
                        onClick={() => removeField(index)}
                        className="text-red-500 hover:text-red-400"
                      >
                        <Trash className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="space-y-2">
                      <input
                        type="text"
                        placeholder="Name"
                        className="w-full px-3 py-2 bg-[#111] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                        value={field.name}
                        onChange={e => {
                          const newFields = [...embed.fields];
                          newFields[index].name = e.target.value;
                          setEmbed(prev => ({ ...prev, fields: newFields }));
                        }}
                      />
                      <textarea
                        placeholder="Value"
                        className="w-full px-3 py-2 bg-[#111] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                        rows={3}
                        value={field.value}
                        onChange={e => {
                          const newFields = [...embed.fields];
                          newFields[index].value = e.target.value;
                          setEmbed(prev => ({ ...prev, fields: newFields }));
                        }}
                      />
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={field.inline}
                          onChange={e => {
                            const newFields = [...embed.fields];
                            newFields[index].inline = e.target.checked;
                            setEmbed(prev => ({ ...prev, fields: newFields }));
                          }}
                          className="rounded border-dark-4 text-theme focus:ring-theme"
                        />
                        <span className="text-sm text-gray-400">Inline</span>
                      </label>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Buttons */}
            <div className="mt-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Buttons</h3>
                <button
                  onClick={addButton}
                  className="flex items-center gap-2 px-3 py-1 rounded bg-theme/20 hover:bg-theme/30 text-theme transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  Add Button
                </button>
              </div>
              <div className="space-y-4">
                {embed.buttons.map((button, index) => (
                  <div key={index} className="bg-[#0a0a0a] rounded-lg p-4">
                    <div className="flex justify-between mb-2">
                      <h4 className="font-medium">Button {index + 1}</h4>
                      <button
                        onClick={() => removeButton(index)}
                        className="text-red-500 hover:text-red-400"
                      >
                        <Trash className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="space-y-2">
                      <input
                        type="text"
                        placeholder="Label"
                        className="w-full px-3 py-2 bg-[#111] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                        value={button.label}
                        onChange={e => {
                          const newButtons = [...embed.buttons];
                          newButtons[index].label = e.target.value;
                          setEmbed(prev => ({ ...prev, buttons: newButtons }));
                        }}
                      />
                      <select
                        className="w-full px-3 py-2 bg-[#111] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                        value={button.style}
                        onChange={e => {
                          const newButtons = [...embed.buttons];
                          newButtons[index].style = e.target.value as any;
                          setEmbed(prev => ({ ...prev, buttons: newButtons }));
                        }}
                      >
                        <option value="primary">Primary</option>
                        <option value="secondary">Secondary</option>
                        <option value="success">Success</option>
                        <option value="danger">Danger</option>
                      </select>
                      <input
                        type="url"
                        placeholder="URL (optional)"
                        className="w-full px-3 py-2 bg-[#111] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                        value={button.url || ''}
                        onChange={e => {
                          const newButtons = [...embed.buttons];
                          newButtons[index].url = e.target.value;
                          setEmbed(prev => ({ ...prev, buttons: newButtons }));
                        }}
                      />
                      <input
                        type="text"
                        placeholder="Emoji (e.g. <:skully:1338653277151035413>)"
                        className="w-full px-3 py-2 bg-[#111] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
                        value={button.emoji || ''}
                        onChange={e => {
                          const newButtons = [...embed.buttons];
                          newButtons[index].emoji = e.target.value;
                          setEmbed(prev => ({ ...prev, buttons: newButtons }));
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Preview Section - Right Side */}
        <div className="space-y-6 lg:sticky lg:top-20">
          <div className="feature-card rounded-lg p-6 border border-dark-4">
            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 mb-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 flex-1">
                <button
                  onClick={generateEmbedCode}
                  className="flex items-center justify-center gap-2 px-4 py-2 w-full rounded-lg bg-theme hover:bg-theme/90 text-white transition-colors"
                >
                  <Code className="w-4 h-4" />
                  <span className="hidden sm:inline">Generate</span>
                </button>
                <button
                  onClick={handleCopyCode}
                  className="flex items-center justify-center gap-2 px-4 py-2 w-full rounded-lg bg-[#0a0a0a] hover:bg-dark-1 text-white transition-colors"
                >
                  <Copy className="w-4 h-4" />
                  <span className="hidden sm:inline">Copy</span>
                </button>
                <button
                  onClick={() => setShowImportModal(true)}
                  className="flex items-center justify-center gap-2 px-4 py-2 w-full rounded-lg bg-[#0a0a0a] hover:bg-dark-1 text-white transition-colors"
                >
                  <Import className="w-4 h-4" />
                  <span className="hidden sm:inline">Import</span>
                </button>
              </div>
            </div>

            {/* Discord Embed Preview */}
            <div className="bg-[#36393f] rounded-lg p-4 mb-4">
              {embed.content && <p className="mb-2 text-gray-100 break-words" dangerouslySetInnerHTML={{ __html: formatDiscordText(embed.content) }} />}
              <div className="border-l-4 relative" style={{ borderColor: embed.color }}>
                {/* Thumbnail - Always positioned in top right */}
                {previewThumbnailUrl && !thumbnailError && (
                  <div className="absolute -top-2 -right-2 w-20 h-20">
                    <img 
                      src={validateUrl(replaceVariables(previewThumbnailUrl))}
                      alt="" 
                      className="w-full h-full object-cover rounded"
                      onError={() => handleImageError('thumbnail')}
                      onLoad={() => handleImageLoad('thumbnail')}
                    />
                  </div>
                )}

                <div className="pl-4">
                  {embed.author && (
                    <div className="flex items-center gap-2 mb-2">
                      {embed.author.icon && (
                        <img src={validateUrl(replaceVariables(embed.author.icon))} alt="" className="w-6 h-6 rounded-full" />
                      )}
                      {embed.author.url ? (
                        <a href={validateUrl(embed.author.url)} className="text-blue-400 hover:underline break-words" target="_blank" rel="noopener noreferrer">
                          <span dangerouslySetInnerHTML={{ __html: formatDiscordText(embed.author.name) }} />
                        </a>
                      ) : (
                        <span className="text-gray-100 break-words" dangerouslySetInnerHTML={{ __html: formatDiscordText(embed.author.name) }} />
                      )}
                    </div>
                  )}
                  
                  {embed.title && (
                    <div className="font-semibold mb-2 text-gray-100 break-words">
                      {embed.url ? (
                        <a href={validateUrl(embed.url)} className="text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">
                          <span dangerouslySetInnerHTML={{ __html: formatDiscordText(embed.title) }} />
                        </a>
                      ) : (
                        <span dangerouslySetInnerHTML={{ __html: formatDiscordText(embed.title) }} />
                      )}
                    </div>
                  )}
                  
                  {embed.description && (
                    <p className="text-gray-300 mb-4 break-words whitespace-pre-wrap" 
                      dangerouslySetInnerHTML={{ __html: formatDiscordText(embed.description) }} 
                    />
                  )}
                  
                  {embed.fields.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                      {embed.fields.map((field, index) => (
                        <div key={index} className={field.inline ? 'col-span-1' : 'col-span-2'}>
                          <h4 className="font-semibold text-gray-100 break-words"
                            dangerouslySetInnerHTML={{ __html: formatDiscordText(field.name) }}
                          />
                          <p className="text-gray-300 break-words whitespace-pre-wrap"
                            dangerouslySetInnerHTML={{ __html: formatDiscordText(field.value) }}
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Main Image */}
                  {previewImageUrl && !imageError && (
                    <div className="max-w-full mb-4">
                      <img 
                        src={validateUrl(replaceVariables(previewImageUrl))}
                        alt="" 
                        className="max-w-full rounded"
                        onError={() => handleImageError('image')}
                        onLoad={() => handleImageLoad('image')}
                      />
                    </div>
                  )}

                  {embed.footer && (
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                      {embed.footer.icon && (
                        <img src={validateUrl(replaceVariables(embed.footer.icon))} alt="" className="w-5 h-5 rounded-full" />
                      )}
                      <span className="break-words" 
                        dangerouslySetInnerHTML={{ __html: formatDiscordText(embed.footer.text) }}
                      />
                    </div>
                  )}
                </div>
              </div>

              {embed.buttons.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-4">
                  {embed.buttons.map((button, index) => {
                    const buttonStyles = {
                      primary: 'bg-[#5865F2] hover:bg-[#4752C4]',
                      secondary: 'bg-gray-500 hover:bg-gray-600',
                      success: 'bg-green-600 hover:bg-green-700',
                      danger: 'bg-red-600 hover:bg-red-700'
                    };

                    // Parse emoji ID and type
                    const emojiMatch = button.emoji?.match(/<(a)?:[\w]+:(\d+)>/);
                    const emojiId = emojiMatch?.[2];
                    const isAnimated = !!emojiMatch?.[1];

                    return (
                      <button
                        key={index}
                        className={`px-4 py-2 rounded-lg text-white transition-colors flex items-center gap-2 ${buttonStyles[button.style]}`}
                      >
                        {emojiId && (
                          <img
                            src={validateUrl(`https://cdn.discordapp.com/emojis/${emojiId}.${isAnimated ? 'gif' : 'png'}`)}
                            alt="emoji"
                            className="w-5 h-5"
                          />
                        )}
                        {button.label}
                        {button.url && <ExternalLink className="w-4 h-4" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Code Preview */}
            {previewCode && (
              <div className="bg-[#0a0a0a] rounded-lg p-4 font-mono text-sm">
                <pre className="whitespace-pre-wrap break-all text-gray-300 overflow-x-auto">{previewCode}</pre>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Import Modal */}
      <Modal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        title="Import Embed Code"
      >
        <div className="space-y-4">
          <textarea
            className="w-full px-3 py-2 bg-[#0a0a0a] rounded-lg border border-dark-4 focus:outline-none focus:border-theme text-white"
            rows={6}
            value={importCode}
            onChange={e => setImportCode(e.target.value)}
            placeholder="Paste your embed code here..."
          />
          <button
            onClick={handleImport}
            className="w-full bg-theme hover:bg-theme/90 text-white px-4 py-2 rounded-lg transition-colors"
          >
            Import
          </button>
        </div>
      </Modal>
    </div>
  );
}

export default EmbedBuilder;