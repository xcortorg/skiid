import React from 'react';
import { Music, PlayCircle, List, Radio, Settings, Volume2 } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

function MusicPlayer() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <PageHeader
        icon={<Music />}
        title="Music Player"
        description="High-quality music streaming for your Discord server"
      />

      {/* Main Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Volume2 className="w-6 h-6 text-theme" />
            Best Audio Quality
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Experience crystal-clear audio with our high-quality music streaming.
            </p>
            <ul className="space-y-2 text-gray-400">
              <li>• High bitrate streaming</li>
              <li>• Optimized audio processing</li>
              <li>• Low latency playback</li>
              <li>• Volume normalization</li>
            </ul>
          </div>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <PlayCircle className="w-6 h-6 text-theme" />
            Platform Support
          </h2>
          <div className="space-y-4">
            <p className="text-gray-400">
              Play music from your favorite platforms seamlessly.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-dark-2 p-4 rounded-lg">
                <h3 className="font-semibold mb-2">YouTube</h3>
                <p className="text-sm text-gray-400">Videos & Playlists</p>
              </div>
              <div className="bg-dark-2 p-4 rounded-lg">
                <h3 className="font-semibold mb-2">Spotify</h3>
                <p className="text-sm text-gray-400">Tracks & Playlists</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Commands Section */}
      <div className="feature-card rounded-xl p-8 mb-16">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center">
            <Settings className="w-6 h-6 text-theme" />
          </div>
          <h2 className="text-2xl font-bold">Music Commands</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <p className="text-gray-400 mb-4">
              Control your music playback with simple commands.
            </p>
            <div className="space-y-2">
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm">play [song/URL]</code>
                <span className="text-gray-400 ml-3">Play a song</span>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm">queue</code>
                <span className="text-gray-400 ml-3">View queue</span>
              </div>
              <div className="bg-dark-2 p-3 rounded-lg">
                <code className="text-sm">skip</code>
                <span className="text-gray-400 ml-3">Skip current song</span>
              </div>
            </div>
          </div>
          <div className="bg-dark-2 rounded-lg p-4">
            <div className="border-l-4 border-theme p-4 rounded bg-dark-1">
              <h3 className="text-lg font-semibold mb-2">Now Playing</h3>
              <p className="text-gray-400">Song Title - Artist</p>
              <div className="mt-2 flex items-center gap-4">
                <button className="text-theme hover:text-theme/80">⏮️</button>
                <button className="text-theme hover:text-theme/80">⏸️</button>
                <button className="text-theme hover:text-theme/80">⏭️</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Additional Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <List className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Queue Management</h3>
          <p className="text-gray-400">
            Manage your playlist with advanced queue controls.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Radio className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">Effects & Filters</h3>
          <p className="text-gray-400">
            Apply audio filters and effects to enhance your music.
          </p>
        </div>

        <div className="feature-card p-6 rounded-xl">
          <div className="w-12 h-12 bg-theme/10 rounded-lg flex items-center justify-center mb-4">
            <Settings className="w-6 h-6 text-theme" />
          </div>
          <h3 className="text-xl font-bold mb-2">DJ Roles</h3>
          <p className="text-gray-400">
            Control who can manage music with DJ role settings.
          </p>
        </div>
      </div>
    </div>
  );
}

export default MusicPlayer;