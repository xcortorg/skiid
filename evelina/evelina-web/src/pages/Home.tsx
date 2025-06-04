import React from 'react';
import { Bot, Shield, Ticket, Gift, UserPlus, Mic2, Tag, Lightbulb, Circle, Award, Clock, Music, Mail, Coins, MessageSquare, PartyPopper, DoorOpen, ShieldAlert, Headphones, Crown, Sparkles, ToggleLeft, Trophy, Bell, Music2, UserPlus2, Terminal, PartyPopperIcon, Search } from 'lucide-react';
import { FaDiscord } from 'react-icons/fa';
import { Link } from 'react-router-dom';
import { useScrollAnimation } from '../hooks/useScrollAnimation';
import AnimatedBackground from '../components/AnimatedBackground';
import { BiVoicemail } from 'react-icons/bi';
import { MdVoiceChat } from 'react-icons/md';

function Home() {
  useScrollAnimation();

  return (
    <div className="relative">
      {/* Hero Section */}
      <header className="relative min-h-[95vh] flex items-center justify-center overflow-hidden bg-black">
        {/* Animated Background with Stars */}
        <div className="absolute inset-0 overflow-hidden">
          <AnimatedBackground />
          <div className="wave-container">
            <div className="wave-gradient"></div>
          </div>
        </div>
        <div className="relative z-10 text-center px-4 max-w-5xl mx-auto">
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold mb-6 tracking-tight">
            <span className="text-white">Evelina is Discord's</span>
            <br className="hidden sm:block" />
            <span className="text-white"> ultimate </span>
            <span className="shimmer-text">all-in-one</span>
            <span className="text-white"> app</span>
          </h1>
          <p className="text-lg sm:text-xl text-gray-300 mb-10 max-w-2xl mx-auto leading-relaxed">
            Simple, yet advanced, feature-rich and completely free Discord Application.
          </p>
          <div className="flex flex-col sm:flex-row gap-5 justify-center items-center">
            <a
              href="https://discord.com/oauth2/authorize?client_id=1242930981967757452"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto bg-[#5865F2] hover:bg-[#4752C4] text-white px-8 py-4 rounded-xl font-medium transition-all duration-300 hover:shadow-xl hover:shadow-[#5865F2]/20 flex items-center justify-center gap-2 border border-[#7289DA]/20"
            >
              <FaDiscord className="w-5 h-5" />
              Add to Discord
            </a>
            <Link 
              to="/commands"
              className="w-full sm:w-auto bg-gradient-to-r from-theme to-[#90c1d8] hover:from-theme/90 hover:to-[#90c1d8]/90 text-white px-8 py-4 rounded-xl font-medium transition-all duration-300 hover:shadow-xl hover:shadow-theme/20 flex items-center justify-center gap-2 border border-theme/20"
            >
              <Terminal className="w-5 h-5" />
              Commands
            </Link>
            <Link 
              to="/premium"
              className="w-full sm:w-auto bg-gradient-to-r from-yellow-400 via-orange-500 to-red-500 hover:from-yellow-500 hover:via-orange-600 hover:to-red-600 text-white px-8 py-4 rounded-xl font-medium transition-all duration-300 hover:shadow-xl hover:shadow-orange-500/30 flex items-center justify-center gap-2 border border-orange-500/20"
            >
              <Crown className="w-5 h-5" />
              Premium
            </Link>
          </div>
        </div>
      </header>

      {/* Cleaner Fade Transition */}
      <div className="relative z-10">
        <div className="absolute inset-x-0 -top-60 h-60 bg-gradient-to-b from-transparent via-black/30 to-[#0a0a0a]"></div>
        <div className="absolute inset-x-0 -top-40 h-40 bg-gradient-to-b from-transparent to-[#0a0a0a]"></div>
      </div>

      {/* Features Section */}
      <section className="relative z-20 w-full bg-[#0a0a0a]">
        <div className="max-w-7xl mx-auto px-4 py-24">
          {/* Security Features - Alternate Layout */}
          <div className="mb-36 bg-gradient-to-br from-dark-2/80 to-dark-2/30 backdrop-blur-sm rounded-2xl p-10 scroll-fade border border-white/5 shadow-xl">
            <div className="text-center mb-14">
              <div className="inline-flex items-center justify-center p-2 rounded-xl bg-theme/10 mb-5">
                <ShieldAlert className="w-8 h-8 text-theme" />
              </div>
              <h3 className="text-3xl font-bold">Advanced Security</h3>
              <p className="text-gray-400 max-w-2xl mx-auto mt-3">
                Keep your server safe with our comprehensive security features.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="feature-card p-7 rounded-xl hover:border-theme/20 transition-all duration-300 hover:translate-y-[-5px] hover:shadow-lg">
                <h4 className="text-xl font-semibold mb-4 flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-theme/10">
                    <Shield className="w-5 h-5 text-theme" />
                  </div>
                  Antinuke Protection
                </h4>
                <ul className="space-y-3 text-gray-300">
                  <li className="flex items-center gap-2">
                    <Circle className="w-1.5 h-1.5 text-theme" />
                    Role deletion protection
                  </li>
                  <li className="flex items-center gap-2">
                    <Circle className="w-1.5 h-1.5 text-theme" />
                    Channel security
                  </li>
                  <li className="flex items-center gap-2">
                    <Circle className="w-1.5 h-1.5 text-theme" />
                    Anti-raid measures
                  </li>
                </ul>
              </div>
              <div className="feature-card p-7 rounded-xl hover:border-theme/20 transition-all duration-300 hover:translate-y-[-5px] hover:shadow-lg">
                <h4 className="text-xl font-semibold mb-4 flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-theme/10">
                    <ShieldAlert className="w-5 h-5 text-theme" />
                  </div>
                  Auto Moderation
                </h4>
                <ul className="space-y-3 text-gray-300">
                  <li className="flex items-center gap-2">
                    <Circle className="w-1.5 h-1.5 text-theme" />
                    Spam detection
                  </li>
                  <li className="flex items-center gap-2">
                    <Circle className="w-1.5 h-1.5 text-theme" />
                    Link filtering
                  </li>
                  <li className="flex items-center gap-2">
                    <Circle className="w-1.5 h-1.5 text-theme" />
                    Customizable filters
                  </li>
                </ul>
              </div>
            </div>
            <Link
              to="/features/automod"
              className="w-full sm:w-1/4 bg-dark-1 hover:bg-dark-1/80 text-white px-8 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 mt-10 mx-auto border border-theme/10 hover:border-theme/30"
            >
              <Shield className="w-5 h-5" />
              Auto Moderation
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-36">
            {/* Ticket System */}
            <div className="feature-card p-8 rounded-xl scroll-fade hover:border-theme/20 transition-all duration-300 hover:translate-y-[-5px] hover:shadow-lg bg-gradient-to-br from-dark-2/80 to-dark-2/30">
              <div className="inline-flex p-3 rounded-xl bg-theme/10 mb-5">
                <MessageSquare className="w-6 h-6 text-theme" />
              </div>
              <h3 className="text-xl font-bold mb-3">
                Ticket System
              </h3>
              <p className="text-gray-300 mb-6">Advanced ticket management with custom forms, categories, and transcripts.</p>
              <Link
                to="/features/tickets"
                className="w-full bg-dark-1 hover:bg-dark-1/80 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 mt-auto border border-theme/10 hover:border-theme/30"
              >
                <MessageSquare className="w-5 h-5" />
                Tickets System
              </Link>
            </div>

            {/* Giveaways */}
            <div className="feature-card p-8 rounded-xl scroll-fade hover:border-theme/20 transition-all duration-300 hover:translate-y-[-5px] hover:shadow-lg bg-gradient-to-br from-dark-2/80 to-dark-2/30">
              <div className="inline-flex p-3 rounded-xl bg-theme/10 mb-5">
                <PartyPopper className="w-6 h-6 text-theme" />
              </div>
              <h3 className="text-xl font-bold mb-3">
                Giveaways
              </h3>
              <p className="text-gray-300 mb-6">Create and manage giveaways with custom requirements and multiple winners.</p>
              <Link
                to="/features/giveaways"
                className="w-full bg-dark-1 hover:bg-dark-1/80 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 mt-auto border border-theme/10 hover:border-theme/30"
              >
                <PartyPopper className="w-5 h-5" />
                Giveaways
              </Link>
            </div>

            {/* Welcome System */}
            <div className="feature-card p-8 rounded-xl scroll-fade hover:border-theme/20 transition-all duration-300 hover:translate-y-[-5px] hover:shadow-lg bg-gradient-to-br from-dark-2/80 to-dark-2/30">
              <div className="inline-flex p-3 rounded-xl bg-theme/10 mb-5">
                <DoorOpen className="w-6 h-6 text-theme" />
              </div>
              <h3 className="text-xl font-bold mb-3">
                Welcome System
              </h3>
              <p className="text-gray-300 mb-6">Customize welcome, leave, and boost messages with images and embeds.</p>
              <Link
                to="/features/welcome"
                className="w-full bg-dark-1 hover:bg-dark-1/80 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 mt-auto border border-theme/10 hover:border-theme/30"
              >
                <DoorOpen className="w-5 h-5" />
                Welcome System
              </Link>
            </div>
          </div>

          {/* Economy System - Full Width Feature */}
          <div className="mb-36 scroll-fade">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
              <div className="order-2 lg:order-1">
                <div className="feature-card rounded-xl p-8 bg-gradient-to-br from-dark-2/80 to-dark-2/30 hover:border-theme/20 transition-all duration-300 hover:shadow-lg">
                  <div className="space-y-6">
                    <div className="flex items-center gap-4 p-3 rounded-lg bg-dark-1/50 hover:bg-dark-1 transition-colors">
                      <span className="font-mono font-medium text-theme">;</span><span className="font-mono">work</span>
                      <span className="text-gray-300 ml-auto flex items-center gap-2">
                        <Coins className="w-4 h-4 text-yellow-400" /> 250 coins earned
                      </span>
                    </div>
                    <div className="flex items-center gap-4 p-3 rounded-lg bg-dark-1/50 hover:bg-dark-1 transition-colors">
                      <span className="font-mono font-medium text-theme">;</span><span className="font-mono">balance</span>
                      <span className="text-gray-300 ml-auto flex items-center gap-2">
                        <Coins className="w-4 h-4 text-yellow-400" /> 1,250 coins
                      </span>
                    </div>
                    <div className="flex items-center gap-4 p-3 rounded-lg bg-dark-1/50 hover:bg-dark-1 transition-colors">
                      <span className="font-mono font-medium text-theme">;</span><span className="font-mono">shop</span>
                      <span className="text-gray-300 ml-auto flex items-center gap-2">
                        <Tag className="w-4 h-4 text-yellow-400" /> Browse items
                      </span>
                    </div>
                  </div>
                </div>
                <Link
                  to="/features/economy"
                  className="w-full bg-dark-1 hover:bg-dark-1/80 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 mt-8 border border-theme/10 hover:border-theme/30"
                >
                  <Gift className="w-5 h-5" />
                  Economy System
                </Link>
              </div>
              <div className="order-1 lg:order-2">
                <div className="inline-flex p-3 rounded-xl bg-theme/10 mb-5">
                  <Coins className="w-7 h-7 text-theme" />
                </div>
                <h3 className="text-3xl font-bold shimmer-text mb-5">Advanced Economy System</h3>
                <p className="text-gray-300 mb-8 text-lg leading-relaxed">
                  Engage your community with a fully-featured economy system. Members can work, earn coins, trade items, and more.
                </p>
                <ul className="space-y-4">
                  <li className="flex items-start gap-3">
                    <div className="p-1 mt-0.5 rounded-full bg-theme/10 text-theme">
                      <Circle className="w-2 h-2" />
                    </div>
                    <span className="text-gray-200">Multiple ways to earn coins through engaging activities</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="p-1 mt-0.5 rounded-full bg-theme/10 text-theme">
                      <Circle className="w-2 h-2" />
                    </div>
                    <span className="text-gray-200">Custom shop system with role rewards and special items</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="p-1 mt-0.5 rounded-full bg-theme/10 text-theme">
                      <Circle className="w-2 h-2" />
                    </div>
                    <span className="text-gray-200">Seamless trading between users with inventory management</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Voice & Role Features */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-14 mb-36 scroll-fade">
            {/* Voice Features */}
            <div>
              <div className="flex items-center gap-3 mb-8">
                <div className="p-2 rounded-lg bg-theme/10">
                  <Headphones className="w-6 h-6 text-theme" />
                </div>
                <h3 className="text-2xl font-bold">Voice Features</h3>
              </div>
              <div className="space-y-6">
                <div className="feature-card p-6 rounded-xl bg-gradient-to-br from-dark-2/80 to-dark-2/30 hover:border-theme/20 transition-all duration-300 hover:translate-y-[-3px] hover:shadow-lg">
                  <h4 className="font-bold mb-3 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-theme/10">
                      <Mic2 className="w-5 h-5 text-theme" />
                    </div>
                    Voicemaster System
                  </h4>
                  <p className="text-gray-300 mb-4">Create custom voice channels with full control over settings and permissions.</p>
                  <Link
                    to="/features/voicemaster"
                    className="w-full bg-dark-1 hover:bg-dark-1/80 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 border border-theme/10 hover:border-theme/30"
                  >
                    <Mic2 className="w-5 h-5" />
                    Voice Master
                  </Link>
                </div>
                <div className="feature-card p-6 rounded-xl bg-gradient-to-br from-dark-2/80 to-dark-2/30 hover:border-theme/20 transition-all duration-300 hover:translate-y-[-3px] hover:shadow-lg">
                  <h4 className="font-bold mb-3 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-theme/10">
                      <Trophy className="w-5 h-5 text-theme" />
                    </div>
                    Voice Leveling
                  </h4>
                  <p className="text-gray-300 mb-4">Earn XP while being active in voice channels with custom rewards and ranks.</p>
                  <Link
                    to="/features/leveling"
                    className="w-full bg-dark-1 hover:bg-dark-1/80 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 border border-theme/10 hover:border-theme/30"
                  >
                    <Trophy className="w-5 h-5" />
                    Leveling System
                  </Link>
                </div>
              </div>
            </div>

            {/* Role Features */}
            <div>
              <div className="flex items-center gap-3 mb-8">
                <div className="p-2 rounded-lg bg-theme/10">
                  <Crown className="w-6 h-6 text-theme" />
                </div>
                <h3 className="text-2xl font-bold">Role Management</h3>
              </div>
              <div className="space-y-6">
                <div className="feature-card p-6 rounded-xl bg-gradient-to-br from-dark-2/80 to-dark-2/30 hover:border-theme/20 transition-all duration-300 hover:translate-y-[-3px] hover:shadow-lg">
                  <h4 className="font-bold mb-3 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-theme/10">
                      <Tag className="w-5 h-5 text-theme" />
                    </div>
                    Vanity Roles
                  </h4>
                  <p className="text-gray-300 mb-4">Custom roles for server boosters and special members with color customization.</p>
                  <Link
                    to="/features/vanityroles"
                    className="w-full bg-dark-1 hover:bg-dark-1/80 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 border border-theme/10 hover:border-theme/30"
                  >
                    <Tag className="w-5 h-5" />
                    Vanity Roles
                  </Link>
                </div>
                <div className="feature-card p-6 rounded-xl bg-gradient-to-br from-dark-2/80 to-dark-2/30 hover:border-theme/20 transition-all duration-300 hover:translate-y-[-3px] hover:shadow-lg">
                  <h4 className="font-bold mb-3 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-theme/10">
                      <ToggleLeft className="w-5 h-5 text-theme" />
                    </div>
                    Button & Reaction Roles
                  </h4>
                  <p className="text-gray-300 mb-4">Self-assignable roles with custom buttons and reactions for easy management.</p>
                  <Link
                    to="/features/buttonroles"
                    className="w-full bg-dark-1 hover:bg-dark-1/80 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 border border-theme/10 hover:border-theme/30"
                  >
                    <MdVoiceChat className="w-5 h-5" />
                    Button Roles
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* Additional Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 scroll-fade">
            {/* Leveling System */}
            <div className="feature-card p-8 rounded-xl text-center bg-gradient-to-br from-dark-2/80 to-dark-2/30 hover:border-theme/20 transition-all duration-300 hover:translate-y-[-3px] hover:shadow-lg">
              <div className="inline-flex p-3 rounded-xl bg-theme/10 mb-5 mx-auto">
                <Trophy className="w-6 h-6 text-theme" />
              </div>
              <h3 className="text-xl font-bold mb-3">
                Leveling System
              </h3>
              <p className="text-gray-300 mb-6">Comprehensive leveling system for both text and voice activity with custom rewards.</p>
              <Link
                to="/features/leveling"
                className="w-full bg-dark-1 hover:bg-dark-1/80 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 border border-theme/10 hover:border-theme/30"
              >
                <Trophy className="w-5 h-5" />
                Leveling System
              </Link>
            </div>

            {/* Bump Reminder */}
            <div className="feature-card p-8 rounded-xl text-center bg-gradient-to-br from-dark-2/80 to-dark-2/30 hover:border-theme/20 transition-all duration-300 hover:translate-y-[-3px] hover:shadow-lg">
              <div className="inline-flex p-3 rounded-xl bg-theme/10 mb-5 mx-auto">
                <Bell className="w-6 h-6 text-theme" />
              </div>
              <h3 className="text-xl font-bold mb-3">
                Bump Reminder
              </h3>
              <p className="text-gray-300 mb-6">Never miss a bump with automated reminders and rewards for active bumpers.</p>
              <Link
                to="/features/bump"
                className="w-full bg-dark-1 hover:bg-dark-1/80 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 border border-theme/10 hover:border-theme/30"
              >
                <Bell className="w-5 h-5" />
                Bump Reminder
              </Link>
            </div>

            {/* Music System */}
            <div className="feature-card p-8 rounded-xl text-center bg-gradient-to-br from-dark-2/80 to-dark-2/30 hover:border-theme/20 transition-all duration-300 hover:translate-y-[-3px] hover:shadow-lg">
              <div className="inline-flex p-3 rounded-xl bg-theme/10 mb-5 mx-auto">
                <Music2 className="w-6 h-6 text-theme" />
              </div>
              <h3 className="text-xl font-bold mb-3">
                Music System
              </h3>
              <p className="text-gray-300 mb-6">High-quality music playback with playlist support from various platforms.</p>
              <Link
                to="/features/music"
                className="w-full bg-dark-1 hover:bg-dark-1/80 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 border border-theme/10 hover:border-theme/30"
              >
                <Music2 className="w-5 h-5" />
                Music Player
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Home;