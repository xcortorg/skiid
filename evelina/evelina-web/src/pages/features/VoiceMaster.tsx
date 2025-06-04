import React from 'react';
import { Mic2, Settings, Users, Lock, Volume2, Crown, Shield, UserPlus } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

function VoiceMaster() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<Mic2 />}
        title="Voice Master"
        description="Create dynamic voice channels for your community"
      />

      {/* Main Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Settings className="w-6 h-6 text-theme" />
            Channel Controls
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Full control over your temporary voice channels.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <code className="text-sm text-gray-300">
                # Channel Commands<br />
                ;voice limit [number]<br />
                ;voice name [name]<br />
                ;voice lock<br />
                ;voice unlock<br />
                ;voice hide<br />
                ;voice unhide<br />
                ;voice permit @user<br />
                ;voice reject @user<br />
                ;voice claim
              </code>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Users className="w-6 h-6 text-theme" />
            User Management
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Manage who can join and interact with your voice channel.
            </p>
            <div className="space-y-2">
              <div className="bg-dark-2 p-3 rounded-lg flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-theme" />
                  Lock Channel
                </span>
                <code className="text-sm">voice lock</code>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <UserPlus className="w-4 h-4 text-theme" />
                  Allow User
                </span>
                <code className="text-sm">voice permit @user</code>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-theme" />
                  Reject User
                </span>
                <code className="text-sm">voice reject @user</code>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Setup Guide */}
      <div className="feature-card rounded-xl p-8 mb-16">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center">
            <Settings className="w-6 h-6 text-theme" />
          </div>
          <h2 className="text-2xl font-bold">Quick Setup</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <p className="text-gray-400 mb-4">
              Set up your voicemaster system in minutes with our simple commands.
            </p>
            <ul className="space-y-2 text-gray-400">
              <li>• Create a voice channel category</li>
              <li>• Set up the join-to-create channel</li>
              <li>• Configure default settings</li>
              <li>• Set up permissions</li>
            </ul>
          </div>
          <div className="bg-dark-2 rounded-lg p-4">
            <code className="text-sm text-gray-300">
              # Setup voicemaster<br />
              ;voicemaster setup<br /><br />
              # Configure settings<br />
              ;voicemaster savesettings on<br /><br />
              # Set default name format<br />
              ;voicemaster name {`{user.display_name}'s vc`}
            </code>
          </div>
        </div>
      </div>

      {/* Additional Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Volume2 className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Channel Settings</h3>
          <p className="text-gray-400">
            Customize bitrate, user limit, and region settings for your voice channels.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Crown className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Owner Controls</h3>
          <p className="text-gray-400">
            Transfer ownership, kick users, and manage channel permissions.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Shield className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Advanced Security</h3>
          <p className="text-gray-400">
            Set up whitelists, blacklists, and role-based access controls.
          </p>
        </div>
      </div>
    </div>
  );
}

export default VoiceMaster;