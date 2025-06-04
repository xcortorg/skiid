import React from 'react';
import { AlertTriangle, Ban, Bell, BotIcon, CoinsIcon, Delete, DeleteIcon, DollarSign, ScrollText, Trash } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { BiMoney } from 'react-icons/bi';

function Economy() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <PageHeader
        icon={<CoinsIcon />}
        title="Economy Rules"
        description="Our economy rules and guidelines for Evelina Discord bot."
      />

      <div className="feature-card rounded-lg p-6 mb-8">
        <p className="text-gray-400 mb-4">Last updated and effective: March 16, 2025, 01:14 PM CET</p>
        <p className="text-gray-400">
          Any information we collect is not used maliciously. If any information stated here seems/is misleading, please contact us immediately at contact@evelina.bot.
        </p>
      </div>
      
      <div className="space-y-8 text-gray-300">
        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Disclaimer</h2>
          </div>
          <p>Violating any of those rules will result in a permanent blacklist for economy commands. In extreme cases, you can be blacklisted from using the bot at all.</p>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <ScrollText className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">General</h2>
          </div>
          <p>By using evelina's economy commands, you agree to refrain from certain actions, which include:</p>
          <ul className="list-disc pl-6 mt-4 space-y-2">
            <li>Abusing any kind of bug, especially if you gain any advantage - if you find a bug or see another player abusing one, you have to alert the evelina developers immediately</li>
            <li>Selling any economy item or cash for real life money, this also includes trading it for gift cards, nitro, etc.</li>
            <li>Using multiple accounts for economy at all (excepted from this rule is voting, so you can gain company votes quicker)</li>
            <li>Using selfbots or macros to claim timed rewards</li>
            <li>Begging for money or items from our staff team</li>
            <li>Using any kind of offensive language in your company name, description, or any other economy-related text</li>
            <li>Lying to the evelina staff team about any economy-related issue</li>
            <li>Bypassing the daily 10 Million transfer limit</li>
          </ul>
        </section>
      </div>
    </div>
  );
}

export default Economy;