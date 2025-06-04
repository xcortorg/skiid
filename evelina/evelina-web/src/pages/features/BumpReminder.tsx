import React from 'react';
import { Bell, Award, Crown, Star, Clock, BarChart2, Gift, Shield } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

function BumpReminder() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<Bell />}
        title="Bump Reminder"
        description="Never miss a server bump again"
      />

      {/* Example Messages */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Bell className="w-6 h-6 text-theme" />
            Bump Messages
          </h2>
          <div className="space-y-4">
            {/* Bump Success Message */}
            <div className="bg-dark-2 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <img 
                  src="https://cdn.evelina.bot/web/bump_icon.png"
                  alt="Evelina"
                  className="w-10 h-10 rounded-full"
                />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-theme">DISBOARD</span>
                    <span className="text-xs text-gray-400">APP</span>
                  </div>
                  <p className="text-gray-300 mt-1">
                    Bump successful!!<br />
                    Check it out on <span className="text-theme">DISBOARD</span>
                  </p>
                  <div className="mt-2">
                    <img 
                      src="https://cdn.evelina.bot/web/bump_banner.png"
                      alt="Bump Success"
                      className="rounded-lg w-full"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Reminder Message */}
            <div className="bg-dark-2 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <img 
                  src="https://r.emogir.ls/evelina-pfp.png"
                  alt="Evelina"
                  className="w-10 h-10 rounded-full"
                />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-theme">Evelina</span>
                    <span className="text-xs text-gray-400">APP</span>
                  </div>
                  <p className="text-gray-300 mt-1">
                    Thank you for bumping the server! I will remind you in <span className="font-semibold">2 hours</span> to do it again
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Shield className="w-6 h-6 text-theme" />
            Setup & Commands
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Easy setup and management of your bump reminders.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <code className="text-sm text-gray-300">
                # Thankyou Message<br />
                ;bump thankyou [embed]<br /><br />
                # Reminder Message<br />
                ;bump reminder [embed]<br /><br />
                # Information<br />
                ;bump leaderboard<br /><br />
              </code>
            </div>
          </div>
        </div>
      </div>

      {/* Additional Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Clock className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Auto Reminders</h3>
          <p className="text-gray-400">
            Get automatic notifications when it's time to bump your server again.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <BarChart2 className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Statistics</h3>
          <p className="text-gray-400">
            Track your bump history and view detailed statistics.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Shield className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Leaderboard</h3>
          <p className="text-gray-400">
            Compete with other servers and climb the bump leaderboard.
          </p>
        </div>
      </div>
    </div>
  );
}

export default BumpReminder;