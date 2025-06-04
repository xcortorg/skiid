"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import {
  IconLock,
  IconCrown,
  IconDownload,
  IconCheck,
  IconX,
  IconSettings,
  IconTrash,
  IconExternalLink,
  IconChevronLeft,
  IconChevronRight,
  IconSearch,
} from "@tabler/icons-react";
import { ColorPicker } from "@/components/ui/appearance/color-picker";
import { Select } from "@/components/ui/appearance/select";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast-provider";

const AVAILABLE_DOMAINS = [
  "emogir.ls",
  "evil.bio",
  "is-a-femboy.lol",
  "wife.lol",
];

interface UserPremium {
  isPremium: boolean;
  features?: {
    imageHosting: boolean;
  };
}

interface DomainSettings {
  title: string;
  description: string;
  color: string;
  provider_name: string;
  author_name: string;
  author_url: string;
  showMetadata: boolean;
}

interface ImageDomain {
  id: string;
  subdomain: string;
  domain: string;
  createdAt: string;
  oembed: DomainSettings | null;
  authorization: string;
}

interface UploadedImage {
  id: string;
  filename: string;
  original_name: string;
  mime_type: string;
  size: number;
  width: number;
  height: number;
  createdAt: string;
}

interface DeleteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  domain: string;
}

const DeleteDomainDialog = ({
  isOpen,
  onClose,
  onConfirm,
  domain,
}: DeleteModalProps) => {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-darker border border-white/10">
        <DialogTitle>Delete Domain</DialogTitle>
        <div className="p-6">
          <p className="text-white/60 mb-6">
            Are you sure you want to delete{" "}
            <span className="text-white font-mono">{domain}</span>? This action
            cannot be undone and all configurations will be lost.
          </p>
          <div className="flex gap-3 justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-black/20 hover:bg-black/40 transition-colors rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="px-4 py-2 bg-red-500/20 text-red-500 hover:bg-red-500/40 transition-colors rounded-lg"
            >
              Delete Domain
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default function ImageHostPage() {
  const { data: session } = useSession();
  const [userPremium, setUserPremium] = useState<UserPremium | null>(null);
  const [loading, setLoading] = useState(true);
  const [domains, setDomains] = useState<ImageDomain[]>([]);
  const [newSubdomain, setNewSubdomain] = useState("");
  const [selectedDomain, setSelectedDomain] = useState(AVAILABLE_DOMAINS[0]);
  const [checking, setChecking] = useState(false);
  const [isAvailable, setIsAvailable] = useState<boolean | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(null);
  const [settings, setSettings] = useState<DomainSettings>({
    title: "",
    description: "",
    color: "#ff3379",
    provider_name: "",
    author_name: "",
    author_url: "",
    showMetadata: true,
  });
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [inputPage, setInputPage] = useState("1");
  const imagesPerPage = 15;
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "name">("newest");
  const [deletingDomain, setDeletingDomain] = useState<ImageDomain | null>(
    null,
  );
  const { toast } = useToast();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [premiumRes, domainsRes, imagesRes] = await Promise.all([
          fetch("/api/user/premium"),
          fetch("/api/user/image-domains"),
          fetch("/api/user/uploads"),
        ]);

        const [premiumData, domainsData, imagesData] = await Promise.all([
          premiumRes.json(),
          domainsRes.json(),
          imagesRes.json(),
        ]);

        setUserPremium(premiumData);
        setDomains(domainsData);
        setImages(imagesData);
      } catch (error) {
        console.error("Failed to fetch data:", error);
        toast({
          title: "Error",
          description: "Failed to load data",
          variant: "error",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const checkAvailability = async () => {
    if (!newSubdomain) return;
    setChecking(true);
    try {
      const res = await fetch(
        `/api/domains/check?subdomain=${newSubdomain}&domain=${selectedDomain}`,
      );
      const data = await res.json();
      setIsAvailable(data.available);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to check availability",
        variant: "error",
      });
    } finally {
      setChecking(false);
    }
  };

  const generateShareXConfig = (domain: ImageDomain) => {
    const config = {
      Version: "15.0.0",
      Name: `${domain.subdomain}.${domain.domain}`,
      DestinationType: "ImageUploader",
      RequestMethod: "POST",
      RequestURL: `https://upload-test.${domain.domain}/upload`,
      Headers: {
        "X-API-Key": domain.authorization,
      },
      Body: "MultipartFormData",
      FileFormName: "file",
      URL: "{json:url}",
      ThumbnailURL: "{json:url}",
      DeletionURL: "",
      ErrorMessage: "{json:error}",
    };

    return config;
  };

  const generateIShareConfig = (domain: ImageDomain) => {
    return {
      name: `${domain.subdomain}.${domain.domain}`,
      endpoint: `https://upload-test.emogir.ls/upload`,
      headers: {
        "X-API-Key": domain.authorization,
      },
      responseUrl: "url",
    };
  };

  const downloadConfig = (domain: ImageDomain, type: "sharex" | "ishare") => {
    const config =
      type === "sharex"
        ? generateShareXConfig(domain)
        : generateIShareConfig(domain);

    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${domain.subdomain}.${domain.domain}-${type}.sxcu`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const addDomain = async () => {
    if (!newSubdomain || !isAvailable) return;

    setIsAdding(true);
    try {
      const res = await fetch("/api/domains/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subdomain: newSubdomain,
          domain: selectedDomain,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to add domain");
      }

      const newDomain = await res.json();
      setDomains([...domains, newDomain]);
      setNewSubdomain("");
      setIsAvailable(null);
      toast({
        title: "Success",
        description: "Domain added successfully!",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to add domain",
        variant: "error",
      });
    } finally {
      setIsAdding(false);
    }
  };

  const updateSettings = async (domainId: string) => {
    try {
      const res = await fetch("/api/domains/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          domainId,
          embedTitle: settings.title,
          embedDescription: settings.description,
          embedColor: settings.color,
          embedSiteName: settings.provider_name,
          embedAuthorName: settings.author_name,
          embedAuthorUrl: settings.author_url,
          showMetadata: settings.showMetadata,
        }),
      });

      if (!res.ok) throw new Error();

      const updatedDomain = await res.json();
      setDomains(domains.map((d) => (d.id === domainId ? updatedDomain : d)));
      toast({
        title: "Success",
        description: "Settings updated successfully!",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update settings",
        variant: "error",
      });
    }
  };

  const loadDomainSettings = (domain: ImageDomain) => {
    if (domain.oembed) {
      setSettings({
        title: domain.oembed.title || "",
        description: domain.oembed.description || "",
        color: domain.oembed.color || "#ff3379",
        provider_name: domain.oembed.provider_name || "",
        author_name: domain.oembed.author_name || "",
        author_url: domain.oembed.author_url || "",
        showMetadata: domain.oembed.showMetadata ?? true,
      });
    } else {
      setSettings({
        title: "",
        description: "",
        color: "#ff3379",
        provider_name: "",
        author_name: "",
        author_url: "",
        showMetadata: true,
      });
    }
  };

  const filteredImages = images
    .filter((img) =>
      img.original_name.toLowerCase().includes(searchQuery.toLowerCase()),
    )
    .sort((a, b) => {
      switch (sortBy) {
        case "oldest":
          return (
            new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
          );
        case "name":
          return a.original_name.localeCompare(b.original_name);
        default:
          return (
            new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
          );
      }
    });

  const totalFilteredPages = Math.ceil(filteredImages.length / imagesPerPage);
  const currentFilteredImages = filteredImages.slice(
    (currentPage - 1) * imagesPerPage,
    currentPage * imagesPerPage,
  );

  const deleteDomain = async (domain: ImageDomain) => {
    try {
      const res = await fetch(`/api/domains/settings/${domain.id}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        throw new Error();
      }

      setDomains(domains.filter((d) => d.id !== domain.id));
      toast({
        title: "Success",
        description: "Domain deleted successfully",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete domain",
        variant: "error",
      });
    } finally {
      setDeletingDomain(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-primary rounded-full border-t-transparent" />
      </div>
    );
  }

  if (!userPremium?.isPremium || !userPremium?.features?.imageHosting) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-darker rounded-xl p-8 text-center space-y-4">
          <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
            <IconLock className="w-8 h-8 text-primary" />
          </div>
          <h2 className="text-2xl font-bold text-white">Premium Feature</h2>
          <p className="text-white/60">
            Image hosting is available exclusively to our premium users. Upgrade
            your account to unlock this feature and many more!
          </p>
          <div className="pt-4">
            <button
              onClick={() => (window.location.href = "/dashboard/settings")}
              className="px-6 py-2 bg-primary text-white rounded-lg flex items-center justify-center gap-2 mx-auto hover:bg-primary/90 transition-colors"
            >
              <IconCrown size={20} />
              <span>Upgrade to Premium</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Image Host</h1>
        <button
          onClick={() => downloadConfig(domains[0], "sharex")}
          className="px-4 py-2 bg-primary/10 text-primary rounded-lg flex items-center gap-2 hover:bg-primary/20 transition-colors"
        >
          <IconDownload size={20} />
          <span>Download ShareX Config</span>
        </button>
      </div>

      <div className="bg-darker rounded-xl p-6 space-y-6">
        <div>
          <h2 className="text-lg font-semibold mb-2">
            Your Domains ({domains.length}/3)
          </h2>
          <div className="grid gap-4">
            {domains.map((domain) => (
              <div key={domain.id} className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-black/20 rounded-lg">
                  <span className="font-mono text-white/80">
                    {domain.subdomain}.{domain.domain}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => downloadConfig(domain, "sharex")}
                      className="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/60"
                      title="Download ShareX Config"
                    >
                      <IconDownload size={20} />
                    </button>
                    <button
                      onClick={() => {
                        setSelectedDomainId(domain.id);
                        loadDomainSettings(domain);
                      }}
                      className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                    >
                      <IconSettings size={20} className="text-white/60" />
                    </button>
                    <button
                      onClick={() => setDeletingDomain(domain)}
                      className="p-2 hover:bg-white/5 rounded-lg transition-colors text-red-500 hover:text-red-400"
                    >
                      <IconTrash size={20} />
                    </button>
                  </div>
                </div>

                {selectedDomainId === domain.id && (
                  <div className="p-4 bg-black/10 rounded-lg space-y-4">
                    <h4 className="font-medium text-white/80">
                      Embed Settings
                    </h4>
                    <div className="grid gap-4">
                      <div>
                        <label className="text-sm text-white/60">Title</label>
                        <input
                          type="text"
                          value={settings.title}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              title: e.target.value,
                            })
                          }
                          className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 mt-1"
                          placeholder="Embed title"
                        />
                      </div>
                      <div>
                        <label className="text-sm text-white/60">
                          Description
                        </label>
                        <input
                          type="text"
                          value={settings.description}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              description: e.target.value,
                            })
                          }
                          className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 mt-1"
                          placeholder="Embed description"
                        />
                      </div>
                      <div>
                        <label className="text-sm text-white/60">
                          Site Name
                        </label>
                        <input
                          type="text"
                          value={settings.provider_name}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              provider_name: e.target.value,
                            })
                          }
                          className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 mt-1"
                          placeholder="Site name"
                        />
                      </div>
                      <div>
                        <ColorPicker
                          label="Embed Color"
                          value={settings.color}
                          onChange={(color) =>
                            setSettings({ ...settings, color })
                          }
                        />
                      </div>
                      <div>
                        <label className="text-sm text-white/60">
                          Author Name
                        </label>
                        <input
                          type="text"
                          value={settings.author_name}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              author_name: e.target.value,
                            })
                          }
                          className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 mt-1"
                          placeholder="Author name"
                        />
                      </div>
                      <div>
                        <label className="text-sm text-white/60">
                          Author URL
                        </label>
                        <input
                          type="text"
                          value={settings.author_url}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              author_url: e.target.value,
                            })
                          }
                          className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 mt-1"
                          placeholder="https://example.com"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={settings.showMetadata}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              showMetadata: e.target.checked,
                            })
                          }
                          className="rounded border-white/10"
                        />
                        <label className="text-sm text-white/60">
                          Show metadata
                        </label>
                      </div>
                      <button
                        onClick={() => updateSettings(domain.id)}
                        className="w-full px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
                      >
                        Save Settings
                      </button>
                    </div>
                    <div className="flex gap-2 mt-4">
                      <button
                        onClick={() => downloadConfig(domain, "sharex")}
                        className="flex-1 px-4 py-2 bg-black/20 hover:bg-black/30 transition-colors rounded-lg text-sm"
                      >
                        <IconDownload size={16} className="inline-block mr-2" />
                        ShareX Config
                      </button>
                      <button
                        onClick={() => downloadConfig(domain, "ishare")}
                        className="flex-1 px-4 py-2 bg-black/20 hover:bg-black/30 transition-colors rounded-lg text-sm"
                      >
                        <IconDownload size={16} className="inline-block mr-2" />
                        iShare Config
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {domains.length < 3 && (
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-white/80">
              Add New Domain
            </h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={newSubdomain}
                onChange={(e) => {
                  setNewSubdomain(e.target.value);
                  setIsAvailable(null);
                }}
                onBlur={checkAvailability}
                placeholder="subdomain"
                className="bg-black/20 border border-white/10 rounded-lg px-4 py-2 flex-1 font-mono"
              />
              <select
                value={selectedDomain}
                onChange={(e) => setSelectedDomain(e.target.value)}
                className="bg-black/20 border border-white/10 rounded-lg px-4 py-2 font-mono"
              >
                {AVAILABLE_DOMAINS.map((domain) => (
                  <option key={domain} value={domain}>
                    {domain}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center justify-between">
              {isAvailable !== null && (
                <div
                  className={`flex items-center gap-2 ${
                    isAvailable ? "text-green-500" : "text-red-500"
                  }`}
                >
                  {isAvailable ? <IconCheck size={16} /> : <IconX size={16} />}
                  <span className="text-sm">
                    {isAvailable
                      ? "Domain is available!"
                      : "Domain is already taken"}
                  </span>
                </div>
              )}

              {isAvailable && (
                <button
                  onClick={addDomain}
                  disabled={isAdding}
                  className="px-4 py-2 bg-primary text-white rounded-lg flex items-center gap-2 hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {isAdding ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                      <span>Adding...</span>
                    </>
                  ) : (
                    <>
                      <IconCheck size={16} />
                      <span>Add Domain</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="bg-darker rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Your Images</h2>
          <a
            href="#setup-guide"
            className="text-sm text-primary hover:underline"
          >
            View Setup Guide
          </a>
        </div>

        <div className="flex gap-4 items-center flex-col sm:flex-row">
          <div className="relative flex-1">
            <IconSearch
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search images..."
              className="w-full bg-black/20 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm"
            />
          </div>

          <Select
            label=""
            value={sortBy}
            onChange={(value: string) =>
              setSortBy(value as "newest" | "oldest" | "name")
            }
            options={[
              { label: "Newest first", value: "newest" },
              { label: "Oldest first", value: "oldest" },
              { label: "Name", value: "name" },
            ]}
          />
        </div>

        {filteredImages.length === 0 ? (
          <div className="text-center py-12 text-white/60">
            <IconSearch size={48} className="mx-auto mb-3 opacity-40" />
            <p>No images found matching your search.</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {currentFilteredImages.map((image) => (
                <div
                  key={image.id}
                  className="group relative aspect-video bg-black/20 rounded-lg overflow-hidden"
                >
                  <img
                    src={`https://images.emogir.ls/${image.filename}`}
                    alt={image.original_name}
                    className="w-full h-full object-cover"
                  />

                  <div className="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    <a
                      href={`https://images.emogir.ls/${image.filename}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors"
                    >
                      <IconExternalLink size={20} />
                    </a>
                    <button
                      onClick={() => {
                        if (
                          confirm("Are you sure you want to delete this image?")
                        ) {
                          fetch(`/api/uploads/${image.id}`, {
                            method: "DELETE",
                          })
                            .then((res) => {
                              if (res.ok) {
                                setImages(
                                  images.filter((img) => img.id !== image.id),
                                );
                                toast({
                                  title: "Success",
                                  description: "Image deleted successfully",
                                  variant: "success",
                                });
                              } else {
                                throw new Error();
                              }
                            })
                            .catch(() => {
                              toast({
                                title: "Error",
                                description: "Failed to delete image",
                                variant: "error",
                              });
                            });
                        }
                      }}
                      className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors text-red-500"
                    >
                      <IconTrash size={20} />
                    </button>
                  </div>

                  <div className="absolute bottom-0 inset-x-0 p-2 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                    <p className="text-sm truncate">{image.original_name}</p>
                    <p className="text-xs text-white/60">
                      {new Date(image.createdAt).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {totalFilteredPages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-4">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-1 rounded-lg bg-black/20 hover:bg-black/40 disabled:opacity-50 disabled:hover:bg-black/20 transition-colors"
                >
                  <IconChevronLeft size={20} />
                </button>

                <div className="flex items-center gap-1">
                  <input
                    type="text"
                    value={inputPage}
                    onChange={(e) => {
                      const value = e.target.value;
                      if (value === "" || /^\d+$/.test(value)) {
                        setInputPage(value);
                      }
                    }}
                    onBlur={() => {
                      const newPage = Math.min(
                        Math.max(1, parseInt(inputPage) || 1),
                        totalFilteredPages,
                      );
                      setCurrentPage(newPage);
                      setInputPage(newPage.toString());
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        const newPage = Math.min(
                          Math.max(1, parseInt(inputPage) || 1),
                          totalFilteredPages,
                        );
                        setCurrentPage(newPage);
                        setInputPage(newPage.toString());
                        e.currentTarget.blur();
                      }
                    }}
                    className="w-12 text-center bg-black/20 border border-white/10 rounded-lg px-1 py-0.5 text-sm font-mono"
                  />
                  <span className="text-sm text-white/60">
                    / {totalFilteredPages}
                  </span>
                </div>

                <button
                  onClick={() =>
                    setCurrentPage((p) => Math.min(totalFilteredPages, p + 1))
                  }
                  disabled={currentPage === totalFilteredPages}
                  className="p-1 rounded-lg bg-black/20 hover:bg-black/40 disabled:opacity-50 disabled:hover:bg-black/20 transition-colors"
                >
                  <IconChevronRight size={20} />
                </button>
              </div>
            )}
          </>
        )}
      </div>

      <div id="setup-guide" className="bg-darker rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">ShareX Setup Guide</h2>
        <div className="prose prose-invert max-w-none">
          <ol className="list-decimal list-inside space-y-2 text-white/80">
            <li>
              Download and install ShareX from{" "}
              <a
                href="https://getsharex.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                getsharex.com
              </a>
            </li>
            <li>
              Download our ShareX configuration file using the button above
            </li>
            <li>
              Double click the downloaded .sxcu file to import it into ShareX
            </li>
            <li>
              Test the uploader by taking a screenshot or uploading an image
            </li>
            <li>
              Your images will be automatically uploaded using your custom
              domain!
            </li>
          </ol>
        </div>
      </div>

      <DeleteDomainDialog
        isOpen={!!deletingDomain}
        onClose={() => setDeletingDomain(null)}
        onConfirm={() => deletingDomain && deleteDomain(deletingDomain)}
        domain={
          deletingDomain
            ? `${deletingDomain.subdomain}.${deletingDomain.domain}`
            : ""
        }
      />
    </div>
  );
}
