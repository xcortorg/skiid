import React from 'react';
import { Crown, Palette, Settings, Shield, Tag, Users, Star, Sparkles, Award } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

function VanityRoles() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<Award />}
        title="Vanity Roles"
        description="Reward activity with custom roles and perks"
      />

      {/* Main Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Palette className="w-6 h-6 text-theme" />
            Configuration
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Let your members get role when they put vanity in their status.
            </p>
            <div className="bg-dark-2 rounded-lg p-4">
              <code className="text-sm text-gray-300">
                # Role Commands<br />
                ;vanity trigger<br />
                ;vanity message<br />
                ;vanity logs<br />
                ;vanity role
              </code>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Settings className="w-6 h-6 text-theme" />
            Ignoring
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Ignoring users from getting the vanity role.
            </p>
            <div className="space-y-2">
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm text-gray-300">
                  ;vanity ignore add<br />
                  ;vanity ignore remove<br />
                  ;vanity ignore list
                </code>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Role Examples */}
      <div className="feature-card rounded-xl p-8 mb-16">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center">
            <Tag className="w-6 h-6 text-theme" />
          </div>
          <h2 className="text-2xl font-bold">Role Examples</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-dark-2 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-4 h-4 rounded-full bg-pink-500"></div>
              <span className="font-semibold">🌸 Cherry Blossom</span>
            </div>
            <p className="text-sm text-gray-400">Custom booster role with pink color and flower theme</p>
          </div>
          <div className="bg-dark-2 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-4 h-4 rounded-full bg-purple-500"></div>
              <span className="font-semibold">⭐ Star Gazer</span>
            </div>
            <p className="text-sm text-gray-400">Premium member role with cosmic theme</p>
          </div>
          <div className="bg-dark-2 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-4 h-4 rounded-full bg-blue-500"></div>
              <span className="font-semibold">🌊 Ocean Master</span>
            </div>
            <p className="text-sm text-gray-400">Special role with aquatic theme</p>
          </div>
        </div>
      </div>

      {/* Additional Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Shield className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Role Hierarchy</h3>
          <p className="text-gray-400">
            Automatic role positioning to maintain server hierarchy and permissions.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Star className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Premium Features</h3>
          <p className="text-gray-400">
            Additional customization options for premium server members.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Sparkles className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Special Effects</h3>
          <p className="text-gray-400">
            Unique role animations and effects for boosters and premium members.
          </p>
        </div>
      </div>
    </div>
  );
}

export default VanityRoles;