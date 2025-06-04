import React from 'react';
import { ToggleLeft, Layout, Settings, Palette, Shield, MessageSquare, Layers, Code } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

function ButtonRoles() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<ToggleLeft />}
        title="Button Roles"
        description="Simplify role management with interactive buttons"
      />

      {/* Main Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Layout className="w-6 h-6 text-theme" />
            Button Styles
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Choose from different button styles and colors.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-dark-2 p-4 rounded-lg">
                <h3 className="font-semibold mb-2">Primary Style</h3>
                <div className="bg-[#5865F2] text-white px-4 py-2 rounded text-center">
                  Gaming Role
                </div>
              </div>
              <div className="bg-dark-2 p-4 rounded-lg">
                <h3 className="font-semibold mb-2">Success Style</h3>
                <div className="bg-green-600 text-white px-4 py-2 rounded text-center">
                  Events Role
                </div>
              </div>
              <div className="bg-dark-2 p-4 rounded-lg">
                <h3 className="font-semibold mb-2">Danger Style</h3>
                <div className="bg-red-600 text-white px-4 py-2 rounded text-center">
                  NSFW Role
                </div>
              </div>
              <div className="bg-dark-2 p-4 rounded-lg">
                <h3 className="font-semibold mb-2">Secondary Style</h3>
                <div className="bg-gray-600 text-white px-4 py-2 rounded text-center">
                  News Role
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Settings className="w-6 h-6 text-theme" />
            Setup Commands
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Create and manage role buttons with simple commands.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <code className="text-sm text-gray-300">
                # Create button roles<br />
                ;buttonrole create<br />
                ;buttonrole add @role [label] [style]<br />
                ;buttonrole remove [message-id] [button-id]<br />
                ;buttonrole edit [message-id] [button-id] [property] [value]<br />
                ;buttonrole list
              </code>
            </div>
          </div>
        </div>
      </div>

      {/* Example Panels */}
      <div className="feature-card rounded-xl p-8 mb-16">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center">
            <MessageSquare className="w-6 h-6 text-theme" />
          </div>
          <h2 className="text-2xl font-bold">Example Panels</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="bg-dark-2 rounded-lg p-6">
            <h3 className="text-xl font-bold mb-4">Game Roles</h3>
            <p className="text-gray-400 mb-4">Select your favorite games to get notified about gaming events!</p>
            <div className="space-y-2">
              <button className="w-full bg-[#5865F2] hover:bg-[#4752C4] text-white px-4 py-2 rounded transition-colors">
                🎮 Minecraft
              </button>
              <button className="w-full bg-[#5865F2] hover:bg-[#4752C4] text-white px-4 py-2 rounded transition-colors">
                🚗 GTA V
              </button>
              <button className="w-full bg-[#5865F2] hover:bg-[#4752C4] text-white px-4 py-2 rounded transition-colors">
                ⚔️ Valorant
              </button>
            </div>
          </div>
          <div className="bg-dark-2 rounded-lg p-6">
            <h3 className="text-xl font-bold mb-4">Notification Roles</h3>
            <p className="text-gray-400 mb-4">Choose what you want to be notified about!</p>
            <div className="space-y-2">
              <button className="w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded transition-colors">
                📢 Announcements
              </button>
              <button className="w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded transition-colors">
                🎉 Events
              </button>
              <button className="w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded transition-colors">
                🎁 Giveaways
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Additional Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Palette className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Custom Styling</h3>
          <p className="text-gray-400">
            Customize button colors, labels, and emojis to match your server theme.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Layers className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Multiple Panels</h3>
          <p className="text-gray-400">
            Create multiple role panels for different categories and purposes.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Code className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Advanced Options</h3>
          <p className="text-gray-400">
            Set up role requirements, cooldowns, and custom messages.
          </p>
        </div>
      </div>
    </div>
  );
}

export default ButtonRoles;