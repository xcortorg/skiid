"use client";

import dynamic from "next/dynamic";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { IconPlus, IconPalette } from "@tabler/icons-react";
import { LinkModal } from "@/components/ui/link-components/link-modal";
import type { DragEndEvent } from "@dnd-kit/core";
import { Link } from "@/types/link";
import { DataCard } from "@/components/ui/data-card";
import { useToast } from "@/components/ui/toast-provider";
import { ColorPicker } from "@/components/ui/appearance/color-picker";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const LinkContainer = dynamic(
  () =>
    import("@/components/ui/link-components/link-container").then(
      (mod) => mod.LinkContainer,
    ),
  { ssr: false },
);

export default function LinksPage() {
  const [links, setLinks] = useState<Link[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingLink, setEditingLink] = useState<Link | null>(null);
  const { toast } = useToast();

  const [iconSettings, setIconSettings] = useState({
    backgroundColor: "#000000",
    size: "24px",
    borderRadius: "8px",
    borderColor: "#ffffff",
    glowColor: "#ffffff",
    glowIntensity: "0.5",
  });

  const [linkSettings, setLinkSettings] = useState<{
    backgroundColor: string | null;
    hoverColor: string | null;
    borderColor: string | null;
    gap: string;
    primaryTextColor: string | null;
    secondaryTextColor: string | null;
    hoverTextColor: string | null;
    textSize: string;
    iconSize: string;
    iconColor: string | null;
    iconBgColor: string | null;
    iconBorderRadius: string;
  }>({
    backgroundColor: null,
    hoverColor: null,
    borderColor: null,
    gap: "8px",
    primaryTextColor: null,
    secondaryTextColor: null,
    hoverTextColor: null,
    textSize: "14px",
    iconSize: "20px",
    iconColor: null,
    iconBgColor: null,
    iconBorderRadius: "8px",
  });

  useEffect(() => {
    fetchLinks();
    fetchIconSettings();
  }, []);

  const fetchLinks = async () => {
    try {
      const response = await fetch("/api/links");
      const data = await response.json();
      setLinks(data);
    } catch (error) {
      console.error("Failed to fetch links:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchIconSettings = async () => {
    try {
      const response = await fetch("/api/settings/icon");

      if (!response.ok) {
        throw new Error("Failed to fetch icon settings");
      }

      const data = await response.json();

      if (!data) {
        throw new Error("No data received");
      }

      setIconSettings((prev) => ({
        ...prev,
        ...data,
      }));
    } catch (error) {
      console.error("Failed to fetch icon settings:", error);
      toast({
        title: "Error",
        description: "Failed to load icon settings",
        variant: "error",
      });
    }
  };

  const handleIconSettingsSubmit = async (
    e: React.FormEvent<HTMLFormElement>,
  ) => {
    e.preventDefault();
    try {
      const response = await fetch("/api/settings/icon", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(iconSettings),
      });

      const data = await response.json();

      if (!response.ok) {
        if (data.errors) {
          data.errors.forEach((error: any) => {
            toast({
              title: "Error",
              description: `${error.message} [${error.code}]`,
              variant: "error",
            });
          });
          return;
        }
        throw new Error();
      }

      toast({
        title: "Success",
        description: "Icon settings updated",
        variant: "success",
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to update icon settings",
        variant: "error",
      });
    }
  };

  const handleLinkSettingsSubmit = async (
    e: React.FormEvent<HTMLFormElement>,
  ) => {
    e.preventDefault();
    try {
      const response = await fetch("/api/settings/links", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(linkSettings),
      });

      if (!response.ok) throw new Error();
      toast({
        title: "Success",
        description: "Link settings updated",
        variant: "success",
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to update link settings",
        variant: "error",
      });
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = links.findIndex((item) => item.id === active.id);
      const newIndex = links.findIndex((item) => item.id === over.id);

      const newItems = [...links];
      const [removed] = newItems.splice(oldIndex, 1);
      newItems.splice(newIndex, 0, removed);

      setLinks(newItems);

      try {
        await fetch("/api/links", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            positions: newItems.map((item, index) => ({
              id: item.id,
              position: index,
            })),
          }),
        });
      } catch (error) {
        console.error("Failed to update positions:", error);
        fetchLinks();
      }
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/links?id=${id}`, { method: "DELETE" });
      setLinks(links.filter((link) => link.id !== id));
    } catch (error) {
      console.error("Failed to delete link:", error);
    }
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    try {
      await fetch("/api/links", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, enabled }),
      });
      setLinks(
        links.map((link) => (link.id === id ? { ...link, enabled } : link)),
      );
    } catch (error) {
      console.error("Failed to toggle link:", error);
    }
  };

  const handleEdit = (link: Link) => {
    setEditingLink(link);
    setIsModalOpen(true);
  };

  const handleSubmit = async (data: any) => {
    try {
      const response = await fetch("/api/links", {
        method: data.id ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!response.ok) throw new Error();

      await fetchLinks();
      setIsModalOpen(false);
      setEditingLink(null);
      toast({
        title: "Success",
        description: data.id ? "Link updated" : "Link added",
        variant: "success",
      });
    } catch {
      toast({
        title: "Error",
        description: data.id ? "Failed to update link" : "Failed to add link",
        variant: "error",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Manage Links</h1>
        <Button
          text="Add Link"
          icon={IconPlus}
          onClick={() => setIsModalOpen(true)}
        />
      </div>

      <Tabs defaultValue="icons">
        <TabsList>
          <TabsTrigger value="icons">Icon Settings</TabsTrigger>
          <TabsTrigger value="links">Link Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="icons">
          <DataCard title="Icon Settings" icon={IconPalette}>
            <form onSubmit={handleIconSettingsSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ColorPicker
                  label="Background Color"
                  value={iconSettings.backgroundColor}
                  onChange={(color) =>
                    setIconSettings((prev) => ({
                      ...prev,
                      backgroundColor: color || "#000000",
                    }))
                  }
                />

                <div>
                  <label className="text-sm font-medium text-white/80">
                    Size
                  </label>
                  <input
                    type="text"
                    value={iconSettings.size}
                    onChange={(e) =>
                      setIconSettings((prev) => ({
                        ...prev,
                        size: e.target.value,
                      }))
                    }
                    placeholder="24px"
                    className="mt-1.5 w-full bg-primary/5 border border-primary/10 rounded px-3 py-2"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium text-white/80">
                    Border Radius
                  </label>
                  <input
                    type="text"
                    value={iconSettings.borderRadius}
                    onChange={(e) =>
                      setIconSettings((prev) => ({
                        ...prev,
                        borderRadius: e.target.value,
                      }))
                    }
                    placeholder="8px"
                    className="mt-1.5 w-full bg-primary/5 border border-primary/10 rounded px-3 py-2"
                  />
                </div>

                <ColorPicker
                  label="Border Color"
                  value={iconSettings.borderColor}
                  onChange={(color) =>
                    setIconSettings((prev) => ({
                      ...prev,
                      borderColor: color || "#000000",
                    }))
                  }
                />

                <ColorPicker
                  label="Glow Color"
                  value={iconSettings.glowColor}
                  onChange={(color) =>
                    setIconSettings((prev) => ({
                      ...prev,
                      glowColor: color || "#000000",
                    }))
                  }
                />

                <div>
                  <label className="text-sm font-medium text-white/80">
                    Glow Intensity
                  </label>
                  <input
                    type="text"
                    value={iconSettings.glowIntensity}
                    onChange={(e) =>
                      setIconSettings((prev) => ({
                        ...prev,
                        glowIntensity: e.target.value,
                      }))
                    }
                    placeholder="0.5"
                    className="mt-1.5 w-full bg-primary/5 border border-primary/10 rounded px-3 py-2"
                  />
                </div>
              </div>

              <Button
                type="submit"
                text="Save Icon Settings"
                className="w-full md:w-auto"
              />
            </form>
          </DataCard>
        </TabsContent>

        <TabsContent value="links">
          <DataCard title="Link Settings" icon={IconPalette}>
            <form onSubmit={handleLinkSettingsSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ColorPicker
                  label="Background Color"
                  value={linkSettings.backgroundColor || "#000000"}
                  onChange={(color) =>
                    setLinkSettings((prev) => ({
                      ...prev,
                      backgroundColor: color,
                    }))
                  }
                />

                <ColorPicker
                  label="Hover Color"
                  value={linkSettings.hoverColor || "#000000"}
                  onChange={(color) =>
                    setLinkSettings((prev) => ({ ...prev, hoverColor: color }))
                  }
                />

                <ColorPicker
                  label="Border Color"
                  value={linkSettings.borderColor || "#000000"}
                  onChange={(color) =>
                    setLinkSettings((prev) => ({ ...prev, borderColor: color }))
                  }
                />

                <div>
                  <label className="text-sm font-medium text-white/80">
                    Gap
                  </label>
                  <input
                    type="text"
                    value={linkSettings.gap}
                    onChange={(e) =>
                      setLinkSettings((prev) => ({
                        ...prev,
                        gap: e.target.value,
                      }))
                    }
                    placeholder="8px"
                    className="mt-1.5 w-full bg-primary/5 border border-primary/10 rounded px-3 py-2"
                  />
                </div>

                <ColorPicker
                  label="Primary Text Color"
                  value={linkSettings.primaryTextColor || "#000000"}
                  onChange={(color) =>
                    setLinkSettings((prev) => ({
                      ...prev,
                      primaryTextColor: color,
                    }))
                  }
                />

                <ColorPicker
                  label="Secondary Text Color"
                  value={linkSettings.secondaryTextColor || "#000000"}
                  onChange={(color) =>
                    setLinkSettings((prev) => ({
                      ...prev,
                      secondaryTextColor: color,
                    }))
                  }
                />

                <ColorPicker
                  label="Hover Text Color"
                  value={linkSettings.hoverTextColor || "#000000"}
                  onChange={(color) =>
                    setLinkSettings((prev) => ({
                      ...prev,
                      hoverTextColor: color,
                    }))
                  }
                />

                <div>
                  <label className="text-sm font-medium text-white/80">
                    Text Size
                  </label>
                  <input
                    type="text"
                    value={linkSettings.textSize}
                    onChange={(e) =>
                      setLinkSettings((prev) => ({
                        ...prev,
                        textSize: e.target.value,
                      }))
                    }
                    placeholder="14px"
                    className="mt-1.5 w-full bg-primary/5 border border-primary/10 rounded px-3 py-2"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium text-white/80">
                    Icon Size
                  </label>
                  <input
                    type="text"
                    value={linkSettings.iconSize}
                    onChange={(e) =>
                      setLinkSettings((prev) => ({
                        ...prev,
                        iconSize: e.target.value,
                      }))
                    }
                    placeholder="20px"
                    className="mt-1.5 w-full bg-primary/5 border border-primary/10 rounded px-3 py-2"
                  />
                </div>

                <ColorPicker
                  label="Icon Color"
                  value={linkSettings.iconColor || "#000000"}
                  onChange={(color) =>
                    setLinkSettings((prev) => ({ ...prev, iconColor: color }))
                  }
                />

                <ColorPicker
                  label="Icon Background Color"
                  value={linkSettings.iconBgColor || "#000000"}
                  onChange={(color) =>
                    setLinkSettings((prev) => ({ ...prev, iconBgColor: color }))
                  }
                />

                <div>
                  <label className="text-sm font-medium text-white/80">
                    Icon Border Radius
                  </label>
                  <input
                    type="text"
                    value={linkSettings.iconBorderRadius}
                    onChange={(e) =>
                      setLinkSettings((prev) => ({
                        ...prev,
                        iconBorderRadius: e.target.value,
                      }))
                    }
                    placeholder="8px"
                    className="mt-1.5 w-full bg-primary/5 border border-primary/10 rounded px-3 py-2"
                  />
                </div>
              </div>

              <Button
                type="submit"
                text="Save Link Settings"
                className="w-full md:w-auto"
              />
            </form>
          </DataCard>
        </TabsContent>
      </Tabs>

      <LinkContainer
        links={links}
        onDragEnd={handleDragEnd}
        onDelete={handleDelete}
        onToggle={handleToggle}
        onEdit={handleEdit}
      />

      <LinkModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingLink(null);
        }}
        onSubmit={handleSubmit}
        initialData={editingLink}
      />
    </div>
  );
}
