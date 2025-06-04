import { IconX } from "@tabler/icons-react";
import { Button } from "../button";

interface LinkEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any) => void;
  initialData?: {
    id?: number;
    title: string;
    url: string;
  };
}

export function LinkEditModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
}: LinkEditModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="relative rounded-lg border border-primary/[0.125] bg-primary/5 bg-gradient-to-br from-primary/[0.01] to-primary/[0.03] w-full max-w-md p-6">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-white/60 hover:text-white"
        >
          <IconX size={20} />
        </button>

        <h2 className="text-xl font-bold mb-4">
          {initialData?.id ? "Edit Link" : "Add New Link"}
        </h2>

        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit(Object.fromEntries(new FormData(e.currentTarget)));
          }}
        >
          <div>
            <label className="text-sm font-medium opacity-80">Title</label>
            <input
              name="title"
              type="text"
              defaultValue={initialData?.title}
              className="mt-1 w-full bg-black/40 border border-primary/10 rounded-lg p-2 text-white focus:outline-none focus:border-primary/30"
              placeholder="Link Title"
            />
          </div>

          <div>
            <label className="text-sm font-medium opacity-80">URL</label>
            <input
              name="url"
              type="url"
              defaultValue={initialData?.url}
              className="mt-1 w-full bg-black/40 border border-primary/10 rounded-lg p-2 text-white focus:outline-none focus:border-primary/30"
              placeholder="https://example.com"
            />
          </div>

          <div className="flex justify-end gap-2 mt-6">
            <Button text="Cancel" onClick={onClose} className="bg-primary/10" />
            <Button
              text={initialData?.id ? "Save Changes" : "Add Link"}
              type="submit"
            />
          </div>
        </form>
      </div>
    </div>
  );
}
