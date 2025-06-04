import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 space-y-4 text-center">
      <h1 className="text-4xl font-bold">Profile Not Found</h1>
      <p className="text-zinc-400">
        This profile doesn&apos;t exist or has been deleted.
      </p>
      <Button>
        <Link href="/">Return Home</Link>
      </Button>
    </div>
  );
}
