"use client";

import { useState, useRef, useEffect } from "react";
import {
  IconUpload,
  IconX,
  IconMusic,
  IconPlayerPlay,
  IconPlayerPause,
  IconVolume,
  IconVolume3,
  IconPlus,
  IconTrash,
  IconGripVertical,
  IconEdit,
} from "@tabler/icons-react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useToast } from "@/components/ui/toast-provider";

function CustomAudioPlayer({ src }: { src: string }) {}

export interface AudioTrack {
  id: string;
  url: string;
  title: string;
  icon: string | null;
  order: number;
}

function SortableTrackItem({
  track,
  onEdit,
  onDelete,
  onPlay,
}: {
  track: AudioTrack;
  onEdit: () => void;
  onDelete: () => void;
  onPlay: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: track.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 p-3 bg-black/20 border border-primary/10 rounded-lg"
    >
      <div {...attributes} {...listeners} className="cursor-grab">
        <IconGripVertical size={18} className="text-white/40" />
      </div>

      <div className="w-8 h-8 flex items-center justify-center bg-pink-500/20 rounded-full">
        {track.icon ? (
          <img src={track.icon} alt="Icon" className="w-5 h-5" />
        ) : (
          <IconMusic size={16} className="text-pink-500" />
        )}
      </div>

      <div className="flex-1 truncate">
        <div className="text-sm font-medium text-white/80 truncate">
          {track.title || "Untitled Track"}
        </div>
        <div className="text-xs text-white/50 truncate">
          {track.url.split("/").pop()}
        </div>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={onPlay}
          className="p-1.5 hover:bg-white/10 rounded-full transition-colors"
        >
          <IconPlayerPlay size={16} className="text-white/60" />
        </button>

        <button
          onClick={onEdit}
          className="p-1.5 hover:bg-white/10 rounded-full transition-colors"
        >
          <IconEdit size={16} className="text-white/60" />
        </button>

        <button
          onClick={onDelete}
          className="p-1.5 hover:bg-white/10 rounded-full transition-colors"
        >
          <IconTrash size={16} className="text-white/60" />
        </button>
      </div>
    </div>
  );
}

