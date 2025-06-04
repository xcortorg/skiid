import React from 'react';
import { AlertTriangle, Ban, Bell, BotIcon, Delete, DeleteIcon, ScrollText, Trash } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { BiMoney } from 'react-icons/bi';

function Terms() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <PageHeader
        icon={<ScrollText />}
        title="Terms of Service"
        description="Our terms and conditions of use"
      />

      <div className="feature-card rounded-lg p-6 mb-8">
        <p className="text-gray-400 mb-4">Last updated and effective: June 6, 2024, 12:15 PM CET</p>
        <p className="text-gray-400 mb-4">
          By visiting ("Evelina") or inviting ("Evelina Bot") to your Discord server or logging into our website ("evelina.bot"), you agree and consent to the terms displayed on this page including our policies (Privacy Policy). When we state "Evelina," "we," "us," and "our" in these terms, we mean Evelina. "Services" mean Evelina's services that we offer to users.
        </p>
        <p className="text-gray-400">
          If any information stated here seems/is misleading, please contact us immediately at contact@evelina.bot
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
          <p>You may not use Evelina to violate any applicable laws or regulations as well as Discord's Terms of Service and Community Guidelines. If you encounter individuals or communities doing so, please send us an email to contact@evelina.bot. If you are refunded under any cirumstances, your Discord account may be subject to blacklist and a ban from all of our services.</p>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <ScrollText className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Evelina Website Usage</h2>
          </div>
          <p>You are required to be compliant with the terms shown on this page. You are not to do any of the following:</p>
          <ul className="list-disc pl-6 mt-4 space-y-2">
            <li>Malicious attempts of exploiting the website</li>
            <li>Malicious use of the website</li>
            <li>Scraping content on this website for malicious use</li>
            <li>Framing a portion or all of the website</li>
            <li>Copy Evelina's website and claiming it as your own work</li>
          </ul>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <BotIcon className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Evelina Bot Usage</h2>
          </div>
          <p>You are not to do any of the following:</p>
          <ul className="list-disc pl-6 mt-4 space-y-2">
            <li>Violate the Discord Terms of Service</li>
            <li>Copy Evelina's services or features</li>
            <li>Assist anyone in copying Evelina's services or features</li>
            <li>Abuse or exploit Evelina or any of our services</li>
            <li>Run a Discord Server that has been terminated repeatedly</li>
            <li>Use multiple accounts for the economic system</li>
          </ul>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <Trash className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Termination</h2>
          </div>
          <p>We reserve the right to terminate your access to our services immediately (under our sole discretion) without prior notice or liability for any reason (including, but not limited to, a breach of the terms). If you are a Instance Owner and you don't use any Commands over one month it will be deleted!</p>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <BiMoney className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Indemnity</h2>
          </div>
          <p>You shall indemnify us against all liabilities, costs, expenses, damages and losses (including any direct, indirect or consequential losses, loss of profit, loss of reputation and all interest, penalties and legal and other reasonable professional costs and expenses) suffered or incurred by you arising out of or in connection with your use of the service, or a breach of the terms.</p>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <Bell className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Changes to the Terms of Service</h2>
          </div>
          <p>We can update these terms at any time without notice. Continuing to use our services after any changes will mean that you agree with these terms and violation of our terms of service could result in a permanent ban across all of our services.</p>
        </section>
      </div>
    </div>
  );
}

export default Terms;