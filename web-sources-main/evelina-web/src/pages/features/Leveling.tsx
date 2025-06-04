import React from 'react';
import { Star, Trophy, Settings, Award, Crown, Gift, BarChart2, Zap, Target, Mic2, Bell } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

function Leveling() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      {/* Header */}
      <PageHeader
        icon={<Star />}
        title="Leveling System"
        description="Engage your community with text and voice leveling"
      />

      {/* Main Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Trophy className="w-6 h-6 text-theme" />
            Text Leveling
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Earn XP and levels through chat activity.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span>Level 5</span>
                  <div className="h-2 w-32 bg-dark-1 rounded-full overflow-hidden">
                    <div className="h-full w-3/4 bg-theme rounded-full"></div>
                  </div>
                  <span>750/1000 XP</span>
                </div>
                <code className="text-sm text-gray-300 block mt-4">
                  # Text Commands<br />
                  ;level<br />
                  ;level leaderboard<br />
                  ;level rewards
                </code>
              </div>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Mic2 className="w-6 h-6 text-theme" />
            Voice Leveling
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Gain experience while being active in voice channels.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span>Voice Time</span>
                  <span>1h 30m</span>
                </div>
                <code className="text-sm text-gray-300 block mt-4">
                  # Voice Commands<br />
                  ;voicetrack leveling<br />
                  ;voicetrack leveling enable<br />
                  ;voicetrack leveling disable
                </code>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Level Rewards */}
      <div className="feature-card rounded-xl p-8 mb-16">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center">
            <Gift className="w-6 h-6 text-theme" />
          </div>
          <h2 className="text-2xl font-bold">Level Rewards</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-dark-2 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <Award className="w-5 h-5 text-theme" />
              <h3 className="text-lg font-semibold">Level 5</h3>
            </div>
            <ul className="space-y-2 text-gray-400">
              <li>• Member Role</li>
              <li>• Custom Color</li>
              <li>• Image Permissions</li>
            </ul>
          </div>
          <div className="bg-dark-2 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <Crown className="w-5 h-5 text-theme" />
              <h3 className="text-lg font-semibold">Level 10</h3>
            </div>
            <ul className="space-y-2 text-gray-400">
              <li>• Elite Role</li>
              <li>• Custom Nickname</li>
              <li>• Reaction Permissions</li>
            </ul>
          </div>
          <div className="bg-dark-2 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <Star className="w-5 h-5 text-theme" />
              <h3 className="text-lg font-semibold">Level 20</h3>
            </div>
            <ul className="space-y-2 text-gray-400">
              <li>• VIP Role</li>
              <li>• Custom Profile</li>
              <li>• Special Commands</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Additional Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <BarChart2 className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Leaderboards</h3>
          <p className="text-gray-400">
            Compete with other members on global and voice leaderboards.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Zap className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">XP Boosters</h3>
          <p className="text-gray-400">
            Earn double XP during events and with special roles.
          </p>
        </div>
      </div>
    </div>
  );
}

export default Leveling;