function TrackEditModal({
  track,
  onSave,
  onCancel,
}: {
  track: AudioTrack;
  onSave: (updatedTrack: AudioTrack) => void;
  onCancel: () => void;
}) {
  const { toast } = useToast();
  const [title, setTitle] = useState(track.title);
  const [icon, setIcon] = useState<string | null>(track.icon);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleIconUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      toast({
        title: "Invalid file type",
        description: "Please upload a JPEG, PNG, or WEBP image.",
        variant: "error",
      });
      return;
    }

    if (file.size > 1 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Please upload an image under 1MB.",
        variant: "error",
      });
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/upload/icon", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");

      const data = await response.json();
      setIcon(data.url);
    } catch (error) {
      toast({
        title: "Upload failed",
        description: "Failed to upload icon",
        variant: "error",
      });
      console.error(error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-black/90 border border-primary/20 rounded-lg p-4 w-full max-w-md">
        <h3 className="text-lg font-medium mb-4">Edit Track</h3>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-white/80 block mb-1">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-black/20 border border-primary/10 rounded-lg px-3 py-2 text-sm"
              placeholder="Enter track title"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-white/80 block mb-1">
              Icon
            </label>
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-full bg-pink-500/20 flex items-center justify-center">
                {icon ? (
                  <img src={icon} alt="Icon" className="w-6 h-6" />
                ) : (
                  <IconMusic size={18} className="text-pink-500" />
                )}
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/svg+xml"
                onChange={handleIconUpload}
                className="hidden"
              />

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="px-3 py-1 text-sm bg-black/20 border border-primary/10 rounded-lg hover:bg-black/30 transition-colors"
                disabled={uploading}
              >
                {uploading ? "Uploading..." : "Upload Icon"}
              </button>

              {icon && (
                <button
                  type="button"
                  onClick={() => setIcon(null)}
                  className="p-1 hover:bg-white/10 rounded-full transition-colors"
                >
                  <IconX size={16} className="text-white/60" />
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1 text-sm bg-black/20 border border-primary/10 rounded-lg hover:bg-black/30 transition-colors"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={() =>
              onSave({ ...track, title: title || "Untitled Track", icon })
            }
            className="px-3 py-1 text-sm bg-pink-500/20 border border-pink-500/30 rounded-lg hover:bg-pink-500/30 transition-colors"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

export function AudioTracksManager({
  tracks,
  playerEnabled,
  onTracksChange,
  onPlayerEnabledChange,
}: {
  tracks: AudioTrack[];
  playerEnabled: boolean;
  onTracksChange: (tracks: AudioTrack[]) => void;
  onPlayerEnabledChange: (enabled: boolean) => void;
}) {
  const { toast } = useToast();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [editingTrack, setEditingTrack] = useState<AudioTrack | null>(null);
  const [playingTrack, setPlayingTrack] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ["audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg"];
    if (!allowedTypes.includes(file.type)) {
      setError("Invalid file type. Please upload an MP3, WAV, or OGG file.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("File too large. Please upload an audio file under 10MB.");
      return;
    }

    try {
      setIsUploading(true);
      setError(null);

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/upload/audio", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");

      const data = await response.json();

      const newTrack: AudioTrack = {
        id: `temp-${Date.now()}`,
        url: data.url,
        title: file.name.split(".").slice(0, -1).join("."),
        icon: null,
        order: tracks.length,
      };

      onTracksChange([...tracks, newTrack]);
      toast({
        title: "Upload successful",
        description: "Audio uploaded successfully",
        variant: "success",
      });
    } catch (error) {
      setError("Failed to upload audio file");
      console.error(error);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDragEnd = (event: any) => {
    const { active, over } = event;

    if (active.id !== over.id) {
      const oldIndex = tracks.findIndex((track) => track.id === active.id);
      const newIndex = tracks.findIndex((track) => track.id === over.id);

      const newTracks = [...tracks];
      const [movedTrack] = newTracks.splice(oldIndex, 1);
      newTracks.splice(newIndex, 0, movedTrack);

      const updatedTracks = newTracks.map((track, index) => ({
        ...track,
        order: index,
      }));

      onTracksChange(updatedTracks);
    }
  };

  const handleDeleteTrack = (id: string) => {
    onTracksChange(tracks.filter((track) => track.id !== id));
  };

  const handleEditTrack = (track: AudioTrack) => {
    setEditingTrack(track);
  };

  const handleSaveTrack = (updatedTrack: AudioTrack) => {
    onTracksChange(
      tracks.map((track) =>
        track.id === updatedTrack.id ? updatedTrack : track,
      ),
    );
    setEditingTrack(null);
  };

  const handlePlayTrack = (url: string) => {
    if (playingTrack === url) {
      setPlayingTrack(null);
      if (audioRef.current) {
        audioRef.current.pause();
      }
    } else {
      setPlayingTrack(url);
      if (!audioRef.current) {
        audioRef.current = new Audio(url);
      } else {
        audioRef.current.src = url;
      }
      audioRef.current.play();
    }
  };

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-white/80">
          Audio Tracks (Max 3)
        </h3>
      </div>

      <div className="space-y-2">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={tracks.map((track) => track.id)}
            strategy={verticalListSortingStrategy}
          >
            {tracks.map((track) => (
              <SortableTrackItem
                key={track.id}
                track={track}
                onEdit={() => handleEditTrack(track)}
                onDelete={() => handleDeleteTrack(track.id)}
                onPlay={() => handlePlayTrack(track.url)}
              />
            ))}
          </SortableContext>
        </DndContext>

        {tracks.length < 3 && (
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
              disabled={isUploading || tracks.length >= 3}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-colors bg-black/20 border border-primary/10 hover:bg-black/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <IconPlus size={16} />
              {isUploading ? "Uploading..." : "Add Track"}
            </button>

            {error && <p className="text-red-500 text-xs">{error}</p>}
          </>
        )}
      </div>

      {editingTrack && (
        <TrackEditModal
          track={editingTrack}
          onSave={handleSaveTrack}
          onCancel={() => setEditingTrack(null)}
        />
      )}
    </div>
  );
}
