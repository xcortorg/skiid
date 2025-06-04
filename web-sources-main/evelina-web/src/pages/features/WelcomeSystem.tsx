import React from 'react';
import { UserPlus, MessageSquare, Settings, Layout, Image, Palette, LogIn } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

function WelcomeSystem() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<LogIn />}
        title="Welcome System"
        description="Greet new members with customizable welcome messages"
      />

      {/* Main Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Layout className="w-6 h-6 text-theme" />
            Custom Channel Messages
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Set up different welcome messages for each channel in your server.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <code className="text-sm text-gray-300">
                # Add welcome message<br />
                ;welcome add<br /><br />
                # Test welcome message<br />
                ;welcome test<br /><br />
                # Configure settings<br />
                ;welcome config
              </code>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <MessageSquare className="w-6 h-6 text-theme" />
            Message Customization
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Create fully customizable welcome messages with variables and formatting.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <div className="border-l-4 border-theme p-4 rounded bg-dark-1">
                <h3 className="text-lg font-semibold mb-2">Welcome {`{user_name}`}!</h3>
                <p className="text-gray-400">You are member #{`{guild_count}`}</p>
                <div className="mt-2 text-sm text-gray-500">
                  Joined: {`{user_joined_at}`}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Variables Section */}
      <div className="feature-card rounded-xl p-8 mb-16">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center">
            <Settings className="w-6 h-6 text-theme" />
          </div>
          <h2 className="text-2xl font-bold">Available Variables</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <p className="text-gray-400 mb-4">
              Use these variables to create dynamic welcome messages.
            </p>
            <div className="space-y-2">
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm">{`{user_name}`}</code>
                <span className="text-gray-400 ml-3">Member's username</span>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm">{`{guild_name}`}</code>
                <span className="text-gray-400 ml-3">Server name</span>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm">{`{guild_count}`}</code>
                <span className="text-gray-400 ml-3">Member count</span>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm">{`{user_joined_at}`}</code>
                <span className="text-gray-400 ml-3">Join date</span>
              </div>
            </div>
          </div>
          <div className="bg-dark-2 rounded-lg p-4">
            <code className="text-sm text-gray-300">
              Welcome {`{user_name}`} to {`{guild_name}`}!<br />
              You are our {`{guild_count}`}th member<br />
              Joined on {`{user_joined_at}`}
            </code>
          </div>
        </div>
      </div>

      {/* Additional Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Image className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Custom Images</h3>
          <p className="text-gray-400">
            Add custom welcome images and banners to your messages.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Palette className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Embed Customization</h3>
          <p className="text-gray-400">
            Customize colors, fields, and layout of welcome embeds.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <UserPlus className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Multiple Channels</h3>
          <p className="text-gray-400">
            Send different welcome messages to multiple channels.
          </p>
        </div>
      </div>
    </div>
  );
}

export default WelcomeSystem;