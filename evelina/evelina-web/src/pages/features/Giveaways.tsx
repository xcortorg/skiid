import React from 'react';
import { Gift, Clock, Users, Trophy, Settings, Star, Crown, Shield, Bell } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

function Giveaways() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<Gift />}
        title="Giveaways System"
        description="Run exciting giveaways to engage your community"
      />

      {/* Main Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Gift className="w-6 h-6 text-theme" />
            Create Giveaways
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Start giveaways with customizable duration, winners, and requirements.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <code className="text-sm text-gray-300">
                # Start a giveaway<br />
                ;gstart 1h 1w Nitro<br /><br />
                # Start with requirements<br />
                ;gstart 12h 2w Discord Nitro --level 10 --role @Booster<br /><br />
                # Quick giveaway<br />
                ;gquick 1w Nitro Classic
              </code>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Settings className="w-6 h-6 text-theme" />
            Manage Giveaways
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Full control over your active giveaways.
            </p>
            <div className="space-y-2">
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm">gend [message-id]</code>
                <span className="text-gray-400 ml-3">End a giveaway early</span>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm">greroll [message-id]</code>
                <span className="text-gray-400 ml-3">Reroll winners</span>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm">gcancel [message-id]</code>
                <span className="text-gray-400 ml-3">Cancel a giveaway</span>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm">glist</code>
                <span className="text-gray-400 ml-3">List active giveaways</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Requirements Section */}
      <div className="feature-card rounded-xl p-8 mb-16">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center">
            <Shield className="w-6 h-6 text-theme" />
          </div>
          <h2 className="text-2xl font-bold">Entry Requirements</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <p className="text-gray-400 mb-4">
              Set custom requirements for giveaway participation.
            </p>
            <ul className="space-y-2 text-gray-400">
              <li>• Minimum server level</li>
              <li>• Required roles</li>
              <li>• Account age</li>
              <li>• Server join date</li>
              <li>• Message count</li>
              <li>• Voice activity</li>
            </ul>
          </div>
          <div className="bg-dark-2 rounded-lg p-4">
            <code className="text-sm text-gray-300">
              # Example requirements<br />
              --level 5<br />
              --role @Member<br />
              --age 30d<br />
              --joined 7d<br />
              --messages 100<br />
              --voice 2h
            </code>
          </div>
        </div>
      </div>

      {/* Additional Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Bell className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Notifications</h3>
          <p className="text-gray-400">
            Automatic winner notifications and reminders for ending giveaways.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Star className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Bonus Entries</h3>
          <p className="text-gray-400">
            Give extra entries to specific roles or boosters.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Crown className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Premium Features</h3>
          <p className="text-gray-400">
            Access to advanced features like multi-prize giveaways and custom messages.
          </p>
        </div>
      </div>
    </div>
  );
}

export default Giveaways;