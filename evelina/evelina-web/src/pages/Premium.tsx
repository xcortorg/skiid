import React from 'react';
import { Crown, Check, Shield, Bot, Rocket, Gift, Coins, Clock, Zap, Wallet, Vote, Server } from 'lucide-react';

const plans = [
  {
    name: 'Donator',
    price: '5',
    currency: '€',
    description: 'Support the development and get exclusive perks',
    features: [
      'Donator Role',
      'Access to all Premium Commands',
      'Priority Support',
    ],
    icon: Gift,
    color: 'from-purple-500 to-pink-500',
  },
  {
    name: 'Premium',
    price: '10',
    currency: '€',
    description: 'Unlock premium features for your entire server',
    features: [
      'Donator Role',
      'Access to all Premium Commands for your server',
      'Priority Support',
      '3 Transfers',
    ],
    icon: Crown,
    color: 'from-yellow-500 to-orange-500',
    popular: true,
  },
  {
    name: 'Instance',
    price: '25',
    currency: '€',
    description: 'Your own private instance of Evelina',
    features: [
      'Instance Owner Role',
      'Custom branding',
      'Dedicated hosting',
      '24/7 priority support',
      '3 Transfers',
    ],
    icon: Bot,
    color: 'from-blue-500 to-cyan-500',
  },
];

const addons = [
  {
    name: 'Balance',
    price: '5',
    currency: '€',
    description: 'Instant balance boost',
    features: [
      'Get 10 Million on your Evelina Balance',
    ],
    icon: Wallet,
    color: 'from-emerald-500 to-green-500',
  },
  {
    name: 'Votes',
    price: '5',
    currency: '€',
    description: 'Speed up your company projects',
    features: [
      'Get 25 votes for your current company',
    ],
    icon: Vote,
    color: 'from-blue-500 to-indigo-500',
  },
  {
    name: 'Instance Server',
    price: '5',
    currency: '€',
    description: 'Expand your instance',
    features: [
      'Whitelist your Instance to an extra server',
    ],
    icon: Server,
    color: 'from-orange-500 to-amber-500',
  },
];

function Premium() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <h1 className="text-4xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-yellow-500 to-orange-500">
          Upgrade Your Discord Experience
        </h1>
        <p className="text-xl text-gray-400 max-w-2xl mx-auto">
          Choose the perfect plan to enhance your server with premium features and exclusive perks.
          All plans are one-time payments!
        </p>
      </div>

      {/* Pricing Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-16">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`feature-card rounded-xl p-8 relative flex flex-col ${
              plan.popular ? 'border-2 border-yellow-500/50' : 'border border-dark-4'
            }`}
          >
            {plan.popular && (
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-yellow-500 text-black px-4 py-1 rounded-full text-sm font-medium">
                Most Popular
              </div>
            )}

            <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${plan.color} p-4 mb-6`}>
              <plan.icon className="w-full h-full text-white" />
            </div>

            <h2 className="text-2xl font-bold mb-2">{plan.name}</h2>
            <div className="flex items-baseline gap-2 mb-4">
              <span className="text-4xl font-bold">{plan.currency}{plan.price}</span>
              <span className="text-green-400 font-medium">one-time</span>
            </div>

            <p className="text-gray-400 mb-6">{plan.description}</p>

            <ul className="space-y-4 mb-8 flex-1">
              {plan.features.map((feature, index) => (
                <li key={index} className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-theme/20 flex items-center justify-center">
                    <Check className="w-3 h-3 text-theme" />
                  </div>
                  <span>{feature}</span>
                </li>
              ))}
            </ul>

            <a
              href="https://discord.gg/evelina"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full bg-gradient-to-r from-theme to-theme/80 hover:from-theme/90 hover:to-theme/70 text-white px-6 py-3 rounded-lg font-medium transition-all duration-300 hover:shadow-lg hover:shadow-theme/20 flex items-center justify-center gap-2 mt-auto"
            >
              <Coins className="w-4 h-4" />
              Purchase Now
            </a>
          </div>
        ))}
      </div>

      {/* Addons Section */}
      <div className="mb-16">
        <h2 className="text-3xl font-bold text-center mb-8">Addon Products</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {addons.map((addon) => (
            <div key={addon.name} className="feature-card rounded-xl p-6 flex flex-col">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${addon.color} p-3 mb-4`}>
                <addon.icon className="w-full h-full text-white" />
              </div>

              <h3 className="text-xl font-bold mb-2">{addon.name}</h3>
              <div className="flex items-baseline gap-2 mb-3">
                <span className="text-2xl font-bold">{addon.currency}{addon.price}</span>
                {addon.duration && (
                  <span className="text-gray-400 text-sm">{addon.duration}</span>
                )}
              </div>

              <p className="text-gray-400 text-sm mb-4">{addon.description}</p>

              <ul className="space-y-2 flex-1">
                {addon.features.map((feature, index) => (
                  <li key={index} className="flex items-center gap-2 text-sm">
                    <Check className="w-4 h-4 text-theme flex-shrink-0" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <a
                href="https://discord.gg/evelina"
                target="_blank"
                rel="noopener noreferrer"
                className="w-full bg-dark-2 hover:bg-dark-1 text-white px-4 py-2 rounded-lg font-medium transition-all duration-300 flex items-center justify-center gap-2 text-sm mt-4"
              >
                <Coins className="w-4 h-4" />
                Purchase
              </a>
            </div>
          ))}
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center mb-4">
            <Shield className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Priority Support</h3>
          <p className="text-gray-400">Get instant help from our dedicated support team whenever you need it.</p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center mb-4">
            <Rocket className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">No Limits</h3>
          <p className="text-gray-400">Enjoy unlimited access to all features without any restrictions.</p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center mb-4">
            <Clock className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Early Access</h3>
          <p className="text-gray-400">Be the first to try new features before they're released to the public.</p>
        </div>
      </div>
    </div>
  );
}

export default Premium;