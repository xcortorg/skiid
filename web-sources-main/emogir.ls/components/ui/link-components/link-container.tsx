import {
  DndContext,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
} from "@dnd-kit/core";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { IconLink, IconEdit } from "@tabler/icons-react";
import { DataCard } from "../data-card";
import { LinkItem } from "./link-item";
import { Link } from "@/types/link";

interface LinkContainerProps {
  links: Link[];
  onDragEnd: (event: DragEndEvent) => void;
  onDelete: (id: string) => Promise<void>;
  onToggle: (id: string, enabled: boolean) => Promise<void>;
  onEdit: (link: Link) => void;
}

export function LinkContainer({
  links,
  onDragEnd,
  onDelete,
  onToggle,
  onEdit,
}: LinkContainerProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 1,
        delay: 0,
        tolerance: 0,
      },
    }),
  );

  return (
    <DataCard
      title="Your Links"
      icon={IconLink}
      className="flex-1 w-full overflow-hidden"
    >
      <DndContext
        sensors={sensors}
        onDragEnd={onDragEnd}
        collisionDetection={closestCenter}
        modifiers={[restrictToVerticalAxis]}
      >
        <SortableContext items={links} strategy={verticalListSortingStrategy}>
          <div className="space-y-3 overflow-x-hidden w-full">
            {links.map((link) => (
              <div key={link.id} className="w-full flex items-center gap-4">
                <div className="flex-1">
                  <LinkItem {...link} onDelete={onDelete} onToggle={onToggle} />
                </div>
                <button
                  onClick={() => onEdit(link)}
                  className="p-2 hover:bg-primary/10 rounded-lg transition-colors"
                >
                  <IconEdit size={18} className="text-primary/60" />
                </button>
              </div>
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </DataCard>
  );
}
