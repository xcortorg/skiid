"use client";

import { useState } from "react";
import { IconX } from "@tabler/icons-react";
import { Button } from "./button";
import { AnimatePresence, motion } from "framer-motion";
import { CategorySlider } from "./category-slider";
import { PRESET_LINKS, CATEGORIES, PresetLink } from "../data/preset-links";
import { InputGroup } from "./input-group";

interface LinkModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any) => void;
  initialData?: any;
}

export function LinkModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
}: LinkModalProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>("Social");
  const [selectedPreset, setSelectedPreset] = useState<PresetLink | null>(null);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-darker border border-primary/10 rounded-lg w-full max-w-md p-6 relative">
            <button
              onClick={onClose}
              className="absolute right-4 top-4 text-white/60 hover:text-white"
            >
              <IconX size={20} />
            </button>

            <h2 className="text-xl font-bold mb-4">Add New Link</h2>

            <div className="p-6 space-y-6">
              {!initialData && (
                <>
                  <CategorySlider
                    categories={CATEGORIES}
                    selectedCategory={selectedCategory}
                    onSelect={setSelectedCategory}
                  />
                  <motion.div
                    className="grid grid-cols-2 sm:grid-cols-3 gap-2"
                    initial="hidden"
                    animate="show"
                    variants={{
                      hidden: {},
                      show: {
                        transition: { staggerChildren: 0.02 },
                      },
                    }}
                  >
                    {PRESET_LINKS.filter(
                      (preset) => preset.category === selectedCategory,
                    ).map((preset: PresetLink) => (
                      <motion.div
                        key={`preset-${preset.id}`}
                        variants={{
                          hidden: { opacity: 0, y: 10 },
                          show: { opacity: 1, y: 0 },
                        }}
                        onClick={() => setSelectedPreset(preset)}
                        className={`group relative flex items-center gap-3 p-3 rounded-lg border transition-all cursor-pointer ${
                          selectedPreset?.id === preset.id
                            ? "border-primary/20 bg-primary/10"
                            : "border-primary/10 hover:border-primary/20 bg-primary/5"
                        }`}
                      >
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-primary/10 bg-primary/5">
                          <preset.icon size={16} className="text-primary" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-white/90">
                            {preset.name}
                          </p>
                          <p className="truncate text-xs text-white/40">
                            {preset.urlPrefix}
                          </p>
                        </div>
                        {selectedPreset?.id === preset.id && (
                          <div className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary" />
                        )}
                      </motion.div>
                    ))}
                  </motion.div>
                </>
              )}

              <form
                className="space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  onSubmit(Object.fromEntries(new FormData(e.currentTarget)));
                }}
              >
                <div>
                  <label className="text-sm font-medium text-white/80">
                    Title
                  </label>
                  <div className="mt-1.5">
                    <InputGroup
                      name="title"
                      defaultValue={initialData?.title}
                      placeholder="Enter title"
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
                      prefix={selectedPreset?.urlPrefix}
                      defaultValue={initialData?.url}
                      placeholder={
                        selectedPreset ? "username" : "https://example.com"
                      }
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2 mt-6">
                  <Button
                    text="Cancel"
                    onClick={onClose}
                    className="bg-primary/10"
                  />
                  <Button
                    text={initialData?.id ? "Save Changes" : "Add Link"}
                    type="submit"
                  />
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </AnimatePresence>
  );
}
