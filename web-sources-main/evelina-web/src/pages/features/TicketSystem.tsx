import React from 'react';
import { MessageSquare, Settings, FileText, Users, Inbox, PanelRight, Ticket } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

function TicketSystem() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<Ticket />}
        title="Ticket System"
        description="Streamline support and inquiries with organized tickets"
      />

      {/* Main Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <FileText className="w-6 h-6 text-theme" />
            Custom Embeds
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Create beautiful ticket panels with custom embeds and buttons.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <div className="border-l-4 border-theme p-4 rounded bg-dark-1">
                <h3 className="text-lg font-semibold mb-2">Support Ticket</h3>
                <p className="text-gray-400 mb-4">Click the button below to create a ticket</p>
                <button className="bg-theme/20 text-theme px-4 py-2 rounded">
                  Create Ticket
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <PanelRight className="w-6 h-6 text-theme" />
            Topics
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Organize tickets by topics for better management and faster response times.
            </p>
            <div className="space-y-2">
              <div className="bg-dark-2 p-3 rounded-lg flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-red-500"></div>
                <span>Bug Reports</span>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
                <span>General Support</span>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span>Feature Requests</span>
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
              Set up your ticket system in minutes with our simple commands.
            </p>
            <ul className="space-y-2 text-gray-400">
              <li>• Create custom ticket categories</li>
              <li>• Set up support roles</li>
              <li>• Customize ticket messages</li>
              <li>• Configure auto-close settings</li>
            </ul>
          </div>
          <div className="bg-dark-2 rounded-lg p-4">
            <code className="text-sm text-gray-300">
              # Setup ticket system<br />
              ;ticket setup<br /><br />
            </code>
          </div>
        </div>
      </div>

      {/* Additional Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Users className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Staff Management</h3>
          <p className="text-gray-400">
            Assign staff roles and manage permissions for ticket handling.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <FileText className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Transcripts</h3>
          <p className="text-gray-400">
            Save and export ticket conversations for future reference.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Inbox className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Auto-Close</h3>
          <p className="text-gray-400">
            Automatically close inactive tickets to keep things organized.
          </p>
        </div>
      </div>
    </div>
  );
}

export default TicketSystem;