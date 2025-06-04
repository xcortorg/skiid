import React from 'react';
import { Lock, Shield, Database, Clock, FileText, Bell, Mail } from 'lucide-react';
import PageHeader from '../components/PageHeader';

function Privacy() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <PageHeader
        icon={<Lock />}
        title="Privacy Policy"
        description="How we handle and protect your data"
      />

      <div className="feature-card rounded-lg p-6 mb-8">
        <p className="text-gray-400 mb-4">Last updated and effective: May 21, 2024, 3:26 PM CET</p>
        <p className="text-gray-400">
          Any information we collect is not used maliciously. If any information stated here seems/is misleading, please contact us immediately at contact@evelina.bot.
        </p>
      </div>
      
      <div className="space-y-8 text-gray-300">
        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <Database className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Collected Information</h2>
          </div>
          <ul className="list-disc pl-6 space-y-2">
            <li>Guild IDs</li>
            <li>Guild Names</li>
            <li>Channel IDs</li>
            <li>Role IDs</li>
            <li>User IDs</li>
            <li>Message Timestamps</li>
            <li>Message IDs</li>
            <li>Nicknames and Usernames</li>
            <li>Avatars</li>
            <li>Message Content when a command is ran (stored for a max of 14 days) or when arguments are passed for commands</li>
            <li>Last deleted message content (stored for a max of 2 hours or less, 19 entries allowed)</li>
            <li>Last message edit history (stored for a max of 2 hours or less, 19 entries allowed)</li>
          </ul>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <Shield className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Why do you need the data and how is it used?</h2>
          </div>
          <div className="space-y-4">
            <p>When a command is invoked, we store that message content for a maximum of 14 days for debugging purposes. We also store a maximum of 18 entries for edited messages and sniping messages that will expire in two hours or less in volatile memory.</p>
            <p>Guild IDs, Channel IDs, Role IDs, User IDs and Message IDs are all stored for our system to aggregate values to find data.</p>
            <p>Nickname and Username changes are logged in order for the "namehistory" command to function. Users can clear this data themselves at any time.</p>
            <p>Avatar changes are logged in order for the "avatarhistory" command to function. Users can clear this data themselves at any time.</p>
            <p>Guild name changes are logged in order for the "gnames" command to function. Server administrators can clear this data themselves at any time.</p>
          </div>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <FileText className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Who is your collected information shared with?</h2>
          </div>
          <p>We do not sell and expose your information to others/third parties by any means.</p>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <Clock className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Data removal</h2>
          </div>
          <p>Email contact@evelina.bot to have your data deleted. Note that when emailing, please be specific with what information that you want gone and provide ownership of your Discord account. Response time may vary and could take up to two weeks.</p>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <Mail className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Request data</h2>
          </div>
          <p>Email contact@evelina.bot for all of your data that we are currently storing. Response time may vary and could take up to 7 days.</p>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <Bell className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Changes to the Privacy Policy</h2>
          </div>
          <p>We can update these terms at any time without notice. Continuing to use our services after any changes will mean that you agree with these terms and violation of our terms of service could result in a permanent ban across all of our services.</p>
        </section>
      </div>
    </div>
  );
}

export default Privacy;