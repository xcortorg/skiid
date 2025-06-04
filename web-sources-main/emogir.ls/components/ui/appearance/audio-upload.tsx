import { useState, useRef, useEffect, ReactNode } from "react";
import {
  IconUpload,
  IconX,
  IconMusic,
  IconPlayerPlay,
  IconPlayerPause,
  IconVolume,
  IconVolume3,
} from "@tabler/icons-react";

interface AudioUploadButtonProps {
  text: string;
  onClick: () => void;
  disabled?: boolean;
  icon: ReactNode;
  className?: string;
}

function AudioUploadButton({
  text,
  onClick,
  disabled,
  icon,
  className,
}: AudioUploadButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${className}`}
    >
      {icon && <span className="flex items-center">{icon}</span>}
      {text}
    </button>
  );
}

interface AudioUploadProps {
  label: string;
  value: string | null;
  title: string | null;
  playerEnabled: boolean;
  onChange: (url: string | null) => void;
  onTitleChange: (title: string) => void;
  onPlayerEnabledChange: (enabled: boolean) => void;
}

function CustomAudioPlayer({ src }: { src: string }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.5);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => setCurrentTime(audio.currentTime);
    const updateDuration = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener("timeupdate", updateTime);
    audio.addEventListener("loadedmetadata", updateDuration);
    audio.addEventListener("ended", handleEnded);

    return () => {
      audio.removeEventListener("timeupdate", updateTime);
      audio.removeEventListener("loadedmetadata", updateDuration);
      audio.removeEventListener("ended", handleEnded);
    };
  }, []);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex items-center gap-2 bg-pink-900/30 rounded-full px-2 py-1">
      <audio ref={audioRef} src={src} preload="metadata" />

      <button
        onClick={togglePlay}
        className="w-8 h-8 flex items-center justify-center rounded-full bg-pink-500/20 hover:bg-pink-500/30 transition-colors"
      >
        {isPlaying ? (
          <IconPlayerPause size={16} />
        ) : (
          <IconPlayerPlay size={16} />
        )}
      </button>

      <div className="flex items-center gap-2 flex-1">
        <div className="relative w-full h-1 bg-white/10 rounded-full overflow-hidden">
          <div
            className="absolute h-full bg-pink-500/60 rounded-full"
            style={{ width: `${(currentTime / duration) * 100}%` }}
          />
        </div>
        <span className="text-xs text-white/60 whitespace-nowrap">
          {formatTime(currentTime)} / {formatTime(duration || 0)}
        </span>
      </div>

      <div className="flex items-center gap-1">
        {volume > 0 ? <IconVolume size={16} /> : <IconVolume3 size={16} />}
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={volume}
          onChange={handleVolumeChange}
          className="w-12 h-1 appearance-none bg-white/10 rounded-full overflow-hidden"
          style={{
            backgroundImage: `linear-gradient(to right, rgba(236, 72, 153, 0.6) 0%, rgba(236, 72, 153, 0.6) ${
              volume * 100
            }%, rgba(255,255,255,0.1) ${
              volume * 100
            }%, rgba(255,255,255,0.1) 100%)`,
          }}
        />
      </div>
    </div>
  );
}

export function AudioUpload({
  label,
  value,
  title,
  playerEnabled,
  onChange,
  onTitleChange,
  onPlayerEnabledChange,
}: AudioUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/upload/audio", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || "Failed to upload audio");
      }

      const data = await response.json();
      onChange(data.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload audio");
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUpload(file);
    }
  };

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-white/80">{label}</label>

      {value ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2 p-3 bg-black/20 border border-primary/10 rounded-lg">
            <IconMusic size={18} className="text-primary/60" />
            <div className="flex-1 truncate text-sm text-white/80">
              {value.split("/").pop()}
            </div>
            {playerEnabled && <CustomAudioPlayer src={value} />}
            <button
              type="button"
              onClick={() => onChange(null)}
              className="p-1 hover:bg-white/10 rounded-full transition-colors"
            >
              <IconX size={16} className="text-white/60" />
            </button>
          </div>

          <div className="space-y-3 p-3 bg-black/20 border border-primary/10 rounded-lg">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-white/80">
                Song Title
              </label>
              <input
                type="text"
                value={title || ""}
                onChange={(e) => onTitleChange(e.target.value)}
                placeholder="Enter song title"
                className="w-full bg-black/20 border border-primary/10 rounded-lg px-3 py-2 text-sm"
              />
              <p className="text-xs text-white/60">
                This will be displayed when the song is playing
              </p>
            </div>

            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-white/80">
                Show Player
              </label>
              <div className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={playerEnabled}
                  onChange={(e) => onPlayerEnabledChange(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-black/40 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-pink-500"></div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*"
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors bg-black/20 border border-primary/10 hover:bg-black/30"
            disabled={isUploading}
          >
            <span className="flex items-center">
              <IconUpload size={16} />
            </span>
            {isUploading ? "Uploading..." : "Upload Audio"}
          </button>
          {error && <p className="text-red-500 text-xs">{error}</p>}
        </>
      )}
    </div>
  );
}
