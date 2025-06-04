import React from 'react';
import { Shield, Link2, MessageSquare, AlertTriangle, Ban, Settings } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

function AutoModeration() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<Shield />}
        title="Auto Moderation"
        description="Powerful tools to keep your server safe"
      />

      {/* Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Link2 className="w-6 h-6 text-theme" />
            Invite, Repeated Messages & Spam Filter
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Automatically detect and remove unwanted Discord invites and malicious links. It also filters out spam messages.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <code className="text-sm text-gray-300">
                ;automod words enable<br />
                ;automod repeat enable<br />
                ;automod spam enable
              </code>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <MessageSquare className="w-6 h-6 text-theme" />
            Bad Words Filter
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Filter out profanity and inappropriate content with our customizable word filter.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <code className="text-sm text-gray-300">
                ;automod words enable<br />
                ;automod words add [word]<br />
                ;automod words remove [word]
              </code>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-theme" />
            Antinuke System
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Protect your server from raids and malicious actions with our advanced antinuke system.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <code className="text-sm text-gray-300">
                ;antinuke enable<br />
                ;antinuke config<br />
                ;antinuke logs [channel]<br />
                ;antinuke admin add [user]
              </code>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Ban className="w-6 h-6 text-theme" />
            Spam Protection
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Advanced spam & repeated message detection to keep your server clean and spam-free.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <code className="text-sm text-gray-300">
                ;automod spam enable<br />
                ;automod spam rate [amount]<br />
                ;automod spam message [mode]<br />
                ;automod spam timeout [option]
              </code>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration Section */}
      <div className="feature-card rounded-xl p-8">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center">
            <Settings className="w-6 h-6 text-theme" />
          </div>
          <h2 className="text-2xl font-bold">Easy Configuration</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <p className="text-gray-400 mb-4">
              Configure auto-moderation settings with simple commands or through our web dashboard.
            </p>
            <ul className="space-y-2 text-gray-400">
              <li>• Customizable punishment system</li>
              <li>• Whitelist trusted users and roles</li>
              <li>• Set custom filter thresholds</li>
              <li>• Detailed logging options</li>
            </ul>
          </div>
          <div className="bg-dark-2 rounded-lg p-4">
            <code className="text-sm text-gray-300">
              # Auto Moderation Commands<br />
              Invites<br />
              Joins<br />
              Links<br />
              Linksedit<br />
              Repeat<br />
              Spam<br />
              Words<br />
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AutoModeration;