import React from 'react';
import { Coins, Briefcase, TrendingUp, Users, ArrowUpCircle, Dice1 as Dice, FlaskRound as Flask, DollarSign } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

function EconomySystem() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<DollarSign />}
        title="Economy System"
        description="Create an engaging virtual economy for your server"
      />

      {/* Main Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Briefcase className="w-6 h-6 text-theme" />
            Businesses
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Start and manage your own virtual businesses.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-dark-2 p-4 rounded-lg">
                <h3 className="font-semibold mb-2">ATM</h3>
                <p className="text-sm text-gray-400">Earn money from transaction fees</p>
              </div>
              <div className="bg-dark-2 p-4 rounded-lg">
                <h3 className="font-semibold mb-2">Gas station</h3>
                <p className="text-sm text-gray-400">Sell fuel and car parts</p>
              </div>
              <div className="bg-dark-2 p-4 rounded-lg">
                <h3 className="font-semibold mb-2">Carsharing</h3>
                <p className="text-sm text-gray-400">Rent cars to other players</p>
              </div>
              <div className="bg-dark-2 p-4 rounded-lg">
                <h3 className="font-semibold mb-2">Car dealer</h3>
                <p className="text-sm text-gray-400">Buy and sell cars</p>
              </div>
            </div>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Flask className="w-6 h-6 text-theme" />
            Labs & Upgrades
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Research and develop upgrades in your personal lab.
            </p>
            <div className="space-y-2">
              <div className="bg-dark-2 p-3 rounded-lg flex justify-between items-center">
                <span>Production Speed</span>
                <div className="flex gap-1">
                  <div className="w-4 h-4 bg-theme rounded"></div>
                  <div className="w-4 h-4 bg-theme rounded"></div>
                  <div className="w-4 h-4 bg-theme/30 rounded"></div>
                </div>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg flex justify-between items-center">
                <span>Storage Capacity</span>
                <div className="flex gap-1">
                  <div className="w-4 h-4 bg-theme rounded"></div>
                  <div className="w-4 h-4 bg-theme/30 rounded"></div>
                  <div className="w-4 h-4 bg-theme/30 rounded"></div>
                </div>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg flex justify-between items-center">
                <span>Efficiency</span>
                <div className="flex gap-1">
                  <div className="w-4 h-4 bg-theme rounded"></div>
                  <div className="w-4 h-4 bg-theme rounded"></div>
                  <div className="w-4 h-4 bg-theme rounded"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Games Section */}
      <div className="feature-card rounded-xl p-8 mb-16">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center">
            <Dice className="w-6 h-6 text-theme" />
          </div>
          <h2 className="text-2xl font-bold">Games & Gambling</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-dark-2 rounded-lg p-6">
            <h3 className="text-xl font-bold mb-4">Casino Games</h3>
            <ul className="space-y-2 text-gray-400">
              <li>• Roulette</li>
              <li>• Blackjack</li>
              <li>• Slots</li>
            </ul>
          </div>
          
          <div className="bg-dark-2 rounded-lg p-6">
            <h3 className="text-xl font-bold mb-4">Skill Games</h3>
            <ul className="space-y-2 text-gray-400">
              <li>• Dice</li>
              <li>• Coinflip</li>
              <li>• Ladder</li>
            </ul>
          </div>

          <div className="bg-dark-2 rounded-lg p-6">
            <h3 className="text-xl font-bold mb-4">Stake Game</h3>
            <ul className="space-y-2 text-gray-400">
              <li>• Mines</li>
              <li>• Crash</li>
              <li>• Higher/Lower</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Companies Section */}
      <div className="feature-card rounded-xl p-8 mb-16">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center">
            <Briefcase className="w-6 h-6 text-theme" />
          </div>
          <h2 className="text-2xl font-bold">Company System</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <p className="text-gray-400 mb-4">
              Form companies with other players and work together to complete contracts and grow your business.
            </p>
            <ul className="space-y-2 text-gray-400">
              <li>• Create and manage companies</li>
              <li>• Hire employees and assign roles</li>
              <li>• Complete contracts for rewards</li>
              <li>• Upgrade company facilities</li>
              <li>• Compete with other companies</li>
            </ul>
          </div>
          <div className="bg-dark-2 rounded-lg p-6">
            <h3 className="text-xl font-bold mb-4">Company Upgrades</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span>Headquarters</span>
                <div className="flex gap-1">
                  <div className="w-4 h-4 bg-theme rounded"></div>
                  <div className="w-4 h-4 bg-theme rounded"></div>
                  <div className="w-4 h-4 bg-theme/30 rounded"></div>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span>Employee Capacity</span>
                <div className="flex gap-1">
                  <div className="w-4 h-4 bg-theme rounded"></div>
                  <div className="w-4 h-4 bg-theme/30 rounded"></div>
                  <div className="w-4 h-4 bg-theme/30 rounded"></div>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span>Contract Limit</span>
                <div className="flex gap-1">
                  <div className="w-4 h-4 bg-theme rounded"></div>
                  <div className="w-4 h-4 bg-theme rounded"></div>
                  <div className="w-4 h-4 bg-theme rounded"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Additional Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <TrendingUp className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Market System</h3>
          <p className="text-gray-400">
            Trade items and resources in the global marketplace.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Users className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Partnerships</h3>
          <p className="text-gray-400">
            Form alliances with other players for mutual benefits.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <ArrowUpCircle className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Balanced</h3>
          <p className="text-gray-400">
            A balanced economy system with inflation control.
          </p>
        </div>
      </div>
    </div>
  );
}

export default EconomySystem;