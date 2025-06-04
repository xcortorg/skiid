import { IconX } from "@tabler/icons-react";
import { Button } from "../button";
import { InputGroup } from "../input-group";
import { useState } from "react";
import { CategorySlider } from "../category-slider";
import { motion, AnimatePresence } from "framer-motion";
import { SOCIAL_ICONS, CATEGORIES, IconConfig } from "@/config/icons";
import { cn } from "@/lib/utils";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ColorPicker } from "@/components/ui/appearance/color-picker";

interface LinkModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any) => void;
  initialData: {
    id?: string;
    title: string;
    url: string;
    enabled?: boolean;
    iconUrl?: string;
    backgroundColor?: string | null;
    hoverColor?: string | null;
    borderColor?: string | null;
    primaryTextColor?: string | null;
    secondaryTextColor?: string | null;
    iconColor?: string | null;
    iconBgColor?: string | null;
    iconSize?: string;
    iconBorderRadius?: string;
  } | null;
}

export function LinkModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
}: LinkModalProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>("Social");
  const [selectedPreset, setSelectedPreset] = useState<IconConfig | null>(null);
  const [formData, setFormData] = useState({
    title: initialData?.title || "",
    url: initialData?.url || "",
    backgroundColor: initialData?.backgroundColor || null,
    hoverColor: initialData?.hoverColor || null,
    borderColor: initialData?.borderColor || null,
    primaryTextColor: initialData?.primaryTextColor || null,
    secondaryTextColor: initialData?.secondaryTextColor || null,
    iconColor: initialData?.iconColor || null,
    iconBgColor: initialData?.iconBgColor || null,
    iconSize: initialData?.iconSize || "20px",
    iconBorderRadius: initialData?.iconBorderRadius || "8px",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const fullUrl = selectedPreset?.urlPrefix
      ? `${selectedPreset.urlPrefix}${formData.url}`
      : formData.url;

    onSubmit({
      ...initialData,
      id: initialData?.id,
      title: formData.title || initialData?.title,
      url: fullUrl,
      iconUrl: selectedPreset?.iconUrl || initialData?.iconUrl,
      backgroundColor: formData.backgroundColor,
      hoverColor: formData.hoverColor,
      borderColor: formData.borderColor,
      primaryTextColor: formData.primaryTextColor,
      secondaryTextColor: formData.secondaryTextColor,
      iconColor: formData.iconColor,
      iconBgColor: formData.iconBgColor,
      iconSize: formData.iconSize,
      iconBorderRadius: formData.iconBorderRadius,
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
            onClick={(e) => {
              if (e.target === e.currentTarget) {
                onClose();
              }
            }}
          />
          <div className="fixed inset-0 flex items-center justify-center p-4 z-50 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative overflow-hidden rounded-xl border border-primary/[0.125] w-full max-w-2xl pointer-events-auto"
            >
              <div className="relative border-b border-primary/10 p-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-white/90">
                    {initialData?.id ? "Edit Link" : "Add New Link"}
                  </h2>
                  <button
                    type="button"
                    onClick={onClose}
                    className="text-white/60 hover:text-white transition-colors"
                  >
                    <IconX size={20} />
                  </button>
                </div>
              </div>

              <div className="relative p-6 space-y-6">
                {!initialData && (
                  <>
                    <CategorySlider
                      categories={CATEGORIES}
                      selectedCategory={selectedCategory}
                      onSelect={setSelectedCategory}
                    />
                    <div className="grid grid-cols-3 sm:grid-cols-4 gap-4">
                      {SOCIAL_ICONS.filter(
                        (icon) => icon.category === selectedCategory,
                      ).map((icon) => (
                        <motion.div
                          key={`preset-${icon.id}`}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          onClick={() => setSelectedPreset(icon)}
                          className={`group relative overflow-hidden rounded-lg border transition-colors cursor-pointer ${
                            selectedPreset?.id === icon.id
                              ? "border-primary/20 bg-primary/10"
                              : "border-primary/10 hover:border-primary/20"
                          }`}
                        >
                          <div className="absolute inset-0 bg-[#0A0A0A]" />
                          <div className="absolute top-0 right-0 w-1/2 h-1/2 bg-gradient-to-bl from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                          <div className="relative flex items-center gap-3 p-3">
                            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-primary/10 bg-primary/5">
                              <img
                                src={icon.iconUrl}
                                alt={icon.name}
                                className="w-4 h-4 preset-icon"
                              />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-sm font-medium text-white/90">
                                {icon.name}
                              </p>
                              <p className="truncate text-xs text-white/40">
                                {icon.urlPrefix}
                              </p>
                            </div>
                            {selectedPreset?.id === icon.id && (
                              <div className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary" />
                            )}
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </>
                )}

                <Tabs defaultValue="basic">
                  <TabsList>
                    <TabsTrigger value="basic">Basic</TabsTrigger>
                    <TabsTrigger value="appearance">Appearance</TabsTrigger>
                  </TabsList>

                  <form onSubmit={handleSubmit}>
                    <TabsContent value="basic">
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="space-y-4"
                      >
                        <div>
                          <label className="text-sm font-medium text-white/80">
                            Title
                          </label>
                          <div className="mt-1.5">
                            <InputGroup
                              name="title"
                              value={formData.title}
                              onChange={(value) =>
                                setFormData((prev) => ({
                                  ...prev,
                                  title: value,
                                }))
                              }
                              placeholder="Enter link title"
                            />
                          </div>
                        </div>

                        <div>
                          <label className="text-sm font-medium text-white/80">
                            URL
                          </label>
                          <div className="mt-1.5">
                            <InputGroup
                              name="url"
                              value={formData.url}
                              onChange={(value) =>
                                setFormData((prev) => ({ ...prev, url: value }))
                              }
                              prefix={selectedPreset?.urlPrefix}
                              placeholder={
                                selectedPreset ? "username" : "Enter URL"
                              }
                            />
                          </div>
                        </div>
                      </motion.div>
                    </TabsContent>

                    <TabsContent value="appearance">
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <ColorPicker
                            label="Background"
                            value={formData.backgroundColor}
                            onChange={(color) =>
                              setFormData((prev) => ({
                                ...prev,
                                backgroundColor: color,
                              }))
                            }
                          />
                          <ColorPicker
                            label="Hover"
                            value={formData.hoverColor}
                            onChange={(color) =>
                              setFormData((prev) => ({
                                ...prev,
                                hoverColor: color,
                              }))
                            }
                          />
                          <ColorPicker
                            label="Border"
                            value={formData.borderColor}
                            onChange={(color) =>
                              setFormData((prev) => ({
                                ...prev,
                                borderColor: color,
                              }))
                            }
                          />
                          <ColorPicker
                            label="Text"
                            value={formData.primaryTextColor}
                            onChange={(color) =>
                              setFormData((prev) => ({
                                ...prev,
                                primaryTextColor: color,
                              }))
                            }
                          />
                          <ColorPicker
                            label="Secondary Text"
                            value={formData.secondaryTextColor}
                            onChange={(color) =>
                              setFormData((prev) => ({
                                ...prev,
                                secondaryTextColor: color,
                              }))
                            }
                          />
                          <ColorPicker
                            label="Icon Color"
                            value={formData.iconColor}
                            onChange={(color) =>
                              setFormData((prev) => ({
                                ...prev,
                                iconColor: color,
                              }))
                            }
                          />
                          <ColorPicker
                            label="Icon Background"
                            value={formData.iconBgColor}
                            onChange={(color) =>
                              setFormData((prev) => ({
                                ...prev,
                                iconBgColor: color,
                              }))
                            }
                          />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <InputGroup
                            name="iconSize"
                            label="Icon Size"
                            value={formData.iconSize}
                            onChange={(value) =>
                              setFormData((prev) => ({
                                ...prev,
                                iconSize: value,
                              }))
                            }
                            placeholder="20px"
                          />
                          <InputGroup
                            name="iconBorderRadius"
                            label="Icon Border Radius"
                            value={formData.iconBorderRadius}
                            onChange={(value) =>
                              setFormData((prev) => ({
                                ...prev,
                                iconBorderRadius: value,
                              }))
                            }
                            placeholder="8px"
                          />
                        </div>
                      </div>
                    </TabsContent>

                    <div className="flex justify-end gap-3 pt-4">
                      <Button
                        type="button"
                        text="Cancel"
                        onClick={onClose}
                        className="bg-white/5 hover:bg-white/10 border-white/10"
                      />
                      <Button
                        type="submit"
                        text={initialData?.id ? "Save Changes" : "Add Link"}
                        className="bg-primary hover:bg-primary/90 border-primary/20"
                      />
                    </div>
                  </form>
                </Tabs>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
