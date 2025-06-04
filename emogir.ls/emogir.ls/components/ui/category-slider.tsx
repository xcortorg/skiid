"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";

interface CategorySliderProps {
  categories: string[];
  selectedCategory: string;
  onSelect: (category: string) => void;
}

function CategoryButton({
  category,
  isSelected,
  ...props
}: {
  category: string;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      className={`px-4 py-2 rounded-lg text-xs font-medium transition-all border whitespace-nowrap ${
        isSelected
          ? "bg-primary text-white border-primary/20"
          : "bg-primary/5 text-white/70 border-primary/10 hover:bg-primary/10 hover:text-white"
      }`}
      {...props}
    >
      {category}
    </motion.button>
  );
}

export function CategorySlider({
  categories,
  selectedCategory,
  onSelect,
}: CategorySliderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const checkScroll = () => {
    if (!containerRef.current) return;
    const { scrollLeft, scrollWidth, clientWidth } = containerRef.current;
    setCanScrollLeft(scrollLeft > 0);
    setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 10);
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    checkScroll();
    container.addEventListener("scroll", checkScroll);
    window.addEventListener("resize", checkScroll);

    return () => {
      container.removeEventListener("scroll", checkScroll);
      window.removeEventListener("resize", checkScroll);
    };
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setStartX(e.pageX - (containerRef.current?.offsetLeft || 0));
    setScrollLeft(containerRef.current?.scrollLeft || 0);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    e.preventDefault();
    const x = e.pageX - (containerRef.current?.offsetLeft || 0);
    const walk = (x - startX) * 0.7;
    if (containerRef.current) {
      containerRef.current.scrollLeft = scrollLeft - walk;
      checkScroll();
    }
  };

  const scrollBy = (direction: "left" | "right") => {
    if (!containerRef.current) return;
    const scrollAmount = 200;
    containerRef.current.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    });
  };

  return (
    <div className="relative rounded-xl border border-primary/[0.125] bg-gradient-to-tr from-darker/80 to-darker/60 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-primary/[0.02] to-transparent"></div>

      <AnimatePresence mode="wait">
        {canScrollLeft && (
          <motion.button
            key="left-button"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={() => scrollBy("left")}
            className="absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-darker to-transparent z-10 flex items-center justify-start hover:from-primary/5 transition-all group rounded-l-lg"
          >
            <IconChevronLeft
              size={18}
              className="text-white/40 group-hover:text-white ml-2 transition-colors"
            />
          </motion.button>
        )}

        {canScrollRight && (
          <motion.button
            key="right-button"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={() => scrollBy("right")}
            className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-darker to-transparent z-10 flex items-center justify-end hover:from-primary/5 transition-all group rounded-r-lg"
          >
            <IconChevronRight
              size={18}
              className="text-white/40 group-hover:text-white mr-2 transition-colors"
            />
          </motion.button>
        )}
      </AnimatePresence>

      <div className="relative p-1.5">
        <div
          ref={containerRef}
          className="overflow-x-scroll no-scrollbar"
          style={{
            cursor: isDragging ? "grabbing" : "grab",
            msOverflowStyle: "none",
            scrollbarWidth: "none",
          }}
          onMouseDown={handleMouseDown}
          onMouseLeave={() => setIsDragging(false)}
          onMouseUp={() => setIsDragging(false)}
          onMouseMove={handleMouseMove}
        >
          <div className="flex items-center gap-1.5 px-3 min-w-max">
            {categories.map((category, index) => (
              <CategoryButton
                key={`${category}-${index}`}
                category={category}
                isSelected={selectedCategory === category}
                onClick={() => onSelect(category)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
