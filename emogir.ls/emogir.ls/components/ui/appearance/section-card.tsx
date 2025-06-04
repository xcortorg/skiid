import { IconCaretDown, IconProps } from "@tabler/icons-react";
import { DataCard } from "../data-card";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface SectionCardProps {
  title: string;
  description?: string;
  icon: React.ComponentType<IconProps>;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export function SectionCard({
  title,
  description,
  icon: Icon,
  defaultOpen = false,
  children,
}: SectionCardProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="relative">
      <DataCard title={title} icon={Icon}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="absolute top-4 right-4 p-2 hover:bg-primary/5 rounded-lg transition-colors"
        >
          <IconCaretDown
            size={16}
            className={`text-white/60 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
          />
        </button>

        {description && (
          <p className="text-sm text-white/60 mb-4">{description}</p>
        )}

        <AnimatePresence initial={false}>
          {isOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="pt-4">{children}</div>
            </motion.div>
          )}
        </AnimatePresence>
      </DataCard>
    </div>
  );
}
