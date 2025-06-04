import { useState, useEffect } from "react";
import Image from "next/image";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import {
  IconSearch,
  IconX,
  IconLoader2,
  IconChevronDown,
} from "@tabler/icons-react";

interface DecorationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentAvatar: string | null;
  currentDecoration: string | null;
  onSelect: (decoration: string) => void;
}

let cachedDecorations: string[] = [];

export function DecorationDialog({
  open,
  onOpenChange,
  currentAvatar,
  currentDecoration,
  onSelect,
}: DecorationDialogProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [previewDecoration, setPreviewDecoration] = useState<string | null>(
    currentDecoration,
  );
  const [error, setError] = useState<string | null>(null);
  const [decorations, setDecorations] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const itemsPerPage = 24; // 6 rows of 4 items

  useEffect(() => {
    if (open) {
      setPreviewDecoration(currentDecoration);
      setSearchQuery("");
      setError(null);
      setPage(1);

      if (cachedDecorations.length > 0) {
        setDecorations(cachedDecorations);
        setLoading(false);
        return;
      }

      setLoading(true);
      fetch("/api/decorations")
        .then((res) => {
          if (!res.ok) {
            throw new Error(`API returned status ${res.status}`);
          }
          return res.json();
        })
        .then((data) => {
          if (data.decorations && Array.isArray(data.decorations)) {
            cachedDecorations = data.decorations;
            setDecorations(data.decorations);
          } else {
            setDecorations([]);
          }
          setLoading(false);
        })
        .catch((err) => {
          console.error("Failed to load decorations:", err);
          setError(err.message || "Failed to load decorations");
          setLoading(false);
        });
    }
  }, [open, currentDecoration]);

  useEffect(() => {
    setPage(1);
  }, [searchQuery]);

  const filteredDecorations = decorations.filter((decoration) =>
    decoration.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const currentItems = filteredDecorations.slice(0, page * itemsPerPage);
  const hasMore = currentItems.length < filteredDecorations.length;

  const formatDecorationName = (filename: string) => {
    return filename
      .replace(".png", "")
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Select Avatar Decoration</DialogTitle>
        </DialogHeader>

        <div className="relative mb-4 mt-4">
          <Input
            placeholder="Search decorations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
          <IconSearch
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            size={18}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
            >
              <IconX size={16} />
            </button>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-4 flex-1 overflow-hidden">
          <div className="flex-shrink-0 flex flex-col items-center justify-center p-4 bg-black/20 rounded-lg">
            <div className="relative w-32 h-32 mb-4">
              <div className="w-32 h-32 overflow-hidden rounded-full bg-gray-800">
                {currentAvatar ? (
                  <Image
                    src={currentAvatar}
                    alt="Avatar"
                    width={128}
                    height={128}
                    className="w-full h-full object-cover"
                    unoptimized
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-500">
                    No Avatar
                  </div>
                )}
              </div>
              {previewDecoration && (
                <Image
                  src={`/decorations/${previewDecoration}`}
                  alt="Decoration"
                  width={128}
                  height={128}
                  className="absolute -inset-0 w-full h-full scale-[1.2] pointer-events-none"
                  unoptimized
                />
              )}
            </div>
            <p className="text-sm text-center">
              {previewDecoration
                ? formatDecorationName(previewDecoration)
                : "No decoration selected"}
            </p>
            {previewDecoration && (
              <button
                onClick={() => onSelect(previewDecoration)}
                className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm"
              >
                Apply Decoration
              </button>
            )}
          </div>

          <div className="flex-1 relative">
            <ScrollArea className="h-[400px] pr-2">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-full gap-2">
                  <IconLoader2 className="animate-spin" size={24} />
                  <p>Loading decorations...</p>
                </div>
              ) : error ? (
                <div className="flex flex-col items-center justify-center h-full text-red-400 gap-2">
                  <p>Error: {error}</p>
                  <button
                    onClick={() => {
                      setLoading(true);
                      setError(null);
                      cachedDecorations = [];
                      fetch("/api/decorations")
                        .then((res) => res.json())
                        .then((data) => {
                          if (data.decorations) {
                            cachedDecorations = data.decorations;
                            setDecorations(data.decorations);
                          }
                          setLoading(false);
                        })
                        .catch((err) => {
                          setError(err.message || "Failed to load decorations");
                          setLoading(false);
                        });
                    }}
                    className="px-4 py-2 bg-primary/20 hover:bg-primary/30 rounded-md text-sm"
                  >
                    Retry
                  </button>
                </div>
              ) : filteredDecorations.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <p>No decorations found</p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-3 sm:grid-cols-4 gap-3 p-1 pr-2">
                    {currentItems.map((decoration) => (
                      <button
                        key={decoration}
                        onClick={() => setPreviewDecoration(decoration)}
                        className={`relative p-1 rounded-lg transition-all ${
                          previewDecoration === decoration
                            ? "bg-primary/20 ring-2 ring-primary"
                            : "hover:bg-white/5"
                        }`}
                      >
                        <div className="relative w-full aspect-square bg-black/40 rounded-lg overflow-hidden">
                          <div className="w-full h-full flex items-center justify-center">
                            <Image
                              src={`/decorations/${decoration}`}
                              alt={formatDecorationName(decoration)}
                              width={64}
                              height={64}
                              className="object-contain max-w-full max-h-full"
                              unoptimized
                              loading="lazy"
                            />
                          </div>
                        </div>
                        <p className="text-xs mt-1 text-center truncate">
                          {formatDecorationName(decoration)}
                        </p>
                      </button>
                    ))}
                  </div>

                  {hasMore && (
                    <div className="flex justify-center py-4">
                      <button
                        onClick={() => setPage(page + 1)}
                        className="flex items-center gap-2 px-4 py-2 bg-primary/10 hover:bg-primary/20 rounded-md text-sm"
                      >
                        Load More <IconChevronDown size={16} />
                      </button>
                    </div>
                  )}
                </>
              )}
            </ScrollArea>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
