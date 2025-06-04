import React from 'react';
import { RotateCcw, Ban, Clock, FileCheck, HelpCircle, AlertTriangle, RefreshCcw } from 'lucide-react';
import PageHeader from '../components/PageHeader';

function Refund() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <PageHeader
        icon={<RotateCcw />}
        title="Refund Policy"
        description="Our refund terms and conditions"
      />

      <div className="feature-card rounded-lg p-6 mb-8">
        <p className="text-gray-400 mb-4">Last updated and effective: May 21, 2024 - 2025, 3:26 PM CET</p>
        <p className="text-gray-400">
          We ("Evelina", "Evelina Bot", "us", "our") have a strict policy on refunds and will deny you for any refund request for one of the following reasons listed.
        </p>
      </div>
      
      <div className="space-y-8 text-gray-300">
        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <Ban className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">No refunds will be issued if:</h2>
          </div>
          <ul className="list-disc pl-6 space-y-2">
            <li>You elude a ban or blacklist issued by using alternative accounts or sending other individuals to make a payment on your behalf without disclosing it.</li>
            <li>You are being disrespectful to Evelina itself or Evelina developers along with moderators or any support team.</li>
            <li>A purchase has already been made for a server that you made again (another server will be whitelisted).</li>
            <li>A command or any other feature has been used by you or any of your server members.</li>
            <li>A full 24 hour cycle has progressed since the purchase by you.</li>
            <li>You are a blacklisted user across all of our services.</li>
            <li>You have malicious intentions with your refund.</li>
            <li>You are forging or hiding details.</li>
          </ul>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Changes to the Refund Policy</h2>
          </div>
          <p>We can update these terms at any time without notice. Continuing to use our services after any changes will mean that you agree with these terms and violation of our terms of service could result in a permanent ban across all of our services.</p>
        </section>
      </div>
    </div>
  );
}

export default Refund;